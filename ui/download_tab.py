import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import webbrowser
import re
import uuid
import os
from PIL import Image, ImageTk
import io
import requests

from utils.app_utils import AppUtils
from utils.ui_utils import UIConstants

class DownloadTab:
    """Aba de download de vídeos"""
    
    def __init__(self, parent, download_manager, config_manager, history_manager, log_manager, main_app):
        self.parent = parent
        self.download_manager = download_manager
        self.config_manager = config_manager
        self.history_manager = history_manager
        self.log_manager = log_manager
        self.main_app = main_app
        
        self.frame = tk.Frame(parent)
        self.current_resolutions = []
        self.current_db_download_id = None
        
        self.audio_only_var = tk.BooleanVar()
        self.is_playlist_var = tk.BooleanVar(value=False)
        self.audio_quality_var = tk.StringVar(value='192kbps')
        
        self.create_widgets()
        self.setup_layout()
        self.enable_download_if_ready()
        
        self.load_last_directory()
    
    def load_last_directory(self):
        """Carrega o último diretório de download salvo"""
        try:
            last_dir = self.config_manager.db_manager.get_setting('last_download_directory')
            if last_dir and os.path.isdir(last_dir):
                self.download_manager.set_download_directory(last_dir)
                self.directory_label.config(text=f"Diretório: {last_dir}")
                self.log_manager.log_info(f"Último diretório carregado: {last_dir}")
                self.enable_download_if_ready()
        except Exception as e:
            self.log_manager.log_error(str(e), "Erro ao carregar último diretório")
    
    def create_widgets(self):
        """Cria widgets da aba"""
        self.url_label = tk.Label(self.frame, text="URL do Vídeo:")
        self.url_entry = tk.Entry(self.frame, width=60)
        self.url_entry.bind("<Button-3>", self.show_context_menu)
        
        self.context_menu = tk.Menu(self.frame, tearoff=0)
        self.context_menu.add_command(label="Colar", command=self.paste_url)
        
        self.content_type_label = tk.Label(self.frame, text="", font=UIConstants.FONT_ITALIC)
        
        self.extract_button = tk.Button(self.frame, text="Extrair informações", command=self.extract_info)
        
        self.playlist_frame = tk.Frame(self.frame)
        self.playlist_checkbox = tk.Checkbutton(
            self.playlist_frame,
            text="Baixar como playlist",
            variable=self.is_playlist_var,
            command=self.on_playlist_mode_change,
            state=tk.DISABLED
        )
        self.playlist_info_label = tk.Label(self.playlist_frame, text="")
        
        self.resolutions_frame = tk.LabelFrame(self.frame, text="Resoluções Disponíveis", padx=10, pady=10)
        self.resolutions_label = tk.Label(self.resolutions_frame, text="Selecione a resolução:")
        self.resolutions_listbox = tk.Listbox(self.resolutions_frame, selectmode=tk.SINGLE, exportselection=False)
        self.resolutions_listbox.bind('<<ListboxSelect>>', self.on_resolution_select)
        
        self.audio_frame = tk.Frame(self.resolutions_frame)
        self.audio_only_checkbox = tk.Checkbutton(
            self.audio_frame,
            text="Baixar apenas áudio",
            variable=self.audio_only_var,
            command=self.on_audio_only_change
        )
        self.audio_quality_label = tk.Label(self.audio_frame, text="Qualidade:")
        self.audio_quality_combo = ttk.Combobox(
            self.audio_frame,
            textvariable=self.audio_quality_var,
            values=['128kbps', '192kbps', '256kbps', '320kbps'],
            state='readonly',
            width=10
        )
        
        self.metadata_frame = tk.LabelFrame(self.frame, text="Metadados do Vídeo", padx=10, pady=10)
        self.metadata_label = tk.Label(self.metadata_frame, text="Informações:")
        self.metadata_text = tk.Text(self.metadata_frame, wrap=tk.WORD, height=15, width=50)
        self.metadata_scrollbar = tk.Scrollbar(self.metadata_frame, command=self.metadata_text.yview)
        self.metadata_text.config(yscrollcommand=self.metadata_scrollbar.set)
        
        self.metadata_text.tag_configure("link", foreground="blue", underline=True)
        self.metadata_text.tag_bind("link", "<Enter>", self.on_link_enter)
        self.metadata_text.tag_bind("link", "<Leave>", self.on_link_leave)
        self.metadata_text.tag_bind("link", "<Button-1>", self.on_link_click)
        
        self.metadata_context_menu = tk.Menu(self.metadata_text, tearoff=0)
        self.metadata_context_menu.add_command(label="Copiar Seleção", command=self.copy_selected_text)
        self.metadata_context_menu.add_command(label="Copiar Tudo", command=self.copy_all_text)
        self.metadata_context_menu.add_separator()
        self.metadata_context_menu.add_command(label="Selecionar Tudo", command=self.select_all_text)
        self.metadata_text.bind("<Button-3>", self.show_metadata_context_menu)
        
        self.download_button = tk.Button(self.frame, text="Baixar vídeo", command=self.start_download, state=tk.DISABLED)
        self.directory_button = tk.Button(self.frame, text="Selecionar Diretório", command=self.select_directory)
        self.directory_label = tk.Label(self.frame, text=f"Diretório: {self.download_manager.download_directory}", wraplength=400)
        self.exit_button = tk.Button(self.frame, text="Sair", command=self.frame.quit)
        
        self.progress_frame = tk.Frame(self.frame)
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient='horizontal', mode='determinate')
        self.progress_label = tk.Label(self.progress_frame, text="")
        
        self.mini_player_frame = tk.Frame(self.frame, bd=1, relief=tk.SOLID)
        self.thumbnail_label = tk.Label(self.mini_player_frame)
        self.mini_player_title = tk.Label(self.mini_player_frame, text="", font=UIConstants.FONT_BOLD, wraplength=280)
        self.mini_player_info = tk.Label(self.mini_player_frame, text="", wraplength=280)

    def show_metadata_context_menu(self, event):
        """Mostra menu de contexto para metadados"""
        try:
            self.metadata_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.metadata_context_menu.grab_release()
    
    def copy_selected_text(self):
        """Copia texto selecionado dos metadados"""
        try:
            selected_text = self.metadata_text.get(tk.SEL_FIRST, tk.SEL_LAST)
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
            index = self.metadata_text.index(f"@{event.x},{event.y}")
            tags = self.metadata_text.tag_names(index)
            if "link" in tags:
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
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = list(re.finditer(url_pattern, text))
        if not urls:
            self.metadata_text.insert(tk.END, text)
            return
        last_end = 0
        for match in urls:
            start, end = match.span()
            url = match.group()
            if start > last_end:
                self.metadata_text.insert(tk.END, text[last_end:start])
            link_start = self.metadata_text.index(tk.INSERT)
            self.metadata_text.insert(tk.END, url)
            link_end = self.metadata_text.index(tk.INSERT)
            self.metadata_text.tag_add("link", link_start, link_end)
            last_end = end
        if last_end < len(text):
            self.metadata_text.insert(tk.END, text[last_end:])
        self.log_manager.log_info(f"Texto inserido com {len(urls)} links detectados")

    def setup_layout(self):
        """Configura layout da aba"""
        for i in range(12):
            if i == 4:
                self.frame.rowconfigure(i, weight=1, pad=UIConstants.PADDING)
            elif i == 6:
                self.frame.rowconfigure(i, minsize=130, pad=UIConstants.PADDING)
            else:
                self.frame.rowconfigure(i, pad=UIConstants.PADDING)
        for i in range(2):
            self.frame.columnconfigure(i, weight=1, pad=UIConstants.PADDING)
        self.url_label.grid(row=0, column=0, sticky='w')
        self.url_entry.grid(row=0, column=1, sticky='ew')
        self.content_type_label.grid(row=1, column=0, columnspan=2, sticky='w', pady=2)
        self.extract_button.grid(row=2, column=0, columnspan=2, pady=2)
        self.playlist_frame.grid(row=3, column=0, columnspan=2, sticky='ew', pady=2)
        self.playlist_checkbox.pack(side='left')
        self.playlist_info_label.pack(side='left', padx=(10, 0))
        self.resolutions_frame.grid(row=4, column=0, sticky='nsew', padx=(0, 5))
        self.metadata_frame.grid(row=4, column=1, sticky='nsew', padx=(5, 0))
        self.resolutions_label.pack()
        self.resolutions_listbox.pack(fill=tk.BOTH, expand=True)
        self.audio_frame.pack(fill=tk.X, pady=5)
        self.audio_only_checkbox.pack(anchor='w')
        self.audio_quality_frame = tk.Frame(self.audio_frame)
        self.audio_quality_label.pack(side=tk.LEFT)
        self.audio_quality_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.metadata_label.pack()
        self.metadata_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.metadata_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.download_button.grid(row=5, column=0, columnspan=2, pady=UIConstants.BUTTON_PADDING)
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
        self.extract_button.config(state=tk.DISABLED, text="Extraindo...")
        def extract_worker():
            success, data, resolutions = self.download_manager.extract_video_info(url)
            self.frame.after(0, lambda: self.on_extraction_complete(success, data, resolutions))
        thread = threading.Thread(target=extract_worker, daemon=True)
        thread.start()
    
    def on_extraction_complete(self, success, data, resolutions):
        """Callback para conclusão da extração"""
        self.log_manager.log_info(f"Extração concluída - Sucesso: {success}")
        self.extract_button.config(state=tk.NORMAL, text="Extrair informações")
        if success:
            is_playlist = data and data.get('type') == 'playlist'
            if is_playlist:
                self.log_manager.log_info(f"Playlist detectada: {data.get('title', 'N/A')[:50]}... ({data.get('video_count', 0)} vídeos)")
                self.content_type_label.config(text=f"📋 Playlist detectada ({data.get('video_count', 0)} vídeos)")
                self.playlist_checkbox.config(state=tk.NORMAL)
                self.is_playlist_var.set(True)
                self.on_playlist_mode_change()
                self.update_resolutions(['1080p', '720p', '480p', '360p'])
                self.update_metadata(data)
            else:
                self.log_manager.log_info(f"Vídeo individual: {data.get('title', 'N/A')[:50]}...")
                self.log_manager.log_info(f"Resoluções recebidas: {len(resolutions)} itens - {resolutions}")
                self.content_type_label.config(text="🎥 Vídeo individual")
                self.is_playlist_var.set(False)
                self.playlist_checkbox.config(state=tk.DISABLED)
                self.on_playlist_mode_change()
                self.update_resolutions(resolutions)
                self.update_metadata(data)
                self.hide_mini_player()
                if data and isinstance(data, dict):
                    self.update_mini_player(data)
            self.enable_download_if_ready()
            self.log_manager.log_info("Interface atualizada com sucesso após extração")
        else:
            self.log_manager.log_error(f"Erro na extração: {data}", "Extração de Informações")
            AppUtils.show_error_message("Erro", data)
            self.content_type_label.config(text="")
            self.is_playlist_var.set(False)
            self.playlist_checkbox.config(state=tk.DISABLED)
            self.playlist_info_label.config(text="")
            self.hide_mini_player()
            self.resolutions_listbox.delete(0, tk.END)
            self.metadata_text.delete("1.0", tk.END)
    
    def update_resolutions(self, resolutions):
        """Atualiza lista de resoluções"""
        self.log_manager.log_info(f"Atualizando lista de resoluções: {resolutions}")
        self.resolutions_listbox.delete(0, tk.END)
        self.current_resolutions = resolutions
        if not resolutions:
            self.log_manager.log_warning("Nenhuma resolução recebida para atualização")
            self.resolutions_listbox.insert(tk.END, "Nenhuma resolução disponível")
            return
        for i, resolution in enumerate(resolutions):
            self.resolutions_listbox.insert(tk.END, resolution)
            self.log_manager.log_info(f"Resolução {i+1}: {resolution}")
        if len(resolutions) > 0 and resolutions[0] != "Nenhuma resolução disponível":
            self.resolutions_listbox.selection_set(0)
            self.log_manager.log_info(f"Primeira resolução selecionada automaticamente: {resolutions[0]}")
        self.log_manager.log_info(f"Lista de resoluções atualizada com {len(resolutions)} itens")
    
    def update_metadata(self, video_info):
        """Atualiza metadados do vídeo com conteúdo completo e links clicáveis"""
        self.metadata_text.delete("1.0", tk.END)
        if isinstance(video_info, dict):
            metadata = self.download_manager.get_video_metadata()
            title = metadata.get('title', 'N/A')
            self.metadata_text.insert(tk.END, f"📺 Título: {title}\n\n")
            uploader = metadata.get('uploader', 'N/A')
            self.metadata_text.insert(tk.END, f"👤 Canal: {uploader}\n\n")
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
            view_count = metadata.get('view_count', 'N/A')
            if view_count != 'N/A' and isinstance(view_count, (int, float)):
                view_count_str = f"{int(view_count):,}".replace(',', '.')
                self.metadata_text.insert(tk.END, f"👁️ Visualizações: {view_count_str}\n\n")
            else:
                self.metadata_text.insert(tk.END, f"👁️ Visualizações: {view_count}\n\n")
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
            webpage_url = metadata.get('webpage_url', 'N/A')
            if webpage_url != 'N/A':
                self.metadata_text.insert(tk.END, "🔗 URL: ")
                start_pos = self.metadata_text.index(tk.INSERT)
                self.metadata_text.insert(tk.END, webpage_url)
                end_pos = self.metadata_text.index(tk.INSERT)
                self.metadata_text.tag_add("link", start_pos, end_pos)
                self.metadata_text.insert(tk.END, "\n\n")
            description = metadata.get('description', 'N/A')
            if description != 'N/A' and description and description.strip():
                self.metadata_text.insert(tk.END, "📝 Descrição:\n")
                self._insert_text_with_links(description)
            else:
                self.metadata_text.insert(tk.END, "📝 Descrição: Não disponível")
            self.log_manager.log_info(f"Metadados completos atualizados para: {title[:50]}...")
            self.update_mini_player(video_info)
        else:
            self.metadata_text.insert(tk.END, "❌ Erro: Informações do vídeo não disponíveis")
            self.log_manager.log_error("video_info inválido em update_metadata", "UI")
            self.hide_mini_player()

    def on_resolution_select(self, event):
        """Callback para seleção de resolução"""
        self.enable_download_if_ready()
    
    def on_audio_only_change(self):
        """Callback para mudança na opção de áudio apenas"""
        if self.audio_only_var.get():
            self.resolutions_listbox.config(state=tk.DISABLED)
            self.audio_quality_frame.pack(fill=tk.X, pady=2)
        else:
            self.resolutions_listbox.config(state=tk.NORMAL)
            self.audio_quality_frame.pack_forget()
        self.enable_download_if_ready()
    
    def on_playlist_mode_change(self):
        """Callback quando modo playlist muda"""
        if self.is_playlist_var.get():
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
                video_entry, index, total = data
                def update_progress_ui():
                    try:
                        progress_text = f"Baixando vídeo {index}/{total}: {video_entry.get('title', 'N/A')[:30]}..."
                        self.download_button.config(text=progress_text)
                        self.log_manager.log_info(f"Processando vídeo {index}/{total} da playlist: {video_entry.get('title', 'N/A')}")
                    except Exception as e:
                        self.log_manager.log_error(f"Erro ao atualizar UI para vídeo da playlist: {str(e)}")
                self.frame.after(0, update_progress_ui)
            elif callback_type == 'success':
                video_success_data = data
                def update_success_ui():
                    try:
                        video_info = video_success_data['video_info']
                        index = video_success_data['index']
                        total = video_success_data['total']
                        resolution = video_success_data['resolution']
                        audio_only = video_success_data['audio_only']
                        self.update_mini_player(video_info)
                        self.add_video_to_history(video_info, resolution, audio_only)
                        self.log_manager.log_info(f"Vídeo {index}/{total} salvo no histórico: {video_info.get('title', 'N/A')}")
                    except Exception as e:
                        self.log_manager.log_error(f"Erro ao processar sucesso do vídeo da playlist: {str(e)}")
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
            title = video_info.get('title', 'N/A')
            duration = video_info.get('duration', 0)
            uploader = video_info.get('uploader', 'N/A')
            upload_date = video_info.get('upload_date', 'N/A')
            view_count = video_info.get('view_count', 0)
            like_count = video_info.get('like_count', 0)
            description = video_info.get('description', 'N/A')
            url = video_info.get('webpage_url', video_info.get('url', 'N/A'))
            if audio_only:
                resolution_for_history = 'music'
            else:
                resolution_for_history = resolution
            estimated_size = 0
            if 'filesize' in video_info and video_info['filesize']:
                estimated_size = video_info['filesize']
            elif 'filesize_approx' in video_info and video_info['filesize_approx']:
                estimated_size = video_info['filesize_approx']
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
        if self.is_playlist_var.get():
            if self.audio_only_var.get():
                has_format = True
                button_text = "Baixar Playlist (áudio)"
            else:
                has_format = bool(self.resolutions_listbox.curselection())
                button_text = "Baixar Playlist (vídeo)"
        else:
            if self.audio_only_var.get():
                has_format = True
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
        if self.is_playlist_var.get():
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
            self.download_button.config(state=tk.DISABLED, text=f"Baixando {download_type}...")
            self.show_progress_bar()
            if hasattr(self.main_app, 'bandwidth_tracker'):
                try:
                    download_id = str(uuid.uuid4())
                    self.main_app.current_download_id = download_id
                    self.main_app.bandwidth_tracker.start_tracking(download_id)
                    self.log_manager.log_info(f"Rastreamento iniciado (playlist) com ID: {download_id}")
                except Exception as e:
                    self.log_manager.log_error(f"Erro ao inicializar rastreamento (playlist): {e}")
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
            if self.audio_only_var.get():
                audio_quality = self.audio_quality_var.get()
                selected_resolution = None
                download_type = "áudio"
            else:
                selected_index = self.resolutions_listbox.curselection()
                if not selected_index:
                    AppUtils.show_error_message("Erro", "Por favor, selecione uma resolução.")
                    return
                selected_resolution = self.resolutions_listbox.get(selected_index)
                audio_quality = None
                download_type = "vídeo"
            self.download_button.config(state=tk.DISABLED, text=f"Baixando {download_type}...")
            self.show_progress_bar()
            if hasattr(self.main_app, 'bandwidth_tracker'):
                try:
                    download_id = str(uuid.uuid4())
                    self.main_app.current_download_id = download_id
                    self.main_app.bandwidth_tracker.start_tracking(download_id)
                    self.log_manager.log_info(f"Rastreamento iniciado com ID: {download_id}")
                except Exception as e:
                    self.log_manager.log_error(f"Erro ao inicializar rastreamento: {e}")
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
        if not self.progress_bar.winfo_manager():
            self.progress_bar.pack(fill=tk.X, pady=2)
            self.progress_label.pack()
        self.progress_frame.grid(row=7, column=0, columnspan=2, sticky='ew', padx=UIConstants.PADDING, pady=UIConstants.BUTTON_PADDING)
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Preparando download...")
        self.progress_frame.update_idletasks()
        self.frame.update_idletasks()
    
    def hide_progress_bar(self):
        """Esconde barra de progresso"""
        self.progress_frame.grid_remove()
        self.progress_bar.pack_forget()
        self.progress_label.pack_forget()
    
    def update_progress(self, d):
        """Atualiza progresso do download"""
        if d['status'] == 'downloading':
            try:
                percent = self.extract_progress_percent(d)
                speed_str = d.get('_speed_str', d.get('speed', 'N/A'))
                eta_str = d.get('_eta_str', d.get('eta', 'N/A'))
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
        download_id = self.add_to_history()
        if download_id:
            self.current_db_download_id = download_id
            self.log_manager.log_info(f"Download ID definido: {download_id}")
            if (hasattr(self.main_app, 'bandwidth_tracker') and 
                hasattr(self.main_app, '_pending_finish_tracking') and 
                self.main_app._pending_finish_tracking):
                try:
                    self.main_app.bandwidth_tracker.finish_tracking(
                        self.main_app._pending_finish_tracking,
                        download_id
                    )
                    self.log_manager.log_info(f"Rastreamento finalizado: {self.main_app._pending_finish_tracking} -> DB ID: {download_id}")
                    self.main_app._pending_finish_tracking = None
                except Exception as e:
                    self.log_manager.log_error(f"Erro ao finalizar rastreamento: {e}")
        if self.config_manager.should_auto_open_folder():
            try:
                os.startfile(self.download_manager.download_directory)
            except Exception as e:
                self.log_manager.log_error(e, "Erro ao abrir pasta automaticamente")
        messagebox.showinfo("Sucesso", "Download concluído com sucesso!")
        self.frame.after(3000, self.reset_download_ui)
    
    def on_download_error(self, error_msg):
        """Callback para erro no download"""
        AppUtils.show_error_message("Erro no Download", error_msg)
        self.reset_download_ui()
    
    def add_to_history(self):
        """Adiciona download ao histórico e retorna o ID do download"""
        try:
            metadata = self.download_manager.get_video_metadata()
            if self.audio_only_var.get():
                resolution = 'music'
            else:
                selected_index = self.resolutions_listbox.curselection()
                resolution = self.resolutions_listbox.get(selected_index) if selected_index else 'N/A'
            current_info = self.download_manager.current_info
            file_size = 'N/A'
            if current_info:
                if self.audio_only_var.get():
                    duration = current_info.get('duration', 0)
                    if duration and isinstance(duration, (int, float)):
                        estimated_size = int(duration * 24 * 1024)
                        file_size = str(estimated_size)
                else:
                    formats = current_info.get('formats', [])
                    for f in formats:
                        if f.get('format_note') == resolution:
                            file_size = f.get('filesize', f.get('filesize_approx', 'N/A'))
                            break
            return self.history_manager.add_download_to_history(
                title=metadata.get('title', 'N/A'),
                url=metadata.get('webpage_url', 'N/A'),
                resolution=resolution,
                file_size=file_size,
                duration=metadata.get('duration', 0),
                uploader=metadata.get('uploader', 'N/A'),
                upload_date=metadata.get('upload_date', 'N/A'),
                view_count=metadata.get('view_count', 0),
                like_count=metadata.get('like_count', 0),
                description=metadata.get('description', 'N/A')
            )
        except Exception as e:
            self.log_manager.log_error(e, "Erro ao adicionar ao histórico")
            return None
    
    def reset_download_ui(self):
        """Reseta a UI de download para o estado inicial"""
        self.hide_progress_bar()
        self.enable_download_if_ready()
        if self.is_playlist_var.get():
            self.download_button.config(text="Baixar Playlist")
        else:
            if self.audio_only_var.get():
                self.download_button.config(text="Baixar áudio")
            else:
                self.download_button.config(text="Baixar vídeo")
    
    def update_mini_player(self, video_info):
        """Atualiza o mini-player com informações do vídeo"""
        if not video_info or not isinstance(video_info, dict):
            self.hide_mini_player()
            return
        title = video_info.get('title', 'N/A')
        uploader = video_info.get('uploader', 'N/A')
        thumbnail_url = video_info.get('thumbnail')
        if not all([title, uploader, thumbnail_url]):
            self.hide_mini_player()
            return
        self.mini_player_title.config(text=title)
        self.mini_player_info.config(text=f"por {uploader}")
        def load_image():
            try:
                response = requests.get(thumbnail_url, stream=True)
                response.raise_for_status()
                image_data = response.content
                img = Image.open(io.BytesIO(image_data))
                img.thumbnail((120, 90))
                photo = ImageTk.PhotoImage(img)
                self.thumbnail_label.config(image=photo)
                self.thumbnail_label.image = photo
                self.show_mini_player()
            except Exception as e:
                self.log_manager.log_error(f"Erro ao carregar thumbnail: {e}")
                self.hide_mini_player()
        threading.Thread(target=load_image, daemon=True).start()
    
    def show_mini_player(self):
        """Mostra o mini-player"""
        self.mini_player_frame.grid(row=6, column=0, columnspan=2, sticky='ew', padx=UIConstants.PADDING, pady=5)
        self.thumbnail_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.mini_player_title.pack(anchor='w', padx=5)
        self.mini_player_info.pack(anchor='w', padx=5)
    
    def hide_mini_player(self):
        """Esconde o mini-player"""
        self.mini_player_frame.grid_remove()
        self.thumbnail_label.pack_forget()
        self.mini_player_title.pack_forget()
        self.mini_player_info.pack_forget()
