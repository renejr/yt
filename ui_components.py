import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import threading
import os
import webbrowser
import requests
from PIL import Image, ImageTk
from io import BytesIO
import csv
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
from utils import AppUtils, UIConstants, AppConstants
from analytics_manager import AnalyticsManager, RecommendationEngine

class MainApplication:
    """Aplicação principal com interface gráfica"""
    
    def __init__(self, download_manager, config_manager, history_manager, log_manager):
        """
        Inicializa a aplicação principal
        
        Args:
            download_manager: Instância do DownloadManager
            config_manager: Instância do ConfigManager
            history_manager: Instância do HistoryManager
            log_manager: Instância do LogManager
        """
        self.download_manager = download_manager
        self.config_manager = config_manager
        self.history_manager = history_manager
        self.log_manager = log_manager
        
        # Configurar callbacks do download_manager
        self.download_manager.progress_callback = self.progress_hook
        self.download_manager.postprocessor_callback = self.postprocessor_hook
        
        # Estado da aplicação
        self.current_resolutions = []
        
        # Criar interface
        self.setup_main_window()
        self.create_widgets()
        self.apply_initial_theme()
        
        self.log_manager.log_info("Aplicação iniciada")
    
    def setup_main_window(self):
        """Configura a janela principal"""
        self.root = tk.Tk()
        self.root.title(UIConstants.APP_TITLE)
        self.root.geometry(self.config_manager.get_window_geometry())
        
        min_width, min_height = self.config_manager.get_min_window_size()
        self.root.minsize(min_width, min_height)
        
        # Maximizar a janela ao iniciar
        self.root.state('zoomed')  # Windows
        
        # Configurar fechamento da aplicação
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_widgets(self):
        """Cria todos os widgets da interface"""
        # Criar notebook para abas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=UIConstants.PADDING, pady=UIConstants.PADDING)
        
        # Criar abas
        self.create_download_tab()
        self.create_history_tab()
        self.create_analytics_tab()
        self.create_config_tab()
    
    def create_download_tab(self):
        """Cria a aba de download"""
        self.download_frame = DownloadTab(
            self.notebook, 
            self.download_manager, 
            self.config_manager,
            self.history_manager,
            self.log_manager,
            main_app=self
        )
        self.notebook.add(self.download_frame.frame, text="📥 Download")
    
    def create_history_tab(self):
        """Cria a aba de histórico"""
        self.history_frame = HistoryTab(
            self.notebook,
            self.history_manager,
            self.log_manager
        )
        self.notebook.add(self.history_frame.frame, text="📋 Histórico")
    
    def create_analytics_tab(self):
        """Cria a aba de análise e estatísticas"""
        self.analytics_frame = AnalyticsTab(
            self.notebook,
            self.history_manager,
            self.log_manager
        )
        self.notebook.add(self.analytics_frame.frame, text="📊 Analytics")
    
    def create_config_tab(self):
        """Cria a aba de configurações"""
        self.config_frame = ConfigTab(
            self.notebook,
            self.config_manager,
            self.apply_theme_callback
        )
        self.notebook.add(self.config_frame.frame, text="⚙️ Configurações")
    
    def apply_initial_theme(self):
        """Aplica tema inicial baseado nas configurações"""
        self.apply_theme_callback(self.config_manager.get_theme())
    
    def apply_theme_callback(self, theme):
        """Callback para aplicar tema em toda a aplicação"""
        self.config_manager.save_theme(theme)
        self.config_manager.apply_theme_to_children(self.root, theme)
    
    def progress_hook(self, d):
        """Hook para progresso do download"""
        if hasattr(self.download_frame, 'update_progress'):
            self.root.after(0, lambda: self.download_frame.update_progress(d))
    
    def postprocessor_hook(self, d):
        """Hook para pós-processamento"""
        if hasattr(self.download_frame, 'update_postprocessor'):
            self.root.after(0, lambda: self.download_frame.update_postprocessor(d))
    
    def on_closing(self):
        """Callback para fechamento da aplicação"""
        if self.download_manager.get_download_status()['is_downloading']:
            # Verificar se há download em andamento
            resposta = messagebox.askyesno(
                "Download em Andamento", 
                "Há um download em andamento. Deseja realmente sair?\n\n"
                "⚠️ Atenção: O download será interrompido e os arquivos podem ficar incompletos."
            )
            if not resposta:
                return
        
        # Confirmar saída sempre
        resposta = messagebox.askyesno("Confirmar Saída", "Deseja realmente sair da aplicação?")
        if resposta:
            self.log_manager.log_info("Aplicação encerrada pelo usuário")
            self.root.quit()
            self.root.destroy()
    
    def run(self):
        """Inicia o loop principal da aplicação"""
        self.root.mainloop()

class DownloadTab:
    """Aba de download de vídeos"""
    
    def __init__(self, parent, download_manager, config_manager, history_manager, log_manager, main_app=None):
        """Inicializa a aba de download"""
        self.parent = parent
        self.main_app = main_app
        self.download_manager = download_manager
        self.config_manager = config_manager
        self.history_manager = history_manager
        self.log_manager = log_manager
        self.frame = tk.Frame(parent)
        
        self.create_widgets()
        self.setup_layout()
        self.load_last_directory()
        
    def create_widgets(self):
        """Cria widgets da aba de download"""
        # URL input
        self.url_label = tk.Label(self.frame, text="URL do vídeo/playlist:")
        self.url_entry = tk.Entry(self.frame, width=50)
        
        # Indicador de tipo de conteúdo
        self.content_type_label = tk.Label(self.frame, text="", fg="blue", font=("Arial", 9, "italic"))
        
        # Menu de contexto para URL
        self.create_context_menu()
        
        # Botão extrair
        self.extract_button = tk.Button(
            self.frame, 
            text="Extrair informações", 
            command=self.extract_info
        )
        
        # Opção de download de playlist
        self.playlist_frame = tk.Frame(self.frame)
        self.is_playlist_var = tk.BooleanVar()
        self.playlist_checkbox = tk.Checkbutton(
            self.playlist_frame,
            text="Baixar playlist completa",
            variable=self.is_playlist_var,
            command=self.on_playlist_mode_change
        )
        self.playlist_info_label = tk.Label(
            self.playlist_frame, 
            text="", 
            fg="green", 
            font=("Arial", 9)
        )
        
        # Frame para resoluções
        self.resolutions_frame = tk.Frame(self.frame)
        self.resolutions_label = tk.Label(self.resolutions_frame, text="Resoluções:")
        self.resolutions_listbox = tk.Listbox(self.resolutions_frame, height=8)
        self.resolutions_listbox.bind("<<ListboxSelect>>", self.on_resolution_select)
        
        # Opção de download apenas de áudio
        self.audio_frame = tk.Frame(self.resolutions_frame)
        self.audio_only_var = tk.BooleanVar()
        self.audio_only_checkbox = tk.Checkbutton(
            self.audio_frame,
            text="Baixar apenas áudio",
            variable=self.audio_only_var,
            command=self.on_audio_only_change
        )
        
        # Qualidade do áudio
        self.audio_quality_label = tk.Label(self.audio_frame, text="Qualidade:")
        self.audio_quality_var = tk.StringVar(value=AppConstants.DEFAULT_AUDIO_QUALITY)
        self.audio_quality_combo = ttk.Combobox(
            self.audio_frame,
            textvariable=self.audio_quality_var,
            values=AppConstants.AUDIO_QUALITIES,
            state="readonly",
            width=8
        )
        self.audio_quality_combo.set(AppConstants.DEFAULT_AUDIO_QUALITY)
        
        # Frame para metadados
        self.metadata_frame = tk.Frame(self.frame)
        self.metadata_label = tk.Label(self.metadata_frame, text="Informações do Vídeo:")
        
        # Widget de texto com funcionalidades melhoradas
        self.metadata_text = tk.Text(
            self.metadata_frame, 
            wrap=tk.WORD, 
            width=40, 
            height=12,  # Aumentar altura para mais conteúdo
            state=tk.NORMAL,  # Permitir seleção e cópia
            cursor="xterm",  # Cursor de texto para indicar selecionabilidade
            selectbackground="#0078d4",  # Cor de seleção
            selectforeground="white"
        )
        
        # Scrollbar para navegação
        self.metadata_scrollbar = tk.Scrollbar(self.metadata_frame)
        self.metadata_text.config(yscrollcommand=self.metadata_scrollbar.set)
        self.metadata_scrollbar.config(command=self.metadata_text.yview)
        
        # Configurar tags para links clicáveis
        self.metadata_text.tag_configure("link", foreground="#0066cc", underline=True)
        self.metadata_text.tag_configure("link_hover", foreground="#004499", underline=True)
        
        # Bind eventos para links
        self.metadata_text.tag_bind("link", "<Button-1>", self.on_link_click)
        self.metadata_text.tag_bind("link", "<Enter>", self.on_link_enter)
        self.metadata_text.tag_bind("link", "<Leave>", self.on_link_leave)
        
        # Menu de contexto para copiar
        self.create_metadata_context_menu()
        
        # Atalhos de teclado
        self.metadata_text.bind("<Control-c>", lambda e: self.copy_selected_text())
        self.metadata_text.bind("<Control-a>", lambda e: self.select_all_text())
        self.metadata_text.bind("<Control-A>", lambda e: self.select_all_text())  # Maiúsculo também
        
        # Botão download
        self.download_button = tk.Button(
            self.frame, 
            text="Baixar vídeo", 
            command=self.start_download,
            state=tk.DISABLED
        )
        
        # Frame de progresso
        self.progress_frame = tk.Frame(self.frame)
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, 
            length=UIConstants.PROGRESS_BAR_LENGTH, 
            mode='determinate', 
            maximum=100
        )
        self.progress_label = tk.Label(self.progress_frame, text="")
        
        # Seleção de diretório
        self.directory_button = tk.Button(
            self.frame, 
            text="Selecionar Diretório", 
            command=self.select_directory
        )
        self.directory_label = tk.Label(
            self.frame, 
            text=UIConstants.NO_DIRECTORY_TEXT,
            wraplength=800, 
            justify='left'
        )
        
        # Botão sair
        self.exit_button = tk.Button(
            self.frame, 
            text="Sair", 
            command=self.main_app.on_closing if self.main_app else self.parent.master.quit,
            bg="#ff6b6b", 
            fg="white", 
            font=("Arial", 10, "bold")
        )
        
        # Mini-player de preview
        self.create_mini_player()
    
    def create_mini_player(self):
        """Cria o mini-player de preview do vídeo"""
        # Frame principal do mini-player (inicialmente oculto)
        self.mini_player_frame = tk.Frame(self.frame, relief=tk.RAISED, bd=1, height=120)
        
        # Frame para thumbnail com tamanho fixo
        self.thumbnail_frame = tk.Frame(self.mini_player_frame, width=160, height=100)
        self.thumbnail_frame.pack_propagate(False)  # Impedir redimensionamento do frame da thumbnail
        
        self.thumbnail_label = tk.Label(
            self.thumbnail_frame,
            text="📺",
            font=("Arial", 20),
            relief=tk.SUNKEN,
            bd=1,
            bg="#f0f0f0"
        )
        
        # Frame para informações do vídeo
        self.info_frame = tk.Frame(self.mini_player_frame)
        
        # Título do vídeo
        self.video_title_label = tk.Label(
            self.info_frame,
            text="",
            font=("Arial", 10, "bold"),
            wraplength=300,
            justify=tk.LEFT,
            anchor='nw',
            height=2
        )
        
        # Informações adicionais (duração, canal, etc.)
        self.video_info_label = tk.Label(
            self.info_frame,
            text="",
            font=("Arial", 9),
            justify=tk.LEFT,
            anchor='nw',
            height=2
        )
        
        # Botão para abrir vídeo no navegador
        self.preview_button = tk.Button(
            self.info_frame,
            text="🎬 Preview",
            command=self.open_video_preview,
            font=("Arial", 9),
            bg="#4CAF50",
            fg="white",
            width=12,
            height=1
        )
        
        # Layout do mini-player com dimensões controladas
        self.thumbnail_label.pack(fill=tk.BOTH, expand=True)
        self.thumbnail_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.video_title_label.pack(anchor='nw', pady=(5, 2), fill=tk.X)
        self.video_info_label.pack(anchor='nw', pady=(0, 2), fill=tk.X)
        self.preview_button.pack(anchor='nw', pady=(5, 5))
        self.info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Variáveis para armazenar dados do vídeo
        self.current_video_url = ""
        self.current_thumbnail_url = ""
        
    def open_video_preview(self):
        """Abre o vídeo no navegador para preview"""
        if self.current_video_url:
            try:
                webbrowser.open(self.current_video_url)
            except Exception as e:
                AppUtils.show_error_message("Erro", f"Não foi possível abrir o vídeo: {str(e)}")
    
    def show_mini_player(self):
        """Exibe o mini-player com dimensões fixas"""
        # Configurar dimensões antes de posicionar
        self.mini_player_frame.configure(height=120)
        self.mini_player_frame.grid_propagate(False)
        
        # Garantir que o frame da thumbnail mantenha suas dimensões
        self.thumbnail_frame.configure(width=160, height=100)
        self.thumbnail_frame.pack_propagate(False)
        
        # Posicionar mini-player na row=6 (separado dos frames principais)
        self.mini_player_frame.grid(
            row=6, 
            column=0, 
            columnspan=2, 
            sticky='ew', 
            pady=10,
            ipady=10  # Padding interno maior para garantir altura
        )
        
        # Forçar atualização da interface
        self.mini_player_frame.update_idletasks()
        self.thumbnail_frame.update_idletasks()
        
        # Log para debug
        self.log_manager.log_info("Mini-player exibido com dimensões fixas (altura: 120px, thumbnail: 160x100px)")
    
    def hide_mini_player(self):
        """Oculta o mini-player"""
        self.mini_player_frame.grid_remove()
    
    def update_mini_player(self, video_info):
        """Atualiza as informações do mini-player"""
        try:
            self.log_manager.log_info("Iniciando atualização do mini-player")
            
            # Verificar se video_info é válido
            if not video_info or not isinstance(video_info, dict):
                self.log_manager.log_error("video_info inválido para mini-player", "Mini-Player")
                self.hide_mini_player()
                return
            
            # Atualizar título
            title = video_info.get('title', 'Título não disponível')
            if len(title) > UIConstants.MINI_PLAYER_MAX_TITLE_LENGTH:
                title = title[:UIConstants.MINI_PLAYER_MAX_TITLE_LENGTH] + "..."
            self.video_title_label.config(text=title)
            self.log_manager.log_info(f"Título do mini-player atualizado: {title[:30]}...")
            
            # Atualizar informações
            duration = AppUtils.format_duration(video_info.get('duration', 0))
            uploader = video_info.get('uploader', 'Canal desconhecido')
            view_count = AppUtils.format_view_count(video_info.get('view_count', 0))
            
            info_text = f"📺 {uploader}\n⏱️ {duration} | 👁️ {view_count}"
            self.video_info_label.config(text=info_text)
            
            # Armazenar URL do vídeo
            self.current_video_url = video_info.get('webpage_url', '')
            
            # Tentar carregar thumbnail
            thumbnail_url = video_info.get('thumbnail')
            if thumbnail_url:
                self.log_manager.log_info(f"Carregando thumbnail: {thumbnail_url[:50]}...")
                self.load_thumbnail(thumbnail_url)
            else:
                self.log_manager.log_info("Nenhuma thumbnail disponível")
            
            # Exibir mini-player
            self.show_mini_player()
            self.log_manager.log_info("Mini-player atualizado e exibido com sucesso")
            
        except Exception as e:
            self.log_manager.log_error(e, "Erro ao atualizar mini-player")
            print(f"Erro ao atualizar mini-player: {e}")
            self.hide_mini_player()
    
    def load_thumbnail(self, thumbnail_url):
        """Carrega e exibe a thumbnail do vídeo"""
        if not thumbnail_url:
            self.log_manager.log_info("URL da thumbnail não fornecida")
            return
            
        def download_and_display():
            try:
                self.log_manager.log_info(f"Iniciando download da thumbnail: {thumbnail_url[:100]}...")
                
                # Download da thumbnail
                response = requests.get(thumbnail_url, timeout=15, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                response.raise_for_status()
                
                self.log_manager.log_info(f"Thumbnail baixada com sucesso. Tamanho: {len(response.content)} bytes")
                
                # Processar imagem
                image = Image.open(BytesIO(response.content))
                original_size = image.size
                
                image = image.resize(
                    (UIConstants.MINI_PLAYER_THUMBNAIL_WIDTH, UIConstants.MINI_PLAYER_THUMBNAIL_HEIGHT),
                    Image.Resampling.LANCZOS
                )
                
                self.log_manager.log_info(f"Imagem redimensionada de {original_size} para {image.size}")
                
                # Converter para PhotoImage
                photo = ImageTk.PhotoImage(image)
                
                # Atualizar label na thread principal usando after
                def update_ui():
                    try:
                        self.thumbnail_label.config(image=photo, text="")
                        self.thumbnail_label.image = photo  # Manter referência
                        self.log_manager.log_info("Thumbnail exibida com sucesso no mini-player")
                    except Exception as ui_error:
                        self.log_manager.log_error(ui_error, "Erro ao atualizar UI da thumbnail")
                
                # Usar after para thread safety
                self.thumbnail_label.after(0, update_ui)
                
            except requests.exceptions.Timeout:
                self.log_manager.log_error("Timeout ao baixar thumbnail", "Mini-Player")
            except requests.exceptions.RequestException as req_error:
                self.log_manager.log_error(req_error, "Erro de rede ao baixar thumbnail")
            except Exception as e:
                self.log_manager.log_error(e, "Erro geral ao carregar thumbnail")
                print(f"Erro ao carregar thumbnail: {e}")
        
        # Executar download em thread separada
        threading.Thread(target=download_and_display, daemon=True).start()
    
    def create_context_menu(self):
        """Cria menu de contexto para o campo URL"""
        self.context_menu = tk.Menu(self.frame, tearoff=0)
        self.context_menu.add_command(label="Colar", command=self.paste_url)
        self.url_entry.bind("<Button-3>", self.show_context_menu)
    
    def create_metadata_context_menu(self):
        """Cria menu de contexto para o widget de metadados"""
        self.metadata_context_menu = tk.Menu(self.frame, tearoff=0)
        self.metadata_context_menu.add_command(label="📋 Copiar Seleção", command=self.copy_selected_text)
        self.metadata_context_menu.add_command(label="📄 Copiar Tudo", command=self.copy_all_text)
        self.metadata_context_menu.add_separator()
        self.metadata_context_menu.add_command(label="🔍 Selecionar Tudo", command=self.select_all_text)
        
        # Bind do menu ao widget de metadados
        self.metadata_text.bind("<Button-3>", self.show_metadata_context_menu)
    
    def show_metadata_context_menu(self, event):
        """Mostra menu de contexto para metadados"""
        try:
            self.metadata_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.metadata_context_menu.grab_release()
    
    def copy_selected_text(self):
        """Copia texto selecionado dos metadados"""
        try:
            selected_text = self.metadata_text.selection_get()
            if selected_text:
                self.metadata_text.clipboard_clear()
                self.metadata_text.clipboard_append(selected_text)
                self.log_manager.log_info("Texto selecionado copiado para área de transferência")
        except tk.TclError:
            AppUtils.show_error_message("Erro", "Nenhum texto selecionado")
    
    def copy_all_text(self):
        """Copia todo o texto dos metadados"""
        try:
            all_text = self.metadata_text.get("1.0", tk.END)
            if all_text.strip():
                self.metadata_text.clipboard_clear()
                self.metadata_text.clipboard_append(all_text.strip())
                self.log_manager.log_info("Todo o texto dos metadados copiado")
        except Exception as e:
            self.log_manager.log_error(e, "Erro ao copiar texto")
    
    def select_all_text(self):
        """Seleciona todo o texto dos metadados"""
        try:
            self.metadata_text.tag_add(tk.SEL, "1.0", tk.END)
            self.metadata_text.mark_set(tk.INSERT, "1.0")
            self.metadata_text.see(tk.INSERT)
        except Exception as e:
            self.log_manager.log_error(e, "Erro ao selecionar texto")
    
    def on_link_click(self, event):
        """Callback para clique em links"""
        try:
            # Obter posição do clique
            index = self.metadata_text.index(f"@{event.x},{event.y}")
            
            # Verificar se há uma tag de link na posição
            tags = self.metadata_text.tag_names(index)
            if "link" in tags:
                # Obter o texto do link
                ranges = self.metadata_text.tag_ranges("link")
                for i in range(0, len(ranges), 2):
                    start, end = ranges[i], ranges[i+1]
                    if self.metadata_text.compare(start, "<=", index) and self.metadata_text.compare(index, "<", end):
                        link_text = self.metadata_text.get(start, end)
                        if link_text.startswith("http"):
                            webbrowser.open(link_text)
                            self.log_manager.log_info(f"Link aberto: {link_text}")
                        break
        except Exception as e:
            self.log_manager.log_error(e, "Erro ao processar clique em link")
    
    def on_link_enter(self, event):
        """Callback para mouse sobre link"""
        self.metadata_text.config(cursor="hand2")
    
    def on_link_leave(self, event):
        """Callback para mouse sair do link"""
        self.metadata_text.config(cursor="xterm")
    
    def _insert_text_with_links(self, text):
        """Insere texto detectando e formatando links automaticamente"""
        import re
        
        # Padrão para detectar URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        
        # Encontrar todas as URLs no texto
        urls = list(re.finditer(url_pattern, text))
        
        if not urls:
            # Nenhum link encontrado, inserir texto normal
            self.metadata_text.insert(tk.END, text)
            return
        
        # Processar texto com links
        last_end = 0
        
        for match in urls:
            start, end = match.span()
            url = match.group()
            
            # Inserir texto antes do link
            if start > last_end:
                self.metadata_text.insert(tk.END, text[last_end:start])
            
            # Inserir link com formatação
            link_start = self.metadata_text.index(tk.INSERT)
            self.metadata_text.insert(tk.END, url)
            link_end = self.metadata_text.index(tk.INSERT)
            self.metadata_text.tag_add("link", link_start, link_end)
            
            last_end = end
        
        # Inserir texto restante após o último link
        if last_end < len(text):
            self.metadata_text.insert(tk.END, text[last_end:])
        
        self.log_manager.log_info(f"Texto inserido com {len(urls)} links detectados")
    
    def setup_layout(self):
        """Configura layout da aba"""
        # Configurar grid (reorganizado para evitar conflitos)
        for i in range(12):  # Aumentado para acomodar todos os elementos
            if i == 4:  # Linha dos frames principais (resoluções e metadados)
                self.frame.rowconfigure(i, weight=1, pad=UIConstants.PADDING)
            elif i == 6:  # Linha do mini-player - altura mínima garantida
                self.frame.rowconfigure(i, minsize=130, pad=UIConstants.PADDING)
            else:
                self.frame.rowconfigure(i, pad=UIConstants.PADDING)
        
        for i in range(2):
            self.frame.columnconfigure(i, weight=1, pad=UIConstants.PADDING)
        
        # Posicionar widgets com layout reorganizado
        self.url_label.grid(row=0, column=0, sticky='w')
        self.url_entry.grid(row=0, column=1, sticky='ew')
        
        # Indicador de tipo de conteúdo
        self.content_type_label.grid(row=1, column=0, columnspan=2, sticky='w', pady=2)
        
        self.extract_button.grid(row=2, column=0, columnspan=2, pady=2)
        
        # Opções de playlist
        self.playlist_frame.grid(row=3, column=0, columnspan=2, sticky='ew', pady=2)
        self.playlist_checkbox.pack(side='left')
        self.playlist_info_label.pack(side='left', padx=(10, 0))
        
        # Frames principais
        self.resolutions_frame.grid(row=4, column=0, sticky='nsew', padx=(0, 5))
        self.metadata_frame.grid(row=4, column=1, sticky='nsew', padx=(5, 0))
        
        # Layout do frame de resoluções
        self.resolutions_label.pack()
        self.resolutions_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Layout do frame de áudio
        self.audio_frame.pack(fill=tk.X, pady=5)
        self.audio_only_checkbox.pack(anchor='w')
        
        # Frame para qualidade de áudio (inicialmente oculto)
        self.audio_quality_frame = tk.Frame(self.audio_frame)
        self.audio_quality_label.pack(side=tk.LEFT)
        self.audio_quality_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Layout do frame de metadados
        self.metadata_label.pack()
        self.metadata_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.metadata_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.download_button.grid(row=5, column=0, columnspan=2, pady=UIConstants.BUTTON_PADDING)
        
        # Mini-player (row=6) - será posicionado dinamicamente
        # Progress frame (row=7) - será posicionado dinamicamente
        
        self.directory_button.grid(row=8, column=0, columnspan=2, pady=UIConstants.BUTTON_PADDING)
        self.directory_label.grid(row=9, column=0, columnspan=2, sticky='ew', padx=UIConstants.PADDING)
        
        self.exit_button.grid(row=10, column=0, columnspan=2, pady=UIConstants.PADDING)
    
    def show_context_menu(self, event):
        """Mostra menu de contexto"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    def paste_url(self):
        """Cola URL da área de transferência"""
        try:
            clipboard_content = AppUtils.safe_get_clipboard()
            if clipboard_content:
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, clipboard_content)
                self.log_manager.log_info("URL colada da área de transferência")
        except Exception as e:
            self.log_manager.log_error(e, "Erro ao colar URL")
    
    def extract_info(self):
        """Extrai informações do vídeo"""
        url = self.url_entry.get().strip()
        
        if not url:
            AppUtils.show_error_message("Erro", "Por favor, insira a URL do vídeo.")
            return
        
        # Desabilitar botão durante extração
        self.extract_button.config(state=tk.DISABLED, text="Extraindo...")
        
        def extract_worker():
            success, data, resolutions = self.download_manager.extract_video_info(url)
            
            # Atualizar UI de forma thread-safe
            self.frame.after(0, lambda: self.on_extraction_complete(success, data, resolutions))
        
        # Executar em thread separada
        thread = threading.Thread(target=extract_worker, daemon=True)
        thread.start()
    
    def on_extraction_complete(self, success, data, resolutions):
        """Callback para conclusão da extração"""
        # Log do resultado da extração
        self.log_manager.log_info(f"Extração concluída - Sucesso: {success}")
        
        # Reabilitar botão
        self.extract_button.config(state=tk.NORMAL, text="Extrair informações")
        
        if success:
            # Verificar se é playlist ou vídeo individual
            is_playlist = data and data.get('type') == 'playlist'
            
            if is_playlist:
                self.log_manager.log_info(f"Playlist detectada: {data.get('title', 'N/A')[:50]}... ({data.get('video_count', 0)} vídeos)")
                
                # Atualizar indicador de tipo de conteúdo
                self.content_type_label.config(text=f"📋 Playlist detectada ({data.get('video_count', 0)} vídeos)")
                
                # Mostrar checkbox de playlist e marcar como habilitado
                self.playlist_checkbox.config(state=tk.NORMAL)
                self.is_playlist_var.set(True)
                self.on_playlist_mode_change()
                
                # Para playlists, não há resoluções específicas - usar padrões
                self.update_resolutions(['1080p', '720p', '480p', '360p'])
                self.update_metadata(data)
                
            else:
                self.log_manager.log_info(f"Vídeo individual: {data.get('title', 'N/A')[:50]}...")
                self.log_manager.log_info(f"Resoluções recebidas: {len(resolutions)} itens - {resolutions}")
                
                # Atualizar indicador de tipo de conteúdo
                self.content_type_label.config(text="🎥 Vídeo individual")
                
                # Desmarcar playlist e desabilitar checkbox
                self.is_playlist_var.set(False)
                self.playlist_checkbox.config(state=tk.DISABLED)
                self.on_playlist_mode_change()
                
                # Atualizar interface com dados extraídos
                self.update_resolutions(resolutions)
                self.update_metadata(data)
                
                # Ocultar mini-player anterior e mostrar novo se dados válidos
                self.hide_mini_player()
                if data and isinstance(data, dict):
                    self.update_mini_player(data)
            
            self.enable_download_if_ready()
            self.log_manager.log_info("Interface atualizada com sucesso após extração")
        else:
            self.log_manager.log_error(f"Erro na extração: {data}", "Extração de Informações")
            AppUtils.show_error_message("Erro", data)
            
            # Limpar interface em caso de erro
            self.content_type_label.config(text="")
            self.is_playlist_var.set(False)
            self.playlist_checkbox.config(state=tk.DISABLED)
            self.playlist_info_label.config(text="")
            self.hide_mini_player()
            self.resolutions_listbox.delete(0, tk.END)
            self.metadata_text.delete("1.0", tk.END)
    
    def update_resolutions(self, resolutions):
        """Atualiza lista de resoluções"""
        # Log para debug
        self.log_manager.log_info(f"Atualizando lista de resoluções: {resolutions}")
        
        # Limpar lista atual
        self.resolutions_listbox.delete(0, tk.END)
        self.current_resolutions = resolutions
        
        # Verificar se há resoluções válidas
        if not resolutions:
            self.log_manager.log_warning("Nenhuma resolução recebida para atualização")
            self.resolutions_listbox.insert(tk.END, "Nenhuma resolução disponível")
            return
        
        # Inserir resoluções na lista
        for i, resolution in enumerate(resolutions):
            self.resolutions_listbox.insert(tk.END, resolution)
            self.log_manager.log_info(f"Resolução {i+1}: {resolution}")
        
        # Selecionar primeira resolução automaticamente se disponível
        if len(resolutions) > 0 and resolutions[0] != "Nenhuma resolução disponível":
            self.resolutions_listbox.selection_set(0)
            self.log_manager.log_info(f"Primeira resolução selecionada automaticamente: {resolutions[0]}")
        
        self.log_manager.log_info(f"Lista de resoluções atualizada com {len(resolutions)} itens")
    
    def update_metadata(self, video_info):
        """Atualiza metadados do vídeo com conteúdo completo e links clicáveis"""
        self.metadata_text.delete("1.0", tk.END)
        
        if isinstance(video_info, dict):
            metadata = self.download_manager.get_video_metadata()
            
            # Título
            title = metadata.get('title', 'N/A')
            self.metadata_text.insert(tk.END, f"📺 Título: {title}\n\n")
            
            # Canal/Uploader
            uploader = metadata.get('uploader', 'N/A')
            self.metadata_text.insert(tk.END, f"👤 Canal: {uploader}\n\n")
            
            # Duração formatada
            duration = metadata.get('duration', 'N/A')
            if duration != 'N/A' and isinstance(duration, (int, float)):
                hours = int(duration // 3600)
                minutes = int((duration % 3600) // 60)
                seconds = int(duration % 60)
                if hours > 0:
                    duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    duration_str = f"{minutes:02d}:{seconds:02d}"
                self.metadata_text.insert(tk.END, f"⏱️ Duração: {duration_str}\n\n")
            else:
                self.metadata_text.insert(tk.END, f"⏱️ Duração: {duration}\n\n")
            
            # Visualizações formatadas
            view_count = metadata.get('view_count', 'N/A')
            if view_count != 'N/A' and isinstance(view_count, (int, float)):
                view_count_str = f"{int(view_count):,}".replace(',', '.')
                self.metadata_text.insert(tk.END, f"👁️ Visualizações: {view_count_str}\n\n")
            else:
                self.metadata_text.insert(tk.END, f"👁️ Visualizações: {view_count}\n\n")
            
            # Data de upload formatada
            upload_date = metadata.get('upload_date', 'N/A')
            if upload_date != 'N/A' and len(str(upload_date)) == 8:
                try:
                    date_str = str(upload_date)
                    formatted_date = f"{date_str[6:8]}/{date_str[4:6]}/{date_str[0:4]}"
                    self.metadata_text.insert(tk.END, f"📅 Data de Upload: {formatted_date}\n\n")
                except:
                    self.metadata_text.insert(tk.END, f"📅 Data de Upload: {upload_date}\n\n")
            else:
                self.metadata_text.insert(tk.END, f"📅 Data de Upload: {upload_date}\n\n")
            
            # URL do vídeo
            webpage_url = metadata.get('webpage_url', 'N/A')
            if webpage_url != 'N/A':
                self.metadata_text.insert(tk.END, "🔗 URL: ")
                start_pos = self.metadata_text.index(tk.INSERT)
                self.metadata_text.insert(tk.END, webpage_url)
                end_pos = self.metadata_text.index(tk.INSERT)
                self.metadata_text.tag_add("link", start_pos, end_pos)
                self.metadata_text.insert(tk.END, "\n\n")
            
            # Descrição COMPLETA (sem cortes)
            description = metadata.get('description', 'N/A')
            if description != 'N/A' and description and description.strip():
                self.metadata_text.insert(tk.END, "📝 Descrição:\n")
                
                # Processar descrição para detectar links
                self._insert_text_with_links(description)
            else:
                self.metadata_text.insert(tk.END, "📝 Descrição: Não disponível")
            
            # Log para debug
            self.log_manager.log_info(f"Metadados completos atualizados para: {title[:50]}...")
            
            # Atualizar mini-player com informações do vídeo
            self.update_mini_player(video_info)
        else:
            self.metadata_text.insert(tk.END, "❌ Erro: Informações do vídeo não disponíveis")
            self.log_manager.log_error("video_info inválido em update_metadata", "UI")
            # Ocultar mini-player em caso de erro
            self.hide_mini_player()
    
    def on_resolution_select(self, event):
        """Callback para seleção de resolução"""
        self.enable_download_if_ready()
    
    def on_audio_only_change(self):
        """Callback para mudança na opção de áudio apenas"""
        if self.audio_only_var.get():
            # Desabilitar seleção de resolução e mostrar opções de áudio
            self.resolutions_listbox.config(state=tk.DISABLED)
            self.audio_quality_frame.pack(fill=tk.X, pady=2)
        else:
            # Habilitar seleção de resolução e ocultar opções de áudio
            self.resolutions_listbox.config(state=tk.NORMAL)
            self.audio_quality_frame.pack_forget()
        
        self.enable_download_if_ready()
    
    def on_playlist_mode_change(self):
        """Callback quando modo playlist muda"""
        if self.is_playlist_var.get():
            # Verificar se há informações de playlist disponíveis
            if (hasattr(self.download_manager, 'current_info') and 
                self.download_manager.current_info and 
                self.download_manager.current_info.get('type') == 'playlist'):
                
                video_count = self.download_manager.current_info.get('video_count', 0)
                self.playlist_info_label.config(text=f"({video_count} vídeos)")
                self.download_button.config(text="Baixar Playlist")
            else:
                self.playlist_info_label.config(text="(Extraia informações primeiro)")
                self.download_button.config(text="Baixar Playlist")
        else:
            self.playlist_info_label.config(text="")
            if self.audio_only_var.get():
                self.download_button.config(text="Baixar áudio")
            else:
                self.download_button.config(text="Baixar vídeo")
        
        self.enable_download_if_ready()
    
    def on_playlist_video_processed(self, data, callback_type='progress'):
        """
        Callback chamado quando um vídeo da playlist é processado
        
        Args:
            data: Dados do vídeo (entry para progresso, video_success_data para sucesso)
            callback_type: Tipo do callback ('progress' ou 'success')
        """
        try:
            if callback_type == 'progress':
                # Callback de progresso - quando vídeo está sendo processado
                video_entry, index, total = data
                
                def update_progress_ui():
                    try:
                        # Atualizar texto do botão com progresso
                        progress_text = f"Baixando vídeo {index}/{total}: {video_entry.get('title', 'N/A')[:30]}..."
                        self.download_button.config(text=progress_text)
                        
                        # Log do progresso
                        self.log_manager.log_info(f"Processando vídeo {index}/{total} da playlist: {video_entry.get('title', 'N/A')}")
                        
                    except Exception as e:
                        self.log_manager.log_error(f"Erro ao atualizar UI para vídeo da playlist: {str(e)}")
                
                # Executar atualização na thread principal
                self.frame.after(0, update_progress_ui)
                
            elif callback_type == 'success':
                # Callback de sucesso - quando vídeo foi baixado com sucesso
                video_success_data = data
                
                def update_success_ui():
                    try:
                        video_info = video_success_data['video_info']
                        index = video_success_data['index']
                        total = video_success_data['total']
                        resolution = video_success_data['resolution']
                        audio_only = video_success_data['audio_only']
                        
                        # Atualizar mini-player com informações do vídeo atual
                        self.update_mini_player(video_info)
                        
                        # Salvar no histórico
                        self.add_video_to_history(video_info, resolution, audio_only)
                        
                        # Log de sucesso
                        self.log_manager.log_info(f"Vídeo {index}/{total} salvo no histórico: {video_info.get('title', 'N/A')}")
                        
                    except Exception as e:
                        self.log_manager.log_error(f"Erro ao processar sucesso do vídeo da playlist: {str(e)}")
                
                # Executar atualização na thread principal
                self.frame.after(0, update_success_ui)
            
        except Exception as e:
            self.log_manager.log_error(f"Erro no callback de vídeo da playlist: {str(e)}")
    
    def add_video_to_history(self, video_info, resolution, audio_only):
        """
        Adiciona um vídeo específico da playlist ao histórico
        
        Args:
            video_info: Informações do vídeo
            resolution: Resolução selecionada
            audio_only: Se é download apenas de áudio
        """
        try:
            # Coletar metadados do vídeo
            title = video_info.get('title', 'N/A')
            duration = video_info.get('duration', 0)
            uploader = video_info.get('uploader', 'N/A')
            upload_date = video_info.get('upload_date', 'N/A')
            view_count = video_info.get('view_count', 0)
            like_count = video_info.get('like_count', 0)
            description = video_info.get('description', 'N/A')
            url = video_info.get('webpage_url', video_info.get('url', 'N/A'))
            
            # Determinar resolução para histórico
            if audio_only:
                resolution_for_history = 'music'
            else:
                resolution_for_history = resolution
            
            # Calcular tamanho estimado
            estimated_size = 0
            if 'filesize' in video_info and video_info['filesize']:
                estimated_size = video_info['filesize']
            elif 'filesize_approx' in video_info and video_info['filesize_approx']:
                estimated_size = video_info['filesize_approx']
            
            # Adicionar ao histórico
            self.history_manager.add_download_to_history(
                title=title,
                url=url,
                resolution=resolution_for_history,
                file_size=estimated_size,
                duration=duration,
                uploader=uploader,
                upload_date=upload_date,
                view_count=view_count,
                like_count=like_count,
                description=description
            )
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao adicionar vídeo da playlist ao histórico: {str(e)}")
    
    def select_directory(self):
        """Seleciona diretório de download"""
        directory = filedialog.askdirectory()
        if directory:
            success, error_msg = self.download_manager.set_download_directory(directory)
            if success:
                self.directory_label.config(text=f"Diretório: {directory}")
                self.enable_download_if_ready()
                
                # Salvar último diretório selecionado (funcionalidade restaurada)
                try:
                    self.config_manager.db_manager.set_setting('last_download_directory', directory)
                    self.log_manager.log_info(f"Último diretório salvo: {directory}")
                except Exception as e:
                    self.log_manager.log_error(str(e), "Erro ao salvar último diretório")
            else:
                AppUtils.show_error_message("Erro", error_msg)
    
    def enable_download_if_ready(self):
        """Habilita botão de download se tudo estiver pronto"""
        has_directory = bool(self.download_manager.download_directory)
        has_info = self.download_manager.get_download_status()['has_info']
        
        # Determinar texto do botão e verificar formato baseado no modo
        if self.is_playlist_var.get():
            # Modo playlist
            if self.audio_only_var.get():
                has_format = True  # Para áudio, não precisa de resolução específica
                button_text = "Baixar Playlist (áudio)"
            else:
                has_format = bool(self.resolutions_listbox.curselection())
                button_text = "Baixar Playlist (vídeo)"
        else:
            # Modo individual
            if self.audio_only_var.get():
                has_format = True  # Para áudio, não precisa de resolução específica
                button_text = "Baixar áudio"
            else:
                has_format = bool(self.resolutions_listbox.curselection())
                button_text = "Baixar vídeo"
        
        if has_format and has_directory and has_info:
            self.download_button.config(state=tk.NORMAL, text=button_text)
        else:
            self.download_button.config(state=tk.DISABLED, text=button_text)
    
    def start_download(self):
        """Inicia o download"""
        url = self.url_entry.get().strip()
        
        # Verificar se é download de playlist
        if self.is_playlist_var.get():
            # Download de playlist
            if self.audio_only_var.get():
                audio_quality = self.audio_quality_var.get()
                selected_resolution = None
                download_type = "playlist (áudio)"
            else:
                selected_index = self.resolutions_listbox.curselection()
                if not selected_index:
                    AppUtils.show_error_message("Erro", "Por favor, selecione uma resolução.")
                    return
                selected_resolution = self.resolutions_listbox.get(selected_index)
                audio_quality = None
                download_type = "playlist (vídeo)"
            
            # Preparar interface para download de playlist
            self.download_button.config(state=tk.DISABLED, text=f"Baixando {download_type}...")
            self.show_progress_bar()
            
            # Iniciar download de playlist
            success, message = self.download_manager.start_playlist_download(
                url,
                selected_resolution,
                success_callback=self.on_download_success,
                error_callback=self.on_download_error,
                audio_only=self.audio_only_var.get(),
                audio_quality=audio_quality,
                video_callback=self.on_playlist_video_processed
            )
            
        else:
            # Download individual
            # Verificar se é download de áudio ou vídeo
            if self.audio_only_var.get():
                # Download apenas de áudio
                audio_quality = self.audio_quality_var.get()
                selected_resolution = None
                download_type = "áudio"
            else:
                # Download de vídeo
                selected_index = self.resolutions_listbox.curselection()
                if not selected_index:
                    AppUtils.show_error_message("Erro", "Por favor, selecione uma resolução.")
                    return
                selected_resolution = self.resolutions_listbox.get(selected_index)
                audio_quality = None
                download_type = "vídeo"
            
            # Preparar interface para download
            self.download_button.config(state=tk.DISABLED, text=f"Baixando {download_type}...")
            self.show_progress_bar()
            
            # Iniciar download
            success, message = self.download_manager.start_download(
                url, 
                selected_resolution,
                success_callback=self.on_download_success,
                error_callback=self.on_download_error,
                audio_only=self.audio_only_var.get(),
                audio_quality=audio_quality
            )
        
        if not success:
            AppUtils.show_error_message("Erro", message)
            self.reset_download_ui()
    
    def show_progress_bar(self):
        """Mostra barra de progresso"""
        # Configurar layout interno do progress_frame APENAS se não estiver configurado
        if not self.progress_bar.winfo_manager():
            self.progress_bar.pack(fill=tk.X, pady=2)
            self.progress_label.pack()
        
        # Posicionar o frame no grid (row=7 para evitar conflito com mini-player)
        self.progress_frame.grid(row=7, column=0, columnspan=2, sticky='ew', padx=UIConstants.PADDING, pady=UIConstants.BUTTON_PADDING)
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Preparando download...")
        
        # Forçar atualização da interface
        self.progress_frame.update_idletasks()
        self.frame.update_idletasks()
    
    def hide_progress_bar(self):
        """Esconde barra de progresso"""
        self.progress_frame.grid_remove()
        # Limpar layout interno para evitar problemas na próxima exibição
        self.progress_bar.pack_forget()
        self.progress_label.pack_forget()
    
    def update_progress(self, d):
        """Atualiza progresso do download"""
        if d['status'] == 'downloading':
            try:
                percent = self.extract_progress_percent(d)
                speed_str = d.get('_speed_str', d.get('speed', 'N/A'))
                eta_str = d.get('_eta_str', d.get('eta', 'N/A'))
                
                # Limitar a 90% para reservar espaço para merge
                display_percent = min(percent * 0.9, UIConstants.DOWNLOAD_PROGRESS_LIMIT)
                
                self.progress_bar['value'] = display_percent
                self.progress_label.config(
                    text=f"Progresso: {display_percent:.1f}% | Velocidade: {speed_str} | ETA: {eta_str}"
                )
                
            except Exception as e:
                self.log_manager.log_error(e, "Erro no progress_hook")
        
        elif d['status'] == 'finished':
            self.progress_bar['value'] = UIConstants.DOWNLOAD_PROGRESS_LIMIT
            self.progress_label.config(text="90% | Preparando merge...")
    
    def extract_progress_percent(self, d):
        """Extrai porcentagem de progresso dos dados do yt-dlp"""
        # Tentar várias formas de obter porcentagem
        if 'downloaded_bytes' in d and 'total_bytes' in d and d['total_bytes']:
            return (d['downloaded_bytes'] / d['total_bytes']) * 100
        elif 'downloaded_bytes' in d and 'total_bytes_estimate' in d and d['total_bytes_estimate']:
            return (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
        elif '_percent_str' in d:
            percent_str = str(d['_percent_str']).strip()
            return float(percent_str.replace('%', ''))
        else:
            return 0
    
    def update_postprocessor(self, d):
        """Atualiza progresso do pós-processamento"""
        if d['status'] == 'started':
            if 'FFmpegVideoRemuxer' in str(d.get('postprocessor', '')):
                self.progress_bar['value'] = UIConstants.MERGE_PROGRESS_START
                self.progress_label.config(text="92% | Fazendo merge...")
            elif 'FFmpegMerger' in str(d.get('postprocessor', '')):
                self.progress_bar['value'] = UIConstants.MERGE_PROGRESS_END
                self.progress_label.config(text="95% | Finalizando merge...")
        elif d['status'] == 'finished':
            self.progress_bar['value'] = UIConstants.MERGE_PROGRESS_END
            self.progress_label.config(text="98% | Limpando arquivos...")
    
    def on_download_success(self):
        """Callback para download bem-sucedido"""
        self.progress_bar['value'] = 100
        self.progress_label.config(text="Download concluído!")
        
        # Adicionar ao histórico
        self.add_to_history()
        
        # Auto-abrir pasta se configurado
        if self.config_manager.should_auto_open_folder():
            try:
                import os
                os.startfile(self.download_manager.download_directory)
            except Exception as e:
                self.log_manager.log_error(e, "Erro ao abrir pasta automaticamente")
        
        # Exibir aviso de sucesso
        messagebox.showinfo("Sucesso", "Download concluído com sucesso!")
        
        # Resetar UI após delay
        self.frame.after(3000, self.reset_download_ui)
    
    def on_download_error(self, error_msg):
        """Callback para erro no download"""
        AppUtils.show_error_message("Erro no Download", error_msg)
        self.reset_download_ui()
    
    def add_to_history(self):
        """Adiciona download ao histórico"""
        try:
            metadata = self.download_manager.get_video_metadata()
            
            # Determinar resolução baseada no tipo de download
            if self.audio_only_var.get():
                # Para downloads de áudio, usar 'music' ao invés de 'N/A'
                resolution = 'music'
            else:
                # Para downloads de vídeo, obter resolução selecionada
                selected_index = self.resolutions_listbox.curselection()
                resolution = self.resolutions_listbox.get(selected_index) if selected_index else 'N/A'
            
            # Obter informações do vídeo atual
            current_info = self.download_manager.current_info
            
            # Calcular tamanho estimado do arquivo
            file_size = 'N/A'
            if current_info:
                if self.audio_only_var.get():
                    # Para áudio, estimar baseado na duração (aproximadamente 1MB por minuto para 192kbps)
                    duration = current_info.get('duration', 0)
                    if duration and isinstance(duration, (int, float)):
                        # Estimar tamanho do áudio em bytes (192kbps = 24KB/s)
                        estimated_size = int(duration * 24 * 1024)  # bytes
                        file_size = str(estimated_size)
                else:
                    # Para vídeo, tentar obter tamanho aproximado
                    file_size = str(current_info.get('filesize_approx', 'N/A'))
                    if file_size == 'None':
                        file_size = 'N/A'
            
            # Obter caminho do diretório de download
            download_path = self.download_manager.download_directory or ''
            
            # Obter URL da thumbnail
            thumbnail_url = ''
            if current_info:
                thumbnail_url = current_info.get('thumbnail', '')
            
            download_data = {
                'url': self.url_entry.get().strip(),
                'title': metadata.get('title', 'N/A'),
                'duration': metadata.get('duration', 'N/A'),
                'resolution': resolution,
                'file_size': file_size,
                'download_path': download_path,
                'thumbnail_url': thumbnail_url,
                'uploader': metadata.get('uploader', 'N/A'),
                'view_count': metadata.get('view_count', 0),
                'description': metadata.get('description', '')
            }
            
            # Log para debug
            self.log_manager.log_info(
                f"Adicionando ao histórico - Tipo: {'áudio' if self.audio_only_var.get() else 'vídeo'}, "
                f"Resolução: {resolution}, File_size: {file_size}, Path: {download_path}, "
                f"Thumbnail: {'Sim' if thumbnail_url else 'Não'}"
            )
            
            self.history_manager.add_download_to_history(download_data)
            
        except Exception as e:
            self.log_manager.log_error(e, "Erro ao adicionar ao histórico")
    
    def reset_download_ui(self):
        """Reseta interface após download"""
        # Resetar texto do botão baseado na opção atual
        button_text = "Baixar áudio" if self.audio_only_var.get() else "Baixar vídeo"
        self.download_button.config(state=tk.DISABLED, text=button_text)
        self.hide_progress_bar()
        
        # Ocultar mini-player
        self.hide_mini_player()
        
        # Resetar opções de áudio se necessário
        if self.audio_only_var.get():
            self.audio_quality_var.set(AppConstants.DEFAULT_AUDIO_QUALITY)
        self.enable_download_if_ready()
    
    def load_last_directory(self):
        """Carrega o último diretório usado"""
        try:
            last_directory = self.config_manager.db_manager.get_setting('last_download_directory')
            if last_directory and os.path.exists(last_directory):
                success, error_msg = self.download_manager.set_download_directory(last_directory)
                if success:
                    self.directory_label.config(text=f"Diretório: {last_directory}")
                    self.log_manager.log_info(f"Último diretório carregado: {last_directory}")
                else:
                    self.log_manager.log_error(error_msg, "Erro ao carregar último diretório")
        except Exception as e:
            self.log_manager.log_error(str(e), "Erro ao carregar último diretório")

class HistoryTab:
    """Aba de histórico de downloads"""
    
    def __init__(self, parent, history_manager, log_manager):
        self.parent = parent
        self.history_manager = history_manager
        self.log_manager = log_manager
        
        # Variáveis de paginação
        self.current_page = 1
        self.per_page = 50
        self.total_pages = 1
        self.total_count = 0
        
        self.frame = tk.Frame(parent)
        self.create_widgets()
        self.setup_layout()
        self.update_history()
    
    def create_widgets(self):
        """Cria widgets da aba de histórico"""
        # Frame de controles
        self.controls_frame = tk.Frame(self.frame)
        
        self.refresh_button = tk.Button(
            self.controls_frame,
            text="🔄 Atualizar",
            command=self.update_history
        )
        
        self.clear_button = tk.Button(
            self.controls_frame,
            text="🗑️ Limpar Histórico",
            command=self.clear_history
        )
        
        # Frame de busca
        self.search_frame = tk.Frame(self.frame)
        
        tk.Label(self.search_frame, text="Buscar:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(self.search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry.bind('<Return>', self.on_search)
        
        self.search_button = tk.Button(
            self.search_frame,
            text="🔍 Buscar",
            command=self.on_search
        )
        self.search_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.clear_search_button = tk.Button(
            self.search_frame,
            text="✖ Limpar",
            command=self.clear_search
        )
        self.clear_search_button.pack(side=tk.LEFT)
        
        # Frame de filtros avançados
        self.filters_frame = tk.Frame(self.frame)
        
        # Filtro por resolução
        tk.Label(self.filters_frame, text="Resolução:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.resolution_var = tk.StringVar(value="Todas")
        self.resolution_combo = ttk.Combobox(
            self.filters_frame,
            textvariable=self.resolution_var,
            values=["Todas", "144p", "240p", "360p", "480p", "720p", "1080p", "1440p", "2160p", "Audio"],
            width=10,
            state="readonly"
        )
        self.resolution_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.resolution_combo.bind('<<ComboboxSelected>>', self.on_filter_change)
        
        # Filtro por status
        tk.Label(self.filters_frame, text="Status:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.status_var = tk.StringVar(value="Todos")
        self.status_combo = ttk.Combobox(
            self.filters_frame,
            textvariable=self.status_var,
            values=["Todos", "completed", "failed", "downloading", "pending"],
            width=12,
            state="readonly"
        )
        self.status_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.status_combo.bind('<<ComboboxSelected>>', self.on_filter_change)
        
        # Filtro por período
        tk.Label(self.filters_frame, text="Período:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.period_var = tk.StringVar(value="Todos")
        self.period_combo = ttk.Combobox(
            self.filters_frame,
            textvariable=self.period_var,
            values=["Todos", "Hoje", "Última semana", "Último mês", "Últimos 3 meses", "Último ano"],
            width=15,
            state="readonly"
        )
        self.period_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.period_combo.bind('<<ComboboxSelected>>', self.on_filter_change)
        
        # Botão para limpar filtros
        self.clear_filters_button = tk.Button(
            self.filters_frame,
            text="🗑️ Limpar Filtros",
            command=self.clear_filters
        )
        self.clear_filters_button.pack(side=tk.LEFT)
        
        # Treeview para histórico
        self.tree_frame = tk.Frame(self.frame)
        
        columns = ('ID', 'Título', 'Resolução', 'Data', 'Status')
        self.history_tree = ttk.Treeview(self.tree_frame, columns=columns, show='headings', height=15)
        
        # Configurar colunas
        self.history_tree.heading('ID', text='ID')
        self.history_tree.heading('Título', text='Título')
        self.history_tree.heading('Resolução', text='Resolução')
        self.history_tree.heading('Data', text='Data')
        self.history_tree.heading('Status', text='Status')
        
        self.history_tree.column('ID', width=50)
        self.history_tree.column('Título', width=300)
        self.history_tree.column('Resolução', width=100)
        self.history_tree.column('Data', width=150)
        self.history_tree.column('Status', width=100)
        
        # Scrollbar para treeview
        self.tree_scrollbar = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=self.tree_scrollbar.set)
        
        # Menu de contexto
        self.create_context_menu()
        
        # Frame de paginação
        self.pagination_frame = tk.Frame(self.frame)
        
        # Botões de navegação
        self.first_button = tk.Button(
            self.pagination_frame,
            text="⏮ Primeira",
            command=self.go_to_first_page,
            state=tk.DISABLED
        )
        self.first_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.prev_button = tk.Button(
            self.pagination_frame,
            text="◀ Anterior",
            command=self.go_to_previous_page,
            state=tk.DISABLED
        )
        self.prev_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Informações da página
        self.page_info_var = tk.StringVar()
        self.page_info_label = tk.Label(self.pagination_frame, textvariable=self.page_info_var)
        self.page_info_label.pack(side=tk.LEFT, padx=(10, 10))
        
        self.next_button = tk.Button(
            self.pagination_frame,
            text="Próxima ▶",
            command=self.go_to_next_page,
            state=tk.DISABLED
        )
        self.next_button.pack(side=tk.LEFT, padx=(5, 0))
        
        self.last_button = tk.Button(
            self.pagination_frame,
            text="Última ⏭",
            command=self.go_to_last_page,
            state=tk.DISABLED
        )
        self.last_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Seletor de itens por página
        tk.Label(self.pagination_frame, text="Itens por página:").pack(side=tk.LEFT, padx=(20, 5))
        
        self.per_page_var = tk.StringVar(value=str(self.per_page))
        self.per_page_combo = ttk.Combobox(
            self.pagination_frame,
            textvariable=self.per_page_var,
            values=["25", "50", "100", "200"],
            width=5,
            state="readonly"
        )
        self.per_page_combo.pack(side=tk.LEFT)
        self.per_page_combo.bind('<<ComboboxSelected>>', self.on_per_page_change)
        
        # Botões de exportação
        tk.Label(self.pagination_frame, text="Exportar:").pack(side=tk.LEFT, padx=(20, 5))
        
        self.export_csv_button = tk.Button(
            self.pagination_frame,
            text="📊 CSV",
            command=self.export_to_csv
        )
        self.export_csv_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.export_pdf_button = tk.Button(
            self.pagination_frame,
            text="📄 PDF",
            command=self.export_to_pdf
        )
        self.export_pdf_button.pack(side=tk.LEFT)
    
    def create_context_menu(self):
        """Cria menu de contexto para o histórico"""
        self.context_menu = tk.Menu(self.frame, tearoff=0)
        self.context_menu.add_command(label="Abrir Arquivo", command=self.open_file)
        self.context_menu.add_command(label="Abrir Pasta", command=self.open_folder)
        self.context_menu.add_command(label="Copiar URL", command=self.copy_url)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Remover do Histórico", command=self.remove_item)
        
        self.history_tree.bind("<Button-3>", self.show_context_menu)
    
    def setup_layout(self):
        """Configura layout da aba"""
        self.frame.rowconfigure(3, weight=1)  # Ajustar para acomodar filtros
        self.frame.columnconfigure(0, weight=1)
        
        # Controles
        self.controls_frame.grid(row=0, column=0, sticky='ew', padx=UIConstants.PADDING, pady=UIConstants.BUTTON_PADDING)
        self.refresh_button.pack(side=tk.LEFT, padx=(0, 5))
        self.clear_button.pack(side=tk.LEFT)
        
        # Busca
        self.search_frame.grid(row=1, column=0, sticky='ew', padx=UIConstants.PADDING, pady=(0, UIConstants.PADDING))
        
        # Filtros
        self.filters_frame.grid(row=2, column=0, sticky='ew', padx=UIConstants.PADDING, pady=(0, UIConstants.PADDING))
        
        # Treeview
        self.tree_frame.grid(row=3, column=0, sticky='nsew', padx=UIConstants.PADDING, pady=(0, UIConstants.PADDING))
        self.tree_frame.rowconfigure(0, weight=1)
        self.tree_frame.columnconfigure(0, weight=1)
        
        self.history_tree.grid(row=0, column=0, sticky='nsew')
        self.tree_scrollbar.grid(row=0, column=1, sticky='ns')
        
        # Paginação
        self.pagination_frame.grid(row=4, column=0, sticky='ew', padx=UIConstants.PADDING, pady=UIConstants.PADDING)
    
    def update_history(self, reset_page=True):
        """Atualiza lista do histórico"""
        if reset_page:
            self.current_page = 1
        
        # Limpar itens existentes
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # Obter filtros de busca
        filters = self.get_current_filters()
        
        # Obter downloads paginados
        result = self.history_manager.get_downloads_paginated(
            page=self.current_page,
            per_page=self.per_page,
            filters=filters
        )
        
        downloads = result['downloads']
        pagination = result['pagination']
        
        # Atualizar informações de paginação
        self.total_pages = pagination['total_pages']
        self.total_count = pagination['total_count']
        
        # Adicionar ao treeview
        for download in downloads:
            self.history_tree.insert('', 'end', values=(
                download.get('id', ''),
                download.get('title_short', download.get('title', 'N/A')),
                download.get('resolution', 'N/A'),
                download.get('date_formatted', 'N/A'),
                download.get('status', 'N/A')
            ))
        
        # Atualizar controles de paginação
        self.update_pagination_controls()
    
    def show_context_menu(self, event):
        """Mostra menu de contexto"""
        item = self.history_tree.selection()[0] if self.history_tree.selection() else None
        if item:
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()
    
    def get_selected_download_id(self):
        """Obtém ID do download selecionado"""
        selection = self.history_tree.selection()
        if selection:
            item = selection[0]
            values = self.history_tree.item(item, 'values')
            return int(values[0]) if values[0] else None
        return None
    
    def open_file(self):
        """Abre arquivo do download selecionado"""
        download_id = self.get_selected_download_id()
        if download_id:
            success, message = self.history_manager.open_download_file(download_id)
            if not success:
                AppUtils.show_error_message("Erro", message)
    
    def open_folder(self):
        """Abre pasta do download selecionado"""
        download_id = self.get_selected_download_id()
        if download_id:
            success, message = self.history_manager.open_download_folder(download_id)
            if not success:
                AppUtils.show_error_message("Erro", message)
    
    def copy_url(self):
        """Copia URL do download selecionado"""
        download_id = self.get_selected_download_id()
        if download_id:
            success, message = self.history_manager.copy_download_url(download_id)
            if success:
                AppUtils.show_info_message("Sucesso", message)
            else:
                AppUtils.show_error_message("Erro", message)
    
    def remove_item(self):
        """Remove item do histórico"""
        download_id = self.get_selected_download_id()
        if download_id:
            if messagebox.askyesno("Confirmar", "Deseja remover este item do histórico?"):
                success = self.history_manager.remove_download_from_history(download_id)
                if success:
                    self.update_history()
                else:
                    AppUtils.show_error_message("Erro", "Não foi possível remover o item")
    
    def clear_history(self):
        """Limpa todo o histórico"""
        if messagebox.askyesno("Confirmar", "Deseja limpar todo o histórico? Esta ação não pode ser desfeita."):
            success = self.history_manager.clear_history()
            if success:
                self.update_history()
                AppUtils.show_info_message("Sucesso", "Histórico limpo com sucesso")
            else:
                AppUtils.show_error_message("Erro", "Não foi possível limpar o histórico")
    
    def get_current_filters(self):
        """Obtém filtros atuais de busca"""
        filters = {}
        
        # Filtro de busca por texto
        search_text = self.search_var.get().strip()
        if search_text:
            filters['search_query'] = search_text
        
        # Filtro por resolução
        resolution = self.resolution_var.get()
        if resolution and resolution != "Todas":
            filters['resolution'] = resolution
        
        # Filtro por status
        status = self.status_var.get()
        if status and status != "Todos":
            filters['status'] = status
        
        # Filtro por período
        period = self.period_var.get()
        if period and period != "Todos":
            filters['period'] = period
        
        return filters if filters else None
    
    def update_pagination_controls(self):
        """Atualiza estado dos controles de paginação"""
        # Atualizar informações da página
        if self.total_count > 0:
            start_item = (self.current_page - 1) * self.per_page + 1
            end_item = min(self.current_page * self.per_page, self.total_count)
            page_info = f"Página {self.current_page} de {self.total_pages} ({start_item}-{end_item} de {self.total_count} itens)"
        else:
            page_info = "Nenhum item encontrado"
        
        self.page_info_var.set(page_info)
        
        # Atualizar estado dos botões
        has_previous = self.current_page > 1
        has_next = self.current_page < self.total_pages
        
        self.first_button.config(state=tk.NORMAL if has_previous else tk.DISABLED)
        self.prev_button.config(state=tk.NORMAL if has_previous else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if has_next else tk.DISABLED)
        self.last_button.config(state=tk.NORMAL if has_next else tk.DISABLED)
    
    def go_to_first_page(self):
        """Vai para a primeira página"""
        if self.current_page > 1:
            self.current_page = 1
            self.update_history(reset_page=False)
    
    def go_to_previous_page(self):
        """Vai para a página anterior"""
        if self.current_page > 1:
            self.current_page -= 1
            self.update_history(reset_page=False)
    
    def go_to_next_page(self):
        """Vai para a próxima página"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_history(reset_page=False)
    
    def go_to_last_page(self):
        """Vai para a última página"""
        if self.current_page < self.total_pages:
            self.current_page = self.total_pages
            self.update_history(reset_page=False)
    
    def on_per_page_change(self, event=None):
        """Callback para mudança de itens por página"""
        try:
            new_per_page = int(self.per_page_var.get())
            if new_per_page != self.per_page:
                self.per_page = new_per_page
                self.current_page = 1
                self.update_history(reset_page=False)
        except ValueError:
            # Restaurar valor anterior se inválido
            self.per_page_var.set(str(self.per_page))
    
    def on_search(self, event=None):
        """Callback para busca"""
        self.update_history()
    
    def clear_search(self):
        """Limpa busca e atualiza histórico"""
        self.search_var.set("")
        self.update_history()
    
    def on_filter_change(self, event=None):
        """Callback para mudança nos filtros"""
        self.current_page = 1  # Resetar para primeira página
        self.update_history(reset_page=False)
    
    def clear_filters(self):
        """Limpa todos os filtros e atualiza histórico"""
        self.search_var.set("")
        self.resolution_var.set("Todas")
        self.status_var.set("Todos")
        self.period_var.set("Todos")
        self.update_history()
    
    def export_to_csv(self):
        """Exporta os dados filtrados para CSV"""
        try:
            # Obter todos os dados filtrados (sem paginação)
            filters = self.get_current_filters()
            all_downloads = self.history_manager.get_all_downloads_filtered(filters)
            
            if not all_downloads:
                AppUtils.show_info_message("Exportação", "Não há dados para exportar.")
                return
            
            # Solicitar local para salvar
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Salvar arquivo CSV"
            )
            
            if not filename:
                return
            
            # Escrever dados no CSV
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Cabeçalho
                writer.writerow(['ID', 'Título', 'URL', 'Resolução', 'Data', 'Status', 'Caminho do Arquivo'])
                
                # Dados
                for download in all_downloads:
                    writer.writerow([
                        download['id'],
                        download['title'],
                        download['url'],
                        download['resolution'],
                        download['timestamp'],
                        download['status'],
                        download.get('file_path', '')
                    ])
            
            AppUtils.show_info_message("Exportação", f"Dados exportados com sucesso para:\n{filename}")
            
        except Exception as e:
            AppUtils.show_error_message("Erro na Exportação", f"Erro ao exportar para CSV: {str(e)}")
    
    def export_to_pdf(self):
        """Exporta os dados filtrados para PDF"""
        try:
            # Obter todos os dados filtrados (sem paginação)
            filters = self.get_current_filters()
            all_downloads = self.history_manager.get_all_downloads_filtered(filters)
            
            if not all_downloads:
                AppUtils.show_info_message("Exportação", "Não há dados para exportar.")
                return
            
            # Solicitar local para salvar
            filename = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                title="Salvar arquivo PDF"
            )
            
            if not filename:
                return
            
            # Criar documento PDF
            doc = SimpleDocTemplate(
                filename,
                pagesize=A4,
                rightMargin=0.5*inch,
                leftMargin=0.5*inch,
                topMargin=0.5*inch,
                bottomMargin=0.5*inch
            )
            
            # Elementos do documento
            elements = []
            styles = getSampleStyleSheet()
            
            # Título
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=1  # Centralizado
            )
            
            title = Paragraph("Relatório de Downloads - YouTube Downloader", title_style)
            elements.append(title)
            
            # Data de geração
            date_style = ParagraphStyle(
                'DateStyle',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=20,
                alignment=1  # Centralizado
            )
            
            current_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            date_para = Paragraph(f"Gerado em: {current_date}", date_style)
            elements.append(date_para)
            
            # Informações dos filtros aplicados
            if filters:
                filter_info = "Filtros aplicados: "
                filter_parts = []
                
                if 'search_query' in filters:
                    filter_parts.append(f"Busca: '{filters['search_query']}'")
                if 'resolution' in filters:
                    filter_parts.append(f"Resolução: {filters['resolution']}")
                if 'status' in filters:
                    filter_parts.append(f"Status: {filters['status']}")
                if 'period' in filters:
                    filter_parts.append(f"Período: {filters['period']}")
                
                if filter_parts:
                    filter_info += "; ".join(filter_parts)
                    filter_para = Paragraph(filter_info, styles['Normal'])
                    elements.append(filter_para)
                    elements.append(Spacer(1, 12))
            
            # Preparar dados da tabela
            table_data = [['ID', 'Título', 'Resolução', 'Data', 'Status']]
            
            for download in all_downloads:
                # Truncar título se muito longo
                title = download['title']
                if len(title) > 50:
                    title = title[:47] + "..."
                
                # Formatar data
                try:
                    date_obj = datetime.fromisoformat(download['timestamp'].replace('Z', '+00:00'))
                    formatted_date = date_obj.strftime("%d/%m/%Y %H:%M")
                except:
                    formatted_date = download['timestamp']
                
                table_data.append([
                    str(download['id']),
                    title,
                    download['resolution'],
                    formatted_date,
                    download['status']
                ])
            
            # Criar tabela
            table = Table(table_data, colWidths=[0.8*inch, 3.5*inch, 1*inch, 1.2*inch, 1*inch])
            
            # Estilo da tabela
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            
            elements.append(table)
            
            # Rodapé com total de registros
            elements.append(Spacer(1, 20))
            footer_para = Paragraph(f"Total de registros: {len(all_downloads)}", styles['Normal'])
            elements.append(footer_para)
            
            # Gerar PDF
            doc.build(elements)
            
            AppUtils.show_info_message("Exportação", f"Relatório PDF gerado com sucesso:\n{filename}")
            
        except Exception as e:
            AppUtils.show_error_message("Erro na Exportação", f"Erro ao gerar PDF: {str(e)}")

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
            else:
                AppUtils.show_error_message("Erro", "Não foi possível restaurar as configurações")

class AnalyticsTab:
    """Aba de análise e estatísticas de downloads"""
    
    def __init__(self, parent, history_manager, log_manager):
        """
        Inicializa a aba de análise
        
        Args:
            parent: Widget pai
            history_manager: Instância do HistoryManager
            log_manager: Instância do LogManager
        """
        self.parent = parent
        self.history_manager = history_manager
        self.log_manager = log_manager
        
        # Inicializar gerenciadores de análise
        self.analytics_manager = AnalyticsManager(
            self.history_manager.db_manager,
            self.log_manager
        )
        self.recommendation_engine = RecommendationEngine(
            self.analytics_manager,
            self.history_manager.db_manager,
            self.log_manager
        )
        
        # Configurar matplotlib para tema escuro
        plt.style.use('dark_background')
        
        self.create_widgets()
        self.setup_layout()
        self.load_analytics_data()
    
    def create_widgets(self):
        """Cria os widgets da aba de análise"""
        # Frame principal
        self.frame = ttk.Frame(self.parent)
        
        # Criar notebook para sub-abas
        self.analytics_notebook = ttk.Notebook(self.frame)
        
        # Criar sub-abas
        self.create_dashboard_tab()
        self.create_charts_tab()
        self.create_reports_tab()
        self.create_recommendations_tab()
        
        # Botão de atualização
        self.refresh_button = ttk.Button(
            self.frame,
            text="🔄 Atualizar Dados",
            command=self.refresh_analytics
        )
    
    def create_dashboard_tab(self):
        """Cria a aba do dashboard principal"""
        self.dashboard_frame = ttk.Frame(self.analytics_notebook)
        self.analytics_notebook.add(self.dashboard_frame, text="📊 Dashboard")
        
        # Frame para estatísticas gerais
        stats_frame = ttk.LabelFrame(self.dashboard_frame, text="Estatísticas Gerais")
        stats_frame.pack(fill='x', padx=10, pady=5)
        
        # Grid para estatísticas
        self.stats_labels = {}
        stats_data = [
            ('total_downloads', 'Total de Downloads'),
            ('successful_downloads', 'Downloads Concluídos'),
            ('success_rate', 'Taxa de Sucesso (%)'),
            ('total_size_gb', 'Tamanho Total (GB)'),
            ('unique_channels', 'Canais Únicos'),
            ('avg_size_mb', 'Tamanho Médio (MB)')
        ]
        
        for i, (key, label) in enumerate(stats_data):
            row = i // 3
            col = (i % 3) * 2
            
            ttk.Label(stats_frame, text=f"{label}:").grid(
                row=row, column=col, sticky='w', padx=5, pady=2
            )
            
            value_label = ttk.Label(stats_frame, text="0", font=('Arial', 10, 'bold'))
            value_label.grid(row=row, column=col+1, sticky='w', padx=5, pady=2)
            self.stats_labels[key] = value_label
        
        # Frame para top canais
        channels_frame = ttk.LabelFrame(self.dashboard_frame, text="Top 5 Canais")
        channels_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Treeview para canais
        self.channels_tree = ttk.Treeview(
            channels_frame,
            columns=('downloads', 'size'),
            show='tree headings',
            height=6
        )
        self.channels_tree.heading('#0', text='Canal')
        self.channels_tree.heading('downloads', text='Downloads')
        self.channels_tree.heading('size', text='Tamanho (MB)')
        
        self.channels_tree.column('#0', width=300)
        self.channels_tree.column('downloads', width=100)
        self.channels_tree.column('size', width=100)
        
        # Scrollbar para canais
        channels_scrollbar = ttk.Scrollbar(channels_frame, orient='vertical', command=self.channels_tree.yview)
        self.channels_tree.configure(yscrollcommand=channels_scrollbar.set)
        
        self.channels_tree.pack(side='left', fill='both', expand=True)
        channels_scrollbar.pack(side='right', fill='y')
    
    def create_charts_tab(self):
        """Cria a aba de gráficos"""
        self.charts_frame = ttk.Frame(self.analytics_notebook)
        self.analytics_notebook.add(self.charts_frame, text="📈 Gráficos")
        
        # Frame de controles
        controls_frame = ttk.Frame(self.charts_frame)
        controls_frame.pack(fill='x', padx=10, pady=5)
        
        # Seletor de período
        ttk.Label(controls_frame, text="Período:").pack(side='left', padx=5)
        self.period_var = tk.StringVar(value="30")
        period_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.period_var,
            values=["7", "30", "90", "365"],
            state="readonly",
            width=10
        )
        period_combo.pack(side='left', padx=5)
        period_combo.bind('<<ComboboxSelected>>', self.on_period_change)
        
        # Botão para atualizar gráficos
        ttk.Button(
            controls_frame,
            text="Atualizar Gráficos",
            command=self.update_charts
        ).pack(side='left', padx=10)
        
        # Notebook para diferentes gráficos
        self.charts_notebook = ttk.Notebook(self.charts_frame)
        self.charts_notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Criar frames para gráficos
        self.create_resolution_chart()
        self.create_trend_chart()
        self.create_hourly_chart()
        self.create_storage_chart()
    
    def create_resolution_chart(self):
        """Cria gráfico de distribuição por resolução"""
        self.resolution_frame = ttk.Frame(self.charts_notebook)
        self.charts_notebook.add(self.resolution_frame, text="Resoluções")
        
        # Figura matplotlib
        self.resolution_fig = Figure(figsize=(8, 6), dpi=100)
        self.resolution_canvas = FigureCanvasTkAgg(self.resolution_fig, self.resolution_frame)
        self.resolution_canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def create_trend_chart(self):
        """Cria gráfico de tendência temporal"""
        self.trend_frame = ttk.Frame(self.charts_notebook)
        self.charts_notebook.add(self.trend_frame, text="Tendência")
        
        self.trend_fig = Figure(figsize=(8, 6), dpi=100)
        self.trend_canvas = FigureCanvasTkAgg(self.trend_fig, self.trend_frame)
        self.trend_canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def create_hourly_chart(self):
        """Cria gráfico de distribuição por hora"""
        self.hourly_frame = ttk.Frame(self.charts_notebook)
        self.charts_notebook.add(self.hourly_frame, text="Por Hora")
        
        self.hourly_fig = Figure(figsize=(8, 6), dpi=100)
        self.hourly_canvas = FigureCanvasTkAgg(self.hourly_fig, self.hourly_frame)
        self.hourly_canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def create_storage_chart(self):
        """Cria gráfico de análise de armazenamento"""
        self.storage_frame = ttk.Frame(self.charts_notebook)
        self.charts_notebook.add(self.storage_frame, text="Armazenamento")
        
        self.storage_fig = Figure(figsize=(8, 6), dpi=100)
        self.storage_canvas = FigureCanvasTkAgg(self.storage_fig, self.storage_frame)
        self.storage_canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def create_reports_tab(self):
        """Cria a aba de relatórios"""
        self.reports_frame = ttk.Frame(self.analytics_notebook)
        self.analytics_notebook.add(self.reports_frame, text="📋 Relatórios")
        
        # Frame de controles
        controls_frame = ttk.Frame(self.reports_frame)
        controls_frame.pack(fill='x', padx=10, pady=5)
        
        # Seletor de tipo de relatório
        ttk.Label(controls_frame, text="Tipo de Relatório:").pack(side='left', padx=5)
        self.report_type_var = tk.StringVar(value="summary")
        report_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.report_type_var,
            values=["summary", "detailed", "channels", "resolutions"],
            state="readonly",
            width=15
        )
        report_combo.pack(side='left', padx=5)
        
        # Botões de ação
        ttk.Button(
            controls_frame,
            text="Gerar Relatório",
            command=self.generate_report
        ).pack(side='left', padx=10)
        
        ttk.Button(
            controls_frame,
            text="Exportar PDF",
            command=self.export_report_pdf
        ).pack(side='left', padx=5)
        
        ttk.Button(
            controls_frame,
            text="Exportar CSV",
            command=self.export_report_csv
        ).pack(side='left', padx=5)
        
        # Área de texto para relatório
        text_frame = ttk.Frame(self.reports_frame)
        text_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.report_text = tk.Text(
            text_frame,
            wrap='word',
            font=('Consolas', 10)
        )
        
        report_scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.report_text.yview)
        self.report_text.configure(yscrollcommand=report_scrollbar.set)
        
        self.report_text.pack(side='left', fill='both', expand=True)
        report_scrollbar.pack(side='right', fill='y')
    
    def create_recommendations_tab(self):
        """Cria a aba de recomendações"""
        self.recommendations_frame = ttk.Frame(self.analytics_notebook)
        self.analytics_notebook.add(self.recommendations_frame, text="💡 Recomendações")
        
        # Frame para recomendações de resolução
        resolution_rec_frame = ttk.LabelFrame(
            self.recommendations_frame,
            text="Recomendação de Resolução"
        )
        resolution_rec_frame.pack(fill='x', padx=10, pady=5)
        
        self.resolution_rec_label = ttk.Label(
            resolution_rec_frame,
            text="Analisando padrões...",
            font=('Arial', 10)
        )
        self.resolution_rec_label.pack(padx=10, pady=5)
        
        # Frame para recomendações de horário
        time_rec_frame = ttk.LabelFrame(
            self.recommendations_frame,
            text="Melhor Horário para Downloads"
        )
        time_rec_frame.pack(fill='x', padx=10, pady=5)
        
        self.time_rec_label = ttk.Label(
            time_rec_frame,
            text="Analisando padrões...",
            font=('Arial', 10)
        )
        self.time_rec_label.pack(padx=10, pady=5)
        
        # Frame para recomendações de armazenamento
        storage_rec_frame = ttk.LabelFrame(
            self.recommendations_frame,
            text="Gerenciamento de Armazenamento"
        )
        storage_rec_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Listbox para recomendações de armazenamento
        self.storage_rec_listbox = tk.Listbox(
            storage_rec_frame,
            font=('Arial', 9),
            height=8
        )
        
        storage_rec_scrollbar = ttk.Scrollbar(
            storage_rec_frame,
            orient='vertical',
            command=self.storage_rec_listbox.yview
        )
        self.storage_rec_listbox.configure(yscrollcommand=storage_rec_scrollbar.set)
        
        self.storage_rec_listbox.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        storage_rec_scrollbar.pack(side='right', fill='y', pady=5)
    
    def setup_layout(self):
        """Configura o layout da aba"""
        self.analytics_notebook.pack(fill='both', expand=True, padx=5, pady=5)
        self.refresh_button.pack(pady=5)
    
    def load_analytics_data(self):
        """Carrega os dados de análise"""
        try:
            # Carregar estatísticas gerais
            self.update_dashboard_stats()
            
            # Carregar gráficos
            self.update_charts()
            
            # Carregar recomendações
            self.update_recommendations()
            
            # Gerar relatório inicial
            self.generate_report()
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao carregar dados de análise: {e}")
            messagebox.showerror("Erro", f"Erro ao carregar dados de análise: {e}")
    
    def update_dashboard_stats(self):
        """Atualiza as estatísticas do dashboard"""
        try:
            stats = self.analytics_manager.get_download_statistics()
            
            for key, label_widget in self.stats_labels.items():
                value = stats.get(key, 0)
                if isinstance(value, float):
                    value = f"{value:.2f}"
                label_widget.config(text=str(value))
            
            # Atualizar top canais
            self.update_top_channels()
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao atualizar estatísticas: {e}")
    
    def update_top_channels(self):
        """Atualiza a lista de top canais"""
        try:
            # Limpar árvore
            for item in self.channels_tree.get_children():
                self.channels_tree.delete(item)
            
            top_channels = self.analytics_manager.get_top_channels(limit=5)
            
            for channel, count in top_channels:
                # Calcular tamanho aproximado (placeholder)
                size_mb = count * 50  # Estimativa
                
                self.channels_tree.insert(
                    '',
                    'end',
                    text=channel,
                    values=(count, f"{size_mb:.1f}")
                )
                
        except Exception as e:
            self.log_manager.log_error(f"Erro ao atualizar top canais: {e}")
    
    def update_charts(self):
        """Atualiza todos os gráficos"""
        try:
            period_days = int(self.period_var.get())
            
            # Atualizar gráfico de resolução
            self.update_resolution_chart(period_days)
            
            # Atualizar gráfico de tendência
            self.update_trend_chart(period_days)
            
            # Atualizar gráfico por hora
            self.update_hourly_chart(period_days)
            
            # Atualizar gráfico de armazenamento
            self.update_storage_chart()
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao atualizar gráficos: {e}")
    
    def update_resolution_chart(self, period_days):
        """Atualiza o gráfico de distribuição por resolução"""
        try:
            self.resolution_fig.clear()
            ax = self.resolution_fig.add_subplot(111)
            
            distribution = self.analytics_manager.get_resolution_distribution(period_days)
            
            if distribution:
                resolutions = list(distribution.keys())
                counts = list(distribution.values())
                
                colors_list = plt.cm.Set3(np.linspace(0, 1, len(resolutions)))
                
                wedges, texts, autotexts = ax.pie(
                    counts,
                    labels=resolutions,
                    autopct='%1.1f%%',
                    colors=colors_list,
                    startangle=90
                )
                
                ax.set_title(f'Distribuição por Resolução ({period_days} dias)', fontsize=12, color='white')
                
                # Configurar cores do texto
                for text in texts:
                    text.set_color('white')
                for autotext in autotexts:
                    autotext.set_color('black')
                    autotext.set_fontweight('bold')
            else:
                ax.text(0.5, 0.5, 'Sem dados disponíveis', 
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax.transAxes, fontsize=12, color='white')
            
            self.resolution_fig.patch.set_facecolor('#2e2e2e')
            ax.set_facecolor('#2e2e2e')
            self.resolution_canvas.draw()
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao atualizar gráfico de resolução: {e}")
    
    def update_trend_chart(self, period_days):
        """Atualiza o gráfico de tendência temporal"""
        try:
            self.trend_fig.clear()
            ax = self.trend_fig.add_subplot(111)
            
            trend_data = self.analytics_manager.get_daily_download_trend(period_days)
            
            if trend_data['dates'] and trend_data['counts']:
                dates = [datetime.strptime(date, '%Y-%m-%d') for date in trend_data['dates']]
                counts = trend_data['counts']
                
                ax.plot(dates, counts, marker='o', linewidth=2, markersize=4, color='#00ff88')
                ax.fill_between(dates, counts, alpha=0.3, color='#00ff88')
                
                ax.set_title(f'Tendência de Downloads ({period_days} dias)', fontsize=12, color='white')
                ax.set_xlabel('Data', color='white')
                ax.set_ylabel('Número de Downloads', color='white')
                
                # Configurar cores dos eixos
                ax.tick_params(colors='white')
                ax.spines['bottom'].set_color('white')
                ax.spines['top'].set_color('white')
                ax.spines['right'].set_color('white')
                ax.spines['left'].set_color('white')
                
                # Rotacionar labels das datas
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            else:
                ax.text(0.5, 0.5, 'Sem dados disponíveis', 
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax.transAxes, fontsize=12, color='white')
            
            self.trend_fig.patch.set_facecolor('#2e2e2e')
            ax.set_facecolor('#2e2e2e')
            self.trend_fig.tight_layout()
            self.trend_canvas.draw()
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao atualizar gráfico de tendência: {e}")
    
    def update_hourly_chart(self, period_days):
        """Atualiza o gráfico de distribuição por hora"""
        try:
            self.hourly_fig.clear()
            ax = self.hourly_fig.add_subplot(111)
            
            hourly_dist = self.analytics_manager.get_hourly_distribution(period_days)
            
            if hourly_dist:
                hours = list(range(24))
                counts = [hourly_dist.get(hour, 0) for hour in hours]
                
                bars = ax.bar(hours, counts, color='#ff6b6b', alpha=0.7)
                
                # Destacar hora de pico
                max_hour = max(hourly_dist.items(), key=lambda x: x[1])[0] if hourly_dist else 0
                if max_hour < len(bars):
                    bars[max_hour].set_color('#ff3333')
                
                ax.set_title(f'Downloads por Hora do Dia ({period_days} dias)', fontsize=12, color='white')
                ax.set_xlabel('Hora do Dia', color='white')
                ax.set_ylabel('Número de Downloads', color='white')
                ax.set_xticks(range(0, 24, 2))
                
                # Configurar cores
                ax.tick_params(colors='white')
                ax.spines['bottom'].set_color('white')
                ax.spines['top'].set_color('white')
                ax.spines['right'].set_color('white')
                ax.spines['left'].set_color('white')
            else:
                ax.text(0.5, 0.5, 'Sem dados disponíveis', 
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax.transAxes, fontsize=12, color='white')
            
            self.hourly_fig.patch.set_facecolor('#2e2e2e')
            ax.set_facecolor('#2e2e2e')
            self.hourly_canvas.draw()
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao atualizar gráfico por hora: {e}")
    
    def update_storage_chart(self):
        """Atualiza o gráfico de análise de armazenamento"""
        try:
            self.storage_fig.clear()
            ax = self.storage_fig.add_subplot(111)
            
            storage_analysis = self.analytics_manager.get_storage_analysis()
            
            if storage_analysis['by_resolution']:
                resolutions = [item['resolution'] for item in storage_analysis['by_resolution']]
                sizes = [item['total_size_mb'] for item in storage_analysis['by_resolution']]
                
                colors_list = plt.cm.viridis(np.linspace(0, 1, len(resolutions)))
                
                bars = ax.bar(resolutions, sizes, color=colors_list)
                
                ax.set_title('Uso de Armazenamento por Resolução', fontsize=12, color='white')
                ax.set_xlabel('Resolução', color='white')
                ax.set_ylabel('Tamanho Total (MB)', color='white')
                
                # Rotacionar labels
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
                
                # Configurar cores
                ax.tick_params(colors='white')
                ax.spines['bottom'].set_color('white')
                ax.spines['top'].set_color('white')
                ax.spines['right'].set_color('white')
                ax.spines['left'].set_color('white')
            else:
                ax.text(0.5, 0.5, 'Sem dados disponíveis', 
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax.transAxes, fontsize=12, color='white')
            
            self.storage_fig.patch.set_facecolor('#2e2e2e')
            ax.set_facecolor('#2e2e2e')
            self.storage_fig.tight_layout()
            self.storage_canvas.draw()
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao atualizar gráfico de armazenamento: {e}")
    
    def update_recommendations(self):
        """Atualiza as recomendações"""
        try:
            # Recomendação de resolução
            resolution_rec = self.recommendation_engine.get_resolution_recommendation()
            resolution_text = f"Resolução recomendada: {resolution_rec['recommended_resolution']}\n"
            resolution_text += f"Motivo: {resolution_rec['reason']}\n"
            resolution_text += f"Confiança: {resolution_rec['confidence']*100:.1f}%"
            self.resolution_rec_label.config(text=resolution_text)
            
            # Recomendação de horário
            time_rec = self.recommendation_engine.get_optimal_download_time()
            time_text = f"Melhores horários: {', '.join(map(str, time_rec['recommended_hours'][:3]))}h\n"
            time_text += f"Horário de pico: {time_rec['peak_hour']}h\n"
            time_text += f"Motivo: {time_rec['reason']}"
            self.time_rec_label.config(text=time_text)
            
            # Recomendações de armazenamento
            storage_recs = self.recommendation_engine.get_storage_recommendations()
            self.storage_rec_listbox.delete(0, tk.END)
            
            if storage_recs:
                for rec in storage_recs:
                    priority_icon = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🟢"
                    text = f"{priority_icon} {rec['title']}: {rec['description']}"
                    self.storage_rec_listbox.insert(tk.END, text)
            else:
                self.storage_rec_listbox.insert(tk.END, "✅ Nenhuma recomendação no momento")
                
        except Exception as e:
            self.log_manager.log_error(f"Erro ao atualizar recomendações: {e}")
    
    def generate_report(self):
        """Gera relatório baseado no tipo selecionado"""
        try:
            report_type = self.report_type_var.get()
            
            self.report_text.delete(1.0, tk.END)
            
            if report_type == "summary":
                report = self.generate_summary_report()
            elif report_type == "detailed":
                report = self.generate_detailed_report()
            elif report_type == "channels":
                report = self.generate_channels_report()
            elif report_type == "resolutions":
                report = self.generate_resolutions_report()
            else:
                report = "Tipo de relatório não reconhecido."
            
            self.report_text.insert(1.0, report)
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao gerar relatório: {e}")
            self.report_text.insert(1.0, f"Erro ao gerar relatório: {e}")
    
    def generate_summary_report(self):
        """Gera relatório resumido"""
        stats = self.analytics_manager.get_download_statistics()
        
        report = f"""RELATÓRIO RESUMIDO DE DOWNLOADS
{'='*50}
Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}

ESTATÍSTICAS GERAIS (30 dias):
{'-'*30}
Total de Downloads: {stats.get('total_downloads', 0)}
Downloads Concluídos: {stats.get('successful_downloads', 0)}
Taxa de Sucesso: {stats.get('success_rate', 0):.2f}%
Tamanho Total: {stats.get('total_size_gb', 0):.2f} GB
Tamanho Médio: {stats.get('avg_size_mb', 0):.2f} MB
Canais Únicos: {stats.get('unique_channels', 0)}
Downloads de Áudio: {stats.get('audio_downloads', 0)}
Downloads de Vídeo: {stats.get('video_downloads', 0)}

TOP 5 CANAIS:
{'-'*15}"""
        
        top_channels = self.analytics_manager.get_top_channels(limit=5)
        for i, (channel, count) in enumerate(top_channels, 1):
            report += f"\n{i}. {channel}: {count} downloads"
        
        return report
    
    def generate_detailed_report(self):
        """Gera relatório detalhado"""
        stats = self.analytics_manager.get_download_statistics()
        resolution_dist = self.analytics_manager.get_resolution_distribution()
        storage_analysis = self.analytics_manager.get_storage_analysis()
        
        report = f"""RELATÓRIO DETALHADO DE DOWNLOADS
{'='*50}
Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}

ESTATÍSTICAS GERAIS:
{'-'*20}
Período analisado: 30 dias
Total de Downloads: {stats.get('total_downloads', 0)}
Downloads Concluídos: {stats.get('successful_downloads', 0)}
Downloads com Erro: {stats.get('failed_downloads', 0)}
Taxa de Sucesso: {stats.get('success_rate', 0):.2f}%

ARMAZENAMENTO:
{'-'*15}
Tamanho Total: {stats.get('total_size_gb', 0):.2f} GB
Tamanho Médio por Download: {stats.get('avg_size_mb', 0):.2f} MB
Total de Arquivos: {storage_analysis.get('total_files', 0)}

DISTRIBUIÇÃO POR RESOLUÇÃO:
{'-'*30}"""
        
        for resolution, count in resolution_dist.items():
            percentage = (count / stats.get('total_downloads', 1)) * 100
            report += f"\n{resolution}: {count} downloads ({percentage:.1f}%)"
        
        report += f"\n\nANÁLISE DE ARMAZENAMENTO POR RESOLUÇÃO:\n{'-'*40}"
        for item in storage_analysis.get('by_resolution', []):
            report += f"\n{item['resolution']}: {item['total_size_mb']:.1f} MB ({item['count']} arquivos)"
        
        return report
    
    def generate_channels_report(self):
        """Gera relatório de canais"""
        top_channels = self.analytics_manager.get_top_channels(limit=20)
        
        report = f"""RELATÓRIO DE CANAIS
{'='*30}
Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}

TOP 20 CANAIS MAIS BAIXADOS:
{'-'*35}"""
        
        for i, (channel, count) in enumerate(top_channels, 1):
            report += f"\n{i:2d}. {channel:<40} {count:>3d} downloads"
        
        return report
    
    def generate_resolutions_report(self):
        """Gera relatório de resoluções"""
        resolution_dist = self.analytics_manager.get_resolution_distribution()
        storage_analysis = self.analytics_manager.get_storage_analysis()
        
        report = f"""RELATÓRIO DE RESOLUÇÕES
{'='*35}
Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}

DISTRIBUIÇÃO POR RESOLUÇÃO:
{'-'*30}"""
        
        total_downloads = sum(resolution_dist.values()) if resolution_dist else 1
        
        for resolution, count in resolution_dist.items():
            percentage = (count / total_downloads) * 100
            report += f"\n{resolution:<15} {count:>4d} downloads ({percentage:>5.1f}%)"
        
        report += f"\n\nUSO DE ARMAZENAMENTO POR RESOLUÇÃO:\n{'-'*40}"
        for item in storage_analysis.get('by_resolution', []):
            avg_size = item['avg_size_mb']
            report += f"\n{item['resolution']:<15} {item['total_size_mb']:>8.1f} MB (média: {avg_size:.1f} MB)"
        
        return report
    
    def export_report_pdf(self):
        """Exporta relatório atual para PDF"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                title="Salvar Relatório PDF"
            )
            
            if filename:
                report_content = self.report_text.get(1.0, tk.END)
                
                doc = SimpleDocTemplate(filename, pagesize=A4)
                styles = getSampleStyleSheet()
                story = []
                
                # Título
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=16,
                    spaceAfter=30,
                    alignment=1  # Center
                )
                story.append(Paragraph("Relatório de Analytics - YouTube Downloader", title_style))
                story.append(Spacer(1, 12))
                
                # Conteúdo
                content_style = ParagraphStyle(
                    'CustomContent',
                    parent=styles['Normal'],
                    fontSize=10,
                    fontName='Courier'
                )
                
                # Dividir conteúdo em linhas e criar parágrafos
                lines = report_content.split('\n')
                for line in lines:
                    if line.strip():
                        story.append(Paragraph(line, content_style))
                    else:
                        story.append(Spacer(1, 6))
                
                doc.build(story)
                messagebox.showinfo("Sucesso", f"Relatório exportado para: {filename}")
                
        except Exception as e:
            self.log_manager.log_error(f"Erro ao exportar PDF: {e}")
            messagebox.showerror("Erro", f"Erro ao exportar PDF: {e}")
    
    def export_report_csv(self):
        """Exporta dados para CSV"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Salvar Dados CSV"
            )
            
            if filename:
                report_type = self.report_type_var.get()
                
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    if report_type == "channels":
                        writer.writerow(['Canal', 'Downloads'])
                        top_channels = self.analytics_manager.get_top_channels(limit=50)
                        for channel, count in top_channels:
                            writer.writerow([channel, count])
                    
                    elif report_type == "resolutions":
                        writer.writerow(['Resolução', 'Downloads', 'Tamanho Total (MB)', 'Tamanho Médio (MB)'])
                        resolution_dist = self.analytics_manager.get_resolution_distribution()
                        storage_analysis = self.analytics_manager.get_storage_analysis()
                        
                        storage_by_res = {item['resolution']: item for item in storage_analysis.get('by_resolution', [])}
                        
                        for resolution, count in resolution_dist.items():
                            storage_info = storage_by_res.get(resolution, {})
                            total_size = storage_info.get('total_size_mb', 0)
                            avg_size = storage_info.get('avg_size_mb', 0)
                            writer.writerow([resolution, count, total_size, avg_size])
                    
                    else:
                        # Exportar estatísticas gerais
                        stats = self.analytics_manager.get_download_statistics()
                        writer.writerow(['Métrica', 'Valor'])
                        for key, value in stats.items():
                            writer.writerow([key.replace('_', ' ').title(), value])
                
                messagebox.showinfo("Sucesso", f"Dados exportados para: {filename}")
                
        except Exception as e:
            self.log_manager.log_error(f"Erro ao exportar CSV: {e}")
            messagebox.showerror("Erro", f"Erro ao exportar CSV: {e}")
    
    def on_period_change(self, event=None):
        """Callback para mudança de período"""
        self.update_charts()
    
    def refresh_analytics(self):
        """Atualiza todos os dados de análise"""
        try:
            # Limpar cache
            self.analytics_manager.clear_cache()
            
            # Recarregar dados
            self.load_analytics_data()
            
            messagebox.showinfo("Sucesso", "Dados de análise atualizados!")
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao atualizar análise: {e}")
            messagebox.showerror("Erro", f"Erro ao atualizar análise: {e}")