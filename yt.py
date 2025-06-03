import os
import sys
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import yt_dlp
import threading
import logging
import json
from datetime import datetime
from database_manager import DatabaseManager

# Configurar logging
logging.basicConfig(
    filename='youtube_downloader.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Declare info as a global variable
info = None

# Variable to store the selected download directory
download_directory = ""
download_dir = ""  # Adicionar esta linha para compatibilidade

# Threading control
download_thread = None
is_downloading = False

def log_info(message):
    """Log informações importantes"""
    logging.info(message)
    print(f"[INFO] {message}")

def log_error(error, context=""):
    """Log erros com contexto"""
    error_msg = f"{context}: {str(error)}" if context else str(error)
    logging.error(error_msg)
    return get_friendly_error(error)

def get_friendly_error(error):
    """Converte erros técnicos em mensagens amigáveis"""
    error_str = str(error).lower()
    
    if "http error 403" in error_str or "forbidden" in error_str:
        return "Vídeo privado ou com restrições de acesso"
    elif "video unavailable" in error_str or "not available" in error_str:
        return "Vídeo não disponível ou foi removido"
    elif "no space left" in error_str:
        return "Espaço insuficiente no disco"
    elif "network" in error_str or "connection" in error_str:
        return "Problema de conexão com a internet"
    elif "permission" in error_str:
        return "Sem permissão para salvar no diretório selecionado"
    else:
        return f"Erro inesperado: {str(error)[:100]}..."

def progress_hook(d):
    """Hook para atualizar progresso do download - Versão Completa"""
    if d['status'] == 'downloading':
        try:
            # Tentar todas as formas possíveis de obter porcentagem
            percent = 0
            
            # Verificar se existe downloaded_bytes e total_bytes
            if 'downloaded_bytes' in d and 'total_bytes' in d and d['total_bytes']:
                percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                percent_str = f"{percent:.1f}%"
            
            # Verificar se existe downloaded_bytes e total_bytes_estimate
            elif 'downloaded_bytes' in d and 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                percent_str = f"{percent:.1f}%"
            
            # Tentar _percent_str
            elif '_percent_str' in d:
                percent_str = str(d['_percent_str']).strip()
                percent = float(percent_str.replace('%', ''))
            
            else:
                # Último recurso: tentar extrair de qualquer campo que contenha %
                for key, value in d.items():
                    if isinstance(value, str) and '%' in value:
                        try:
                            percent = float(value.replace('%', ''))
                            percent_str = value
                            break
                        except:
                            continue
                else:
                    percent_str = "0%"
            
            speed_str = d.get('_speed_str', d.get('speed', 'N/A'))
            eta_str = d.get('_eta_str', d.get('eta', 'N/A'))
            
            # Atualizar UI - limitando a 90% para reservar espaço para merge
            display_percent = min(percent * 0.9, 90)  # Download = 90% do total
            root.after(0, lambda p=display_percent, ps=f"{display_percent:.1f}%", ss=str(speed_str), es=str(eta_str): 
                      update_progress_ui(p, ps, ss, es))
            
        except Exception as e:
            log_error(e, "Erro no progress_hook")
    
    elif d['status'] == 'finished':
        # Download concluído, mas ainda falta merge - mostrar 90%
        root.after(0, lambda: update_progress_ui(90, "90%", "Preparando merge...", "Processando"))
        log_info(f"Download concluído: {d.get('filename', 'arquivo')}")
    
    elif d['status'] == 'error':
        error_msg = d.get('error', 'Erro desconhecido')
        log_info(f"Erro no fragmento (continuando): {error_msg}")

def postprocessor_hook(d):
    """Hook para acompanhar o progresso do pós-processamento (merge)"""
    if d['status'] == 'started':
        if 'postprocessor' in d and 'FFmpegVideoRemuxer' in str(d['postprocessor']):
            root.after(0, lambda: update_progress_ui(92, "92%", "Fazendo merge...", "Processando"))
            log_info("Iniciando merge de vídeo e áudio")
        elif 'postprocessor' in d and 'FFmpegMerger' in str(d['postprocessor']):
            root.after(0, lambda: update_progress_ui(95, "95%", "Finalizando merge...", "Processando"))
            log_info("Finalizando processo de merge")
    
    elif d['status'] == 'finished':
        if 'postprocessor' in d and ('FFmpeg' in str(d['postprocessor']) or 'Merger' in str(d['postprocessor'])):
            root.after(0, lambda: update_progress_ui(98, "98%", "Limpando arquivos...", "Finalizando"))
            log_info("Merge concluído, limpando arquivos temporários")

def update_progress_ui(percent, percent_str, speed_str, eta_str):
    """Atualiza a interface com informações de progresso"""
    try:
        # IMPORTANTE: Garantir que o valor esteja no range correto
        percent = max(0, min(100, percent))  # Limitar entre 0 e 100
        
        # Atualizar a barra de progresso
        progress_bar['value'] = percent
        progress_label.config(text=f"Progresso: {percent_str} | Velocidade: {speed_str} | ETA: {eta_str}")
        
        # CRÍTICO: Forçar múltiplas atualizações para garantir que seja visível
        progress_bar.update_idletasks()
        progress_frame.update_idletasks()
        root.update_idletasks()
        
        # Log para debug
        log_info(f"Barra atualizada: {percent}% - {speed_str}")
        
    except Exception as e:
        log_error(e, "Erro ao atualizar UI de progresso")

def extrair_informacoes():
    global info
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("Erro", "Por favor, insira a URL do vídeo.")
        return
    
    # Desabilitar botão durante extração
    extrair_button.config(state=tk.DISABLED)
    extrair_button.config(text="Extraindo...")
    
    def extract_worker():
        global info  # CORREÇÃO CRÍTICA: Declarar global aqui também
        try:
            log_info(f"Iniciando extração de informações: {url}")
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extractflat': False
            }
            ydl = yt_dlp.YoutubeDL(ydl_opts)
            info = ydl.extract_info(url, download=False)  # Agora atualiza a global
            
            log_info(f"Info extraída com sucesso: {info.get('title', 'N/A') if info else 'Erro'}")
            
            resolutions = []
            if 'formats' in info and info['formats']:
                for format in info['formats']:
                    if format.get('resolution') and format.get('resolution') != 'audio only':
                        resolution = format['resolution']
                        if resolution not in resolutions:
                            resolutions.append(resolution)
            
            # Ordenar resoluções
            if resolutions:
                resolutions.sort(key=lambda x: int(x.split('x')[1]) if 'x' in x and x.split('x')[1].isdigit() else 0)
            else:
                resolutions = ['Melhor qualidade disponível']
            
            # Atualizar UI de forma thread-safe
            root.after(0, lambda: update_extraction_ui(resolutions))
            
        except Exception as e:
            error_msg = get_friendly_error(str(e))
            log_error(e, "Erro ao extrair informações")
            root.after(0, lambda: show_extraction_error(error_msg))
    
    # Executar em thread separada
    thread = threading.Thread(target=extract_worker, daemon=True)
    thread.start()

def update_extraction_ui(resolutions):
    """Atualiza UI após extração bem-sucedida"""
    global info
    try:
        # Limpar e atualizar lista de resoluções
        resolutions_listbox.delete(0, tk.END)
        for resolution in resolutions:
            resolutions_listbox.insert(tk.END, resolution)
        
        # Atualizar metadados - CORRIGIDO
        metadata_text.delete("1.0", tk.END)
        
        if info:  # Verificar se info existe
            title = info.get('title', 'N/A')
            description = info.get('description', 'N/A')
            view_count = info.get('view_count', 'N/A')
            duration = info.get('duration', 'N/A')
            
            metadata_text.insert(tk.END, f"Título: {title}\n\n")
            
            if description and description != 'N/A':
                if len(str(description)) > 500:
                    description = str(description)[:500] + "..."
                metadata_text.insert(tk.END, f"Descrição: {description}\n\n")
            else:
                metadata_text.insert(tk.END, "Descrição: Não disponível\n\n")
            
            # Formatar visualizações
            if view_count and view_count != 'N/A':
                try:
                    view_count = f"{int(view_count):,}"
                except:
                    pass
            metadata_text.insert(tk.END, f"Visualizações: {view_count}\n")
            
            # Formatar duração
            if duration and duration != 'N/A':
                try:
                    minutes = int(duration) // 60
                    seconds = int(duration) % 60
                    duration_formatted = f"{minutes}:{seconds:02d}"
                    metadata_text.insert(tk.END, f"Duração: {duration_formatted}")
                except:
                    metadata_text.insert(tk.END, f"Duração: {duration} segundos")
            else:
                metadata_text.insert(tk.END, "Duração: Não disponível")
        else:
            metadata_text.insert(tk.END, "Erro: Informações do vídeo não disponíveis")
        
        # Reabilitar botão
        extrair_button.config(state=tk.NORMAL, text="Extrair informações")
        
        # Habilitar botão de download
        habilitar_botao_download()
        
        log_info(f"Extração concluída: {len(resolutions)} resoluções encontradas")
        
    except Exception as e:
        log_error(e, "Erro ao atualizar UI após extração")
        show_extraction_error("Erro interno ao processar informações")

def show_extraction_error(error_msg):
    """Mostra erro de extração e reabilita interface"""
    try:
        messagebox.showerror("Erro", error_msg)
        extrair_button.config(state=tk.NORMAL, text="Extrair informações")
    except Exception as e:
        print(f"Erro crítico na interface: {e}")

def baixar_video():
    global info, download_directory, download_thread, is_downloading
    
    if is_downloading:
        messagebox.showwarning("Aviso", "Um download já está em andamento!")
        return
    
    if info is None:
        messagebox.showerror("Erro", "Extraia as informações do vídeo primeiro.")
        return
    
    selected_index = resolutions_listbox.curselection()
    if not selected_index:
        messagebox.showerror("Erro", "Por favor, selecione uma resolução.")
        return
    
    selected_resolution = resolutions_listbox.get(selected_index)
    format_id = None
    
    for format in info['formats']:
        if format['resolution'] == selected_resolution:
            format_id = format['format_id']
            break
    
    if not format_id:
        messagebox.showerror("Erro", "Não foi possível encontrar o formato selecionado.")
        return
    
    # CORRIGIDO: Preparar interface para download - mostrar barra IMEDIATAMENTE
    is_downloading = True
    baixar_button.config(state=tk.DISABLED, text="Baixando...")
    
    # IMPORTANTE: Mostrar a barra de progresso ANTES de iniciar o download
    progress_frame.grid(row=4, column=0, columnspan=2, sticky='ew', padx=10, pady=5)
    progress_bar.config(maximum=100)  # Configurar máximo explicitamente
    progress_bar['value'] = 0
    progress_label.config(text="Preparando download...")
    root.update_idletasks()  # Forçar atualização da interface
    
def verificar_auto_open_folder():
    """Verifica se deve abrir pasta automaticamente após download"""
    try:
        auto_open = db_manager.get_setting('auto_open_folder', 'false')
        if auto_open.lower() == 'true' and download_directory and os.path.exists(download_directory):
            os.startfile(download_directory)
            log_info("Pasta aberta automaticamente após download")
    except Exception as e:
        log_error(e, "Erro ao abrir pasta automaticamente")

def download_success():
    """Função chamada quando o download é concluído com sucesso"""
    global info, db_manager
    
    try:
        # Atualizar UI para 100%
        progress_bar['value'] = 100
        progress_label.config(text="Download concluído!")
        root.update()
        
        # Salvar no histórico do banco de dados
        if info:
            download_data = {
                'url': url_entry.get(),
                'title': info.get('title', 'Título não disponível'),
                'duration': info.get('duration_string', 'N/A'),
                'resolution': resolucao_var.get(),
                'file_size': info.get('filesize_approx', 0),
                'download_path': download_directory,
                'status': 'completed',
                'thumbnail_url': info.get('thumbnail'),
                'uploader': info.get('uploader', 'N/A'),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'description': info.get('description', '')
            }
            
            try:
                download_id = db_manager.add_download(download_data)
                log_info(f"Download salvo no histórico com ID: {download_id}")
            except Exception as e:
                log_error(e, "Erro ao salvar download no histórico")
        
        # Verificar se deve abrir pasta automaticamente
        verificar_auto_open_folder()
        
        # Finalizar UI após 2 segundos
        root.after(2000, finalize_ui)
        
    except Exception as e:
        log_error(e, "Erro em download_success")
        def finalize_ui():
            global is_downloading
            is_downloading = False
            baixar_button.config(state=tk.NORMAL, text="Baixar vídeo")
            progress_frame.grid_remove()  # Ocultar barra de progresso
            messagebox.showinfo("Sucesso", "Download concluído com sucesso!")
            log_info("Download concluído com sucesso")
            habilitar_botao_download()
        
        # Aguardar 1 segundo antes de finalizar a UI
        root.after(1000, finalize_ui)

    def download_worker():
        global is_downloading
        try:
            url = url_entry.get().strip()
            log_info(f"Iniciando download: {info.get('title', 'video')} - {selected_resolution}")
            
            # Determinar caminho do ffmpeg
            if getattr(sys, 'frozen', False):
                ffmpeg_path = os.path.join(sys._MEIPASS, "ffmpeg.exe")
            else:
                ffmpeg_path = "ffmpeg.exe"
            
            # Opções melhoradas para lidar com erros de conexão
            ydl_opts = {
                'format': f"{format_id}+bestaudio",
                'outtmpl': f"{download_directory}/%(title)s.%(ext)s",
                'restrictfilenames': True,
                'merge_output_format': 'mp4',
                'ffmpeg_location': ffmpeg_path,
                'progress_hooks': [progress_hook],
                'postprocessor_hooks': [postprocessor_hook],
                'quiet': False,
                'retries': 10,
                'fragment_retries': 10,
                'skip_unavailable_fragments': True,
                'keep_fragments': False,
                'abort_on_unavailable_fragment': False,
                'socket_timeout': 30,
                'http_chunk_size': 10485760,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # CORRIGIDO: Chamar download_success após o download ser concluído
            download_success()
            
        except Exception as e:
            error_msg = log_error(e, "Erro durante download")
            root.after(0, lambda: download_error(error_msg))
        finally:
            is_downloading = False
    
    # Executar download em thread separada
    download_thread = threading.Thread(target=download_worker, daemon=True)
    download_thread.start()

def download_error(error_msg):
    """Callback para erro no download"""
    global is_downloading
    is_downloading = False
    baixar_button.config(state=tk.NORMAL, text="Baixar vídeo")
    progress_frame.grid_remove()  # Ocultar barra de progresso
    messagebox.showerror("Erro", f"Erro no download: {error_msg}")
    habilitar_botao_download()

def reset_download_ui():
    """Reseta interface após download"""
    global is_downloading
    is_downloading = False
    baixar_button.config(state=tk.NORMAL, text="Baixar vídeo")
    progress_frame.pack_forget()
    habilitar_botao_download()  # Revalidar estado do botão

def mostrar_menu(event):
    menu.post(event.x_root, event.y_root)

def colar_texto():
    """Cola texto da área de transferência no campo URL"""
    try:
        # Limpa o campo atual
        url_entry.delete(0, tk.END)
        # Cola o texto da área de transferência
        texto_colado = root.clipboard_get()
        url_entry.insert(0, texto_colado)
        print(f"[INFO] Texto colado: {texto_colado[:50]}{'...' if len(texto_colado) > 50 else ''}")
    except tk.TclError:
        print("[AVISO] Área de transferência vazia ou inacessível")
    except Exception as e:
        print(f"[ERRO] Erro ao colar texto: {e}")

def habilitar_botao_download():
    """Verifica se o botão de download pode ser habilitado"""
    try:
        # Verifica se há informações extraídas e uma resolução selecionada
        if info and resolutions_listbox.curselection():
            baixar_button.config(state=tk.NORMAL)
            print("[INFO] Botão de download habilitado")
        else:
            baixar_button.config(state=tk.DISABLED)
            print("[INFO] Botão de download desabilitado - faltam informações")
    except Exception as e:
        print(f"[ERRO] Erro ao habilitar botão: {e}")
        baixar_button.config(state=tk.DISABLED)

def resolucao_selecionada(event):
    """Callback quando uma resolução é selecionada na listbox"""
    try:
        selection = resolutions_listbox.curselection()
        if selection:
            index = selection[0]
            resolucao = resolutions_listbox.get(index)
            print(f"[INFO] Resolução selecionada: {resolucao}")
            
            # Habilita o botão de download se uma resolução foi selecionada
            habilitar_botao_download()
            
    except Exception as e:
        print(f"[ERRO] Erro ao selecionar resolução: {e}")

def selecionar_diretorio():
    """Abre diálogo para selecionar diretório de download"""
    global download_directory, db_manager
    
    try:
        diretorio = filedialog.askdirectory(title="Selecionar diretório para download")
        if diretorio:
            download_directory = diretorio
            # Quebrar texto longo para melhor visualização
            texto_diretorio = f"Diretório: {diretorio}"
            diretorio_label.config(text=texto_diretorio)
            
            # Salvar configuração no banco de dados
            try:
                db_manager.set_setting('default_download_path', diretorio)
                log_info(f"Diretório padrão salvo: {diretorio}")
            except Exception as e:
                log_error(e, "Erro ao salvar configuração de diretório")
            
            log_info(f"Diretório selecionado: {diretorio}")
            
            # Habilitar botão de download se URL estiver preenchida
            if url_entry.get().strip():
                baixar_button.config(state=tk.NORMAL)
                print("[INFO] Botão de download habilitado")
            else:
                baixar_button.config(state=tk.DISABLED)
                print("[INFO] Botão de download desabilitado - faltam informações")
                
    except Exception as e:
        print(f"[ERRO] Erro ao selecionar diretório: {e}")

def criar_aba_configuracoes():
    """Cria aba de configurações"""
    config_frame = ttk.Frame(notebook)
    notebook.add(config_frame, text="⚙️ Configurações")
    
    # Frame principal
    main_frame = tk.Frame(config_frame)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Seção: Downloads
    downloads_frame = tk.LabelFrame(main_frame, text="Downloads", font=('Arial', 10, 'bold'))
    downloads_frame.pack(fill=tk.X, pady=(0, 10))
    
    # Auto-abrir pasta
    global auto_open_var
    auto_open_var = tk.BooleanVar()
    auto_open_check = tk.Checkbutton(
        downloads_frame, 
        text="Abrir pasta automaticamente após download",
        variable=auto_open_var,
        command=salvar_auto_open_config
    )
    auto_open_check.pack(anchor='w', padx=10, pady=5)
    
    # Carregar configuração atual
    current_auto_open = db_manager.get_setting('auto_open_folder', 'false')
    auto_open_var.set(current_auto_open.lower() == 'true')
    
    # Seção: Interface
    interface_frame = tk.LabelFrame(main_frame, text="Interface", font=('Arial', 10, 'bold'))
    interface_frame.pack(fill=tk.X, pady=(0, 10))
    
    # Tema
    tk.Label(interface_frame, text="Tema:").pack(anchor='w', padx=10, pady=(5, 0))
    
    global theme_var
    theme_var = tk.StringVar()
    theme_frame = tk.Frame(interface_frame)
    theme_frame.pack(anchor='w', padx=10, pady=5)
    
    tk.Radiobutton(theme_frame, text="Claro", variable=theme_var, 
                   value="light", command=salvar_theme_config).pack(side=tk.LEFT)
    tk.Radiobutton(theme_frame, text="Escuro", variable=theme_var, 
                   value="dark", command=salvar_theme_config).pack(side=tk.LEFT, padx=(10, 0))
    
    # Carregar tema atual
    current_theme = db_manager.get_setting('theme', 'light')
    theme_var.set(current_theme)
    
    # Seção: Resolução Padrão
    resolution_frame = tk.LabelFrame(main_frame, text="Qualidade", font=('Arial', 10, 'bold'))
    resolution_frame.pack(fill=tk.X, pady=(0, 10))
    
    tk.Label(resolution_frame, text="Resolução padrão:").pack(anchor='w', padx=10, pady=(5, 0))
    
    resolution_config_frame = tk.Frame(resolution_frame)
    resolution_config_frame.pack(anchor='w', padx=10, pady=5)
    
    global resolution_config_var
    resolution_config_var = tk.StringVar()
    resolution_combo = ttk.Combobox(
        resolution_config_frame,
        textvariable=resolution_config_var,
        values=['144p', '240p', '360p', '480p', '720p', '1080p', 'best'],
        state='readonly',
        width=10
    )
    resolution_combo.pack(side=tk.LEFT)
    resolution_combo.bind('<<ComboboxSelected>>', lambda e: salvar_resolution_config())
    
    # Carregar resolução atual
    current_resolution = db_manager.get_setting('default_resolution', '1080p')
    resolution_config_var.set(current_resolution)
    
    # Botão para aplicar mudanças
    apply_frame = tk.Frame(main_frame)
    apply_frame.pack(fill=tk.X, pady=(10, 0))
    
    tk.Button(apply_frame, text="💾 Salvar Configurações", 
              command=aplicar_configuracoes, bg='#4CAF50', fg='white',
              font=('Arial', 10, 'bold')).pack(side=tk.RIGHT)

def salvar_auto_open_config():
    """Salva configuração de auto-abrir pasta"""
    try:
        value = 'true' if auto_open_var.get() else 'false'
        db_manager.set_setting('auto_open_folder', value)
        log_info(f"Auto-abrir pasta: {value}")
    except Exception as e:
        log_error(e, "Erro ao salvar configuração auto-abrir")

def salvar_theme_config():
    """Salva configuração de tema"""
    try:
        theme = theme_var.get()
        db_manager.set_setting('theme', theme)
        aplicar_tema(theme)
        log_info(f"Tema alterado para: {theme}")
    except Exception as e:
        log_error(e, "Erro ao salvar tema")

def salvar_resolution_config():
    """Salva configuração de resolução padrão"""
    try:
        resolution = resolution_config_var.get()
        db_manager.set_setting('default_resolution', resolution)
        resolucao_var.set(resolution)  # Atualiza a seleção principal
        log_info(f"Resolução padrão alterada para: {resolution}")
    except Exception as e:
        log_error(e, "Erro ao salvar resolução padrão")

def aplicar_tema(theme):
    """Aplica o tema selecionado"""
    try:
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
        
        # Aplicar cores aos widgets principais
        root.configure(bg=bg_color)
        
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
        
        # Aplicar tema aos frames das abas
        for widget in [main_frame, config_frame, history_frame]:
            if widget.winfo_exists():
                widget.configure(bg=bg_color)
                # Atualizar widgets filhos recursivamente
                atualizar_widgets_tema(widget, bg_color, fg_color)
        
        log_info(f"Tema {theme} aplicado")
        
    except Exception as e:
        log_error(e, "Erro ao aplicar tema")

def atualizar_widgets_tema(parent, bg_color, fg_color):
    """Atualiza recursivamente todos os widgets filhos com o tema"""
    try:
        for child in parent.winfo_children():
            widget_class = child.winfo_class()
            
            if widget_class in ['Frame', 'Toplevel']:
                child.configure(bg=bg_color)
                atualizar_widgets_tema(child, bg_color, fg_color)
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
    except Exception as e:
        log_error(e, "Erro ao atualizar widgets do tema")

def aplicar_configuracoes():
    """Aplica todas as configurações"""
    try:
        messagebox.showinfo("Sucesso", "Configurações salvas com sucesso!")
        log_info("Configurações aplicadas")
    except Exception as e:
        log_error(e, "Erro ao aplicar configurações")

def criar_aba_historico():
    """Cria aba do histórico de downloads"""
    global history_frame, history_tree
    
    # Frame principal do histórico
    history_frame = tk.Frame(notebook)
    notebook.add(history_frame, text="📋 Histórico")
    
    # Título e controles
    title_frame = tk.Frame(history_frame)
    title_frame.pack(fill=tk.X, padx=10, pady=5)
    
    tk.Label(title_frame, text="Histórico de Downloads", 
             font=("Arial", 14, "bold")).pack(side=tk.LEFT)
    
    # Botões de controle
    controls_frame = tk.Frame(title_frame)
    controls_frame.pack(side=tk.RIGHT)
    
    tk.Button(controls_frame, text="🔄 Atualizar", 
              command=atualizar_historico).pack(side=tk.LEFT, padx=2)
    tk.Button(controls_frame, text="🗑️ Limpar Tudo", 
              command=limpar_historico).pack(side=tk.LEFT, padx=2)
    tk.Button(controls_frame, text="📁 Abrir Pasta", 
              command=lambda: os.startfile(download_directory) if download_directory and os.path.exists(download_directory) else messagebox.showwarning("Aviso", "Diretório não selecionado ou não existe")).pack(side=tk.LEFT, padx=2)
    
    # Treeview para mostrar histórico
    tree_frame = tk.Frame(history_frame)
    tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    # Configurar colunas
    columns = ('Data', 'Título', 'Resolução', 'Status', 'Tamanho')
    history_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
    
    # Configurar cabeçalhos
    history_tree.heading('Data', text='Data/Hora')
    history_tree.heading('Título', text='Título do Vídeo')
    history_tree.heading('Resolução', text='Resolução')
    history_tree.heading('Status', text='Status')
    history_tree.heading('Tamanho', text='Tamanho')
    
    # Configurar larguras das colunas
    history_tree.column('Data', width=150)
    history_tree.column('Título', width=400)
    history_tree.column('Resolução', width=100)
    history_tree.column('Status', width=100)
    history_tree.column('Tamanho', width=100)
    
    # Scrollbars
    v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=history_tree.yview)
    h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=history_tree.xview)
    history_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
    
    # Pack treeview e scrollbars
    history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
    
    # Menu de contexto (clique direito)
    history_menu = tk.Menu(root, tearoff=0)
    history_menu.add_command(label="🔄 Redownload", command=redownload_video)
    history_menu.add_command(label="📁 Abrir Arquivo", command=abrir_arquivo_historico)
    history_menu.add_command(label="📂 Mostrar na Pasta", command=abrir_pasta_arquivo_historico)
    history_menu.add_command(label="📋 Copiar URL", command=copiar_url_historico)
    history_menu.add_separator()
    history_menu.add_command(label="🗑️ Remover", command=remover_item_historico)
    
    def mostrar_menu_historico(event):
        try:
            history_menu.post(event.x_root, event.y_root)
        except:
            pass
    
    history_tree.bind("<Button-3>", mostrar_menu_historico)
    
    # Carregar dados iniciais
    atualizar_historico()

def atualizar_historico():
    """Atualiza a exibição do histórico"""
    try:
        # Limpar treeview
        for item in history_tree.get_children():
            history_tree.delete(item)
        
        # Carregar dados recentes
        recent_downloads = db_manager.get_recent_downloads()
        
        for download in recent_downloads:
            # Formatar data
            try:
                dt = datetime.fromisoformat(download['timestamp'])
                data_formatada = dt.strftime('%d/%m/%Y %H:%M')
            except:
                data_formatada = download.get('timestamp', 'N/A')
            
            # Formatar tamanho
            tamanho = download.get('file_size', 'N/A')
            if isinstance(tamanho, (int, float)):
                if tamanho > 1024*1024*1024:  # GB
                    tamanho = f"{tamanho/(1024*1024*1024):.1f} GB"
                elif tamanho > 1024*1024:  # MB
                    tamanho = f"{tamanho/(1024*1024):.1f} MB"
                else:
                    tamanho = f"{tamanho/1024:.1f} KB"
            
            # Truncar título se muito longo
            titulo = download.get('title', 'N/A')
            if len(titulo) > 60:
                titulo = titulo[:57] + "..."
            
            # Inserir no treeview
            history_tree.insert('', 'end', values=(
                data_formatada,
                titulo,
                download.get('resolution', 'N/A'),
                download.get('status', 'N/A'),
                tamanho
            ), tags=(download.get('id'),))
        
        log_info(f"Histórico atualizado: {len(recent_downloads)} entradas")
        
    except Exception as e:
        log_error(e, "Erro ao atualizar histórico")

def limpar_historico():
    """Limpa todo o histórico com confirmação"""
    resposta = messagebox.askyesno(
        "Confirmar Limpeza", 
        "Deseja realmente limpar todo o histórico de downloads?\n\n"
        "⚠️ Esta ação não pode ser desfeita."
    )
    if resposta:
        db_manager.clear_history()
        atualizar_historico()
        messagebox.showinfo("Sucesso", "Histórico limpo com sucesso!")

# Funções do menu de contexto do histórico
def abrir_arquivo_historico():
    """Abre o arquivo selecionado no histórico"""
    selection = history_tree.selection()
    if not selection:
        messagebox.showwarning("Aviso", "Selecione um item do histórico")
        return
    
    try:
        # Obter dados do item selecionado
        item_id = history_tree.item(selection[0])['tags'][0]
        download_data = db_manager.get_download_by_id(item_id)
        
        # CORRIGIDO: usar 'download_path' em vez de 'file_path'
        if download_data and download_data.get('download_path'):
            file_path = download_data['download_path']
            if os.path.exists(file_path):
                os.startfile(file_path)  # Windows
                log_info(f"Arquivo aberto: {file_path}")
            else:
                messagebox.showerror("Erro", "Arquivo não encontrado no disco")
        else:
            messagebox.showerror("Erro", "Caminho do arquivo não disponível")
    except Exception as e:
        log_error(e, "Erro ao abrir arquivo")
        messagebox.showerror("Erro", "Erro ao abrir arquivo")

def abrir_pasta_arquivo_historico():
    """Abre a pasta contendo o arquivo selecionado"""
    selection = history_tree.selection()
    if not selection:
        messagebox.showwarning("Aviso", "Selecione um item do histórico")
        return
    
    try:
        item_id = history_tree.item(selection[0])['tags'][0]
        download_data = db_manager.get_download_by_id(item_id)
        
        if download_data and download_data.get('download_path'):
            file_path = download_data['download_path']
            if os.path.exists(file_path):
                # Abre a pasta e seleciona o arquivo
                os.system(f'explorer /select,"{file_path}"')
                log_info(f"Pasta aberta com arquivo selecionado: {file_path}")
            else:
                messagebox.showerror("Erro", "Arquivo não encontrado no disco")
        else:
            messagebox.showerror("Erro", "Caminho do arquivo não disponível")
    except Exception as e:
        log_error(e, "Erro ao abrir pasta do arquivo")

def copiar_url_historico():
    """Copia a URL do vídeo selecionado"""
    selection = history_tree.selection()
    if not selection:
        messagebox.showwarning("Aviso", "Selecione um item do histórico")
        return
    
    try:
        item_id = history_tree.item(selection[0])['tags'][0]
        download_data = db_manager.get_download_by_id(item_id)
        
        if download_data and download_data.get('url'):
            root.clipboard_clear()
            root.clipboard_append(download_data['url'])
            messagebox.showinfo("Sucesso", "URL copiada para a área de transferência")
            log_info("URL copiada do histórico")
        else:
            messagebox.showerror("Erro", "URL não disponível")
    except Exception as e:
        log_error(e, "Erro ao copiar URL")
        messagebox.showerror("Erro", "Erro ao copiar URL")

def remover_item_historico():
    """Remove item específico do histórico"""
    selection = history_tree.selection()
    if not selection:
        messagebox.showwarning("Aviso", "Selecione um item do histórico")
        return
    
    try:
        # Obter título para confirmação
        item_values = history_tree.item(selection[0])['values']
        titulo = item_values[1] if len(item_values) > 1 else "Item selecionado"
        
        resposta = messagebox.askyesno(
            "Confirmar Remoção", 
            f"Deseja remover este item do histórico?\n\n{titulo}\n\n⚠️ Esta ação não pode ser desfeita."
        )
        if resposta:
            item_id = history_tree.item(selection[0])['tags'][0]
            db_manager.remove_download(item_id)
            atualizar_historico()
            messagebox.showinfo("Sucesso", "Item removido do histórico")
            log_info(f"Item removido do histórico: {titulo}")
    except Exception as e:
        log_error(e, "Erro ao remover item")
        messagebox.showerror("Erro", "Erro ao remover item do histórico")

def redownload_video():
    """Recarrega a URL na aba principal para novo download"""
    selection = history_tree.selection()
    if not selection:
        messagebox.showwarning("Aviso", "Selecione um item do histórico")
        return
    
    try:
        item_id = history_tree.item(selection[0])['tags'][0]
        download_data = db_manager.get_download_by_id(item_id)
        
        if download_data and download_data.get('url'):
            # Mudar para aba principal
            notebook.select(0)
            # Limpar e inserir URL
            url_entry.delete(0, tk.END)
            url_entry.insert(0, download_data['url'])
            # Limpar informações anteriores
            resolutions_listbox.delete(0, tk.END)
            metadata_text.delete("1.0", tk.END)
            baixar_button.config(state=tk.DISABLED)
            
            messagebox.showinfo("Sucesso", "URL carregada na aba principal\n\nClique em 'Extrair informações' para continuar")
            log_info(f"URL recarregada: {download_data['url']}")
        else:
            messagebox.showerror("Erro", "URL não disponível")
    except Exception as e:
        log_error(e, "Erro ao recarregar vídeo")
        messagebox.showerror("Erro", "Erro ao recarregar vídeo")

def sair_aplicacao():
    """Função para sair da aplicação com confirmação"""
    global is_downloading
    
    # Verificar se há download em andamento
    if is_downloading:
        resposta = messagebox.askyesno(
            "Download em Andamento", 
            "Há um download em andamento. Deseja realmente sair?\n\n"
            "⚠️ Atenção: O download será interrompido e os arquivos podem ficar incompletos."
        )
        if not resposta:
            return
    
    # Confirmar saída
    resposta = messagebox.askyesno("Confirmar Saída", "Deseja realmente sair da aplicação?")
    if resposta:
        log_info("Aplicação encerrada pelo usuário")
        root.quit()
        root.destroy()

# Criar janela principal PRIMEIRO
root = tk.Tk()
root.title("Baixador de Vídeos do YouTube v2.1 - Histórico")
root.geometry("1000x750")  # Aumentar tamanho para acomodar histórico
root.minsize(900, 650)

# Criar variáveis tkinter
resolucao_var = tk.StringVar(value="1080p")  # Valor padrão alterado para melhor qualidade

# Criar notebook (abas)
notebook = ttk.Notebook(root)
notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Aba principal (download)
main_frame = tk.Frame(notebook)
notebook.add(main_frame, text="📥 Download")

# Configuração do grid com padding e pesos
for i in range(8):  # 8 linhas no layout
    if i == 2:  # Linha dos frames principais (resoluções e metadados)
        main_frame.rowconfigure(i, weight=1, pad=10)  # Expandir esta linha
    else:
        main_frame.rowconfigure(i, pad=10)
        
for i in range(2):
    main_frame.columnconfigure(i, weight=1, pad=10)  # Ambas colunas expandem

# URL Input
url_label = tk.Label(main_frame, text="URL do vídeo:")
url_label.grid(row=0, column=0, sticky='w')
url_entry = tk.Entry(main_frame, width=50)
url_entry.grid(row=0, column=1, sticky='ew')

# Create right-click menu
menu = tk.Menu(root, tearoff=0)
menu.add_command(label="Colar", command=colar_texto)
url_entry.bind("<Button-3>", mostrar_menu)

# Extract button
extrair_button = tk.Button(main_frame, text="Extrair informações", command=extrair_informacoes)
extrair_button.grid(row=1, column=0, columnspan=2, pady=5)

# Resolutions Frame
resolutions_frame = tk.Frame(main_frame)
resolutions_frame.grid(row=2, column=0, sticky='nsew', padx=(0,5))  # Adicionar padding
resolutions_label = tk.Label(resolutions_frame, text="Resoluções:")
resolutions_label.pack()
resolutions_listbox = tk.Listbox(resolutions_frame, height=10)  # Altura fixa
resolutions_listbox.pack(fill=tk.BOTH, expand=True)
resolutions_listbox.bind("<<ListboxSelect>>", resolucao_selecionada)

# Metadata Frame
metadata_frame = tk.Frame(main_frame)
metadata_frame.grid(row=2, column=1, sticky='nsew', padx=(5,0))  # Adicionar padding
metadata_label = tk.Label(metadata_frame, text="Informações do Vídeo:")  # Adicionar label
metadata_label.pack()
metadata_text = tk.Text(metadata_frame, wrap=tk.WORD, width=40, height=10)  # Altura fixa
metadata_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar = tk.Scrollbar(metadata_frame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
metadata_text.config(yscrollcommand=scrollbar.set)
scrollbar.config(command=metadata_text.yview)

# Download Button
baixar_button = tk.Button(main_frame, text="Baixar vídeo", command=baixar_video, state=tk.DISABLED)
baixar_button.grid(row=3, column=0, columnspan=2, pady=5)

# Progress Frame (inicialmente oculto)
# CORRIGIDO: Criação da barra de progresso com configuração adequada
progress_frame = tk.Frame(main_frame)
# IMPORTANTE: Definir maximum=100 na criação
progress_bar = ttk.Progressbar(progress_frame, length=400, mode='determinate', maximum=100)
progress_bar.pack(fill=tk.X, pady=2)
progress_label = tk.Label(progress_frame, text="")
progress_label.pack()

# Directory Selection
diretorio_button = tk.Button(main_frame, text="Selecionar Diretório", command=selecionar_diretorio)
diretorio_button.grid(row=5, column=0, columnspan=2, pady=5)

# CORRIGIR: Label do diretório com melhor configuração
diretorio_label = tk.Label(main_frame, text="Diretório: Nenhum selecionado", 
                          wraplength=800, justify='left')  # Quebra de linha automática
diretorio_label.grid(row=6, column=0, columnspan=2, sticky='ew', padx=10)

# NOVO: Botão Sair
sair_button = tk.Button(main_frame, text="Sair", command=sair_aplicacao, 
                       bg="#ff6b6b", fg="white", font=("Arial", 10, "bold"))
sair_button.grid(row=7, column=0, columnspan=2, pady=10)

# Configurar protocolo de fechamento da janela
root.protocol("WM_DELETE_WINDOW", sair_aplicacao)

# Log inicial
log_info("Aplicação iniciada")

# Inicializar banco de dados
db_manager = DatabaseManager()

def initialize_app():
    """Inicializa a aplicação e o banco de dados"""
    try:
        # Inicializa o banco de dados automaticamente
        db_manager.initialize()
        log_info("Sistema de banco de dados inicializado com sucesso")
        
        # Carrega configurações salvas
        global download_directory
        saved_dir = db_manager.get_setting('default_download_path', '')
        if saved_dir and os.path.exists(saved_dir):
            download_directory = saved_dir
            diretorio_label.config(text=f"Diretório: {download_directory}")
            log_info(f"Diretório padrão carregado: {download_directory}")
        
        # Carregar resolução padrão
        default_resolution = db_manager.get_setting('default_resolution', '1080p')
        if default_resolution in ['144p', '240p', '360p', '480p', '720p', '1080p', 'best']:
            resolucao_var.set(default_resolution)
            log_info(f"Resolução padrão carregada: {default_resolution}")
            
    except Exception as e:
        log_error(e, "Erro ao inicializar banco de dados")
        messagebox.showerror("Erro", "Erro ao inicializar sistema de dados")

# Chamar antes de root.mainloop()
initialize_app()

def salvar_resolucao_padrao():
    """Salva a resolução selecionada como padrão"""
    try:
        resolucao_atual = resolucao_var.get()
        db_manager.set_setting('default_resolution', resolucao_atual)
        log_info(f"Resolução padrão salva: {resolucao_atual}")
    except Exception as e:
        log_error(e, "Erro ao salvar resolução padrão")

# Adicionar callback para salvar resolução quando alterada
def on_resolution_change(*args):
    """Callback chamado quando resolução é alterada"""
    salvar_resolucao_padrao()

# Vincular callback à variável de resolução
resolucao_var.trace('w', on_resolution_change)

def mostrar_menu(event):
    menu.post(event.x_root, event.y_root)

def colar_texto():
    """Cola texto da área de transferência no campo URL"""
    try:
        # Limpa o campo atual
        url_entry.delete(0, tk.END)
        # Cola o texto da área de transferência
        texto_colado = root.clipboard_get()
        url_entry.insert(0, texto_colado)
        print(f"[INFO] Texto colado: {texto_colado[:50]}{'...' if len(texto_colado) > 50 else ''}")
    except tk.TclError:
        print("[AVISO] Área de transferência vazia ou inacessível")
    except Exception as e:
        print(f"[ERRO] Erro ao colar texto: {e}")

def habilitar_botao_download():
    """Verifica se o botão de download pode ser habilitado"""
    try:
        # Verifica se há informações extraídas e uma resolução selecionada
        if info and resolutions_listbox.curselection():
            baixar_button.config(state=tk.NORMAL)
            print("[INFO] Botão de download habilitado")
        else:
            baixar_button.config(state=tk.DISABLED)
            print("[INFO] Botão de download desabilitado - faltam informações")
    except Exception as e:
        print(f"[ERRO] Erro ao habilitar botão: {e}")
        baixar_button.config(state=tk.DISABLED)

def resolucao_selecionada(event):
    """Callback quando uma resolução é selecionada na listbox"""
    try:
        selection = resolutions_listbox.curselection()
        if selection:
            index = selection[0]
            resolucao = resolutions_listbox.get(index)
            print(f"[INFO] Resolução selecionada: {resolucao}")
            
            # Habilita o botão de download se uma resolução foi selecionada
            habilitar_botao_download()
            
    except Exception as e:
        print(f"[ERRO] Erro ao selecionar resolução: {e}")

def selecionar_diretorio():
    """Abre diálogo para selecionar diretório de download"""
    global download_directory, db_manager
    
    try:
        diretorio = filedialog.askdirectory(title="Selecionar diretório para download")
        if diretorio:
            download_directory = diretorio
            # Quebrar texto longo para melhor visualização
            texto_diretorio = f"Diretório: {diretorio}"
            diretorio_label.config(text=texto_diretorio)
            
            # Salvar configuração no banco de dados
            try:
                db_manager.set_setting('default_download_path', diretorio)
                log_info(f"Diretório padrão salvo: {diretorio}")
            except Exception as e:
                log_error(e, "Erro ao salvar configuração de diretório")
            
            log_info(f"Diretório selecionado: {diretorio}")
            
            # Habilitar botão de download se URL estiver preenchida
            if url_entry.get().strip():
                baixar_button.config(state=tk.NORMAL)
                print("[INFO] Botão de download habilitado")
            else:
                baixar_button.config(state=tk.DISABLED)
                print("[INFO] Botão de download desabilitado - faltam informações")
                
    except Exception as e:
        print(f"[ERRO] Erro ao selecionar diretório: {e}")

def criar_aba_configuracoes():
    """Cria aba de configurações"""
    config_frame = ttk.Frame(notebook)
    notebook.add(config_frame, text="⚙️ Configurações")
    
    # Frame principal
    main_frame = tk.Frame(config_frame)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Seção: Downloads
    downloads_frame = tk.LabelFrame(main_frame, text="Downloads", font=('Arial', 10, 'bold'))
    downloads_frame.pack(fill=tk.X, pady=(0, 10))
    
    # Auto-abrir pasta
    global auto_open_var
    auto_open_var = tk.BooleanVar()
    auto_open_check = tk.Checkbutton(
        downloads_frame, 
        text="Abrir pasta automaticamente após download",
        variable=auto_open_var,
        command=salvar_auto_open_config
    )
    auto_open_check.pack(anchor='w', padx=10, pady=5)
    
    # Carregar configuração atual
    current_auto_open = db_manager.get_setting('auto_open_folder', 'false')
    auto_open_var.set(current_auto_open.lower() == 'true')
    
    # Seção: Interface
    interface_frame = tk.LabelFrame(main_frame, text="Interface", font=('Arial', 10, 'bold'))
    interface_frame.pack(fill=tk.X, pady=(0, 10))
    
    # Tema
    tk.Label(interface_frame, text="Tema:").pack(anchor='w', padx=10, pady=(5, 0))
    
    global theme_var
    theme_var = tk.StringVar()
    theme_frame = tk.Frame(interface_frame)
    theme_frame.pack(anchor='w', padx=10, pady=5)
    
    tk.Radiobutton(theme_frame, text="Claro", variable=theme_var, 
                   value="light", command=salvar_theme_config).pack(side=tk.LEFT)
    tk.Radiobutton(theme_frame, text="Escuro", variable=theme_var, 
                   value="dark", command=salvar_theme_config).pack(side=tk.LEFT, padx=(10, 0))
    
    # Carregar tema atual
    current_theme = db_manager.get_setting('theme', 'light')
    theme_var.set(current_theme)
    
    # Seção: Resolução Padrão
    resolution_frame = tk.LabelFrame(main_frame, text="Qualidade", font=('Arial', 10, 'bold'))
    resolution_frame.pack(fill=tk.X, pady=(0, 10))
    
    tk.Label(resolution_frame, text="Resolução padrão:").pack(anchor='w', padx=10, pady=(5, 0))
    
    resolution_config_frame = tk.Frame(resolution_frame)
    resolution_config_frame.pack(anchor='w', padx=10, pady=5)
    
    global resolution_config_var
    resolution_config_var = tk.StringVar()
    resolution_combo = ttk.Combobox(
        resolution_config_frame,
        textvariable=resolution_config_var,
        values=['144p', '240p', '360p', '480p', '720p', '1080p', 'best'],
        state='readonly',
        width=10
    )
    resolution_combo.pack(side=tk.LEFT)
    resolution_combo.bind('<<ComboboxSelected>>', lambda e: salvar_resolution_config())
    
    # Carregar resolução atual
    current_resolution = db_manager.get_setting('default_resolution', '1080p')
    resolution_config_var.set(current_resolution)
    
    # Botão para aplicar mudanças
    apply_frame = tk.Frame(main_frame)
    apply_frame.pack(fill=tk.X, pady=(10, 0))
    
    tk.Button(apply_frame, text="💾 Salvar Configurações", 
              command=aplicar_configuracoes, bg='#4CAF50', fg='white',
              font=('Arial', 10, 'bold')).pack(side=tk.RIGHT)

def salvar_auto_open_config():
    """Salva configuração de auto-abrir pasta"""
    try:
        value = 'true' if auto_open_var.get() else 'false'
        db_manager.set_setting('auto_open_folder', value)
        log_info(f"Auto-abrir pasta: {value}")
    except Exception as e:
        log_error(e, "Erro ao salvar configuração auto-abrir")

def salvar_theme_config():
    """Salva configuração de tema"""
    try:
        theme = theme_var.get()
        db_manager.set_setting('theme', theme)
        aplicar_tema(theme)
        log_info(f"Tema alterado para: {theme}")
    except Exception as e:
        log_error(e, "Erro ao salvar tema")

def salvar_resolution_config():
    """Salva configuração de resolução padrão"""
    try:
        resolution = resolution_config_var.get()
        db_manager.set_setting('default_resolution', resolution)
        resolucao_var.set(resolution)  # Atualiza a seleção principal
        log_info(f"Resolução padrão alterada para: {resolution}")
    except Exception as e:
        log_error(e, "Erro ao salvar resolução padrão")

def aplicar_tema(theme):
    """Aplica o tema selecionado"""
    try:
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
        
        # Aplicar cores aos widgets principais
        root.configure(bg=bg_color)
        
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
        
        # Aplicar tema aos frames das abas
        for widget in [main_frame, config_frame, history_frame]:
            if widget.winfo_exists():
                widget.configure(bg=bg_color)
                # Atualizar widgets filhos recursivamente
                atualizar_widgets_tema(widget, bg_color, fg_color)
        
        log_info(f"Tema {theme} aplicado")
        
    except Exception as e:
        log_error(e, "Erro ao aplicar tema")

def atualizar_widgets_tema(parent, bg_color, fg_color):
    """Atualiza recursivamente todos os widgets filhos com o tema"""
    try:
        for child in parent.winfo_children():
            widget_class = child.winfo_class()
            
            if widget_class in ['Frame', 'Toplevel']:
                child.configure(bg=bg_color)
                atualizar_widgets_tema(child, bg_color, fg_color)
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
    except Exception as e:
        log_error(e, "Erro ao atualizar widgets do tema")

def aplicar_configuracoes():
    """Aplica todas as configurações"""
    try:
        messagebox.showinfo("Sucesso", "Configurações salvas com sucesso!")
        log_info("Configurações aplicadas")
    except Exception as e:
        log_error(e, "Erro ao aplicar configurações")

def criar_aba_historico():
    """Cria aba do histórico de downloads"""
    global history_frame, history_tree
    
    # Frame principal do histórico
    history_frame = tk.Frame(notebook)
    notebook.add(history_frame, text="📋 Histórico")
    
    # Título e controles
    title_frame = tk.Frame(history_frame)
    title_frame.pack(fill=tk.X, padx=10, pady=5)
    
    tk.Label(title_frame, text="Histórico de Downloads", 
             font=("Arial", 14, "bold")).pack(side=tk.LEFT)
    
    # Botões de controle
    controls_frame = tk.Frame(title_frame)
    controls_frame.pack(side=tk.RIGHT)
    
    tk.Button(controls_frame, text="🔄 Atualizar", 
              command=atualizar_historico).pack(side=tk.LEFT, padx=2)
    tk.Button(controls_frame, text="🗑️ Limpar Tudo", 
              command=limpar_historico).pack(side=tk.LEFT, padx=2)
    tk.Button(controls_frame, text="📁 Abrir Pasta", 
              command=lambda: os.startfile(download_directory) if download_directory and os.path.exists(download_directory) else messagebox.showwarning("Aviso", "Diretório não selecionado ou não existe")).pack(side=tk.LEFT, padx=2)
    
    # Treeview para mostrar histórico
    tree_frame = tk.Frame(history_frame)
    tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    # Configurar colunas
    columns = ('Data', 'Título', 'Resolução', 'Status', 'Tamanho')
    history_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
    
    # Configurar cabeçalhos
    history_tree.heading('Data', text='Data/Hora')
    history_tree.heading('Título', text='Título do Vídeo')
    history_tree.heading('Resolução', text='Resolução')
    history_tree.heading('Status', text='Status')
    history_tree.heading('Tamanho', text='Tamanho')
    
    # Configurar larguras das colunas
    history_tree.column('Data', width=150)
    history_tree.column('Título', width=400)
    history_tree.column('Resolução', width=100)
    history_tree.column('Status', width=100)
    history_tree.column('Tamanho', width=100)
    
    # Scrollbars
    v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=history_tree.yview)
    h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=history_tree.xview)
    history_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
    
    # Pack treeview e scrollbars
    history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
    
    # Menu de contexto (clique direito)
    history_menu = tk.Menu(root, tearoff=0)
    history_menu.add_command(label="🔄 Redownload", command=redownload_video)
    history_menu.add_command(label="📁 Abrir Arquivo", command=abrir_arquivo_historico)
    history_menu.add_command(label="📂 Mostrar na Pasta", command=abrir_pasta_arquivo_historico)
    history_menu.add_command(label="📋 Copiar URL", command=copiar_url_historico)
    history_menu.add_separator()
    history_menu.add_command(label="🗑️ Remover", command=remover_item_historico)
    
    def mostrar_menu_historico(event):
        try:
            history_menu.post(event.x_root, event.y_root)
        except:
            pass
    
    history_tree.bind("<Button-3>", mostrar_menu_historico)
    
    # Carregar dados iniciais
    atualizar_historico()

def atualizar_historico():
    """Atualiza a exibição do histórico"""
    try:
        # Limpar treeview
        for item in history_tree.get_children():
            history_tree.delete(item)
        
        # Carregar dados recentes
        recent_downloads = db_manager.get_recent_downloads()
        
        for download in recent_downloads:
            # Formatar data
            try:
                dt = datetime.fromisoformat(download['timestamp'])
                data_formatada = dt.strftime('%d/%m/%Y %H:%M')
            except:
                data_formatada = download.get('timestamp', 'N/A')
            
            # Formatar tamanho
            tamanho = download.get('file_size', 'N/A')
            if isinstance(tamanho, (int, float)):
                if tamanho > 1024*1024*1024:  # GB
                    tamanho = f"{tamanho/(1024*1024*1024):.1f} GB"
                elif tamanho > 1024*1024:  # MB
                    tamanho = f"{tamanho/(1024*1024):.1f} MB"
                else:
                    tamanho = f"{tamanho/1024:.1f} KB"
            
            # Truncar título se muito longo
            titulo = download.get('title', 'N/A')
            if len(titulo) > 60:
                titulo = titulo[:57] + "..."
            
            # Inserir no treeview
            history_tree.insert('', 'end', values=(
                data_formatada,
                titulo,
                download.get('resolution', 'N/A'),
                download.get('status', 'N/A'),
                tamanho
            ), tags=(download.get('id'),))
        
        log_info(f"Histórico atualizado: {len(recent_downloads)} entradas")
        
    except Exception as e:
        log_error(e, "Erro ao atualizar histórico")

def limpar_historico():
    """Limpa todo o histórico com confirmação"""
    resposta = messagebox.askyesno(
        "Confirmar Limpeza", 
        "Deseja realmente limpar todo o histórico de downloads?\n\n"
        "⚠️ Esta ação não pode ser desfeita."
    )
    if resposta:
        db_manager.clear_history()
        atualizar_historico()
        messagebox.showinfo("Sucesso", "Histórico limpo com sucesso!")

# Funções do menu de contexto do histórico
def abrir_arquivo_historico():
    """Abre o arquivo selecionado no histórico"""
    selection = history_tree.selection()
    if not selection:
        messagebox.showwarning("Aviso", "Selecione um item do histórico")
        return
    
    try:
        # Obter dados do item selecionado
        item_id = history_tree.item(selection[0])['tags'][0]
        download_data = db_manager.get_download_by_id(item_id)
        
        # CORRIGIDO: usar 'download_path' em vez de 'file_path'
        if download_data and download_data.get('download_path'):
            file_path = download_data['download_path']
            if os.path.exists(file_path):
                os.startfile(file_path)  # Windows
                log_info(f"Arquivo aberto: {file_path}")
            else:
                messagebox.showerror("Erro", "Arquivo não encontrado no disco")
        else:
            messagebox.showerror("Erro", "Caminho do arquivo não disponível")
    except Exception as e:
        log_error(e, "Erro ao abrir arquivo")
        messagebox.showerror("Erro", "Erro ao abrir arquivo")

def abrir_pasta_arquivo_historico():
    """Abre a pasta contendo o arquivo selecionado"""
    selection = history_tree.selection()
    if not selection:
        messagebox.showwarning("Aviso", "Selecione um item do histórico")
        return
    
    try:
        item_id = history_tree.item(selection[0])['tags'][0]
        download_data = db_manager.get_download_by_id(item_id)
        
        if download_data and download_data.get('download_path'):
            file_path = download_data['download_path']
            if os.path.exists(file_path):
                # Abre a pasta e seleciona o arquivo
                os.system(f'explorer /select,"{file_path}"')
                log_info(f"Pasta aberta com arquivo selecionado: {file_path}")
            else:
                messagebox.showerror("Erro", "Arquivo não encontrado no disco")
        else:
            messagebox.showerror("Erro", "Caminho do arquivo não disponível")
    except Exception as e:
        log_error(e, "Erro ao abrir pasta do arquivo")

def copiar_url_historico():
    """Copia a URL do vídeo selecionado"""
    selection = history_tree.selection()
    if not selection:
        messagebox.showwarning("Aviso", "Selecione um item do histórico")
        return
    
    try:
        item_id = history_tree.item(selection[0])['tags'][0]
        download_data = db_manager.get_download_by_id(item_id)
        
        if download_data and download_data.get('url'):
            root.clipboard_clear()
            root.clipboard_append(download_data['url'])
            messagebox.showinfo("Sucesso", "URL copiada para a área de transferência")
            log_info("URL copiada do histórico")
        else:
            messagebox.showerror("Erro", "URL não disponível")
    except Exception as e:
        log_error(e, "Erro ao copiar URL")
        messagebox.showerror("Erro", "Erro ao copiar URL")

def remover_item_historico():
    """Remove item específico do histórico"""
    selection = history_tree.selection()
    if not selection:
        messagebox.showwarning("Aviso", "Selecione um item do histórico")
        return
    
    try:
        # Obter título para confirmação
        item_values = history_tree.item(selection[0])['values']
        titulo = item_values[1] if len(item_values) > 1 else "Item selecionado"
        
        resposta = messagebox.askyesno(
            "Confirmar Remoção", 
            f"Deseja remover este item do histórico?\n\n{titulo}\n\n⚠️ Esta ação não pode ser desfeita."
        )
        if resposta:
            item_id = history_tree.item(selection[0])['tags'][0]
            db_manager.remove_download(item_id)
            atualizar_historico()
            messagebox.showinfo("Sucesso", "Item removido do histórico")
            log_info(f"Item removido do histórico: {titulo}")
    except Exception as e:
        log_error(e, "Erro ao remover item")
        messagebox.showerror("Erro", "Erro ao remover item do histórico")

def redownload_video():
    """Recarrega a URL na aba principal para novo download"""
    selection = history_tree.selection()
    if not selection:
        messagebox.showwarning("Aviso", "Selecione um item do histórico")
        return
    
    try:
        item_id = history_tree.item(selection[0])['tags'][0]
        download_data = db_manager.get_download_by_id(item_id)
        
        if download_data and download_data.get('url'):
            # Mudar para aba principal
            notebook.select(0)
            # Limpar e inserir URL
            url_entry.delete(0, tk.END)
            url_entry.insert(0, download_data['url'])
            # Limpar informações anteriores
            resolutions_listbox.delete(0, tk.END)
            metadata_text.delete("1.0", tk.END)
            baixar_button.config(state=tk.DISABLED)
            
            messagebox.showinfo("Sucesso", "URL carregada na aba principal\n\nClique em 'Extrair informações' para continuar")
            log_info(f"URL recarregada: {download_data['url']}")
        else:
            messagebox.showerror("Erro", "URL não disponível")
    except Exception as e:
        log_error(e, "Erro ao recarregar vídeo")
        messagebox.showerror("Erro", "Erro ao recarregar vídeo")

def sair_aplicacao():
    """Função para sair da aplicação com confirmação"""
    global is_downloading
    
    # Verificar se há download em andamento
    if is_downloading:
        resposta = messagebox.askyesno(
            "Download em Andamento", 
            "Há um download em andamento. Deseja realmente sair?\n\n"
            "⚠️ Atenção: O download será interrompido e os arquivos podem ficar incompletos."
        )
        if not resposta:
            return
    
    # Confirmar saída
    resposta = messagebox.askyesno("Confirmar Saída", "Deseja realmente sair da aplicação?")
    if resposta:
        log_info("Aplicação encerrada pelo usuário")
        root.quit()
        root.destroy()

# Criar aba do histórico
criar_aba_historico()

# Criar aba de configurações
criar_aba_configuracoes()

# Declarar variáveis globais para frames das abas
config_frame = None
history_frame = None

# Chamar antes de root.mainloop()
initialize_app()
root.mainloop()