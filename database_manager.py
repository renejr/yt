import sqlite3
import logging
from datetime import datetime
from database_schema import DatabaseSchema

class DatabaseManager:
    def __init__(self, db_path="youtube_downloader.db"):
        self.db_path = db_path
        self.schema = DatabaseSchema(db_path)
        
    def initialize(self):
        """Inicializa o banco de dados com schema atualizado"""
        self.schema.initialize_database()
    
    def add_download(self, download_data):
        """Adiciona um download ao histórico"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO downloads (
                    url, title, duration, resolution, file_size, 
                    download_path, status, thumbnail_url, uploader, 
                    view_count, like_count, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                download_data.get('url'),
                download_data.get('title'),
                download_data.get('duration'),
                download_data.get('resolution'),
                download_data.get('file_size'),
                download_data.get('download_path'),
                download_data.get('status', 'completed'),
                download_data.get('thumbnail_url'),
                download_data.get('uploader'),
                download_data.get('view_count'),
                download_data.get('like_count'),
                download_data.get('description')
            ))
            
            conn.commit()
            download_id = cursor.lastrowid
            logging.info(f"Download adicionado ao histórico: ID {download_id}")
            return download_id
            
        except Exception as e:
            conn.rollback()
            logging.error(f"Erro ao adicionar download: {e}")
            raise
        finally:
            conn.close()
    
    def get_recent_downloads(self, limit=50):
        """Obtém downloads recentes para o histórico (método legado)"""
        return self.get_downloads_paginated(page=1, per_page=limit)['downloads']
    
    def get_downloads_paginated(self, page=1, per_page=50, filters=None):
        """Obtém downloads com paginação e filtros opcionais"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Construir query base
            base_query = """
                SELECT id, url, title, duration, resolution, file_size, 
                       download_path, status, thumbnail_url, uploader, 
                       view_count, like_count, description, download_date as timestamp
                FROM downloads
            """
            
            # Construir condições WHERE se houver filtros
            where_conditions = []
            params = []
            
            if filters:
                if filters.get('search_query'):
                    where_conditions.append("title LIKE ?")
                    params.append(f"%{filters['search_query']}%")
                
                if filters.get('resolution'):
                    where_conditions.append("resolution = ?")
                    params.append(filters['resolution'])
                
                if filters.get('status'):
                    where_conditions.append("status = ?")
                    params.append(filters['status'])
                
                if filters.get('date_from'):
                    where_conditions.append("download_date >= ?")
                    params.append(filters['date_from'])
                
                if filters.get('date_to'):
                    where_conditions.append("download_date <= ?")
                    params.append(filters['date_to'])
            
            # Montar query completa
            if where_conditions:
                base_query += " WHERE " + " AND ".join(where_conditions)
            
            # Adicionar ordenação e paginação
            offset = (page - 1) * per_page
            query = base_query + " ORDER BY download_date DESC LIMIT ? OFFSET ?"
            params.extend([per_page, offset])
            
            # Executar query principal
            cursor.execute(query, params)
            columns = [description[0] for description in cursor.description]
            downloads = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # Obter contagem total
            count_query = "SELECT COUNT(*) FROM downloads"
            if where_conditions:
                count_query += " WHERE " + " AND ".join(where_conditions)
            
            cursor.execute(count_query, params[:-2])  # Remover LIMIT e OFFSET dos parâmetros
            total_count = cursor.fetchone()[0]
            
            # Calcular informações de paginação
            total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
            
            return {
                'downloads': downloads,
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_previous': page > 1,
                    'has_next': page < total_pages
                }
            }
            
        except Exception as e:
            logging.error(f"Erro ao obter downloads paginados: {e}")
            return {
                'downloads': [],
                'pagination': {
                    'current_page': 1,
                    'per_page': per_page,
                    'total_count': 0,
                    'total_pages': 0,
                    'has_previous': False,
                    'has_next': False
                }
            }
        finally:
            conn.close()
    
    def get_total_downloads_count(self, filters=None):
        """Obtém contagem total de downloads com filtros opcionais"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = "SELECT COUNT(*) FROM downloads"
            params = []
            
            if filters:
                where_conditions = []
                
                if filters.get('search_query'):
                    where_conditions.append("title LIKE ?")
                    params.append(f"%{filters['search_query']}%")
                
                if filters.get('resolution'):
                    where_conditions.append("resolution = ?")
                    params.append(filters['resolution'])
                
                if filters.get('status'):
                    where_conditions.append("status = ?")
                    params.append(filters['status'])
                
                if where_conditions:
                    query += " WHERE " + " AND ".join(where_conditions)
            
            cursor.execute(query, params)
            return cursor.fetchone()[0]
            
        except Exception as e:
            logging.error(f"Erro ao obter contagem de downloads: {e}")
            return 0
        finally:
            conn.close()
    
    def clear_history(self):
        """Limpa todo o histórico de downloads"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM downloads")
            conn.commit()
            logging.info("Histórico de downloads limpo")
            return True
            
        except Exception as e:
            conn.rollback()
            logging.error(f"Erro ao limpar histórico: {e}")
            return False
        finally:
            conn.close()
    
    def get_download_by_id(self, download_id):
        """Obtém dados de um download específico pelo ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, url, title, resolution, download_path, file_size, 
                       download_date as timestamp, status
                FROM downloads 
                WHERE id = ?
            """, (download_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'url': row[1],
                    'title': row[2],
                    'resolution': row[3],
                    'download_path': row[4],
                    'file_size': row[5],
                    'timestamp': row[6],
                    'status': row[7]
                }
            return None
        except Exception as e:
            logging.error(f"Erro ao obter download por ID: {e}")
            return None
        finally:
            conn.close()
    
    def remove_download(self, download_id):
        """Remove um download específico do histórico"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM downloads WHERE id = ?", (download_id,))
            conn.commit()
            logging.info(f"Download removido: ID {download_id}")
            return True
        except Exception as e:
            logging.error(f"Erro ao remover download: {e}")
            return False
        finally:
            conn.close()
    
    def get_all_downloads_filtered(self, filters=None):
        """Obtém todos os downloads filtrados (sem paginação) para exportação"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Query base
            query = """
                SELECT id, url, title, resolution, download_path, file_size, 
                       download_date as timestamp, status
                FROM downloads
            """
            
            params = []
            conditions = []
            
            # Aplicar filtros se fornecidos
            if filters:
                if 'search_query' in filters:
                    conditions.append("(title LIKE ? OR url LIKE ?)")
                    search_term = f"%{filters['search_query']}%"
                    params.extend([search_term, search_term])
                
                if 'resolution' in filters:
                    conditions.append("resolution = ?")
                    params.append(filters['resolution'])
                
                if 'status' in filters:
                    conditions.append("status = ?")
                    params.append(filters['status'])
                
                if 'date_from' in filters:
                    conditions.append("download_date >= ?")
                    params.append(filters['date_from'])
                
                if 'date_to' in filters:
                    conditions.append("download_date <= ?")
                    params.append(filters['date_to'])
            
            # Adicionar condições WHERE se existirem
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            # Ordenar por data de download (mais recente primeiro)
            query += " ORDER BY download_date DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Converter para lista de dicionários
            downloads = []
            for row in rows:
                downloads.append({
                    'id': row[0],
                    'url': row[1],
                    'title': row[2],
                    'resolution': row[3],
                    'file_path': row[4],
                    'file_size': row[5],
                    'timestamp': row[6],
                    'status': row[7]
                })
            
            return downloads
            
        except Exception as e:
            logging.error(f"Erro ao obter downloads filtrados: {e}")
            return []
        finally:
            conn.close()
    
    def get_setting(self, key, default=None):
        """Obtém uma configuração"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else default
        except Exception as e:
            logging.error(f"Erro ao obter configuração {key}: {e}")
            return default
        finally:
            conn.close()
    
    def set_setting(self, key, value):
        """Define uma configuração"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at) 
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
            conn.commit()
            logging.info(f"Configuração salva: {key} = {value}")
        except Exception as e:
            logging.error(f"Erro ao salvar configuração {key}: {e}")
        finally:
            conn.close()