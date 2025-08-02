import os
import json
from database_manager import DatabaseManager
from utils import UIConstants, AppConstants

class ConfigManager:
    """Gerenciador de configurações da aplicação"""
    
    def __init__(self, db_manager=None):
        """
        Inicializa o gerenciador de configurações
        
        Args:
            db_manager: Instância do DatabaseManager (opcional)
        """
        self.db_manager = db_manager or DatabaseManager()
        self.current_theme = 'light'
        self.current_resolution = AppConstants.DEFAULT_RESOLUTION
        self.auto_open_folder = False
        
        # Carregar configurações salvas
        self.load_settings()
    
    def load_settings(self):
        """Carrega configurações salvas do banco de dados"""
        try:
            # Carregar tema
            theme_setting = self.db_manager.get_setting('theme', 'light')
            self.current_theme = theme_setting
            
            # Carregar resolução padrão
            resolution_setting = self.db_manager.get_setting('default_resolution', AppConstants.DEFAULT_RESOLUTION)
            self.current_resolution = resolution_setting
            
            # Carregar configuração de auto-abertura de pasta
            auto_open_setting = self.db_manager.get_setting('auto_open_folder', 'false')
            self.auto_open_folder = auto_open_setting.lower() == 'true'
            
        except Exception as e:
            print(f"Erro ao carregar configurações: {e}")
            # Usar valores padrão em caso de erro
            self.current_theme = 'light'
            self.current_resolution = AppConstants.DEFAULT_RESOLUTION
            self.auto_open_folder = False
    
    def save_theme(self, theme):
        """
        Salva configuração de tema
        
        Args:
            theme (str): 'light' ou 'dark'
            
        Returns:
            bool: Sucesso da operação
        """
        try:
            if theme in ['light', 'dark']:
                self.db_manager.set_setting('theme', theme)
                self.current_theme = theme
                return True
            return False
        except Exception as e:
            print(f"Erro ao salvar tema: {e}")
            return False
    
    def save_resolution(self, resolution):
        """
        Salva resolução padrão
        
        Args:
            resolution (str): Resolução padrão
            
        Returns:
            bool: Sucesso da operação
        """
        try:
            self.db_manager.set_setting('default_resolution', resolution)
            self.current_resolution = resolution
            return True
        except Exception as e:
            print(f"Erro ao salvar resolução: {e}")
            return False
    
    def save_auto_open_folder(self, auto_open):
        """
        Salva configuração de auto-abertura de pasta
        
        Args:
            auto_open (bool): Se deve abrir pasta automaticamente
            
        Returns:
            bool: Sucesso da operação
        """
        try:
            value = 'true' if auto_open else 'false'
            self.db_manager.set_setting('auto_open_folder', value)
            self.auto_open_folder = auto_open
            return True
        except Exception as e:
            print(f"Erro ao salvar configuração de auto-abertura: {e}")
            return False
    
    def get_theme(self):
        """Retorna tema atual"""
        return self.current_theme
    
    def get_resolution(self):
        """Retorna resolução padrão atual"""
        return self.current_resolution
    
    def get_auto_open_folder(self):
        """Retorna configuração de auto-abertura de pasta"""
        return self.auto_open_folder
    
    def get_theme_colors(self, theme=None):
        """
        Retorna cores do tema especificado
        
        Args:
            theme (str): Tema desejado (opcional, usa atual se não especificado)
            
        Returns:
            dict: Dicionário com cores do tema
        """
        if theme is None:
            theme = self.current_theme
        
        if theme == 'dark':
            return UIConstants.THEME_DARK.copy()
        else:
            return UIConstants.THEME_LIGHT.copy()
    
    def apply_theme_to_widget(self, widget, theme=None):
        """
        Aplica tema a um widget específico
        
        Args:
            widget: Widget tkinter
            theme (str): Tema a aplicar (opcional)
        """
        colors = self.get_theme_colors(theme)
        widget_class = "Unknown"
        
        try:
            # Obter classe do widget
            widget_class = widget.__class__.__name__
            
            # Aplicar cores básicas
            widget.config(
                bg=colors['bg'],
                fg=colors['fg']
            )
            
            # Configurações específicas para alguns tipos de widget
            if widget_class in ['Listbox', 'Text']:
                widget.config(
                    selectbackground=colors['select_bg'],
                    selectforeground=colors['select_fg']
                )
            
        except Exception as e:
            # Alguns widgets podem não suportar todas as configurações
            print(f"Aviso ao aplicar tema ao widget {widget_class}: {e}")
    
    def apply_theme_to_children(self, parent_widget, theme=None):
        """
        Aplica tema recursivamente a todos os widgets filhos
        
        Args:
            parent_widget: Widget pai
            theme (str): Tema a aplicar (opcional)
        """
        colors = self.get_theme_colors(theme)
        
        def update_widget_recursive(widget):
            try:
                # Aplicar tema ao widget atual
                self.apply_theme_to_widget(widget, theme)
                
                # Aplicar recursivamente aos filhos
                for child in widget.winfo_children():
                    update_widget_recursive(child)
                    
            except Exception as e:
                print(f"Erro ao aplicar tema recursivamente: {e}")
        
        update_widget_recursive(parent_widget)
    
    def get_all_settings(self):
        """
        Retorna todas as configurações atuais
        
        Returns:
            dict: Dicionário com todas as configurações
        """
        return {
            'theme': self.current_theme,
            'default_resolution': self.current_resolution,
            'auto_open_folder': self.auto_open_folder
        }
    
    def export_settings(self, file_path):
        """
        Exporta configurações para arquivo JSON
        
        Args:
            file_path (str): Caminho do arquivo de destino
            
        Returns:
            bool: Sucesso da operação
        """
        try:
            settings = self.get_all_settings()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Erro ao exportar configurações: {e}")
            return False
    
    def import_settings(self, file_path):
        """
        Importa configurações de arquivo JSON
        
        Args:
            file_path (str): Caminho do arquivo de origem
            
        Returns:
            bool: Sucesso da operação
        """
        try:
            if not os.path.exists(file_path):
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            # Aplicar configurações importadas
            if 'theme' in settings:
                self.save_theme(settings['theme'])
            
            if 'default_resolution' in settings:
                self.save_resolution(settings['default_resolution'])
            
            if 'auto_open_folder' in settings:
                self.save_auto_open_folder(settings['auto_open_folder'])
            
            return True
            
        except Exception as e:
            print(f"Erro ao importar configurações: {e}")
            return False
    
    def reset_to_defaults(self):
        """
        Restaura configurações para valores padrão
        
        Returns:
            bool: Sucesso da operação
        """
        try:
            self.save_theme('light')
            self.save_resolution(AppConstants.DEFAULT_RESOLUTION)
            self.save_auto_open_folder(False)
            return True
        except Exception as e:
            print(f"Erro ao restaurar configurações padrão: {e}")
            return False
    
    def get_window_geometry(self):
        """
        Retorna geometria padrão da janela
        
        Returns:
            str: String de geometria para tkinter
        """
        return f"{UIConstants.WINDOW_WIDTH}x{UIConstants.WINDOW_HEIGHT}"
    
    def get_min_window_size(self):
        """
        Retorna tamanho mínimo da janela
        
        Returns:
            tuple: (largura, altura)
        """
        return (UIConstants.MIN_WIDTH, UIConstants.MIN_HEIGHT)
    
    def should_auto_open_folder(self):
        """
        Verifica se deve abrir pasta automaticamente após download
        
        Returns:
            bool: True se deve abrir automaticamente
        """
        return self.auto_open_folder