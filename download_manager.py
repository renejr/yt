import yt_dlp
import threading
import os
from utils import AppUtils, AppConstants

class DownloadManager:
    """Gerenciador de downloads de vídeos do YouTube"""
    
    def __init__(self, log_manager, progress_callback=None, postprocessor_callback=None):
        """
        Inicializa o gerenciador de downloads
        
        Args:
            log_manager: Instância do LogManager para logging
            progress_callback: Função callback para progresso do download
            postprocessor_callback: Função callback para pós-processamento
        """
        self.log_manager = log_manager
        self.progress_callback = progress_callback
        self.postprocessor_callback = postprocessor_callback
        
        # Estado do download
        self.is_downloading = False
        self.download_thread = None
        self.current_info = None
        
        # Configurações
        self.download_directory = ""
    
    def set_download_directory(self, directory):
        """Define o diretório de download"""
        is_valid, error_msg = AppUtils.validate_directory(directory)
        if is_valid:
            self.download_directory = directory
            self.log_manager.log_info(f"Diretório de download definido: {directory}")
            return True, ""
        else:
            return False, error_msg
    
    def extract_video_info(self, url):
        """
        Extrai informações do vídeo sem fazer download
        
        Args:
            url (str): URL do vídeo
            
        Returns:
            tuple: (sucesso, dados_ou_erro, resoluções)
        """
        # Validar URL
        is_valid, error_msg = AppUtils.validate_url(url)
        if not is_valid:
            return False, error_msg, []
        
        try:
            self.log_manager.log_info(f"Iniciando extração de informações: {url}")
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extractflat': False
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            
            self.current_info = info
            
            # Extrair resoluções disponíveis
            resolutions = self._extract_resolutions(info)
            
            self.log_manager.log_info(
                f"Informações extraídas com sucesso: {info.get('title', 'N/A')}"
            )
            
            return True, info, resolutions
            
        except Exception as e:
            error_msg = self.log_manager.log_error(e, "Erro ao extrair informações")
            return False, error_msg, []
    
    def _extract_resolutions(self, info):
        """Extrai e ordena resoluções disponíveis do vídeo"""
        resolutions = set()  # Usar set para evitar duplicatas
        valid_formats = []
        
        if 'formats' in info and info['formats']:
            for format_info in info['formats']:
                resolution = format_info.get('resolution')
                vcodec = format_info.get('vcodec', 'none')
                height = format_info.get('height')
                
                # Log para debug
                self.log_manager.log_info(
                    f"Formato encontrado: {format_info.get('format_id')} - "
                    f"Resolução: {resolution} - Vcodec: {vcodec} - Altura: {height}"
                )
                
                # Filtrar apenas formatos de vídeo válidos
                if (resolution and 
                    resolution != 'audio only' and 
                    vcodec != 'none' and 
                    height is not None):
                    
                    resolutions.add(resolution)
                    valid_formats.append(format_info)
        
        # Converter set para lista e ordenar
        resolutions_list = list(resolutions)
        
        if resolutions_list:
            resolutions_list = AppUtils.sort_resolutions(resolutions_list)
            self.log_manager.log_info(f"Resoluções extraídas: {resolutions_list}")
        else:
            resolutions_list = ['Melhor qualidade disponível']
            self.log_manager.log_warning("Nenhuma resolução válida encontrada, usando fallback")
        
        self.log_manager.log_info(f"Total de formatos válidos: {len(valid_formats)}")
        return resolutions_list
    
    def find_format_id(self, selected_resolution):
        """
        Encontra o format_id adequado para a resolução selecionada
        
        Args:
            selected_resolution (str): Resolução selecionada
            
        Returns:
            str or None: format_id encontrado
        """
        if not self.current_info or 'formats' not in self.current_info:
            return None
        
        # Tentar encontrar um stream de vídeo puro primeiro
        for fmt_obj in self.current_info['formats']:
            if (fmt_obj.get('resolution') == selected_resolution and 
                fmt_obj.get('vcodec') != 'none' and 
                fmt_obj.get('acodec') == 'none'):
                
                format_id = fmt_obj['format_id']
                self.log_manager.log_info(
                    f"Formato de vídeo puro selecionado: {format_id} para resolução {selected_resolution}"
                )
                return format_id
        
        # Se não encontrar, pegar qualquer stream de vídeo da resolução
        for fmt_obj in self.current_info['formats']:
            if (fmt_obj.get('resolution') == selected_resolution and 
                fmt_obj.get('vcodec') != 'none'):
                
                format_id = fmt_obj['format_id']
                self.log_manager.log_info(
                    f"Formato de vídeo selecionado: {format_id} para resolução {selected_resolution}"
                )
                return format_id
        
        return None
    
    def start_download(self, url, selected_resolution, success_callback=None, error_callback=None, audio_only=False, audio_quality='best'):
        """
        Inicia o download do vídeo ou áudio em thread separada
        
        Args:
            url (str): URL do vídeo
            selected_resolution (str): Resolução selecionada (ignorado se audio_only=True)
            success_callback: Função chamada em caso de sucesso
            error_callback: Função chamada em caso de erro
            audio_only (bool): Se True, baixa apenas áudio
            audio_quality (str): Qualidade do áudio (best, 320, 256, 192, 128)
            
        Returns:
            tuple: (sucesso, mensagem)
        """
        if self.is_downloading:
            return False, "Um download já está em andamento!"
        
        if not self.current_info:
            return False, "Extraia as informações do vídeo primeiro."
        
        if not self.download_directory:
            return False, "Selecione um diretório de destino."
        
        # Determinar formato baseado no tipo de download
        if audio_only:
            format_id = 'bestaudio'
            download_type = f"áudio ({audio_quality})"
        else:
            # Encontrar format_id para vídeo
            video_format_id = self.find_format_id(selected_resolution)
            if not video_format_id:
                return False, f"Não foi possível encontrar formato adequado para {selected_resolution}"
            format_id = video_format_id
            download_type = f"vídeo ({selected_resolution})"
        
        # Iniciar download em thread separada
        self.is_downloading = True
        self.download_thread = threading.Thread(
            target=self._download_worker,
            args=(url, format_id, download_type, success_callback, error_callback, audio_only, audio_quality),
            daemon=True
        )
        self.download_thread.start()
        
        return True, f"Download de {download_type} iniciado"
    
    def _download_worker(self, url, format_id, download_type, success_callback, error_callback, audio_only=False, audio_quality='best'):
        """Worker thread para executar o download de vídeo ou áudio"""
        try:
            self.log_manager.log_info(
                f"Iniciando download: {self.current_info.get('title', 'video')} - {download_type}"
            )
            
            # Obter caminho do FFmpeg
            ffmpeg_path = AppUtils.get_ffmpeg_path()
            self.log_manager.log_info(f"Usando ffmpeg em: {ffmpeg_path}")
            
            # Configurar opções do yt-dlp
            ydl_opts = self._get_download_options(format_id, ffmpeg_path, audio_only, audio_quality)
            
            # Executar download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Sucesso
            if success_callback:
                success_callback()
            
        except Exception as e:
            error_msg = self.log_manager.log_error(e, "Erro durante download")
            if error_callback:
                error_callback(error_msg)
        
        finally:
            self.is_downloading = False
    
    def _get_download_options(self, format_id, ffmpeg_path, audio_only=False, audio_quality='best'):
        """Configura opções do yt-dlp para download de vídeo ou áudio"""
        if audio_only:
            # Configurações para download apenas de áudio
            options = {
                'format': 'bestaudio/best',
                'outtmpl': f"{self.download_directory}/%(title).200s.%(ext)s",
                'restrictfilenames': True,
                'windowsfilenames': True,
                'ignoreerrors': False,
                'ffmpeg_location': ffmpeg_path,
                'progress_hooks': [self._progress_hook] if self.progress_callback else [],
                'postprocessor_hooks': [self._postprocessor_hook] if self.postprocessor_callback else [],
                'windowsfilenames': True,
                'quiet': False,
                'retries': AppConstants.MAX_RETRIES,
                'fragment_retries': AppConstants.FRAGMENT_RETRIES,
                'skip_unavailable_fragments': True,
                'keep_fragments': False,
                'abort_on_unavailable_fragment': False,
                'socket_timeout': AppConstants.SOCKET_TIMEOUT,
                'http_chunk_size': AppConstants.HTTP_CHUNK_SIZE,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': AppConstants.SUPPORTED_AUDIO_FORMAT,
                    'preferredquality': audio_quality if audio_quality != 'best' else '192',
                }]
            }
        else:
            # Configurações para download de vídeo com fallback robusto
            # Usar estratégia de fallback para evitar erros de formato
            format_selector = f"{format_id}+bestaudio/best[height<={self._extract_height_from_resolution(format_id)}]/best"
            options = {
                'format': format_selector,
                'outtmpl': f"{self.download_directory}/%(title).200s.%(ext)s",
                'restrictfilenames': True,
                'windowsfilenames': True,
                'ignoreerrors': False,
                'merge_output_format': AppConstants.SUPPORTED_OUTPUT_FORMAT,
                'ffmpeg_location': ffmpeg_path,
                'progress_hooks': [self._progress_hook] if self.progress_callback else [],
                'postprocessor_hooks': [self._postprocessor_hook] if self.postprocessor_callback else [],
                'windowsfilenames': True,
                'quiet': False,
                'retries': AppConstants.MAX_RETRIES,
                'fragment_retries': AppConstants.FRAGMENT_RETRIES,
                'skip_unavailable_fragments': True,
                'keep_fragments': False,
                'abort_on_unavailable_fragment': False,
                'socket_timeout': AppConstants.SOCKET_TIMEOUT,
                'http_chunk_size': AppConstants.HTTP_CHUNK_SIZE,
                'writesubtitles': False,
                'writeautomaticsub': False,
            }
        
        return options
    
    def _extract_height_from_resolution(self, format_id):
        """Extrai altura da resolução para fallback"""
        if not self.current_info or 'formats' not in self.current_info:
            return 1080  # fallback padrão
        
        for fmt_obj in self.current_info['formats']:
            if fmt_obj.get('format_id') == format_id:
                return fmt_obj.get('height', 1080)
        
        return 1080  # fallback padrão
    
    def _progress_hook(self, d):
        """Hook para progresso do download"""
        if self.progress_callback:
            self.progress_callback(d)
    
    def _postprocessor_hook(self, d):
        """Hook para pós-processamento"""
        if self.postprocessor_callback:
            self.postprocessor_callback(d)
    
    def stop_download(self):
        """Para o download atual (se possível)"""
        if self.is_downloading:
            self.log_manager.log_info("Tentativa de parar download em andamento")
            # Note: yt-dlp não tem uma forma direta de parar download
            # Esta funcionalidade pode ser implementada com mais complexidade se necessário
            return True
        return False
    
    def get_download_status(self):
        """Retorna status atual do download"""
        return {
            'is_downloading': self.is_downloading,
            'has_info': self.current_info is not None,
            'download_directory': self.download_directory
        }
    
    def get_video_metadata(self):
        """
        Retorna metadados formatados do vídeo atual
        
        Returns:
            dict: Metadados formatados
        """
        if not self.current_info:
            return {}
        
        return {
            'title': self.current_info.get('title', 'N/A'),
            'description': AppUtils.truncate_text(self.current_info.get('description', 'N/A')),
            'duration': AppUtils.format_duration(self.current_info.get('duration')),
            'view_count': AppUtils.format_view_count(self.current_info.get('view_count')),
            'uploader': self.current_info.get('uploader', 'N/A'),
            'upload_date': self.current_info.get('upload_date', 'N/A'),
            'thumbnail_url': self.current_info.get('thumbnail', ''),
            'webpage_url': self.current_info.get('webpage_url', '')
        }
    
    def clear_current_info(self):
        """Limpa informações do vídeo atual"""
        self.current_info = None
        self.log_manager.log_info("Informações do vídeo atual limpas")