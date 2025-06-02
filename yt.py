import os
import sys
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import yt_dlp
import threading
import logging
from datetime import datetime

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
                'postprocessor_hooks': [postprocessor_hook],  # NOVO: Hook para merge
                'quiet': False,
                # Configurações para melhor tratamento de erros
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
            
            # Download concluído com sucesso
            root.after(0, download_success)
            
        except Exception as e:
            error_msg = log_error(e, "Erro durante download")
            root.after(0, lambda: download_error(error_msg))
        finally:
            is_downloading = False
    
    # Executar download em thread separada
    download_thread = threading.Thread(target=download_worker, daemon=True)
    download_thread.start()

def download_success():
    """Callback para download bem-sucedido"""
    global is_downloading
    
    # Mostrar 100% apenas quando tudo estiver realmente concluído
    root.after(0, lambda: update_progress_ui(100, "100%", "Concluído!", "Finalizado"))
    
    # Aguardar um pouco para o usuário ver o 100%
    def finalize_ui():
        global is_downloading
        is_downloading = False
        baixar_button.config(state=tk.NORMAL, text="Baixar vídeo")
        progress_frame.grid_remove()  # Ocultar barra de progresso
        messagebox.showinfo("Sucesso", "Download concluído com sucesso!")
        log_info("Download concluído com sucesso")
        habilitar_botao_download()
    
    # Aguardar 2 segundos antes de finalizar a UI
    root.after(2000, finalize_ui)

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
    try:
        url = root.clipboard_get()
        url_entry.delete(0, tk.END)
        url_entry.insert(tk.INSERT, url)
        log_info("URL colada da área de transferência")
    except tk.TclError:
        pass

def selecionar_diretorio():
    global download_directory
    download_directory = filedialog.askdirectory()
    if download_directory:
        # Truncar caminho se muito longo
        display_path = download_directory
        if len(display_path) > 80:
            display_path = "..." + display_path[-77:]
        
        diretorio_label.config(text=f"Diretório: {display_path}")
        habilitar_botao_download()
        log_info(f"Diretório selecionado: {download_directory}")

def resolucao_selecionada(event):
    habilitar_botao_download()

def habilitar_botao_download():
    """Habilita o botão de download quando todas as condições são atendidas"""
    try:
        # Verificar condições de forma mais flexível
        has_selection = bool(resolutions_listbox.curselection())
        has_directory = bool(download_directory)
        has_info = info is not None
        not_downloading = not is_downloading
        
        # Debug detalhado
        log_info(f"Verificando condições - Seleção: {has_selection}, Diretório: {has_directory}, Info: {has_info}, Não baixando: {not_downloading}")
        if has_info:
            log_info(f"Título do vídeo: {info.get('title', 'N/A')}")
        
        if has_selection and has_directory and has_info and not_downloading:
            baixar_button.config(state=tk.NORMAL)
            log_info("✅ Botão de download habilitado")
        else:
            baixar_button.config(state=tk.DISABLED)
            # Log das condições não atendidas
            missing = []
            if not has_selection: missing.append("resolução")
            if not has_directory: missing.append("diretório")
            if not has_info: missing.append("informações do vídeo")
            if not not_downloading: missing.append("download em andamento")
            if missing:
                log_info(f"❌ Botão desabilitado - Faltando: {', '.join(missing)}")
                
    except Exception as e:
        log_error(e, "Erro ao habilitar botão de download")
        baixar_button.config(state=tk.DISABLED)

# Criar janela principal
root = tk.Tk()
root.title("Baixador de Vídeos do YouTube v2.0")
root.geometry("900x700")  # AUMENTAR altura e largura
root.minsize(800, 600)  # Tamanho mínimo

# Configuração do grid com padding e pesos
for i in range(8):  # 8 linhas no layout
    if i == 2:  # Linha dos frames principais (resoluções e metadados)
        root.rowconfigure(i, weight=1, pad=10)  # Expandir esta linha
    else:
        root.rowconfigure(i, pad=10)
        
for i in range(2):
    root.columnconfigure(i, weight=1, pad=10)  # Ambas colunas expandem

# URL Input
url_label = tk.Label(root, text="URL do vídeo:")
url_label.grid(row=0, column=0, sticky='w')
url_entry = tk.Entry(root, width=50)
url_entry.grid(row=0, column=1, sticky='ew')

# Create right-click menu
menu = tk.Menu(root, tearoff=0)
menu.add_command(label="Colar", command=colar_texto)
url_entry.bind("<Button-3>", mostrar_menu)

# Extract button
extrair_button = tk.Button(root, text="Extrair informações", command=extrair_informacoes)
extrair_button.grid(row=1, column=0, columnspan=2, pady=5)

# Resolutions Frame
resolutions_frame = tk.Frame(root)
resolutions_frame.grid(row=2, column=0, sticky='nsew', padx=(0,5))  # Adicionar padding
resolutions_label = tk.Label(resolutions_frame, text="Resoluções:")
resolutions_label.pack()
resolutions_listbox = tk.Listbox(resolutions_frame, height=10)  # Altura fixa
resolutions_listbox.pack(fill=tk.BOTH, expand=True)
resolutions_listbox.bind("<<ListboxSelect>>", resolucao_selecionada)

# Metadata Frame
metadata_frame = tk.Frame(root)
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
baixar_button = tk.Button(root, text="Baixar vídeo", command=baixar_video, state=tk.DISABLED)
baixar_button.grid(row=3, column=0, columnspan=2, pady=5)

# Progress Frame (inicialmente oculto)
# CORRIGIDO: Criação da barra de progresso com configuração adequada
progress_frame = tk.Frame(root)
# IMPORTANTE: Definir maximum=100 na criação
progress_bar = ttk.Progressbar(progress_frame, length=400, mode='determinate', maximum=100)
progress_bar.pack(fill=tk.X, pady=2)
progress_label = tk.Label(progress_frame, text="")
progress_label.pack()

# Directory Selection
diretorio_button = tk.Button(root, text="Selecionar Diretório", command=selecionar_diretorio)
diretorio_button.grid(row=5, column=0, columnspan=2, pady=5)

# CORRIGIR: Label do diretório com melhor configuração
diretorio_label = tk.Label(root, text="Diretório: Nenhum selecionado", 
                          wraplength=800, justify='left')  # Quebra de linha automática
diretorio_label.grid(row=6, column=0, columnspan=2, sticky='ew', padx=10)

# Log inicial
log_info("Aplicação iniciada")

# Iniciar loop principal
root.mainloop()

# https://www.youtube.com/watch?v=6ywMN2N47Mc
# https://www.youtube.com/watch?v=pJT6JBJyqFc
# https://www.youtube.com/watch?v=MflImOTUjMw

def debug_state():
    """Função para debug do estado atual"""
    print(f"Info disponível: {info is not None}")
    print(f"Diretório selecionado: {download_directory}")
    print(f"Resolução selecionada: {bool(resolutions_listbox.curselection())}")
    print(f"Download em andamento: {is_downloading}")
    if info:
        print(f"Título do vídeo: {info.get('title', 'N/A')}")