import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from utils import AppUtils, UIConstants

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
