import tkinter as tk
from tkinter import ttk, messagebox

from utils import AppUtils, UIConstants

class ConfigTab:
    """Aba de configurações"""
    
    def __init__(self, parent, config_manager, theme_callback):
        self.parent = parent
        self.config_manager = config_manager
        self.theme_callback = theme_callback
        
        self.frame = tk.Frame(parent)
        self.create_widgets()
        self.setup_layout()
        self.load_current_settings()
    
    def create_widgets(self):
        """Cria widgets da aba de configurações"""
        # Seção de tema
        self.theme_frame = tk.LabelFrame(self.frame, text="Aparência", padx=10, pady=10)
        
        self.theme_var = tk.StringVar()
        self.theme_light_radio = tk.Radiobutton(
            self.theme_frame,
            text="Tema Claro",
            variable=self.theme_var,
            value="light",
            command=self.on_theme_change
        )
        self.theme_dark_radio = tk.Radiobutton(
            self.theme_frame,
            text="Tema Escuro",
            variable=self.theme_var,
            value="dark",
            command=self.on_theme_change
        )
        
        # Seção de download
        self.download_frame = tk.LabelFrame(self.frame, text="Download", padx=10, pady=10)
        
        self.resolution_label = tk.Label(self.download_frame, text="Resolução Padrão:")
        self.resolution_var = tk.StringVar()
        self.resolution_combo = ttk.Combobox(
            self.download_frame,
            textvariable=self.resolution_var,
            values=['360p', '480p', '720p', '1080p', '1440p', '2160p'],
            state='readonly'
        )
        self.resolution_combo.bind('<<ComboboxSelected>>', self.on_resolution_change)
        
        self.auto_open_var = tk.BooleanVar()
        self.auto_open_check = tk.Checkbutton(
            self.download_frame,
            text="Abrir pasta automaticamente após download",
            variable=self.auto_open_var,
            command=self.on_auto_open_change
        )
        
        # Botões de ação
        self.buttons_frame = tk.Frame(self.frame)
        
        self.reset_button = tk.Button(
            self.buttons_frame,
            text="Restaurar Padrões",
            command=self.reset_to_defaults
        )
    
    def setup_layout(self):
        """Configura layout da aba"""
        self.frame.columnconfigure(0, weight=1)
        
        # Seção de tema
        self.theme_frame.grid(row=0, column=0, sticky='ew', padx=UIConstants.PADDING, pady=UIConstants.PADDING)
        self.theme_light_radio.grid(row=0, column=0, sticky='w')
        self.theme_dark_radio.grid(row=1, column=0, sticky='w')
        
        # Seção de download
        self.download_frame.grid(row=1, column=0, sticky='ew', padx=UIConstants.PADDING, pady=UIConstants.PADDING)
        self.resolution_label.grid(row=0, column=0, sticky='w', pady=(0, 5))
        self.resolution_combo.grid(row=0, column=1, sticky='w', padx=(10, 0), pady=(0, 5))
        self.auto_open_check.grid(row=1, column=0, columnspan=2, sticky='w')
        
        # Botões
        self.buttons_frame.grid(row=2, column=0, sticky='ew', padx=UIConstants.PADDING, pady=UIConstants.PADDING)
        self.reset_button.pack(side=tk.LEFT)
    
    def load_current_settings(self):
        """Carrega configurações atuais"""
        # Tema
        self.theme_var.set(self.config_manager.get_theme())
        
        # Resolução
        self.resolution_var.set(self.config_manager.get_resolution())
        
        # Auto-abertura
        self.auto_open_var.set(self.config_manager.get_auto_open_folder())
    
    def on_theme_change(self):
        """Callback para mudança de tema"""
        new_theme = self.theme_var.get()
        self.config_manager.save_theme(new_theme)
        self.theme_callback(new_theme)
    
    def on_resolution_change(self, event=None):
        """Callback para mudança de resolução"""
        new_resolution = self.resolution_var.get()
        self.config_manager.save_resolution(new_resolution)
    
    def on_auto_open_change(self):
        """Callback para mudança de auto-abertura"""
        new_auto_open = self.auto_open_var.get()
        self.config_manager.save_auto_open_folder(new_auto_open)
    
    def reset_to_defaults(self):
        """Restaura configurações padrão"""
        if messagebox.askyesno("Confirmar", "Deseja restaurar todas as configurações para os valores padrão?"):
            success = self.config_manager.reset_to_defaults()
            if success:
                self.load_current_settings()
                self.theme_callback(self.config_manager.get_theme())
                AppUtils.show_info_message("Sucesso", "Configurações restauradas para os valores padrão")
