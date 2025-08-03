import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import threading
import os
import webbrowser
import requests
from PIL import Image, ImageTk
from io import BytesIO
from utils import AppUtils, UIConstants, AppConstants

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
        self.url_label = tk.Label(self.frame, text="URL do vídeo:")
        self.url_entry = tk.Entry(self.frame, width=50)
        
        # Menu de contexto para URL
        self.create_context_menu()
        
        # Botão extrair
        self.extract_button = tk.Button(
            self.frame, 
            text="Extrair informações", 
            command=self.extract_info
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
        self.metadata_text = tk.Text(self.metadata_frame, wrap=tk.WORD, width=40, height=10)
        self.metadata_scrollbar = tk.Scrollbar(self.metadata_frame)
        self.metadata_text.config(yscrollcommand=self.metadata_scrollbar.set)
        self.metadata_scrollbar.config(command=self.metadata_text.yview)
        
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
        self.mini_player_frame = tk.Frame(self.frame, relief=tk.RAISED, bd=1)
        
        # Frame para thumbnail
        self.thumbnail_frame = tk.Frame(self.mini_player_frame)
        self.thumbnail_label = tk.Label(
            self.thumbnail_frame,
            text="📺",
            font=("Arial", 24),
            width=20,
            height=5,
            relief=tk.SUNKEN,
            bd=1
        )
        
        # Frame para informações do vídeo
        self.info_frame = tk.Frame(self.mini_player_frame)
        
        # Título do vídeo
        self.video_title_label = tk.Label(
            self.info_frame,
            text="",
            font=("Arial", 10, "bold"),
            wraplength=300,
            justify=tk.LEFT
        )
        
        # Informações adicionais (duração, canal, etc.)
        self.video_info_label = tk.Label(
            self.info_frame,
            text="",
            font=("Arial", 9),
            justify=tk.LEFT
        )
        
        # Botão para abrir vídeo no navegador
        self.preview_button = tk.Button(
            self.info_frame,
            text="🎬 Preview",
            command=self.open_video_preview,
            font=("Arial", 9),
            bg="#4CAF50",
            fg="white"
        )
        
        # Layout do mini-player
        self.thumbnail_label.pack()
        self.thumbnail_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.video_title_label.pack(anchor='w', pady=(5, 2))
        self.video_info_label.pack(anchor='w', pady=(0, 2))
        self.preview_button.pack(anchor='w', pady=(5, 5))
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
        """Exibe o mini-player"""
        self.mini_player_frame.grid(row=4, column=0, columnspan=2, sticky='ew', pady=5)
    
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
    
    def setup_layout(self):
        """Configura layout da aba"""
        # Configurar grid (adicionando linha para mini-player)
        for i in range(10):
            if i == 2:  # Linha dos frames principais
                self.frame.rowconfigure(i, weight=1, pad=UIConstants.PADDING)
            else:
                self.frame.rowconfigure(i, pad=UIConstants.PADDING)
        
        for i in range(2):
            self.frame.columnconfigure(i, weight=1, pad=UIConstants.PADDING)
        
        # Posicionar widgets
        self.url_label.grid(row=0, column=0, sticky='w')
        self.url_entry.grid(row=0, column=1, sticky='ew')
        
        self.extract_button.grid(row=1, column=0, columnspan=2, pady=UIConstants.BUTTON_PADDING)
        
        # Frames principais
        self.resolutions_frame.grid(row=2, column=0, sticky='nsew', padx=(0, 5))
        self.metadata_frame.grid(row=2, column=1, sticky='nsew', padx=(5, 0))
        
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
        
        self.download_button.grid(row=3, column=0, columnspan=2, pady=UIConstants.BUTTON_PADDING)
        
        # Mini-player (inicialmente oculto)
        # Será posicionado dinamicamente quando um vídeo for carregado
        
        # Progress frame (inicialmente oculto)
        # Não posicionar aqui - será posicionado dinamicamente em show_progress_bar()
        
        self.directory_button.grid(row=6, column=0, columnspan=2, pady=UIConstants.BUTTON_PADDING)
        self.directory_label.grid(row=7, column=0, columnspan=2, sticky='ew', padx=UIConstants.PADDING)
        
        self.exit_button.grid(row=8, column=0, columnspan=2, pady=UIConstants.PADDING)
    
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
        self.extract_button.config(state=tk.NORMAL, text="Extrair informações")
        
        if success:
            self.update_resolutions(resolutions)
            self.update_metadata(data)
            self.enable_download_if_ready()
        else:
            AppUtils.show_error_message("Erro", data)
    
    def update_resolutions(self, resolutions):
        """Atualiza lista de resoluções"""
        self.resolutions_listbox.delete(0, tk.END)
        self.current_resolutions = resolutions
        
        for resolution in resolutions:
            self.resolutions_listbox.insert(tk.END, resolution)
    
    def update_metadata(self, video_info):
        """Atualiza metadados do vídeo"""
        self.metadata_text.delete("1.0", tk.END)
        
        if isinstance(video_info, dict):
            metadata = self.download_manager.get_video_metadata()
            
            # Título
            title = metadata.get('title', 'N/A')
            self.metadata_text.insert(tk.END, f"📺 Título: {title}\n\n")
            
            # Canal/Uploader
            uploader = metadata.get('uploader', 'N/A')
            self.metadata_text.insert(tk.END, f"👤 Canal: {uploader}\n\n")
            
            # Duração
            duration = metadata.get('duration', 'N/A')
            self.metadata_text.insert(tk.END, f"⏱️ Duração: {duration}\n\n")
            
            # Visualizações
            view_count = metadata.get('view_count', 'N/A')
            self.metadata_text.insert(tk.END, f"👁️ Visualizações: {view_count}\n\n")
            
            # Data de upload
            upload_date = metadata.get('upload_date', 'N/A')
            if upload_date != 'N/A':
                self.metadata_text.insert(tk.END, f"📅 Data de Upload: {upload_date}\n\n")
            
            # Descrição (truncada)
            description = metadata.get('description', 'N/A')
            if description != 'N/A' and description.strip():
                self.metadata_text.insert(tk.END, f"📝 Descrição: {description}")
            
            # Log para debug
            self.log_manager.log_info(f"Metadados atualizados para: {title[:50]}...")
            
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
        
        # Verificar se tem resolução selecionada OU se é download apenas de áudio
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
        
        # Posicionar o frame no grid
        self.progress_frame.grid(row=4, column=0, columnspan=2, sticky='ew', padx=UIConstants.PADDING, pady=UIConstants.BUTTON_PADDING)
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
            selected_index = self.resolutions_listbox.curselection()
            selected_resolution = self.resolutions_listbox.get(selected_index) if selected_index else 'N/A'
            
            download_data = {
                'url': self.url_entry.get().strip(),
                'title': metadata.get('title', 'N/A'),
                'duration': metadata.get('duration', 'N/A'),
                'resolution': selected_resolution,
                'download_path': '',  # Seria necessário obter o caminho real do arquivo
                'uploader': metadata.get('uploader', 'N/A'),
                'view_count': metadata.get('view_count', 0),
                'description': metadata.get('description', '')
            }
            
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
        self.frame.rowconfigure(1, weight=1)
        self.frame.columnconfigure(0, weight=1)
        
        # Controles
        self.controls_frame.grid(row=0, column=0, sticky='ew', padx=UIConstants.PADDING, pady=UIConstants.BUTTON_PADDING)
        self.refresh_button.pack(side=tk.LEFT, padx=(0, 5))
        self.clear_button.pack(side=tk.LEFT)
        
        # Treeview
        self.tree_frame.grid(row=1, column=0, sticky='nsew', padx=UIConstants.PADDING, pady=UIConstants.PADDING)
        self.tree_frame.rowconfigure(0, weight=1)
        self.tree_frame.columnconfigure(0, weight=1)
        
        self.history_tree.grid(row=0, column=0, sticky='nsew')
        self.tree_scrollbar.grid(row=0, column=1, sticky='ns')
    
    def update_history(self):
        """Atualiza lista do histórico"""
        # Limpar itens existentes
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # Obter downloads recentes
        downloads = self.history_manager.get_recent_downloads()
        
        # Adicionar ao treeview
        for download in downloads:
            self.history_tree.insert('', 'end', values=(
                download.get('id', ''),
                download.get('title_short', download.get('title', 'N/A')),
                download.get('resolution', 'N/A'),
                download.get('date_formatted', 'N/A'),
                download.get('status', 'N/A')
            ))
    
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