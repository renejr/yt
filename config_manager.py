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
        
        # Configurações da API
        self.api_enabled = False
        self.api_host = '127.0.0.1'
        self.api_port = 5000
        self.api_debug = False
        
        # Configuração do arquivo de cookies
        self.cookies_file_path = None
        
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
            
            # Carregar configurações da API
            api_enabled_setting = self.db_manager.get_setting('api_enabled', 'false')
            self.api_enabled = api_enabled_setting.lower() == 'true'
            
            api_host_setting = self.db_manager.get_setting('api_host', '127.0.0.1')
            self.api_host = api_host_setting
            
            api_port_setting = self.db_manager.get_setting('api_port', '5000')
            try:
                self.api_port = int(api_port_setting)
            except ValueError:
                self.api_port = 5000
            
            api_debug_setting = self.db_manager.get_setting('api_debug', 'false')
            self.api_debug = api_debug_setting.lower() == 'true'
            
            # Carregar caminho do arquivo de cookies
            cookies_path_setting = self.db_manager.get_setting('cookies_file_path')
            self.cookies_file_path = cookies_path_setting
            
        except Exception as e:
            print(f"Erro ao carregar configurações: {e}")
            # Usar valores padrão em caso de erro
            self.current_theme = 'light'
            self.current_resolution = AppConstants.DEFAULT_RESOLUTION
            self.auto_open_folder = False
            self.api_enabled = False
            self.api_host = '127.0.0.1'
            self.api_port = 5000
            self.api_debug = False
            self.cookies_file_path = None
    
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
    
    def save_api_enabled(self, enabled):
        """
        Salva configuração de API habilitada
        
        Args:
            enabled (bool): Se a API deve estar habilitada
            
        Returns:
            bool: Sucesso da operação
        """
        try:
            value = 'true' if enabled else 'false'
            self.db_manager.set_setting('api_enabled', value)
            self.api_enabled = enabled
            return True
        except Exception as e:
            print(f"Erro ao salvar configuração da API: {e}")
            return False
    
    def save_api_host(self, host):
        """
        Salva host da API
        
        Args:
            host (str): Host da API
            
        Returns:
            bool: Sucesso da operação
        """
        try:
            self.db_manager.set_setting('api_host', host)
            self.api_host = host
            return True
        except Exception as e:
            print(f"Erro ao salvar host da API: {e}")
            return False
    
    def save_api_port(self, port):
        """
        Salva porta da API
        
        Args:
            port (int): Porta da API
            
        Returns:
            bool: Sucesso da operação
        """
        try:
            self.db_manager.set_setting('api_port', str(port))
            self.api_port = port
            return True
        except Exception as e:
            print(f"Erro ao salvar porta da API: {e}")
            return False
    
    def save_api_debug(self, debug):
        """
        Salva configuração de debug da API
        
        Args:
            debug (bool): Se o debug da API deve estar habilitado
            
        Returns:
            bool: Sucesso da operação
        """
        try:
            value = 'true' if debug else 'false'
            self.db_manager.set_setting('api_debug', value)
            self.api_debug = debug
            return True
        except Exception as e:
            print(f"Erro ao salvar configuração de debug da API: {e}")
            return False
    
    def get_api_enabled(self):
        """Retorna se a API está habilitada"""
        return self.api_enabled
    
    def get_api_host(self):
        """Retorna host da API"""
        return self.api_host
    
    def get_api_port(self):
        """Retorna porta da API"""
        return self.api_port
    
    def get_api_debug(self):
        """Retorna se o debug da API está habilitado"""
        return self.api_debug
    
    def save_cookies_file_path(self, path):
        """
        Salva o caminho do arquivo de cookies.
        
        Args:
            path (str): Caminho do arquivo de cookies.
            
        Returns:
            bool: Sucesso da operação.
        """
        try:
            self.db_manager.set_setting('cookies_file_path', path)
            self.cookies_file_path = path
            return True
        except Exception as e:
            print(f"Erro ao salvar o caminho do arquivo de cookies: {e}")
            return False

    def get_cookies_file_path(self):
        """Retorna o caminho do arquivo de cookies."""
        return self.cookies_file_path
    
    def get_api_config(self):
        """
        Retorna todas as configurações da API
        
        Returns:
            dict: Dicionário com configurações da API
        """
        return {
            'enabled': self.api_enabled,
            'host': self.api_host,
            'port': self.api_port,
            'debug': self.api_debug,
            'cookies_file_path': self.cookies_file_path
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
            
            # Aplicar configurações da API
            if 'api_enabled' in settings:
                self.save_api_enabled(settings['api_enabled'])
            
            if 'api_host' in settings:
                self.save_api_host(settings['api_host'])
            
            if 'api_port' in settings:
                self.save_api_port(settings['api_port'])
            
            if 'api_debug' in settings:
                self.save_api_debug(settings['api_debug'])
            
            if 'cookies_file_path' in settings:
                self.save_cookies_file_path(settings['cookies_file_path'])
            
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
            self.save_api_enabled(False)
            self.save_api_host('127.0.0.1')
            self.save_api_port(5000)
            self.save_api_debug(False)
            self.save_cookies_file_path(None)
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
    
    def apply_theme_to_children(self, root_widget, theme):
        """
        Aplica o tema selecionado a todos os widgets da aplicação
        
        Args:
            root_widget: Widget raiz da aplicação
            theme (str): Tema a ser aplicado ('light' ou 'dark')
        """
        try:
            import tkinter as tk
            from tkinter import ttk
            
            if theme == 'dark':
                # Tema escuro
                bg_color = '#2b2b2b'
                fg_color = '#ffffff'
                select_bg = '#404040'
                active_bg = '#505050'
                active_fg = '#ffffff'
            else:
                # Tema claro (padrão)
                bg_color = '#f0f0f0'
                fg_color = '#000000'
                select_bg = '#e0e0e0'
                active_bg = '#ffffff'
                active_fg = '#000000'
            
            # Aplicar cores ao widget raiz
            if hasattr(root_widget, 'configure'):
                try:
                    root_widget.configure(bg=bg_color)
                except:
                    pass  # Alguns widgets podem não suportar bg
            
            # Atualizar estilo do notebook com configurações completas
            style = ttk.Style()
            
            # Configurar o notebook principal
            style.configure('TNotebook', background=bg_color, borderwidth=0)
            
            # Configurar as abas em diferentes estados
            style.configure('TNotebook.Tab', 
                           background=select_bg, 
                           foreground=fg_color,
                           padding=[10, 5],
                           borderwidth=1)
            
            # Configurar aba ativa/selecionada
            style.map('TNotebook.Tab',
                     background=[('selected', active_bg), ('active', active_bg)],
                     foreground=[('selected', active_fg), ('active', active_fg)],
                     expand=[('selected', [1, 1, 1, 0])])
            
            # Aplicar tema recursivamente aos widgets filhos
            self._update_widget_theme(root_widget, bg_color, fg_color)
            
            print(f"[INFO] Tema {theme} aplicado com sucesso")
            
        except Exception as e:
            print(f"[ERRO] Erro ao aplicar tema: {e}")
    
    def _update_widget_theme(self, parent, bg_color, fg_color):
        """
        Atualiza recursivamente todos os widgets filhos com o tema
        
        Args:
            parent: Widget pai
            bg_color (str): Cor de fundo
            fg_color (str): Cor do texto
        """
        try:
            # Verificar se o widget ainda existe
            if not hasattr(parent, 'winfo_children'):
                return
                
            for child in parent.winfo_children():
                try:
                    widget_class = child.winfo_class()
                    
                    if widget_class in ['Frame', 'Toplevel', 'LabelFrame']:
                        child.configure(bg=bg_color)
                        # Recursão para widgets filhos
                        self._update_widget_theme(child, bg_color, fg_color)
                    elif widget_class in ['Label', 'Button', 'Checkbutton', 'Radiobutton']:
                        try:
                            child.configure(bg=bg_color, fg=fg_color)
                        except:
                            pass  # Alguns widgets podem não suportar essas opções
                    elif widget_class == 'Entry':
                        try:
                            child.configure(bg=bg_color, fg=fg_color, insertbackground=fg_color)
                        except:
                            pass
                    elif widget_class == 'Text':
                        try:
                            child.configure(bg=bg_color, fg=fg_color, insertbackground=fg_color)
                        except:
                            pass
                    elif widget_class == 'Listbox':
                        try:
                            child.configure(bg=bg_color, fg=fg_color, selectbackground=bg_color)
                        except:
                            pass
                    
                    # Continuar recursão para widgets que podem ter filhos
                    if hasattr(child, 'winfo_children'):
                        self._update_widget_theme(child, bg_color, fg_color)
                        
                except Exception as widget_error:
                    # Continuar mesmo se um widget específico falhar
                    continue
                    
        except Exception as e:
            print(f"[ERRO] Erro ao atualizar widgets do tema: {e}")