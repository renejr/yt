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

    def _get_download_status(self, download_id: str) -> dict:
        """Compõe um snapshot de status do download a partir de self.active_downloads."""
        entry = self.active_downloads.get(download_id)
        if not entry:
            return None
        progress = entry.get('progress', {})
        return {
            'download_id': download_id,
            'url': entry.get('url'),
            'status': entry.get('status'),
            'type': entry.get('type'),
            'format': entry.get('format'),
            'resolution': entry.get('resolution'),
            'audio_quality': entry.get('audio_quality'),
            'filename': entry.get('filename'),
            'created_at': entry.get('created_at'),
            'updated_at': entry.get('updated_at'),
            'percent': progress.get('percent'),
        }

    def _get_download_progress(self, download_id: str) -> dict:
        """Retorna dados detalhados de progresso do download a partir de self.active_downloads."""
        entry = self.active_downloads.get(download_id)
        if not entry:
            return None
        progress = entry.get('progress', {})
        return {
            'download_id': download_id,
            'status': entry.get('status'),
            'stage': progress.get('stage'),
            'percent': progress.get('percent'),
            'downloaded_bytes': progress.get('downloaded_bytes'),
            'total_bytes': progress.get('total_bytes'),
            'speed': progress.get('speed'),
            'eta': progress.get('eta'),
            'filename': entry.get('filename'),
            'updated_at': entry.get('updated_at'),
        }

    def _get_paginated_history(self, params: dict) -> dict:
        """Monta filtros de paginação/pesquisa, consulta o HistoryManager e adapta
        o retorno para o payload esperado pelo schema da API.

        - Consome page e per_page de params
        - Aceita filtros opcionais: status e search (mapeado para search_query)
        - Chama HistoryManager.get_downloads_paginated(page, per_page, filters)
        - Converte a estrutura de paginação interna (pagination) para os campos
          esperados pela API: total, page, per_page, pages.
        """
        page = int(params.get("page", 1))
        per_page = int(params.get("per_page", 20))

        # Montar filtros opcionais
        filters = {}
        status = params.get("status")
        if status:
            filters["status"] = status
        search = params.get("search")
        if search:
            # HistoryManager espera a chave 'search_query' para buscas textuais
            filters["search_query"] = search

        filters = filters or None

        # Consultar histórico paginado usando o HistoryManager
        result = self.history_manager.get_downloads_paginated(page, per_page, filters)

        downloads = result.get("downloads", [])
        pagination = result.get("pagination", {}) or {}

        # Extrair campos e garantir valores padrão coerentes
        total = pagination.get("total_items", len(downloads))
        pages = pagination.get("total_pages")
        if pages is None:
            pages = (total + per_page - 1) // per_page if per_page else 0
        page_out = pagination.get("current_page", page)
        per_page_out = pagination.get("per_page", per_page)

        return {
            "downloads": downloads,
            "total": total,
            "page": page_out,
            "per_page": per_page_out,
            "pages": pages,
        }

    def _check_database(self) -> bool:
        """Verifica a saúde do banco de dados executando uma leitura simples paginada.
        Retorna True se a consulta executar sem exceções e False caso contrário."""
        if not self.history_manager:
            return False
        try:
            # Consulta mínima para validar conexão/integração
            self.history_manager.get_downloads_paginated(page=1, per_page=1, filters=None)
            return True
        except Exception:
            return False

    def _check_download_manager(self) -> bool:
        """Retorna True se o DownloadManager estiver disponível (instanciado)."""
        return bool(self.download_manager)

    def _check_config_manager(self) -> bool:
        """Retorna True se o ConfigManager estiver disponível (instanciado)."""
        return bool(self.config_manager)
 
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
