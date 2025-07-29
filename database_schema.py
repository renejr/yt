import sqlite3
import os
import logging
from datetime import datetime

class DatabaseSchema:
    def __init__(self, db_path="youtube_downloader.db"):
        self.db_path = db_path
        self.current_version = 3  # Versão atual do schema
        
    def get_db_version(self):
        """Obtém a versão atual do banco de dados"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_version ORDER BY id DESC LIMIT 1")
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else 0
        except sqlite3.OperationalError:
            return 0
    
    def create_schema_version_table(self):
        """Cria tabela de controle de versão do schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def apply_migration(self, version, description, sql_commands):
        """Aplica uma migração específica"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Executa os comandos SQL da migração
            for command in sql_commands:
                cursor.execute(command)
            
            # Registra a versão aplicada
            cursor.execute(
                "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                (version, description)
            )
            
            conn.commit()
            logging.info(f"Migração v{version} aplicada: {description}")
            
        except Exception as e:
            conn.rollback()
            logging.error(f"Erro ao aplicar migração v{version}: {e}")
            raise
        finally:
            conn.close()
    
    def migrate_to_version_1(self):
        """Migração v1: Tabelas básicas"""
        commands = [
            """
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                title TEXT,
                duration TEXT,
                resolution TEXT,
                file_size TEXT,
                download_path TEXT,
                status TEXT DEFAULT 'completed',
                download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                thumbnail_url TEXT,
                uploader TEXT,
                view_count INTEGER,
                like_count INTEGER,
                description TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS download_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_end TIMESTAMP,
                total_downloads INTEGER DEFAULT 0,
                total_size_mb REAL DEFAULT 0,
                app_version TEXT
            )
            """
        ]
        self.apply_migration(1, "Criação das tabelas básicas", commands)
    
    def migrate_to_version_2(self):
        """Migração v2: Tabela de configurações"""
        commands = [
            """
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            INSERT OR IGNORE INTO settings (key, value, description) VALUES 
            ('default_download_path', '', 'Diretório padrão para downloads'),
            # Modificar linha 113 para usar 1080p como padrão
            ('default_resolution', '1080p', 'Resolução padrão para downloads'),
            ('auto_open_folder', 'false', 'Abrir pasta após download'),
            ('theme', 'light', 'Tema da interface')
            """
        ]
        self.apply_migration(2, "Adição da tabela de configurações", commands)
    
    def migrate_to_version_3(self):
        """Migração v3: Índices e otimizações"""
        commands = [
            "CREATE INDEX IF NOT EXISTS idx_downloads_date ON downloads(download_date)",
            "CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads(status)",
            "CREATE INDEX IF NOT EXISTS idx_downloads_url ON downloads(url)",
            """
            ALTER TABLE downloads ADD COLUMN error_message TEXT DEFAULT NULL
            """,
            """
            ALTER TABLE downloads ADD COLUMN retry_count INTEGER DEFAULT 0
            """
        ]
        self.apply_migration(3, "Adição de índices e campos de erro", commands)
    
    def initialize_database(self):
        """Inicializa e atualiza o banco de dados automaticamente"""
        logging.info("Iniciando verificação do schema do banco de dados...")
        
        # Cria tabela de controle de versão
        self.create_schema_version_table()
        
        # Obtém versão atual
        current_db_version = self.get_db_version()
        logging.info(f"Versão atual do banco: v{current_db_version}")
        logging.info(f"Versão alvo do schema: v{self.current_version}")
        
        # Aplica migrações necessárias
        if current_db_version < 1:
            self.migrate_to_version_1()
        
        if current_db_version < 2:
            self.migrate_to_version_2()
        
        if current_db_version < 3:
            self.migrate_to_version_3()
        
        if current_db_version < self.current_version:
            logging.info(f"Banco de dados atualizado para v{self.current_version}")
        else:
            logging.info("Banco de dados já está atualizado")
    
    def reset_database(self):
        """Remove o banco de dados (para desenvolvimento)"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            logging.info("Banco de dados removido")
    
    def backup_database(self):
        """Cria backup do banco de dados"""
        if os.path.exists(self.db_path):
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            import shutil
            shutil.copy2(self.db_path, backup_name)
            logging.info(f"Backup criado: {backup_name}")
            return backup_name
        return None