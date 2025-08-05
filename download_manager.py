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
        # Verificar se é uma playlist
        if self.is_playlist_url(url):
            return self.extract_playlist_info(url)
            
        # Processar como vídeo individual
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
        """Limpa as informações do vídeo atual"""
        self.current_info = None
        self.log_manager.log_info("Informações do vídeo atual limpas")
    
    def is_playlist_url(self, url):
        """
        Verifica se a URL é de uma playlist
        
        Args:
            url (str): URL a ser verificada
            
        Returns:
            bool: True se for playlist, False caso contrário
        """
        playlist_indicators = [
            'playlist?list=',
            '&list=',
            '/playlist/',
            'watch?v=',  # Pode ser playlist se tiver &list=
        ]
        
        url_lower = url.lower()
        
        # Verificar indicadores diretos de playlist
        if 'playlist?list=' in url_lower or '/playlist/' in url_lower:
            return True
            
        # Verificar se é um vídeo com parâmetro de playlist
        if 'watch?v=' in url_lower and '&list=' in url_lower:
            return True
            
        return False
    
    def extract_playlist_info(self, url):
        """
        Extrai informações da playlist
        
        Args:
            url (str): URL da playlist
            
        Returns:
            tuple: (sucesso, dados_da_playlist, None)
        """
        try:
            # Primeiro, tentar extrair com extract_flat para obter informações da playlist
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'playlistend': 50,  # Limitar a 50 vídeos para performance
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Verificar se é realmente uma playlist
                # Para URLs do tipo watch?v=...&list=..., o yt-dlp pode retornar o vídeo individual
                # Vamos forçar a extração da playlist usando apenas o parâmetro list
                if 'entries' not in info or len(info.get('entries', [])) <= 1:
                    # Tentar extrair apenas a playlist usando o ID da lista
                    import re
                    list_match = re.search(r'[&?]list=([^&]+)', url)
                    if list_match:
                        playlist_id = list_match.group(1)
                        playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
                        
                        # Tentar novamente com a URL da playlist
                        info = ydl.extract_info(playlist_url, download=False)
                        
                        if 'entries' not in info or len(info.get('entries', [])) == 0:
                            return False, "URL não é uma playlist válida ou playlist vazia", None
                    else:
                        return False, "URL não é uma playlist válida", None
                
                # Processar informações da playlist
                playlist_info = {
                    'type': 'playlist',
                    'title': info.get('title', 'Playlist sem título'),
                    'uploader': info.get('uploader', 'N/A'),
                    'description': info.get('description', 'N/A'),
                    'video_count': len(info['entries']),
                    'entries': info['entries'][:50],  # Limitar a 50 vídeos para performance
                    'url': url
                }
                
                self.current_info = playlist_info
                self.log_manager.log_info(f"Informações da playlist extraídas: {playlist_info['title']} ({playlist_info['video_count']} vídeos)")
                
                return True, playlist_info, None
                
        except Exception as e:
            error_msg = f"Erro ao extrair informações da playlist: {str(e)}"
            self.log_manager.log_error(error_msg)
            return False, error_msg, None
    
    def start_playlist_download(self, url, selected_resolution, success_callback=None, error_callback=None, audio_only=False, audio_quality='best', video_callback=None):
        """
        Inicia o download de uma playlist completa
        
        Args:
            url (str): URL da playlist
            selected_resolution (str): Resolução selecionada (ignorado se audio_only=True)
            success_callback: Função chamada em caso de sucesso
            error_callback: Função chamada em caso de erro
            audio_only (bool): Se True, baixa apenas áudio
            audio_quality (str): Qualidade do áudio
            video_callback: Função chamada para cada vídeo processado (video_info, index, total)
            
        Returns:
            tuple: (sucesso, mensagem)
        """
        if self.is_downloading:
            return False, "Um download já está em andamento!"
        
        if not self.current_info or self.current_info.get('type') != 'playlist':
            return False, "Extraia as informações da playlist primeiro."
        
        if not self.download_directory:
            return False, "Selecione um diretório de destino."
        
        # Determinar tipo de download
        if audio_only:
            download_type = f"playlist de áudio ({audio_quality})"
        else:
            download_type = f"playlist de vídeo ({selected_resolution})"
        
        # Iniciar download em thread separada
        self.is_downloading = True
        self.download_thread = threading.Thread(
            target=self._playlist_download_worker,
            args=(url, selected_resolution, download_type, success_callback, error_callback, audio_only, audio_quality, video_callback),
            daemon=True
        )
        self.download_thread.start()
        
        return True, f"Download de {download_type} iniciado"
    
    def _playlist_download_worker(self, url, selected_resolution, download_type, success_callback, error_callback, audio_only=False, audio_quality='best', video_callback=None):
        """
        Worker thread para download de playlist com processamento individual de cada vídeo
        
        Args:
            url (str): URL da playlist
            selected_resolution (str): Resolução selecionada
            download_type (str): Tipo de download para logging
            success_callback: Callback de sucesso
            error_callback: Callback de erro
            audio_only (bool): Se True, baixa apenas áudio
            audio_quality (str): Qualidade do áudio
            video_callback: Função chamada para cada vídeo processado (video_info, index, total)
        """
        try:
            # Criar subpasta para a playlist
            playlist_title = self.current_info.get('title', 'Playlist')
            # Sanitizar nome da pasta
            safe_title = "".join(c for c in playlist_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            playlist_folder = os.path.join(self.download_directory, safe_title)
            
            # Criar diretório se não existir
            os.makedirs(playlist_folder, exist_ok=True)
            
            # Obter lista de vídeos da playlist
            playlist_entries = self.current_info.get('entries', [])
            total_videos = len(playlist_entries)
            
            self.log_manager.log_info(f"Iniciando download de playlist: {total_videos} vídeos")
            
            # Processar cada vídeo individualmente
            for index, entry in enumerate(playlist_entries, 1):
                if not self.is_downloading:  # Verificar se download foi cancelado
                    break
                    
                try:
                    # Extrair URL do vídeo individual
                    video_url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
                    video_title = entry.get('title', f'Vídeo {index}')
                    
                    self.log_manager.log_info(f"Processando vídeo {index}/{total_videos}: {video_title}")
                    
                    # Chamar callback de progresso se fornecido
                    if video_callback:
                        video_callback((entry, index, total_videos), 'progress')
                    
                    # Extrair informações completas do vídeo individual
                    ydl_opts_info = {
                        'quiet': True,
                        'no_warnings': True,
                        'extractflat': False
                    }
                    
                    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                        video_info = ydl.extract_info(video_url, download=False)
                    
                    # Atualizar current_info temporariamente para este vídeo
                    original_info = self.current_info
                    self.current_info = video_info
                    
                    # Configurar opções de download para o vídeo individual
                    if audio_only:
                        format_selector = 'bestaudio/best'
                        outtmpl = os.path.join(playlist_folder, f'{index:02d} - %(title)s.%(ext)s')
                        postprocessors = [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': AppConstants.SUPPORTED_AUDIO_FORMAT,
                            'preferredquality': audio_quality if audio_quality != 'best' else '192',
                        }]
                    else:
                        # Para vídeo, usar formato específico baseado na resolução
                        height = self._extract_height_from_resolution(selected_resolution)
                        if height:
                            format_selector = f'best[height<={height}]/best'
                        else:
                            format_selector = 'best'
                        
                        outtmpl = os.path.join(playlist_folder, f'{index:02d} - %(title)s.%(ext)s')
                        postprocessors = [{
                            'key': 'FFmpegVideoConvertor',
                            'preferedformat': AppConstants.SUPPORTED_OUTPUT_FORMAT,
                        }]
                    
                    ydl_opts = {
                        'format': format_selector,
                        'outtmpl': outtmpl,
                        'ffmpeg_location': AppUtils.get_ffmpeg_path(),
                        'postprocessors': postprocessors,
                        'progress_hooks': [self._progress_hook],
                        'postprocessor_hooks': [self._postprocessor_hook],
                        'retries': AppConstants.MAX_RETRIES,
                        'fragment_retries': AppConstants.FRAGMENT_RETRIES,
                        'socket_timeout': AppConstants.SOCKET_TIMEOUT,
                        'http_chunk_size': AppConstants.HTTP_CHUNK_SIZE,
                        'noplaylist': True,  # Download individual
                    }
                    
                    # Executar download do vídeo individual
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([video_url])
                    
                    self.log_manager.log_info(f"Vídeo {index}/{total_videos} baixado com sucesso: {video_title}")
                    
                    # Chamar callback de sucesso para este vídeo específico se fornecido
                    if video_callback:
                        # Criar dados do vídeo para callback de sucesso
                        video_success_data = {
                            'video_info': video_info,
                            'index': index,
                            'total': total_videos,
                            'resolution': selected_resolution if not audio_only else 'music',
                            'audio_only': audio_only,
                            'playlist_folder': playlist_folder
                        }
                        try:
                            # Chamar callback adicional para sucesso do vídeo individual
                            video_callback(video_success_data, 'success')
                        except Exception as callback_error:
                            self.log_manager.log_error(f"Erro no callback de sucesso do vídeo: {str(callback_error)}")
                    
                    # Restaurar informações originais da playlist
                    self.current_info = original_info
                    
                except Exception as video_error:
                    self.log_manager.log_error(f"Erro ao baixar vídeo {index}: {str(video_error)}")
                    # Continuar com próximo vídeo mesmo se um falhar
                    continue
            
            self.log_manager.log_info(f"Download de {download_type} concluído com sucesso")
            
            if success_callback:
                success_callback()
                
        except Exception as e:
            error_msg = f"Erro durante download de {download_type}: {str(e)}"
            self.log_manager.log_error(error_msg)
            
            if error_callback:
                error_callback(error_msg)
        
        finally:
            self.is_downloading = False