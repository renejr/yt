import os
import subprocess
from datetime import datetime
from database_manager import DatabaseManager
from utils import AppUtils, AppConstants

class HistoryManager:
    """Gerenciador do histórico de downloads"""
    
    def __init__(self, db_manager=None, log_manager=None):
        """
        Inicializa o gerenciador de histórico
        
        Args:
            db_manager: Instância do DatabaseManager (opcional)
            log_manager: Instância do LogManager (opcional)
        """
        self.db_manager = db_manager or DatabaseManager()
        self.log_manager = log_manager
        
    def add_download_to_history(self, download_data):
        """
        Adiciona um download ao histórico
        
        Args:
            download_data (dict): Dados do download
            
        Returns:
            tuple: (sucesso, id_do_download_ou_erro)
        """
        try:
            # Validar dados obrigatórios
            if not download_data.get('url'):
                return False, "URL é obrigatória"
            
            # Preparar dados com valores padrão
            prepared_data = self._prepare_download_data(download_data)
            
            # Adicionar ao banco
            download_id = self.db_manager.add_download(prepared_data)
            
            if self.log_manager:
                self.log_manager.log_info(
                    f"Download adicionado ao histórico: {prepared_data.get('title', 'N/A')}"
                )
            
            return True, download_id
            
        except Exception as e:
            error_msg = f"Erro ao adicionar download ao histórico: {str(e)}"
            if self.log_manager:
                self.log_manager.log_error(e, "Histórico")
            return False, error_msg
    
    def _prepare_download_data(self, download_data):
        """Prepara dados do download com valores padrão"""
        return {
            'url': download_data.get('url', ''),
            'title': download_data.get('title', 'Título não disponível'),
            'duration': download_data.get('duration', 'N/A'),
            'resolution': download_data.get('resolution', 'N/A'),
            'file_size': download_data.get('file_size', 'N/A'),
            'download_path': download_data.get('download_path', ''),
            'status': download_data.get('status', 'completed'),
            'thumbnail_url': download_data.get('thumbnail_url', ''),
            'uploader': download_data.get('uploader', 'N/A'),
            'view_count': download_data.get('view_count', 0),
            'like_count': download_data.get('like_count', 0),
            'description': download_data.get('description', '')
        }
    
    def get_recent_downloads(self, limit=None):
        """
        Obtém downloads recentes
        
        Args:
            limit (int): Número máximo de downloads (opcional)
            
        Returns:
            list: Lista de downloads
        """
        try:
            if limit is None:
                limit = AppConstants.DEFAULT_HISTORY_LIMIT
            
            downloads = self.db_manager.get_recent_downloads(limit)
            
            # Formatar dados para exibição
            formatted_downloads = []
            for download in downloads:
                formatted_download = self._format_download_for_display(download)
                formatted_downloads.append(formatted_download)
            
            return formatted_downloads
            
        except Exception as e:
            if self.log_manager:
                self.log_manager.log_error(e, "Erro ao obter histórico")
            return []
    
    def _format_download_for_display(self, download):
        """Formata dados do download para exibição na interface"""
        formatted = download.copy()
        
        # Formatar duração
        if 'duration' in formatted:
            formatted['duration_formatted'] = AppUtils.format_duration(formatted['duration'])
        
        # Formatar visualizações
        if 'view_count' in formatted:
            formatted['view_count_formatted'] = AppUtils.format_view_count(formatted['view_count'])
        
        # Formatar data
        if 'timestamp' in formatted:
            try:
                # Assumindo que timestamp está em formato ISO
                dt = datetime.fromisoformat(formatted['timestamp'].replace('Z', '+00:00'))
                formatted['date_formatted'] = dt.strftime('%d/%m/%Y %H:%M')
            except:
                formatted['date_formatted'] = formatted.get('timestamp', 'N/A')
        
        # Truncar título se muito longo
        if 'title' in formatted:
            formatted['title_short'] = AppUtils.truncate_text(formatted['title'], 50)
        
        return formatted
    
    def clear_history(self):
        """
        Limpa todo o histórico de downloads
        
        Returns:
            bool: Sucesso da operação
        """
        try:
            success = self.db_manager.clear_history()
            
            if success and self.log_manager:
                self.log_manager.log_info("Histórico de downloads limpo")
            
            return success
            
        except Exception as e:
            if self.log_manager:
                self.log_manager.log_error(e, "Erro ao limpar histórico")
            return False
    
    def remove_download_from_history(self, download_id):
        """
        Remove um download específico do histórico
        
        Args:
            download_id (int): ID do download
            
        Returns:
            bool: Sucesso da operação
        """
        try:
            # Obter dados do download antes de remover
            download = self.db_manager.get_download_by_id(download_id)
            
            if download:
                success = self.db_manager.remove_download(download_id)
                
                if success and self.log_manager:
                    title = download.get('title', 'N/A')
                    self.log_manager.log_info(f"Download removido do histórico: {title}")
                
                return success
            else:
                return False
                
        except Exception as e:
            if self.log_manager:
                self.log_manager.log_error(e, "Erro ao remover download do histórico")
            return False
    
    def open_download_file(self, download_id):
        """
        Abre o arquivo de um download específico
        
        Args:
            download_id (int): ID do download
            
        Returns:
            tuple: (sucesso, mensagem)
        """
        try:
            download = self.db_manager.get_download_by_id(download_id)
            
            if not download:
                return False, "Download não encontrado no histórico"
            
            file_path = download.get('download_path', '')
            
            if not file_path or not os.path.exists(file_path):
                return False, "Arquivo não encontrado no disco"
            
            # Abrir arquivo com aplicativo padrão
            os.startfile(file_path)
            
            if self.log_manager:
                self.log_manager.log_info(f"Arquivo aberto: {file_path}")
            
            return True, "Arquivo aberto com sucesso"
            
        except Exception as e:
            error_msg = f"Erro ao abrir arquivo: {str(e)}"
            if self.log_manager:
                self.log_manager.log_error(e, "Erro ao abrir arquivo")
            return False, error_msg
    
    def open_download_folder(self, download_id):
        """
        Abre a pasta de um download específico
        
        Args:
            download_id (int): ID do download
            
        Returns:
            tuple: (sucesso, mensagem)
        """
        try:
            download = self.db_manager.get_download_by_id(download_id)
            
            if not download:
                return False, "Download não encontrado no histórico"
            
            file_path = download.get('download_path', '')
            
            if not file_path:
                return False, "Caminho do arquivo não disponível"
            
            # Obter diretório do arquivo
            folder_path = os.path.dirname(file_path)
            
            if not os.path.exists(folder_path):
                return False, "Pasta não encontrada no disco"
            
            # Abrir pasta no explorador
            os.startfile(folder_path)
            
            if self.log_manager:
                self.log_manager.log_info(f"Pasta aberta: {folder_path}")
            
            return True, "Pasta aberta com sucesso"
            
        except Exception as e:
            error_msg = f"Erro ao abrir pasta: {str(e)}"
            if self.log_manager:
                self.log_manager.log_error(e, "Erro ao abrir pasta")
            return False, error_msg
    
    def copy_download_url(self, download_id):
        """
        Copia URL de um download para a área de transferência
        
        Args:
            download_id (int): ID do download
            
        Returns:
            tuple: (sucesso, mensagem)
        """
        try:
            download = self.db_manager.get_download_by_id(download_id)
            
            if not download:
                return False, "Download não encontrado no histórico"
            
            url = download.get('url', '')
            
            if not url:
                return False, "URL não disponível"
            
            # Copiar para área de transferência
            import tkinter as tk
            temp_root = tk.Tk()
            temp_root.withdraw()  # Esconder janela completamente
            temp_root.attributes('-alpha', 0)  # Tornar invisível
            temp_root.clipboard_clear()
            temp_root.clipboard_append(url)
            temp_root.update()  # Necessário para garantir que a cópia funcione
            temp_root.destroy()  # Destruir janela temporária
            
            if self.log_manager:
                self.log_manager.log_info(f"URL copiada: {url}")
            
            return True, "URL copiada para a área de transferência"
            
        except Exception as e:
            error_msg = f"Erro ao copiar URL: {str(e)}"
            if self.log_manager:
                self.log_manager.log_error(e, "Erro ao copiar URL")
            return False, error_msg
    
    def get_download_by_id(self, download_id):
        """
        Obtém dados de um download específico
        
        Args:
            download_id (int): ID do download
            
        Returns:
            dict or None: Dados do download
        """
        try:
            return self.db_manager.get_download_by_id(download_id)
        except Exception as e:
            if self.log_manager:
                self.log_manager.log_error(e, "Erro ao obter download por ID")
            return None
    
    def get_history_stats(self):
        """
        Obtém estatísticas do histórico
        
        Returns:
            dict: Estatísticas do histórico
        """
        try:
            downloads = self.get_recent_downloads(limit=1000)  # Pegar mais para estatísticas
            
            total_downloads = len(downloads)
            total_size_mb = 0
            resolutions = {}
            
            for download in downloads:
                # Contar tamanho total (se disponível)
                file_path = download.get('download_path', '')
                if file_path and os.path.exists(file_path):
                    total_size_mb += AppUtils.get_file_size_mb(file_path)
                
                # Contar resoluções
                resolution = download.get('resolution', 'N/A')
                resolutions[resolution] = resolutions.get(resolution, 0) + 1
            
            return {
                'total_downloads': total_downloads,
                'total_size_mb': round(total_size_mb, 2),
                'total_size_gb': round(total_size_mb / 1024, 2),
                'resolutions': resolutions,
                'most_used_resolution': max(resolutions.items(), key=lambda x: x[1])[0] if resolutions else 'N/A'
            }
            
        except Exception as e:
            if self.log_manager:
                self.log_manager.log_error(e, "Erro ao obter estatísticas")
            return {
                'total_downloads': 0,
                'total_size_mb': 0,
                'total_size_gb': 0,
                'resolutions': {},
                'most_used_resolution': 'N/A'
            }