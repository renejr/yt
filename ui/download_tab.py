import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os

from utils.app_utils import AppUtils
from config.app_constants import AppConstants, UIConstants

class DownloadTab(ttk.Frame):
    def __init__(self, parent, download_manager, history_manager, log_manager, config_manager, main_app):
        super().__init__(parent)
        self.parent = parent
        self.download_manager = download_manager
        self.history_manager = history_manager
        self.log_manager = log_manager
        self.config_manager = config_manager
        self.main_app = main_app

        self.video_info = None
        self.available_subtitles = {}
        
        self.url_var = tk.StringVar()
        self.download_type = tk.StringVar(value='video')
        self.resolution_var = tk.StringVar()
        self.audio_quality_var = tk.StringVar(value=AppConstants.DEFAULT_AUDIO_QUALITY)
        self.subtitle_language = tk.StringVar()
        self.embed_subtitle = tk.BooleanVar(value=False)

        self._create_widgets()
        self._setup_layout()
        self._bind_events()

    def _create_widgets(self):
        """Cria os widgets da aba de download."""
        self.main_frame = ttk.Frame(self, padding=UIConstants.PADDING)

        self.url_frame = ttk.LabelFrame(self.main_frame, text="URL do Vídeo ou Playlist", padding=(10, 5))
        self.url_entry = ttk.Entry(self.url_frame, textvariable=self.url_var, width=60)
        self.info_button = ttk.Button(self.url_frame, text="Obter Informações", command=self._fetch_video_info)

        self.options_frame = ttk.LabelFrame(self.main_frame, text="Opções de Download", padding=(10, 5))
        self.video_radio = ttk.Radiobutton(self.options_frame, text="Vídeo", variable=self.download_type, value='video', command=self._on_download_type_change)
        self.audio_radio = ttk.Radiobutton(self.options_frame, text="Apenas Áudio", variable=self.download_type, value='audio', command=self._on_download_type_change)
        
        self.resolution_label = ttk.Label(self.options_frame, text="Resolução:")
        self.resolution_combobox = ttk.Combobox(self.options_frame, textvariable=self.resolution_var, state='disabled', width=25)

        self.audio_quality_label = ttk.Label(self.options_frame, text="Qualidade:")
        self.audio_quality_combobox = ttk.Combobox(self.options_frame, textvariable=self.audio_quality_var, values=AppConstants.AUDIO_QUALITIES, state='disabled', width=15)

        self.subtitle_frame = ttk.LabelFrame(self.main_frame, text="Opções de Legenda", padding=(10, 5))
        self.subtitle_label = ttk.Label(self.subtitle_frame, text="Idioma da Legenda:")
        self.subtitle_combobox = ttk.Combobox(self.subtitle_frame, textvariable=self.subtitle_language, state='disabled', width=30)
        self.embed_subtitle_check = ttk.Checkbutton(self.subtitle_frame, text="Embutir legenda no vídeo", variable=self.embed_subtitle, state='disabled')

        self.info_frame = ttk.LabelFrame(self.main_frame, text="Informações do Vídeo", padding=(10, 5))
        self.thumbnail_label = ttk.Label(self.info_frame)
        self.video_title_label = ttk.Label(self.info_frame, text="", font=UIConstants.FONT_BOLD, wraplength=400)
        self.video_details_label = ttk.Label(self.info_frame, text="", wraplength=400)

        self.download_button = ttk.Button(self.main_frame, text="Baixar", command=self._start_download, state='disabled')
        self.directory_button = ttk.Button(self.main_frame, text="Selecionar Diretório", command=self._select_directory)
        self.directory_label = ttk.Label(self.main_frame, text=f"Diretório: {self.download_manager.download_directory}", wraplength=500)

        self.progress_frame = ttk.Frame(self.main_frame)
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient='horizontal', mode='determinate')
        self.progress_label = ttk.Label(self.progress_frame, text="")

    def _setup_layout(self):
        """Configura o layout dos widgets na aba."""
        self.main_frame.pack(expand=True, fill='both', padx=5, pady=5)

        self.url_frame.grid(row=0, column=0, columnspan=4, padx=10, pady=5, sticky='ew')
        self.url_entry.pack(side='left', expand=True, fill='x', padx=5, pady=5)
        self.info_button.pack(side='left', padx=5, pady=5)

        self.options_frame.grid(row=1, column=0, columnspan=4, padx=10, pady=5, sticky='ew')
        self.video_radio.grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.audio_radio.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        self.resolution_label.grid(row=0, column=2, padx=(10, 5), pady=5, sticky='w')
        self.resolution_combobox.grid(row=0, column=3, padx=5, pady=5, sticky='we')
        self.audio_quality_label.grid(row=1, column=2, padx=(10, 5), pady=5, sticky='w')
        self.audio_quality_combobox.grid(row=1, column=3, padx=5, pady=5, sticky='we')
        self._on_download_type_change()

        self.info_frame.grid(row=2, column=0, columnspan=4, padx=10, pady=5, sticky='ew')
        self.thumbnail_label.grid(row=0, column=0, rowspan=2, padx=10, pady=5, sticky='nw')
        self.video_title_label.grid(row=0, column=1, padx=10, pady=5, sticky='nw')
        self.video_details_label.grid(row=1, column=1, padx=10, pady=5, sticky='nw')

        self.subtitle_frame.grid(row=3, column=0, columnspan=4, padx=10, pady=(5, 10), sticky='ew')
        self.subtitle_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.subtitle_combobox.grid(row=0, column=1, padx=5, pady=5, sticky='we')
        self.embed_subtitle_check.grid(row=0, column=2, padx=10, pady=5, sticky='w')

        self.directory_button.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky='w')
        self.directory_label.grid(row=5, column=0, columnspan=4, padx=10, pady=2, sticky='w')
        self.download_button.grid(row=4, column=2, columnspan=2, padx=10, pady=5, sticky='e')
        self.progress_frame.grid(row=6, column=0, columnspan=4, padx=10, pady=5, sticky='ew')
        self.progress_bar.pack(expand=True, fill='x')
        self.progress_label.pack(expand=True, fill='x')
        self.progress_frame.grid_remove()

    def _bind_events(self):
        self.url_entry.bind("<Control-v>", self._paste_from_clipboard)
        self.url_entry.bind("<Button-3>", self._show_context_menu)

    def _show_context_menu(self, event):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Colar", command=self._paste_from_clipboard)
        menu.tk_popup(event.x_root, event.y_root)

    def _paste_from_clipboard(self, event=None):
        try:
            self.url_var.set(self.clipboard_get())
        except tk.TclError:
            pass
        return "break"

    def _fetch_video_info(self):
        url = self.url_var.get().strip()
        if not url:
            AppUtils.show_warning_message("URL Vazia", "Por favor, insira uma URL.")
            return

        self._clear_video_info()
        self.info_button.config(state='disabled', text="Buscando...")

        def worker():
            success, data = self.download_manager.get_video_info(url)
            self.after(0, self._on_info_fetched, success, data)

        threading.Thread(target=worker, daemon=True).start()

    def _on_info_fetched(self, success, data):
        self.info_button.config(state='normal', text="Obter Informações")
        if not success:
            AppUtils.show_error_message("Erro", f"Não foi possível obter informações: {data}")
            return

        self.video_info = data
        self._update_info_widgets(data)
        self._fetch_subtitles(data['webpage_url'])
        self._check_download_ready()

    def _fetch_subtitles(self, url):
        self.log_manager.log_info("Buscando legendas...")
        def worker():
            success, subtitles_or_error = self.download_manager.get_available_subtitles(url)
            self.after(0, self._on_subtitles_fetched, success, subtitles_or_error)
        threading.Thread(target=worker, daemon=True).start()

    def _on_subtitles_fetched(self, success, subtitles_or_error):
        if success and subtitles_or_error:
            self.log_manager.log_info(f"Legendas encontradas: {subtitles_or_error}")
            self.available_subtitles = subtitles_or_error
            friendly_names = list(self.available_subtitles.values())
            self.subtitle_combobox['values'] = friendly_names
            self.subtitle_language.set(friendly_names[0])
            self.subtitle_combobox.config(state='readonly')
            self.embed_subtitle_check.config(state='normal')
        else:
            self.log_manager.log_warning("Nenhuma legenda encontrada ou erro ao buscar.")

    def _update_info_widgets(self, data):
        self.video_title_label.config(text=data.get('title', 'N/A'))
        duration = AppUtils.format_duration(data.get('duration', 0))
        views = f"{data.get('view_count', 0):,} views".replace(',', '.')
        self.video_details_label.config(text=f"{data.get('uploader', 'N/A')} • {views} • {duration}")

        resolutions = [f['format_note'] for f in data.get('formats', []) if f.get('vcodec') != 'none' and f.get('ext') == 'mp4' and 'format_note' in f]
        if resolutions:
            self.resolution_combobox['values'] = resolutions
            self.resolution_var.set(resolutions[0])
            self.resolution_combobox.config(state='readonly')
        
        thumbnail_url = data.get('thumbnail')
        if thumbnail_url:
            def load_thumb():
                image_data = AppUtils.fetch_image(thumbnail_url)
                if image_data:
                    self.thumbnail_image = AppUtils.create_photo_image(image_data, (120, 90))
                    self.after(0, lambda: self.thumbnail_label.config(image=self.thumbnail_image))
            threading.Thread(target=load_thumb, daemon=True).start()

    def _clear_video_info(self):
        self.video_info = None
        self.available_subtitles = {}
        self.video_title_label.config(text="")
        self.video_details_label.config(text="")
        self.thumbnail_label.config(image=None)
        self.resolution_combobox['values'] = []
        self.resolution_var.set('')
        self.resolution_combobox.config(state='disabled')
        self.subtitle_combobox['values'] = []
        self.subtitle_language.set('')
        self.subtitle_combobox.config(state='disabled')
        self.embed_subtitle_check.config(state='disabled')
        self.download_button.config(state='disabled')

    def _on_download_type_change(self):
        is_audio = self.download_type.get() == 'audio'
        self.resolution_label.config(state='disabled' if is_audio else 'normal')
        self.resolution_combobox.config(state='disabled' if is_audio else 'readonly')
        self.audio_quality_label.config(state='normal' if is_audio else 'disabled')
        self.audio_quality_combobox.config(state='readonly' if is_audio else 'disabled')
        if self.video_info:
             self.resolution_combobox.config(state='readonly' if not is_audio else 'disabled')
        self._check_download_ready()

    def _select_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.download_manager.set_download_directory(directory)
            self.directory_label.config(text=f"Diretório: {directory}")
            self.config_manager.set_setting('last_download_directory', directory)
            self._check_download_ready()

    def _check_download_ready(self):
        if self.video_info and self.download_manager.download_directory:
            self.download_button.config(state='normal')
        else:
            self.download_button.config(state='disabled')

    def _start_download(self):
        url = self.video_info.get('webpage_url')
        audio_only = self.download_type.get() == 'audio'
        selected_resolution = None if audio_only else self.resolution_var.get()
        audio_quality = self.audio_quality_var.get().split(' ')[0] if audio_only else None

        selected_sub_name = self.subtitle_language.get()
        subtitle_lang_code = None
        if selected_sub_name:
            for code, name in self.available_subtitles.items():
                if name == selected_sub_name:
                    subtitle_lang_code = code
                    break
        
        embed_subtitle = self.embed_subtitle.get()

        self.download_button.config(state='disabled', text="Baixando...")
        self.progress_frame.grid()

        def progress_hook(d):
            self.after(0, self._update_progress, d)

        self.download_manager.start_download(
            url=url,
            selected_resolution=selected_resolution,
            progress_hook=progress_hook,
            success_callback=self._on_download_complete,
            error_callback=self._on_download_error,
            audio_only=audio_only,
            audio_quality=audio_quality,
            subtitle_lang=subtitle_lang_code,
            embed_subtitle=embed_subtitle
        )

    def _update_progress(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes:
                percent = (d['downloaded_bytes'] / total_bytes) * 100
                speed = d.get('_speed_str', 'N/A')
                eta = d.get('_eta_str', 'N/A')
                self.progress_bar['value'] = percent
                self.progress_label.config(text=f"{percent:.1f}% | {speed} | ETA: {eta}")
        elif d['status'] == 'finished':
            self.progress_label.config(text="Download finalizado, processando...")
            self.progress_bar['value'] = 100

    def _on_download_complete(self, download_details):
        self.download_button.config(state='normal', text="Baixar")
        self.progress_frame.grid_remove()
        AppUtils.show_info_message("Sucesso", "Download concluído com sucesso!")

        try:
            file_path = download_details.get('filepath')
            file_size = os.path.getsize(file_path)

            self.history_manager.add_download_to_history(
                title=self.video_info.get('title', 'N/A'),
                url=self.video_info.get('webpage_url'),
                resolution=self.resolution_var.get() if not self.download_type.get() == 'audio' else 'Áudio',
                status='Concluído',
                file_path=file_path,
                file_size=file_size,
                subtitle_lang=download_details.get('subtitle_lang'),
                subtitle_path=download_details.get('subtitle_path'),
                is_embedded=download_details.get('is_embedded')
            )
        except Exception as e:
            self.log_manager.log_error(e, "Erro ao adicionar ao histórico")

        if self.config_manager.get_setting('auto_open_folder', False):
            try:
                os.startfile(self.download_manager.download_directory)
            except Exception as e:
                self.log_manager.log_error(e, "Erro ao abrir pasta automaticamente")

    def _on_download_error(self, error_message):
        self.download_button.config(state='normal', text="Baixar")
        self.progress_frame.grid_remove()
        AppUtils.show_error_message("Erro no Download", error_message)
