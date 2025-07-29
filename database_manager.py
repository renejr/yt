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
        """Obtém downloads recentes para o histórico"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, url, title, duration, resolution, file_size, 
                       download_path, status, thumbnail_url, uploader, 
                       view_count, like_count, description, download_date as timestamp
                FROM downloads 
                ORDER BY download_date DESC 
                LIMIT ?
            """, (limit,))
            
            columns = [description[0] for description in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return results
            
        except Exception as e:
            logging.error(f"Erro ao obter downloads recentes: {e}")
            return []
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