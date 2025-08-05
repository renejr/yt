import os
import sys
import tkinter as tk
from tkinter import messagebox

class AppUtils:
    """Classe com utilitários compartilhados da aplicação"""
    
    @staticmethod
    def get_ffmpeg_path():
        """Determina o caminho correto do FFmpeg baseado no ambiente de execução"""
        if getattr(sys, 'frozen', False):
            # Executável compilado (PyInstaller)
            return os.path.join(sys._MEIPASS, "ffmpeg.exe")
        else:
            # Desenvolvimento - usar caminho absoluto no diretório atual
            ffmpeg_path = os.path.abspath("ffmpeg.exe")
            
            # Verificar se o arquivo existe
            if not os.path.exists(ffmpeg_path):
                raise FileNotFoundError(
                    f"FFMPEG não encontrado em: {ffmpeg_path}. "
                    "Verifique se o arquivo está presente no diretório da aplicação."
                )
            
            return ffmpeg_path
    
    @staticmethod
    def validate_url(url):
        """Valida se a URL fornecida não está vazia"""
        if not url or not url.strip():
            return False, "Por favor, insira a URL do vídeo."
        return True, ""
    
    @staticmethod
    def validate_directory(directory):
        """Valida se o diretório existe e é acessível"""
        if not directory:
            return False, "Por favor, selecione um diretório de destino."
        
        if not os.path.exists(directory):
            return False, "O diretório selecionado não existe."
        
        if not os.access(directory, os.W_OK):
            return False, "Sem permissão de escrita no diretório selecionado."
        
        return True, ""
    
    @staticmethod
    def format_duration(duration_seconds):
        """Formata duração em segundos para formato MM:SS"""
        if not duration_seconds or duration_seconds == 'N/A':
            return "Não disponível"
        
        try:
            minutes = int(duration_seconds) // 60
            seconds = int(duration_seconds) % 60
            return f"{minutes}:{seconds:02d}"
        except (ValueError, TypeError):
            return str(duration_seconds)
    
    @staticmethod
    def format_view_count(view_count):
        """Formata número de visualizações com separadores de milhares"""
        if not view_count or view_count == 'N/A':
            return "Não disponível"
        
        try:
            return f"{int(view_count):,}"
        except (ValueError, TypeError):
            return str(view_count)
    
    @staticmethod
    def truncate_text(text, max_length=50000):
        """Trunca texto se exceder o tamanho máximo"""
        if not text or text == 'N/A':
            return "Não disponível"
        
        text_str = str(text)
        if len(text_str) > max_length:
            return text_str[:max_length] + "..."
        
        return text_str
    
    @staticmethod
    def safe_get_clipboard():
        """Obtém conteúdo da área de transferência de forma segura"""
        try:
            # Criar janela temporária completamente oculta
            temp_root = tk.Tk()
            temp_root.withdraw()  # Esconder janela
            temp_root.attributes('-alpha', 0)  # Tornar invisível
            clipboard_content = temp_root.clipboard_get()
            temp_root.destroy()  # Destruir janela temporária
            return clipboard_content
        except tk.TclError:
            return ""
    
    @staticmethod
    def show_error_message(title, message):
        """Exibe mensagem de erro de forma padronizada"""
        messagebox.showerror(title, message)
    
    @staticmethod
    def show_warning_message(title, message):
        """Exibe mensagem de aviso de forma padronizada"""
        messagebox.showwarning(title, message)
    
    @staticmethod
    def show_info_message(title, message):
        """Exibe mensagem informativa de forma padronizada"""
        messagebox.showinfo(title, message)
    
    @staticmethod
    def extract_resolution_number(resolution_str):
        """Extrai número da resolução para ordenação (ex: '1080p' -> 1080)"""
        try:
            if 'x' in resolution_str:
                # Formato 'widthxheight'
                return int(resolution_str.split('x')[1])
            elif 'p' in resolution_str:
                # Formato 'heightp'
                return int(resolution_str.replace('p', ''))
            else:
                return 0
        except (ValueError, IndexError):
            return 0
    
    @staticmethod
    def sort_resolutions(resolutions):
        """Ordena lista de resoluções por qualidade (menor para maior)"""
        return sorted(resolutions, key=AppUtils.extract_resolution_number)
    
    @staticmethod
    def get_file_size_mb(file_path):
        """Retorna tamanho do arquivo em MB"""
        try:
            if os.path.exists(file_path):
                return os.path.getsize(file_path) / (1024 * 1024)
            return 0
        except OSError:
            return 0
    
    @staticmethod
    def ensure_directory_exists(directory_path):
        """Garante que um diretório existe, criando-o se necessário"""
        try:
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)
            return True
        except OSError:
            return False

class UIConstants:
    """Constantes da interface do usuário"""
    
    # Cores dos temas
    THEME_LIGHT = {
        'bg': '#ffffff',
        'fg': '#000000',
        'select_bg': '#0078d4',
        'select_fg': '#ffffff'
    }
    
    THEME_DARK = {
        'bg': '#2d2d2d',
        'fg': '#ffffff',
        'select_bg': '#404040',
        'select_fg': '#ffffff'
    }
    
    # Dimensões da janela
    WINDOW_WIDTH = 1000
    WINDOW_HEIGHT = 750
    MIN_WIDTH = 900
    MIN_HEIGHT = 650
    
    # Configurações de layout
    PADDING = 10
    BUTTON_PADDING = 5
    
    # Textos padrão
    APP_TITLE = "Baixador de Vídeos do YouTube v2.1 - Histórico"
    NO_DIRECTORY_TEXT = "Diretório: Nenhum selecionado"
    
    # Configurações de progresso
    PROGRESS_BAR_LENGTH = 400
    DOWNLOAD_PROGRESS_LIMIT = 90  # Reservar 10% para merge
    MERGE_PROGRESS_START = 92
    MERGE_PROGRESS_END = 98
    
    # Configurações do mini-player
    MINI_PLAYER_THUMBNAIL_WIDTH = 160
    MINI_PLAYER_THUMBNAIL_HEIGHT = 90
    MINI_PLAYER_MAX_TITLE_LENGTH = 60
    MINI_PLAYER_FRAME_HEIGHT = 120
    
class AppConstants:
    """Constantes gerais da aplicação"""
    
    # Versão da aplicação
    VERSION = "2.1.5"
    
    # Configurações de download
    DEFAULT_RESOLUTION = "1080p"
    MAX_RETRIES = 10
    FRAGMENT_RETRIES = 10
    SOCKET_TIMEOUT = 30
    HTTP_CHUNK_SIZE = 10485760
    
    # Configurações de log
    DEFAULT_LOG_SIZE_MB = 250
    DEFAULT_LOG_RETENTION_DAYS = 30
    
    # Formatos suportados
    SUPPORTED_OUTPUT_FORMAT = 'mp4'
    SUPPORTED_AUDIO_FORMAT = 'mp3'
    
    # Qualidades de áudio disponíveis
    AUDIO_QUALITIES = ['best', '320', '256', '192', '128']
    DEFAULT_AUDIO_QUALITY = 'best'
    
    # Configurações de histórico
    DEFAULT_HISTORY_LIMIT = 50