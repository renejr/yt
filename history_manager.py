import os
from datetime import datetime, timedelta
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
        
        # Estrutura padrão de paginação
        self.DEFAULT_PAGINATION = {
            'current_page': 1,
            'per_page': 50,
            'total_pages': 0,
            'total_items': 0,
            'has_next': False,
            'has_previous': False
        }
    
    def _handle_exception(self, exception, operation_name, default_return=None):
        """
        Método auxiliar para tratamento padronizado de exceções
        
        Args:
            exception: A exceção capturada
            operation_name: Nome da operação que falhou
            default_return: Valor padrão a retornar em caso de erro
            
        Returns:
            O valor padrão especificado
        """
        error_msg = f"Erro em {operation_name}: {str(exception)}"
        if self.log_manager:
            self.log_manager.log_error(exception, error_msg)
        return default_return
    
    def _validate_download_exists(self, download_id):
        """
        Valida se um download existe no banco de dados
        
        Args:
            download_id: ID do download a validar
            
        Returns:
            tuple: (download_data, error_message) - download_data é None se não encontrado
        """
        try:
            download = self.db_manager.get_download_by_id(download_id)
            if not download:
                return None, "Download não encontrado no histórico"
            return download, None
        except Exception as e:
            return None, f"Erro ao buscar download: {str(e)}"
        
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
            
            # Armazenar o último ID para referência
            self._last_download_id = download_id
            
            if self.log_manager:
                self.log_manager.log_info(
                    f"Download adicionado ao histórico: {prepared_data.get('title', 'N/A')} (ID: {download_id})"
                )
            
            return True, download_id
            
        except Exception as e:
            error_msg = f"Erro ao adicionar download ao histórico: {str(e)}"
            if self.log_manager:
                self.log_manager.log_error(e, "Histórico")
            return False, error_msg
    
    def get_last_download_id(self):
        """
        Obtém o ID do último download adicionado ao histórico
        
        Returns:
            int: ID do último download ou None se não houver
        """
        return getattr(self, '_last_download_id', None)
    
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
        Obtém downloads recentes (método legado)
        
        Args:
            limit (int): Número máximo de downloads (opcional)
            
        Returns:
            list: Lista de downloads
        """
        try:
            if limit is None:
                limit = AppConstants.DEFAULT_HISTORY_LIMIT
            
            # Usar método paginado para compatibilidade
            result = self.get_downloads_paginated(page=1, per_page=limit)
            return result['downloads']
            
        except Exception as e:
            return self._handle_exception(e, "obter downloads recentes", [])
    
    def filter_downloads_by_criteria(self, criteria_type, criteria_value, page=1, per_page=50):
        """
        Método genérico para filtrar downloads por diferentes critérios
        
        Args:
            criteria_type (str): Tipo do critério ('resolution', 'status', etc.)
            criteria_value (str): Valor do critério para filtrar
            page (int): Página atual
            per_page (int): Itens por página
            
        Returns:
            dict: Resultado paginado com downloads filtrados
        """
        filters = {criteria_type: criteria_value}
        return self.get_downloads_paginated(page, per_page, filters)
    
    def filter_downloads_by_resolution(self, resolution, page=1, per_page=50):
        """
        Filtra downloads por resolução
        
        Args:
            resolution (str): Resolução para filtrar
            page (int): Página atual
            per_page (int): Itens por página
            
        Returns:
            dict: Resultado paginado com downloads filtrados
        """
        return self.filter_downloads_by_criteria('resolution', resolution, page, per_page)
    
    def filter_downloads_by_status(self, status, page=1, per_page=50):
        """
        Filtra downloads por status
        
        Args:
            status (str): Status para filtrar
            page (int): Página atual
            per_page (int): Itens por página
            
        Returns:
            dict: Resultado paginado com downloads filtrados
        """
        return self.filter_downloads_by_criteria('status', status, page, per_page)
    
    def get_downloads_paginated(self, page=1, per_page=50, filters=None):
        """
        Obtém downloads com paginação e filtros
        
        Args:
            page (int): Número da página (começando em 1)
            per_page (int): Número de itens por página
            filters (dict): Filtros opcionais (search_query, resolution, status, period, etc.)
            
        Returns:
            dict: Dados paginados com downloads e informações de paginação
        """
        try:
            # Processar filtros e converter período em datas
            processed_filters = self._process_filters(filters) if filters else None
            
            # Obter dados paginados do banco
            result = self.db_manager.get_downloads_paginated(page, per_page, processed_filters)
            
            # Formatar downloads para exibição
            formatted_downloads = []
            for download in result['downloads']:
                formatted_download = self._format_download_for_display(download)
                formatted_downloads.append(formatted_download)
            
            # Criar estrutura de paginação baseada no padrão
            pagination = self.DEFAULT_PAGINATION.copy()
            pagination.update(result['pagination'])
            
            # Retornar resultado formatado
            return {
                'downloads': formatted_downloads,
                'pagination': pagination
            }
            
        except Exception as e:
            return self._handle_exception(e, "obter downloads paginados", {
                'downloads': [],
                'pagination': self.DEFAULT_PAGINATION.copy()
            })
    
    def get_total_downloads_count(self, filters=None):
        """
        Obtém contagem total de downloads com filtros opcionais
        
        Args:
            filters (dict): Filtros opcionais
            
        Returns:
            int: Número total de downloads
        """
        try:
            # Processar filtros e converter período em datas
            processed_filters = self._process_filters(filters) if filters else None
            return self.db_manager.get_total_downloads_count(processed_filters)
        except Exception as e:
            if self.log_manager:
                self.log_manager.log_error(e, "Erro ao obter contagem de downloads")
            return 0
    
    def search_downloads(self, search_query, page=1, per_page=50):
        """
        Busca downloads por termo de pesquisa
        
        Args:
            search_query (str): Termo de busca
            page (int): Página atual
            per_page (int): Itens por página
            
        Returns:
            dict: Resultado paginado com downloads encontrados
        """
        filters = {'search_query': search_query}
        return self.get_downloads_paginated(page, per_page, filters)
    
    def get_all_downloads_filtered(self, filters=None):
        """
        Obtém todos os downloads filtrados (sem paginação) para exportação
        
        Args:
            filters (dict): Filtros a serem aplicados
            
        Returns:
            list: Lista de todos os downloads que atendem aos filtros
        """
        try:
            # Processar filtros e converter período em datas
            processed_filters = self._process_filters(filters) if filters else None
            
            # Obter todos os downloads do banco de dados
            downloads = self.db_manager.get_all_downloads_filtered(processed_filters)
            
            # Formatar dados para exibição
            formatted_downloads = []
            for download in downloads:
                formatted = self._format_download_for_display(download)
                formatted_downloads.append(formatted)
            
            return formatted_downloads
            
        except Exception as e:
            if self.log_manager:
                self.log_manager.log_error(e, "Erro ao obter downloads filtrados para exportação")
            return []
    
    def _process_filters(self, filters):
        """
        Processa filtros e converte período em datas específicas
        
        Args:
            filters (dict): Filtros originais
            
        Returns:
            dict: Filtros processados com datas convertidas
        """
        if not filters:
            return None
        
        processed_filters = filters.copy()
        
        # Converter filtro de resolução (Audio -> music)
        if 'resolution' in processed_filters:
            resolution = processed_filters['resolution']
            if resolution == 'Audio':
                processed_filters['resolution'] = 'music'
        
        # Converter filtro de período em datas
        if 'period' in processed_filters:
            period = processed_filters.pop('period')
            date_range = self._get_date_range_for_period(period)
            
            if date_range:
                processed_filters.update(date_range)
        
        return processed_filters
    
    def _get_date_range_for_period(self, period):
        """
        Converte período em intervalo de datas
        
        Args:
            period (str): Período selecionado
            
        Returns:
            dict: Dicionário com date_from e/ou date_to
        """
        now = datetime.now()
        
        if period == "Hoje":
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return {
                'date_from': today_start.strftime('%Y-%m-%d %H:%M:%S')
            }
        
        elif period == "Última semana":
            week_ago = now - timedelta(days=7)
            return {
                'date_from': week_ago.strftime('%Y-%m-%d %H:%M:%S')
            }
        
        elif period == "Último mês":
            month_ago = now - timedelta(days=30)
            return {
                'date_from': month_ago.strftime('%Y-%m-%d %H:%M:%S')
            }
        
        elif period == "Últimos 3 meses":
            three_months_ago = now - timedelta(days=90)
            return {
                'date_from': three_months_ago.strftime('%Y-%m-%d %H:%M:%S')
            }
        
        elif period == "Último ano":
            year_ago = now - timedelta(days=365)
            return {
                'date_from': year_ago.strftime('%Y-%m-%d %H:%M:%S')
            }
        
        # Para "Todos" ou período não reconhecido, não adicionar filtro de data
        return None
    
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
            return self._handle_exception(e, "limpar histórico", False)
    
    def remove_download_from_history(self, download_id):
        """
        Remove um download específico do histórico
        
        Args:
            download_id (int): ID do download a ser removido
            
        Returns:
            bool: True se removido com sucesso, False caso contrário
        """
        try:
            # Verificar se o download existe
            download, error_msg = self._validate_download_exists(download_id)
            
            if not download:
                if self.log_manager:
                    self.log_manager.log_warning(f"Tentativa de remover download inexistente: {download_id}")
                return False
            
            # Remover do banco de dados
            success = self.db_manager.remove_download(download_id)
            
            if success and self.log_manager:
                self.log_manager.log_info(f"Download removido do histórico: {download_id}")
            
            return success
            
        except Exception as e:
            return self._handle_exception(e, f"remover download {download_id} do histórico", False)
    
    def open_download_file(self, download_id):
        """
        Abre o arquivo de um download específico
        
        Args:
            download_id (int): ID do download
            
        Returns:
            tuple: (sucesso, mensagem)
        """
        try:
            # Validar se download existe
            download, error_msg = self._validate_download_exists(download_id)
            if not download:
                return False, error_msg
            
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
            # Validar se download existe
            download, error_msg = self._validate_download_exists(download_id)
            if not download:
                return False, error_msg
            
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
            # Validar se download existe
            download, error_msg = self._validate_download_exists(download_id)
            if not download:
                return False, error_msg
            
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
            return self._handle_exception(e, "obter estatísticas do histórico", {
                'total_downloads': 0,
                'total_size_mb': 0,
                'total_size_gb': 0,
                'resolutions': {},
                'most_used_resolution': 'N/A'
            })