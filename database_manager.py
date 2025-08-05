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
    
    def get_downloads_by_period(self, period_days=30):
        """Obtém downloads de um período específico"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT * FROM downloads 
                WHERE download_date >= datetime('now', '-{} days')
                ORDER BY download_date DESC
            """.format(period_days)
            
            cursor.execute(query)
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
            
        except Exception as e:
            logging.error(f"Erro ao obter downloads por período: {e}")
            return []
        finally:
            conn.close()
    
    def get_downloads_statistics_summary(self):
        """Obtém resumo estatístico dos downloads"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                    COUNT(CASE WHEN status = 'error' THEN 1 END) as failed,
                    COUNT(CASE WHEN status = 'downloading' THEN 1 END) as in_progress,
                    SUM(CASE WHEN file_size IS NOT NULL THEN file_size ELSE 0 END) as total_size,
                    COUNT(DISTINCT uploader) as unique_channels
                FROM downloads
            """
            
            cursor.execute(query)
            result = cursor.fetchone()
            
            if result:
                return {
                    'total': result[0],
                    'completed': result[1],
                    'failed': result[2],
                    'in_progress': result[3],
                    'total_size': result[4],
                    'unique_channels': result[5]
                }
            
            return {}
            
        except Exception as e:
            logging.error(f"Erro ao obter resumo estatístico: {e}")
            return {}
        finally:
            conn.close()
    
    def get_resolution_statistics(self):
        """Obtém estatísticas por resolução"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT 
                    resolution,
                    COUNT(*) as count,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                    SUM(CASE WHEN file_size IS NOT NULL THEN file_size ELSE 0 END) as total_size,
                    AVG(CASE WHEN file_size IS NOT NULL THEN file_size ELSE 0 END) as avg_size
                FROM downloads
                WHERE resolution IS NOT NULL
                GROUP BY resolution
                ORDER BY count DESC
            """
            
            cursor.execute(query)
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
            
        except Exception as e:
            logging.error(f"Erro ao obter estatísticas por resolução: {e}")
            return []
        finally:
            conn.close()
    
    def get_channel_statistics(self, limit=20):
        """Obtém estatísticas por canal"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT 
                    uploader as channel,
                    COUNT(*) as download_count,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_count,
                    SUM(CASE WHEN file_size IS NOT NULL THEN file_size ELSE 0 END) as total_size,
                    MAX(download_date) as last_download
                FROM downloads
                WHERE uploader IS NOT NULL AND uploader != ''
                GROUP BY uploader
                ORDER BY download_count DESC
                LIMIT ?
            """
            
            cursor.execute(query, (limit,))
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
            
        except Exception as e:
            logging.error(f"Erro ao obter estatísticas por canal: {e}")
            return []
        finally:
            conn.close()
    
    def get_daily_download_counts(self, days=30):
        """Obtém contagem diária de downloads"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT 
                    DATE(download_date) as date,
                    COUNT(*) as total_downloads,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_downloads,
                    SUM(CASE WHEN file_size IS NOT NULL THEN file_size ELSE 0 END) as total_size
                FROM downloads
                WHERE download_date >= datetime('now', '-{} days')
                GROUP BY DATE(download_date)
                ORDER BY date DESC
            """.format(days)
            
            cursor.execute(query)
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
            
        except Exception as e:
            logging.error(f"Erro ao obter contagens diárias: {e}")
            return []
        finally:
            conn.close()
    
    def get_hourly_download_pattern(self):
        """Obtém padrão de downloads por hora do dia"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT 
                    CAST(strftime('%H', download_date) AS INTEGER) as hour,
                    COUNT(*) as download_count,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_count
                FROM downloads
                WHERE download_date >= datetime('now', '-30 days')
                GROUP BY hour
                ORDER BY hour
            """
            
            cursor.execute(query)
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
            
        except Exception as e:
            logging.error(f"Erro ao obter padrão por hora: {e}")
            return []
        finally:
            conn.close()
    
    def get_file_size_distribution(self):
        """Obtém distribuição de tamanhos de arquivo"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT 
                    CASE 
                        WHEN file_size < 10485760 THEN 'Pequeno (< 10MB)'
                        WHEN file_size < 104857600 THEN 'Médio (10-100MB)'
                        WHEN file_size < 1073741824 THEN 'Grande (100MB-1GB)'
                        ELSE 'Muito Grande (> 1GB)'
                    END as size_category,
                    COUNT(*) as count,
                    SUM(file_size) as total_size
                FROM downloads
                WHERE file_size IS NOT NULL AND status = 'completed'
                GROUP BY size_category
                ORDER BY 
                    CASE size_category
                        WHEN 'Pequeno (< 10MB)' THEN 1
                        WHEN 'Médio (10-100MB)' THEN 2
                        WHEN 'Grande (100MB-1GB)' THEN 3
                        WHEN 'Muito Grande (> 1GB)' THEN 4
                    END
            """
            
            cursor.execute(query)
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
            
        except Exception as e:
            logging.error(f"Erro ao obter distribuição de tamanhos: {e}")
            return []
        finally:
            conn.close()
    
    def get_download_success_rate_by_resolution(self):
        """Obtém taxa de sucesso por resolução"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT 
                    resolution,
                    COUNT(*) as total_attempts,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful,
                    ROUND(
                        (COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0) / COUNT(*), 
                        2
                    ) as success_rate
                FROM downloads
                WHERE resolution IS NOT NULL
                GROUP BY resolution
                HAVING COUNT(*) >= 5
                ORDER BY success_rate DESC
            """
            
            cursor.execute(query)
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
            
        except Exception as e:
            logging.error(f"Erro ao obter taxa de sucesso por resolução: {e}")
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
    
    def execute_query(self, query, params=None):
        """Executa uma consulta SQL customizada e retorna os resultados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Se é uma consulta SELECT, retorna os resultados
            if query.strip().upper().startswith('SELECT'):
                columns = [description[0] for description in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            else:
                # Para INSERT, UPDATE, DELETE
                conn.commit()
                return cursor.rowcount
                
        except Exception as e:
            logging.error(f"Erro ao executar consulta: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()