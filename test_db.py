#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar o estado do banco de dados e os status dos downloads
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_manager import DatabaseManager
from log_manager import LogManager

def check_database():
    """Verifica o estado do banco de dados"""
    
    db_manager = DatabaseManager()
    db_manager.initialize()
    
    print("=== VERIFICAÇÃO DO BANCO DE DADOS ===")
    
    # Verificar total de downloads
    result = db_manager.execute_query("SELECT COUNT(*) as total FROM downloads")
    if result:
        total = result[0]['total']
        print(f"Total de downloads na tabela: {total}")
    
    # Verificar status únicos
    result = db_manager.execute_query("SELECT DISTINCT status, COUNT(*) as count FROM downloads GROUP BY status")
    print("\nStatus encontrados:")
    if result:
        for row in result:
            print(f"  - {row['status']}: {row['count']} registros")
    
    # Verificar alguns registros recentes
    result = db_manager.execute_query("""
        SELECT title, status, resolution, file_size, download_date 
        FROM downloads 
        ORDER BY download_date DESC 
        LIMIT 5
    """)
    
    print("\nÚltimos 5 downloads:")
    if result:
        for i, row in enumerate(result, 1):
            print(f"  {i}. {row['title'][:50]}...")
            print(f"     Status: {row['status']}, Resolução: {row['resolution']}")
            print(f"     Tamanho: {row['file_size']}, Data: {row['download_date']}")
            print()
    
    # Verificar se há registros com status 'completed'
    result = db_manager.execute_query("SELECT COUNT(*) as total FROM downloads WHERE status = 'completed'")
    if result:
        completed = result[0]['total']
        print(f"Downloads com status 'completed': {completed}")
    
    # Verificar outros possíveis status
    possible_status = ['Concluído', 'concluído', 'success', 'Success', 'COMPLETED']
    for status in possible_status:
        result = db_manager.execute_query("SELECT COUNT(*) as total FROM downloads WHERE status = ?", (status,))
        if result and result[0]['total'] > 0:
            print(f"Downloads com status '{status}': {result[0]['total']}")

if __name__ == "__main__":
    check_database()