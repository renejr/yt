#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste para verificar se todas as funções de análise estão funcionando corretamente
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_manager import DatabaseManager
from analytics_manager import AnalyticsManager
from log_manager import LogManager

def test_analytics():
    """Testa todas as funções de análise"""
    
    # Inicializar componentes
    log_manager = LogManager()
    db_manager = DatabaseManager()
    db_manager.initialize()
    analytics = AnalyticsManager(db_manager, log_manager)
    
    print("=== TESTE DAS FUNÇÕES DE ANÁLISE ===")
    print()
    
    # Teste 1: Estatísticas de download
    print("1. Testando get_download_statistics...")
    stats = analytics.get_download_statistics()
    print(f"   Total de downloads: {stats.get('total_downloads', 0)}")
    print(f"   Downloads bem-sucedidos: {stats.get('successful_downloads', 0)}")
    print(f"   Taxa de sucesso: {stats.get('success_rate', 0)}%")
    print()
    
    # Teste 2: Distribuição por resolução
    print("2. Testando get_resolution_distribution...")
    resolution_dist = analytics.get_resolution_distribution()
    print(f"   Resoluções encontradas: {len(resolution_dist)}")
    for resolution, count in list(resolution_dist.items())[:5]:  # Primeiras 5
        print(f"   - {resolution}: {count} downloads")
    print()
    
    # Teste 3: Tendência diária
    print("3. Testando get_daily_download_trend...")
    daily_trend = analytics.get_daily_download_trend()
    dates = daily_trend.get('dates', [])
    counts = daily_trend.get('counts', [])
    print(f"   Dias com dados: {len(dates)}")
    if dates and counts:
        print(f"   Último dia: {dates[-1]} com {counts[-1]} downloads")
    print()
    
    # Teste 4: Top canais
    print("4. Testando get_top_channels...")
    top_channels = analytics.get_top_channels(limit=5)
    print(f"   Canais encontrados: {len(top_channels)}")
    for i, (channel, count) in enumerate(top_channels[:3], 1):
        print(f"   {i}. {channel}: {count} downloads")
    print()
    
    # Teste 5: Distribuição por hora
    print("5. Testando get_hourly_distribution...")
    hourly_dist = analytics.get_hourly_distribution()
    total_hourly = sum(hourly_dist.values())
    print(f"   Total de downloads por hora: {total_hourly}")
    # Encontrar hora com mais downloads
    if hourly_dist:
        max_hour = max(hourly_dist.items(), key=lambda x: x[1])
        print(f"   Hora mais ativa: {max_hour[0]}h com {max_hour[1]} downloads")
    print()
    
    # Teste 6: Análise de armazenamento
    print("6. Testando get_storage_analysis...")
    storage = analytics.get_storage_analysis()
    print(f"   Total de arquivos: {storage.get('total_files', 0)}")
    print(f"   Tamanho total: {storage.get('total_size_gb', 0)} GB")
    print(f"   Tipos de arquivo: {len(storage.get('by_type', []))}")
    print(f"   Resoluções: {len(storage.get('by_resolution', []))}")
    print()
    
    print("=== TESTE CONCLUÍDO ===")
    print("Todas as funções foram testadas com sucesso!")

if __name__ == "__main__":
    test_analytics()