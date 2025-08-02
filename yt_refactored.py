#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Baixador de Vídeos do YouTube - Versão Refatorada
Aplicação desktop para download de vídeos do YouTube com interface gráfica

Versão: 2.1 Refatorada
Autor: [Seu Nome]
Data: 2024
"""

import os
import sys

# Adicionar diretório atual ao path para importações
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar módulos refatorados
from log_manager import LogManager
from download_manager import DownloadManager
from config_manager import ConfigManager
from history_manager import HistoryManager
from ui_components import MainApplication
from database_manager import DatabaseManager
from utils import AppConstants

def initialize_database():
    """
    Inicializa o banco de dados da aplicação
    
    Returns:
        DatabaseManager: Instância do gerenciador de banco de dados
    """
    try:
        db_manager = DatabaseManager()
        db_manager.initialize()
        return db_manager
    except Exception as e:
        print(f"Erro ao inicializar banco de dados: {e}")
        return None

def create_managers(db_manager):
    """
    Cria e configura todos os gerenciadores da aplicação
    
    Args:
        db_manager: Instância do DatabaseManager
        
    Returns:
        tuple: (log_manager, download_manager, config_manager, history_manager)
    """
    # Criar gerenciador de logs
    log_manager = LogManager()
    log_manager.log_info("Sistema de logging inicializado")
    
    # Criar gerenciador de configurações
    config_manager = ConfigManager(db_manager)
    log_manager.log_info("Gerenciador de configurações inicializado")
    
    # Criar gerenciador de histórico
    history_manager = HistoryManager(db_manager, log_manager)
    log_manager.log_info("Gerenciador de histórico inicializado")
    
    # Criar gerenciador de downloads
    download_manager = DownloadManager(log_manager)
    log_manager.log_info("Gerenciador de downloads inicializado")
    
    return log_manager, download_manager, config_manager, history_manager

def setup_error_handling(log_manager):
    """
    Configura tratamento global de erros
    
    Args:
        log_manager: Instância do LogManager
    """
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        log_manager.log_error(
            f"Erro não tratado: {exc_type.__name__}: {exc_value}",
            "Sistema"
        )
    
    sys.excepthook = handle_exception

def perform_startup_tasks(log_manager):
    """
    Executa tarefas de inicialização da aplicação
    
    Args:
        log_manager: Instância do LogManager
    """
    try:
        # Verificar e limpar logs antigos
        log_manager.limpar_logs_antigos()
        
        # Verificar se precisa rotacionar logs
        if log_manager.verificar_tamanho_log():
            log_manager.comprimir_e_rotacionar_log()
        
        log_manager.log_info("Tarefas de inicialização concluídas")
        
    except Exception as e:
        log_manager.log_error(e, "Erro nas tarefas de inicialização")

def main():
    """
    Função principal da aplicação
    """
    try:
        print(f"Iniciando {AppConstants.VERSION} - Versão Refatorada")
        print("Inicializando componentes...")
        
        # Inicializar banco de dados
        db_manager = initialize_database()
        if not db_manager:
            print("Erro crítico: Não foi possível inicializar o banco de dados")
            return 1
        
        # Criar gerenciadores
        log_manager, download_manager, config_manager, history_manager = create_managers(db_manager)
        
        # Configurar tratamento de erros
        setup_error_handling(log_manager)
        
        # Executar tarefas de inicialização
        perform_startup_tasks(log_manager)
        
        # Criar e executar aplicação principal
        log_manager.log_info("Criando interface gráfica")
        app = MainApplication(
            download_manager=download_manager,
            config_manager=config_manager,
            history_manager=history_manager,
            log_manager=log_manager
        )
        
        log_manager.log_info("Aplicação iniciada com sucesso")
        print("Interface gráfica carregada. Aplicação pronta para uso.")
        
        # Iniciar loop principal
        app.run()
        
        # Cleanup ao sair
        log_manager.log_info("Aplicação encerrada normalmente")
        return 0
        
    except KeyboardInterrupt:
        print("\nAplicação interrompida pelo usuário")
        return 0
    except Exception as e:
        print(f"Erro crítico na aplicação: {e}")
        return 1

def check_dependencies():
    """
    Verifica se todas as dependências estão instaladas
    
    Returns:
        bool: True se todas as dependências estão disponíveis
    """
    required_modules = [
        'yt_dlp',
        'py7zr',
        'tkinter'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print("Erro: Módulos necessários não encontrados:")
        for module in missing_modules:
            print(f"  - {module}")
        print("\nInstale as dependências com: pip install -r requirements.txt")
        return False
    
    return True

def check_ffmpeg():
    """
    Verifica se o FFmpeg está disponível
    
    Returns:
        bool: True se FFmpeg está disponível
    """
    try:
        from utils import AppUtils
        ffmpeg_path = AppUtils.get_ffmpeg_path()
        if os.path.exists(ffmpeg_path):
            print(f"FFmpeg encontrado: {ffmpeg_path}")
            return True
        else:
            print(f"Aviso: FFmpeg não encontrado em {ffmpeg_path}")
            return False
    except Exception as e:
        print(f"Erro ao verificar FFmpeg: {e}")
        return False

if __name__ == "__main__":
    # Verificar dependências antes de iniciar
    if not check_dependencies():
        sys.exit(1)
    
    # Verificar FFmpeg (aviso, não crítico)
    check_ffmpeg()
    
    # Executar aplicação
    exit_code = main()
    sys.exit(exit_code)