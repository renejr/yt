#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servidor da API REST - YouTube Downloader
Implementação do servidor Flask com rotas e gerenciamento

Versão: 1.0
Data: 2024
"""

import threading
import uuid
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from flask import Flask, request
from flask_cors import CORS

# Imports locais
from api_config import APIConfig
from api_utils import APIResponse, APILogger, log_api_request, handle_api_errors
from api_models import (
    health_schema, download_request_schema, video_info_request_schema,
    pagination_schema, validate_request_data
)

class APIServer:
    """Classe principal do servidor Flask da API"""
    
    def __init__(self, config_manager=None, download_manager=None, 
                 history_manager=None, log_manager=None):
        self.config_manager = config_manager
        self.download_manager = download_manager
        self.history_manager = history_manager
        self.log_manager = log_manager

        if self.download_manager and not self.download_manager.download_directory:
            self.download_manager.set_download_directory("downloads")
        
        self.active_downloads = {}
        self.download_lock = threading.Lock()
        
        self.app = Flask(__name__)
        self.app.config['JSON_SORT_KEYS'] = False
        self.app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
        
        cors_config = APIConfig.get_cors_config()
        CORS(self.app, **cors_config)
        
        self.api_logger = APILogger(self.log_manager)
        self.start_time = datetime.now(timezone.utc)

        # Estados internos de execução do servidor
        # _server_thread: thread que executa o Flask quando iniciado pela aplicação
        # _is_running: indica se o servidor está em execução
        # _started_here: indica se o servidor foi iniciado por esta instância (vs. já estar rodando externamente)
        # _shutdown_token: token interno para proteger a rota de desligamento
        # _host/_port/_debug: parâmetros efetivos usados para subir o servidor
        self._server_thread = None
        self._is_running = False
        self._started_here = False
        self._shutdown_token = None
        self._host = None
        self._port = None
        self._debug = None
        
        self._register_routes()
        self._register_error_handlers()

    # ----------------------------
    # Métodos auxiliares conectados ao DownloadManager e HistoryManager
    # ----------------------------

    def _get_video_info_from_url(self, url: str) -> dict:
        """Obtém informações do vídeo via DownloadManager.
        Realiza a extração de metadados e resoluções disponíveis antes do download.
        Levanta exceção em caso de falha para ser tratada pelo decorador handle_api_errors.
        """
        success, info, resolutions = self.download_manager.extract_video_info(url)
        if not success:
            raise ValueError(str(info))
        info = info or {}
        return {
            "title": info.get("title"),
            "duration": info.get("duration"),
            "uploader": info.get("uploader"),
            "upload_date": info.get("upload_date"),
            "view_count": info.get("view_count"),
            "like_count": info.get("like_count"),
            "description": info.get("description"),
            "thumbnail": info.get("thumbnail") or info.get("thumbnail_url"),
            "url": info.get("webpage_url") or url,
            "resolutions": resolutions or []
        }

    def _progress_update_factory(self, download_id: str):
        """Cria uma função de callback de progresso vinculada a um download_id.
        Esta closure é chamada pelo yt-dlp via DownloadManager e atualiza o
        dicionário self.active_downloads com informações de progresso, garantindo
        thread-safety via self.download_lock.
        """
        def _progress_callback(d: dict):
            try:
                stage = 'downloading'
                status = d.get('status')
                if status == 'finished' or status == 'processing':
                    stage = 'postprocessing'
                elif status == 'downloading':
                    stage = 'downloading'

                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes') or 0
                percent = None
                if total_bytes:
                    try:
                        percent = round((downloaded * 100.0) / total_bytes, 2)
                    except Exception:
                        percent = None

                with self.download_lock:
                    entry = self.active_downloads.get(download_id) or {}
                    entry.update({
                        'status': 'downloading' if stage == 'downloading' else entry.get('status', 'queued'),
                        'progress': {
                            'percent': percent if percent is not None else entry.get('progress', {}).get('percent', 0),
                            'downloaded_bytes': downloaded or entry.get('progress', {}).get('downloaded_bytes'),
                            'total_bytes': total_bytes or entry.get('progress', {}).get('total_bytes'),
                            'speed': d.get('speed') or entry.get('progress', {}).get('speed'),
                            'eta': d.get('eta') or entry.get('progress', {}).get('eta'),
                            'stage': stage,
                        },
                        'filename': d.get('filename') or entry.get('filename'),
                        'updated_at': datetime.utcnow().isoformat() + "Z",
                    })
                    self.active_downloads[download_id] = entry
            except Exception:
                # Evitar interrupções no fluxo por erro de callback
                pass
        return _progress_callback

    def _on_download_success(self, download_id: str) -> None:
        """Callback de término com sucesso: marca o download como concluído (100%)."""
        with self.download_lock:
            entry = self.active_downloads.get(download_id)
            if entry is not None:
                progress = entry.get('progress', {})
                if progress.get('percent', 0) < 100:
                    progress['percent'] = 100
                progress['stage'] = 'completed'
                entry['progress'] = progress
                entry['status'] = 'completed'
                entry['updated_at'] = datetime.utcnow().isoformat() + "Z"
                self.active_downloads[download_id] = entry

    def _on_download_error(self, download_id: str, err_msg: str) -> None:
        """Callback de erro: marca o download como erro e registra a mensagem."""
        with self.download_lock:
            entry = self.active_downloads.get(download_id) or {}
            entry.update({
                'status': 'error',
                'error_message': err_msg,
                'updated_at': datetime.utcnow().isoformat() + "Z",
            })
            self.active_downloads[download_id] = entry

    def _start_download_process(self, data: dict) -> dict:
        """Inicia o processo de download usando DownloadManager.
        - Gera um download_id para referência externa (não utilizado pelo DownloadManager).
        - Extrai previamente as informações do vídeo (obrigatório para o DownloadManager).
        - Ajusta diretório de saída caso fornecido.
        - Inicia o download com os callbacks de sucesso/erro e progresso por download_id.
        - Persiste entrada inicial no histórico (status queued).
        Retorna o payload de criação para o cliente.
        """
        download_id = f"dl_{uuid.uuid4().hex[:12]}"

        url = (data.get("url") or "").strip()
        if not url:
            raise ValueError("URL inválida ou ausente")

        # Resolver parâmetros de download (antes de inicializar estado)
        selected_resolution = data.get("resolution", "best")
        audio_only = bool(data.get("audio_only", False))
        audio_quality = data.get("audio_quality", "best")
        subtitle_lang = data.get("subtitle_lang")
        embed_subtitle = bool(data.get("embed_subtitle", False))

        # Definir diretório de saída se fornecido
        output_path = data.get("output_path")
        if output_path and self.download_manager:
            try:
                self.download_manager.set_download_directory(output_path)
            except Exception as e:
                if self.log_manager:
                    self.log_manager.log_warning(f"Falha ao definir diretório de download: {e}")

        # Extrair informações do vídeo antes de iniciar o download
        success, info, _resolutions = self.download_manager.extract_video_info(url)
        if not success:
            raise ValueError(str(info))

        # Inicializar registro em memória para status/progresso
        now_iso = datetime.utcnow().isoformat() + "Z"
        with self.download_lock:
            self.active_downloads[download_id] = {
                'download_id': download_id,
                'url': url,
                'status': 'queued',
                'type': 'audio' if audio_only else 'video',
                'format': 'mp3' if audio_only else 'mp4',
                'resolution': None if audio_only else selected_resolution,
                'audio_quality': audio_quality if audio_only else None,
                'created_at': now_iso,
                'updated_at': now_iso,
                'progress': {
                    'percent': 0,
                    'stage': 'queued'
                },
                'filename': None
            }

        # Preparar callbacks amarrados ao download_id
        progress_cb = self._progress_update_factory(download_id)

        def _on_success():
            if self.log_manager:
                self.log_manager.log_info(f"Download concluído com sucesso: {url}")
            self._on_download_success(download_id)

        def _on_error(err_msg):
            if self.log_manager:
                self.log_manager.log_error(None, f"Erro no download: {err_msg}")
            self._on_download_error(download_id, err_msg)

        # Injetar callbacks no DownloadManager
        self.download_manager.progress_callback = progress_cb
        self.download_manager.postprocessor_callback = progress_cb

        # Iniciar o download respeitando a assinatura do DownloadManager
        ok, msg = self.download_manager.start_download(
            url=url,
            selected_resolution=selected_resolution,
            success_callback=_on_success,
            error_callback=_on_error,
            audio_only=audio_only,
            audio_quality=audio_quality,
            subtitle_lang=subtitle_lang,
            embed_subtitle=embed_subtitle,
        )
        if not ok:
            # Marcar erro no mapa de downloads
            self._on_download_error(download_id, msg)
            raise ValueError(msg)

        # Registrar no histórico (status inicial queued)
        if self.history_manager and isinstance(info, dict):
            try:
                _ = self.history_manager.add_download_to_history(
                    title=info.get("title"),
                    url=url,
                    resolution=(selected_resolution if not audio_only else f"audio-{audio_quality}"),
                    status="queued",
                    download_path=getattr(self.download_manager, "download_directory", None),
                    file_size=None,
                    thumbnail_url=info.get("thumbnail") or info.get("thumbnail_url"),
                    uploader=info.get("uploader"),
                    view_count=info.get("view_count", 0),
                    like_count=info.get("like_count", 0),
                    description=info.get("description", ""),
                    subtitle_lang=subtitle_lang,
                    subtitle_path=None,
                    is_embedded=embed_subtitle,
                )
            except Exception as _hist_err:
                if self.log_manager:
                    self.log_manager.log_warning(f"Falha ao registrar histórico inicial: {_hist_err}")

        return {
            "download_id": download_id,
            "url": url,
            "status": "queued",
            "created_at": now_iso,
            "format": "mp3" if audio_only else "mp4",
            "resolution": selected_resolution,
        }

    # ----------------------------
    # Helpers de consulta de status/progresso/histórico
    # ----------------------------

    def _get_download_status(self, download_id: str) -> dict:
        """Recupera o status consolidado de um download a partir de self.active_downloads.
        Retorna None caso o ID não exista (a rota corresponde com 404).
        """
        try:
            with self.download_lock:
                entry = self.active_downloads.get(download_id)
            if not entry:
                return None

            progress = entry.get('progress', {}) or {}
            data = {
                'download_id': entry.get('download_id') or download_id,
                'status': entry.get('status') or 'queued',
                'url': entry.get('url'),
                'type': entry.get('type'),
                'format': entry.get('format'),
                'resolution': entry.get('resolution'),
                'progress': progress.get('percent'),
                'download_speed': progress.get('speed'),
                'eta': progress.get('eta'),
                'stage': progress.get('stage'),
                'filename': entry.get('filename'),
                'error_message': entry.get('error_message'),
                'created_at': entry.get('created_at'),
                'updated_at': entry.get('updated_at'),
            }
            return data
        except Exception:
            return None

    def _get_download_progress(self, download_id: str) -> dict:
        """Recupera o progresso detalhado de um download (percentual, bytes, velocidade, ETA).
        Retorna None caso o ID não exista (a rota corresponde com 404).
        """
        try:
            with self.download_lock:
                entry = self.active_downloads.get(download_id)
            if not entry:
                return None

            progress = entry.get('progress', {}) or {}
            data = {
                'download_id': entry.get('download_id') or download_id,
                'status': entry.get('status') or 'queued',
                'progress': {
                    'percent': progress.get('percent'),
                    'downloaded_bytes': progress.get('downloaded_bytes'),
                    'total_bytes': progress.get('total_bytes'),
                    'speed': progress.get('speed'),
                    'eta': progress.get('eta'),
                    'stage': progress.get('stage'),
                },
                'filename': entry.get('filename'),
                'updated_at': entry.get('updated_at'),
            }
            return data
        except Exception:
            return None

    def _get_paginated_history(self, params: dict) -> dict:
        """Obtém o histórico paginado do HistoryManager, adaptando a assinatura disponível.
        Aceita page, per_page e opcionalmente status e search. Normaliza o payload de resposta.
        """
        page = int(params.get('page', 1))
        per_page = int(params.get('per_page', 20))
        status = params.get('status')
        search = params.get('search')

        # Valores padrão de retorno
        result = {
            'downloads': [],
            'total': 0,
            'page': page,
            'per_page': per_page,
            'pages': 0,
        }
        hm = getattr(self, 'history_manager', None)
        if not hm:
            return result

        try:
            # Tentativa 1: método unificado com filtros opcionais
            if hasattr(hm, 'get_downloads_paginated'):
                try:
                    data = hm.get_downloads_paginated(page=page, per_page=per_page, status=status, search=search)
                except TypeError:
                    # Assinaturas alternativas: sem status/search
                    data = hm.get_downloads_paginated(page=page, per_page=per_page)

                if isinstance(data, dict):
                    # Já está normalizado
                    # Garantir chaves
                    result.update({
                        'downloads': data.get('downloads', []) or data.get('items', []) or [],
                        'total': int(data.get('total', 0) or len(data.get('downloads', []) or data.get('items', []) or [])),
                        'page': int(data.get('page', page)),
                        'per_page': int(data.get('per_page', per_page)),
                        'pages': int(data.get('pages', 0)),
                    })
                    # Se pages não veio, calcular
                    if result['pages'] == 0 and result['per_page'] > 0:
                        result['pages'] = (result['total'] + result['per_page'] - 1) // result['per_page']
                    return result
                elif isinstance(data, tuple) and len(data) == 2:
                    items, total = data
                    result['downloads'] = list(items) if items else []
                    result['total'] = int(total or 0)
                    if result['per_page'] > 0:
                        result['pages'] = (result['total'] + result['per_page'] - 1) // result['per_page']
                    return result

            # Tentativa 2: busca por termo
            if search and hasattr(hm, 'search_downloads'):
                data = hm.search_downloads(search, page=page, per_page=per_page)
                if isinstance(data, dict):
                    result.update({
                        'downloads': data.get('downloads', []) or data.get('items', []) or [],
                        'total': int(data.get('total', 0) or 0),
                        'page': int(data.get('page', page)),
                        'per_page': int(data.get('per_page', per_page)),
                        'pages': int(data.get('pages', 0)),
                    })
                elif isinstance(data, tuple) and len(data) == 2:
                    items, total = data
                    result['downloads'] = list(items) if items else []
                    result['total'] = int(total or 0)
                if result['per_page'] > 0:
                    result['pages'] = (result['total'] + result['per_page'] - 1) // result['per_page']
                return result

            # Tentativa 3: filtro por status
            if status and hasattr(hm, 'filter_downloads_by_criteria'):
                try:
                    data = hm.filter_downloads_by_criteria(status=status, page=page, per_page=per_page)
                except TypeError:
                    data = hm.filter_downloads_by_criteria(status=status)
                if isinstance(data, dict):
                    result.update({
                        'downloads': data.get('downloads', []) or data.get('items', []) or [],
                        'total': int(data.get('total', 0) or 0),
                        'page': int(data.get('page', page)),
                        'per_page': int(data.get('per_page', per_page)),
                        'pages': int(data.get('pages', 0)),
                    })
                elif isinstance(data, tuple) and len(data) == 2:
                    items, total = data
                    result['downloads'] = list(items) if items else []
                    result['total'] = int(total or 0)
                if result['per_page'] > 0:
                    result['pages'] = (result['total'] + result['per_page'] - 1) // result['per_page']
                return result

            # Tentativa 4: recente como fallback
            if hasattr(hm, 'get_recent_downloads'):
                try:
                    data = hm.get_recent_downloads(page=page, per_page=per_page)
                except TypeError:
                    data = hm.get_recent_downloads()
                if isinstance(data, dict):
                    result.update({
                        'downloads': data.get('downloads', []) or data.get('items', []) or [],
                        'total': int(data.get('total', 0) or 0),
                        'page': int(data.get('page', page)),
                        'per_page': int(data.get('per_page', per_page)),
                        'pages': int(data.get('pages', 0)),
                    })
                elif isinstance(data, tuple) and len(data) == 2:
                    items, total = data
                    result['downloads'] = list(items) if items else []
                    result['total'] = int(total or 0)
                if result['per_page'] > 0:
                    result['pages'] = (result['total'] + result['per_page'] - 1) // result['per_page']
                return result

        except Exception as e:
            if getattr(self, 'log_manager', None):
                self.log_manager.log_error(e, "Falha ao obter histórico paginado")
        return result

    # ----------------------------
    # Ciclo de vida do servidor (start/stop/is_running)
    # ----------------------------

    def _probe_health(self, host: str, port: int, timeout: float = 0.5) -> bool:
        """Verifica se o servidor está saudável consultando /health.

        Observação: usa 127.0.0.1 para a sonda mesmo que o bind seja 0.0.0.0.
        """
        try:
            url = f"http://127.0.0.1:{port}{APIConfig.API_PREFIX}/health"
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.status == 200
        except Exception:
            return False

    @property
    def is_running(self) -> bool:
        """Indica se o servidor está em execução segundo esta instância."""
        return self._is_running

    def start(self, host: str = None, port: int = None, debug: bool = None) -> None:
        """Inicia o servidor Flask em thread de segundo plano, se necessário.

        - Resolve host/port/debug a partir de parâmetros ou ConfigManager, com fallback para APIConfig.
        - Se já houver um servidor acessível em /health, apenas sinaliza is_running sem iniciar outro.
        - Caso contrário, sobe o servidor em thread daemon e aguarda ficar saudável.
        - Em caso de falha (porta ocupada ou erro de bind), lança RuntimeError.
        """
        # Resolver configuração efetiva
        effective_host = host
        effective_port = port
        effective_debug = debug

        if effective_host is None:
            if self.config_manager and hasattr(self.config_manager, 'get_api_host'):
                try:
                    effective_host = self.config_manager.get_api_host()
                except Exception:
                    effective_host = None
            if effective_host is None:
                effective_host = "0.0.0.0"
        if effective_port is None:
            if self.config_manager and hasattr(self.config_manager, 'get_api_port'):
                try:
                    effective_port = int(self.config_manager.get_api_port())
                except Exception:
                    effective_port = None
            if effective_port is None:
                effective_port = getattr(APIConfig, 'DEFAULT_PORT', 5000)
        if effective_debug is None:
            if self.config_manager and hasattr(self.config_manager, 'get_api_debug'):
                try:
                    effective_debug = bool(self.config_manager.get_api_debug())
                except Exception:
                    effective_debug = None
            if effective_debug is None:
                effective_debug = getattr(APIConfig, 'DEFAULT_DEBUG', False)

        # Detectar servidor já ativo
        if self._probe_health(effective_host, effective_port):
            self._is_running = True
            self._started_here = False
            self._host, self._port, self._debug = effective_host, effective_port, effective_debug
            return

        # Subir servidor próprio
        self._shutdown_token = uuid.uuid4().hex

        def _run_server():
            # use_reloader=False para evitar processos duplicados no Windows
            self.app.run(host=effective_host, port=effective_port, debug=effective_debug, use_reloader=False)

        self._server_thread = threading.Thread(target=_run_server, name="APIServerThread", daemon=True)
        self._server_thread.start()

        # Aguardar ficar saudável
        for _ in range(50):  # ~5s
            if self._probe_health(effective_host, effective_port):
                self._is_running = True
                self._started_here = True
                self._host, self._port, self._debug = effective_host, effective_port, effective_debug
                break
            time.sleep(0.1)

        if not self._is_running:
            raise RuntimeError(f"Falha ao iniciar API na porta {effective_port}. Verifique se a porta está livre.")

    def stop(self, timeout: float = 5.0) -> None:
        """Encerra o servidor se ele foi iniciado por esta instância.

        - Se a API já existia (não iniciada aqui), não tenta derrubar.
        - Dispara rota interna de shutdown protegida por token.
        - Aguarda a thread encerrar (join) por até 'timeout' segundos.
        """
        if not self._is_running:
            return
        if not self._started_here:
            # Não fomos nós que iniciamos o servidor; apenas limpar estado local
            self._is_running = False
            return

        token = self._shutdown_token
        try:
            req = urllib.request.Request(
                url=f"http://127.0.0.1:{self._port}/__internal__/shutdown",
                method="POST",
                headers={"X-Internal-Token": token or ""}
            )
            urllib.request.urlopen(req, timeout=2)
        except Exception:
            pass

        if self._server_thread:
            try:
                self._server_thread.join(timeout)
            except Exception:
                pass

        self._is_running = False
        self._started_here = False
        self._server_thread = None
        self._shutdown_token = None

    # ----------------------------
    # Verificações de saúde (helpers usados pela rota /health)
    # ----------------------------
    def _check_database(self) -> bool:
        """Verifica a conectividade e operação básica do banco de dados.
        - Requisitos mínimos: existir self.history_manager e seu db_manager.
        - Realiza uma operação leve (contagem total de downloads) para validar acesso.
        Retorna True se saudável; False caso contrário.
        """
        try:
            # Verificar instâncias essenciais
            if not getattr(self, 'history_manager', None):
                return False
            dbm = getattr(self.history_manager, 'db_manager', None)
            if not dbm:
                return False

            # Preferir uma operação leve de contagem diretamente no DatabaseManager
            if hasattr(dbm, 'get_total_downloads_count'):
                try:
                    _ = dbm.get_total_downloads_count()
                except TypeError:
                    # Algumas assinaturas podem requerer filters=None
                    _ = dbm.get_total_downloads_count(None)
            else:
                # Fallback: usar HistoryManager com a paginação mínima disponível
                if hasattr(self.history_manager, 'get_downloads_paginated'):
                    _ = self.history_manager.get_downloads_paginated(page=1, per_page=1)
                else:
                    return False
            return True
        except Exception as e:
            if getattr(self, 'log_manager', None):
                self.log_manager.log_error(e, "Falha na verificação de saúde do banco de dados")
            return False

    def _check_download_manager(self) -> bool:
        """Verifica a disponibilidade do DownloadManager.
        - Requisitos mínimos: instância presente e métodos essenciais disponíveis.
        Retorna True se saudável; False caso contrário.
        """
        try:
            dm = getattr(self, 'download_manager', None)
            if not dm:
                return False
            # Verificar métodos essenciais usados pelas rotas/fluxo
            has_methods = all([
                hasattr(dm, 'extract_video_info'),
                hasattr(dm, 'start_download'),
            ])
            return bool(has_methods)
        except Exception as e:
            if getattr(self, 'log_manager', None):
                self.log_manager.log_error(e, "Falha na verificação de saúde do DownloadManager")
            return False

    def _check_config_manager(self) -> bool:
        """Verifica a disponibilidade do ConfigManager.
        - Requisitos mínimos: instância presente e atributos básicos (api_host, api_port, api_debug) acessíveis.
        - Valida que a porta é um inteiro válido.
        Retorna True se saudável; False caso contrário.
        """
        try:
            cfg = getattr(self, 'config_manager', None)
            if not cfg:
                return False
            host = getattr(cfg, 'api_host', None)
            port = getattr(cfg, 'api_port', None)
            debug = getattr(cfg, 'api_debug', None)
            if port is None:
                return False
            try:
                int(port)
            except Exception:
                return False
            return host is not None and debug is not None
        except Exception as e:
            if getattr(self, 'log_manager', None):
                self.log_manager.log_error(e, "Falha na verificação de saúde do ConfigManager")
            return False

    # ----------------------------
    # Rotas
    # ----------------------------

    def _register_routes(self):
        @self.app.route(f"{APIConfig.API_PREFIX}/health", methods=['GET'])
        @log_api_request(self.log_manager)
        @handle_api_errors
        
        def health_check():
            now_utc = datetime.now(timezone.utc)
            uptime = (now_utc - self.start_time).total_seconds()
            services = {
                "database": "healthy" if self._check_database() else "unhealthy",
                "download_manager": "healthy" if self._check_download_manager() else "unhealthy",
                "config_manager": "healthy" if self._check_config_manager() else "unhealthy"
            }
            overall_status = "healthy" if all(s == "healthy" for s in services.values()) else "unhealthy"
            health_data = {
                "status": overall_status,
                "timestamp": now_utc.isoformat().replace("+00:00", "Z"),
                "version": APIConfig.API_VERSION,
                "uptime": uptime,
                "services": services
            }
            return APIResponse.success(data=health_data, message="API está funcionando")

        @self.app.route(f"{APIConfig.API_PREFIX}/video/info", methods=['POST'])
        @log_api_request(self.log_manager)
        @handle_api_errors
        def get_video_info():
            request_data = request.get_json() or {}
            is_valid, validated_data, errors = validate_request_data(video_info_request_schema, request_data)
            if not is_valid:
                return APIResponse.validation_error(errors)
            url = validated_data['url']
            if not self.download_manager:
                return APIResponse.error("Serviço de download não disponível", code="SERVICE_UNAVAILABLE", status_code=APIConfig.HTTP_STATUS["SERVICE_UNAVAILABLE"])
            video_info = self._get_video_info_from_url(url)
            return APIResponse.success(data=video_info, message="Informações do vídeo obtidas com sucesso")

        @self.app.route(f"{APIConfig.API_PREFIX}/download", methods=['POST'])
        @log_api_request(self.log_manager)
        @handle_api_errors
        def start_download():
            request_data = request.get_json() or {}
            is_valid, validated_data, errors = validate_request_data(download_request_schema, request_data)
            if not is_valid:
                return APIResponse.validation_error(errors)
            if not self.download_manager:
                return APIResponse.error("Serviço de download não disponível", code="SERVICE_UNAVAILABLE", status_code=APIConfig.HTTP_STATUS["SERVICE_UNAVAILABLE"])
            download_result = self._start_download_process(validated_data)
            return APIResponse.success(data=download_result, message="Download iniciado com sucesso", status_code=APIConfig.HTTP_STATUS["CREATED"])

        @self.app.route(f"{APIConfig.API_PREFIX}/download/<download_id>/status", methods=['GET'])
        @log_api_request(self.log_manager)
        @handle_api_errors
        def get_download_status(download_id):
            if not download_id or not str(download_id).strip():
                return APIResponse.error("Parâmetro download_id ausente ou inválido", code="INVALID_DOWNLOAD_ID", status_code=APIConfig.HTTP_STATUS["BAD_REQUEST"])
            if not self.download_manager:
                return APIResponse.error("Serviço de download não disponível", code="SERVICE_UNAVAILABLE", status_code=APIConfig.HTTP_STATUS["SERVICE_UNAVAILABLE"])
            status_data = self._get_download_status(download_id)
            if not status_data:
                return APIResponse.error("Download não encontrado", code="DOWNLOAD_NOT_FOUND", status_code=APIConfig.HTTP_STATUS["NOT_FOUND"])
            return APIResponse.success(data=status_data, message="Status do download obtido com sucesso")

        @self.app.route(f"{APIConfig.API_PREFIX}/download/<download_id>/progress", methods=['GET'])
        @log_api_request(self.log_manager)
        @handle_api_errors
        def get_download_progress(download_id):
            if not download_id or not str(download_id).strip():
                return APIResponse.error("Parâmetro download_id ausente ou inválido", code="INVALID_DOWNLOAD_ID", status_code=APIConfig.HTTP_STATUS["BAD_REQUEST"])
            if not self.download_manager:
                return APIResponse.error("Serviço de download não disponível", code="SERVICE_UNAVAILABLE", status_code=APIConfig.HTTP_STATUS["SERVICE_UNAVAILABLE"])
            progress_data = self._get_download_progress(download_id)
            if not progress_data:
                return APIResponse.error("Download não encontrado", code="DOWNLOAD_NOT_FOUND", status_code=APIConfig.HTTP_STATUS["NOT_FOUND"])
            return APIResponse.success(data=progress_data, message="Progresso do download obtido com sucesso")

        @self.app.route(f"{APIConfig.API_PREFIX}/downloads", methods=['GET'])
        @log_api_request(self.log_manager)
        @handle_api_errors
        def get_download_history():
            query_params = dict(request.args)
            is_valid, validated_params, errors = validate_request_data(pagination_schema, query_params)
            if not is_valid:
                return APIResponse.validation_error(errors)
            if self.history_manager:
                history_data = self._get_paginated_history(validated_params)
            else:
                history_data = {"downloads": [], "total": 0, "page": validated_params.get('page', 1), "per_page": validated_params.get('per_page', 20), "pages": 0}
            return APIResponse.success(data=history_data, message="Histórico obtido com sucesso")

        # Rota interna para desligamento seguro, protegida por token
        @self.app.route("/__internal__/shutdown", methods=['POST'])
        def __internal_shutdown():
            token = request.headers.get("X-Internal-Token")
            if not token or token != getattr(self, "_shutdown_token", None):
                return APIResponse.error("Acesso negado", code="FORBIDDEN", status_code=403)
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                return APIResponse.error("Shutdown não suportado", code="SHUTDOWN_NOT_SUPPORTED", status_code=500)
            func()
            return APIResponse.success(message="Servidor sendo desligado")

    def _register_error_handlers(self):
        @self.app.errorhandler(404)
        def not_found(e):
            return APIResponse.error("Endpoint não encontrado", code="NOT_FOUND", status_code=404)

        @self.app.errorhandler(500)
        def internal_error(e):
            return APIResponse.error("Erro interno do servidor", code="INTERNAL_ERROR", status_code=500)

if __name__ == "__main__":
    # Inicializa os gerenciadores de forma autônoma (sem dependência de yt_refactored)
    from database_manager import DatabaseManager
    from log_manager import LogManager
    from config_manager import ConfigManager
    from history_manager import HistoryManager
    from download_manager import DownloadManager

    # Inicializar banco de dados
    db_manager = DatabaseManager()
    db_manager.initialize()

    # Criar gerenciadores
    log_manager = LogManager()
    config_manager = ConfigManager(db_manager)
    history_manager = HistoryManager(db_manager, log_manager)
    download_manager = DownloadManager(log_manager, config_manager=config_manager)

    # Instanciar servidor da API
    server = APIServer(
        config_manager=config_manager,
        download_manager=download_manager,
        history_manager=history_manager,
        log_manager=log_manager
    )

    print(f"[API SERVER] Iniciando servidor na porta {APIConfig.DEFAULT_PORT} ...")
    server.app.run(
        host="0.0.0.0",
        port=APIConfig.DEFAULT_PORT,
        debug=APIConfig.DEFAULT_DEBUG
    )
