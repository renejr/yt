#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para habilitar a API REST no banco de dados
"""

import sys
import os

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database_manager import DatabaseManager
from config_manager import ConfigManager

def enable_api():
    """
    Habilita a API REST no banco de dados
    """
    try:
        print("Inicializando banco de dados...")
        db_manager = DatabaseManager()
        db_manager.initialize()
        
        print("Criando gerenciador de configurações...")
        config_manager = ConfigManager(db_manager)
        
        print("Habilitando API REST...")
        success = config_manager.save_api_enabled(True)
        
        if success:
            print("✅ API REST habilitada com sucesso!")
            print(f"Host: {config_manager.get_api_host()}")
            print(f"Porta: {config_manager.get_api_port()}")
            print(f"Debug: {config_manager.get_api_debug()}")
            print("\nReinicie a aplicação para que as mudanças tenham efeito.")
        else:
            print("❌ Erro ao habilitar API REST")
            return 1
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = enable_api()
    sys.exit(exit_code)