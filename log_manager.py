import os
import logging
import py7zr
from datetime import datetime, timedelta
import glob

class LogManager:
    """Gerenciador centralizado do sistema de logging com rotação automática"""
    
    def __init__(self, log_dir="logs", log_file="youtube_downloader.log", max_size_mb=250):
        """
        Inicializa o gerenciador de logs
        
        Args:
            log_dir (str): Diretório dos logs
            log_file (str): Nome do arquivo de log
            max_size_mb (int): Tamanho máximo do log em MB antes da rotação
        """
        self.log_dir = log_dir
        self.log_file = log_file
        self.max_size_mb = max_size_mb
        self.log_path = os.path.join(log_dir, log_file)
        
        # Garantir que a pasta logs existe
        self._ensure_log_directory()
        
        # Configurar logging
        self._setup_logging()
        
        # Verificar se precisa rotacionar
        if self.verificar_tamanho_log():
            self.comprimir_e_rotacionar_log()
    
    def _ensure_log_directory(self):
        """Garante que o diretório de logs existe"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def _setup_logging(self):
        """Configura o sistema de logging"""
        logging.basicConfig(
            filename=self.log_path,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            encoding='utf-8'
        )
    
    def log_info(self, message):
        """Log informações importantes"""
        logging.info(message)
        print(f"[INFO] {message}")
    
    def log_error(self, error, context=""):
        """Log erros com contexto"""
        error_msg = f"{context}: {str(error)}" if context else str(error)
        logging.error(error_msg)
        return self.get_friendly_error(error)
    
    def get_friendly_error(self, error):
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
    
    def verificar_tamanho_log(self):
        """Verifica se o arquivo de log excede o tamanho máximo"""
        if os.path.exists(self.log_path):
            tamanho_mb = os.path.getsize(self.log_path) / (1024 * 1024)
            return tamanho_mb >= self.max_size_mb
        return False
    
    def comprimir_e_rotacionar_log(self):
        """Comprime o log atual em 7z e cria um novo arquivo de log"""
        try:
            if not os.path.exists(self.log_path):
                return False
            
            # Gerar nome do arquivo comprimido com timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            arquivo_7z = os.path.join(self.log_dir, f"log_backup_{timestamp}.7z")
            
            # Comprimir o arquivo de log
            with py7zr.SevenZipFile(arquivo_7z, 'w') as archive:
                archive.write(self.log_path, os.path.basename(self.log_path))
            
            # Verificar se a compressão foi bem-sucedida
            if os.path.exists(arquivo_7z):
                tamanho_original = os.path.getsize(self.log_path) / (1024 * 1024)
                tamanho_comprimido = os.path.getsize(arquivo_7z) / (1024 * 1024)
                taxa_compressao = ((tamanho_original - tamanho_comprimido) / tamanho_original) * 100
                
                # Remover o arquivo de log original
                os.remove(self.log_path)
                
                # Reconfigurar o logging para criar um novo arquivo
                for handler in logging.root.handlers[:]:
                    logging.root.removeHandler(handler)
                
                self._setup_logging()
                
                # Log da rotação no novo arquivo
                self.log_info(f"Rotação de log realizada: {arquivo_7z}")
                self.log_info(f"Tamanho original: {tamanho_original:.2f}MB")
                self.log_info(f"Tamanho comprimido: {tamanho_comprimido:.2f}MB")
                self.log_info(f"Taxa de compressão: {taxa_compressao:.1f}%")
                
                return True
            else:
                self.log_error("Falha na compressão do arquivo de log", "Rotação de log")
                return False
                
        except Exception as e:
            self.log_error(e, "Erro durante rotação de log")
            return False
    
    def limpar_logs_antigos(self, dias_manter=30):
        """Remove arquivos de log comprimidos mais antigos que X dias"""
        try:
            # Buscar todos os arquivos de backup de log
            arquivos_backup = glob.glob(os.path.join(self.log_dir, "log_backup_*.7z"))
            data_limite = datetime.now() - timedelta(days=dias_manter)
            
            removidos = 0
            for arquivo in arquivos_backup:
                try:
                    # Extrair timestamp do nome do arquivo
                    nome_arquivo = os.path.basename(arquivo)
                    timestamp_str = nome_arquivo.replace("log_backup_", "").replace(".7z", "")
                    data_arquivo = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    if data_arquivo < data_limite:
                        os.remove(arquivo)
                        removidos += 1
                        self.log_info(f"Arquivo de log antigo removido: {arquivo}")
                except (ValueError, OSError) as e:
                    self.log_error(e, f"Erro ao processar arquivo {arquivo}")
            
            if removidos > 0:
                self.log_info(f"Limpeza concluída: {removidos} arquivo(s) de log antigo(s) removido(s)")
                
        except Exception as e:
            self.log_error(e, "Erro durante limpeza de logs antigos")
    
    def get_log_stats(self):
        """Retorna estatísticas dos logs"""
        stats = {
            'log_atual_existe': os.path.exists(self.log_path),
            'tamanho_atual_mb': 0,
            'backups_count': 0,
            'tamanho_total_backups_mb': 0
        }
        
        if stats['log_atual_existe']:
            stats['tamanho_atual_mb'] = os.path.getsize(self.log_path) / (1024 * 1024)
        
        # Contar backups
        arquivos_backup = glob.glob(os.path.join(self.log_dir, "log_backup_*.7z"))
        stats['backups_count'] = len(arquivos_backup)
        
        for arquivo in arquivos_backup:
            if os.path.exists(arquivo):
                stats['tamanho_total_backups_mb'] += os.path.getsize(arquivo) / (1024 * 1024)
        
        return stats