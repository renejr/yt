import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import os
from collections import defaultdict
import json
from utils import AppConstants

class AnalyticsManager:
    """
    Gerenciador de análise e estatísticas de downloads
    Responsável por calcular métricas, gerar relatórios e criar insights
    """
    
    def __init__(self, database_manager, log_manager):
        """
        Inicializa o gerenciador de análise
        
        Args:
            database_manager: Instância do DatabaseManager
            log_manager: Instância do LogManager
        """
        self.db_manager = database_manager
        self.log_manager = log_manager
        self.cache = {}
        self.cache_timeout = 300  # 5 minutos
        self.last_cache_update = {}
        
    def _is_cache_valid(self, key: str) -> bool:
        """
        Verifica se o cache para uma chave específica ainda é válido
        
        Args:
            key: Chave do cache
            
        Returns:
            bool: True se o cache é válido, False caso contrário
        """
        if key not in self.last_cache_update:
            return False
        
        elapsed = datetime.now() - self.last_cache_update[key]
        return elapsed.total_seconds() < self.cache_timeout
    
    def _update_cache(self, key: str, data: Any) -> None:
        """
        Atualiza o cache com novos dados
        
        Args:
            key: Chave do cache
            data: Dados para armazenar
        """
        self.cache[key] = data
        self.last_cache_update[key] = datetime.now()
    
    def get_download_statistics(self, period_days: int = 30) -> Dict[str, Any]:
        """
        Obtém estatísticas gerais de downloads
        
        Args:
            period_days: Período em dias para análise
            
        Returns:
            Dict com estatísticas de downloads
        """
        cache_key = f"download_stats_{period_days}"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        try:
            # Data de início do período
            start_date = datetime.now() - timedelta(days=period_days)
            start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
            
            # Consulta para estatísticas básicas
            query = """
            SELECT 
                COUNT(*) as total_downloads,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_downloads,
                COUNT(CASE WHEN status = 'error' THEN 1 END) as failed_downloads,
                SUM(CASE WHEN file_size IS NOT NULL THEN CAST(file_size AS INTEGER) ELSE 0 END) as total_size,
                AVG(CASE WHEN file_size IS NOT NULL THEN CAST(file_size AS INTEGER) ELSE 0 END) as avg_size,
                COUNT(DISTINCT uploader) as unique_channels,
                COUNT(CASE WHEN resolution LIKE '%music%' THEN 1 END) as audio_downloads,
                COUNT(CASE WHEN resolution NOT LIKE '%music%' THEN 1 END) as video_downloads
            FROM downloads 
            WHERE download_date >= ?
            """
            
            result = self.db_manager.execute_query(query, (start_date_str,))
            
            if result:
                stats = result[0]
                
                # Calcular taxa de sucesso
                success_rate = 0
                total_downloads = stats['total_downloads']
                successful_downloads = stats['successful_downloads']
                
                if total_downloads > 0:
                    success_rate = (successful_downloads / total_downloads) * 100
                
                # Converter tamanho para formato legível
                total_size = stats['total_size'] or 0
                avg_size = stats['avg_size'] or 0
                total_size_gb = total_size / (1024**3) if total_size else 0
                avg_size_mb = avg_size / (1024**2) if avg_size else 0
                
                statistics = {
                    'period_days': period_days,
                    'total_downloads': total_downloads,
                    'successful_downloads': successful_downloads,
                    'failed_downloads': stats['failed_downloads'],
                    'success_rate': round(success_rate, 2),
                    'total_size_gb': round(total_size_gb, 2),
                    'avg_size_mb': round(avg_size_mb, 2),
                    'unique_channels': stats['unique_channels'],
                    'audio_downloads': stats['audio_downloads'],
                    'video_downloads': stats['video_downloads']
                }
                
                self._update_cache(cache_key, statistics)
                return statistics
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao obter estatísticas de downloads: {e}")
        
        return {}
    
    def get_resolution_distribution(self, period_days: int = 30) -> Dict[str, int]:
        """
        Obtém distribuição de downloads por resolução
        
        Args:
            period_days: Período em dias para análise
            
        Returns:
            Dict com distribuição por resolução
        """
        cache_key = f"resolution_dist_{period_days}"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        try:
            start_date = datetime.now() - timedelta(days=period_days)
            start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
            
            query = """
            SELECT resolution, COUNT(*) as count
            FROM downloads 
            WHERE download_date >= ? AND status = 'completed'
            GROUP BY resolution
            ORDER BY count DESC
            """
            
            results = self.db_manager.execute_query(query, (start_date_str,))
            
            distribution = {}
            if results:
                for row in results:
                    resolution = row['resolution'] if row['resolution'] else 'Desconhecida'
                    count = row['count']
                    distribution[resolution] = count
            
            self._update_cache(cache_key, distribution)
            return distribution
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao obter distribuição por resolução: {e}")
            return {}
    
    def get_daily_download_trend(self, period_days: int = 30) -> Dict[str, List]:
        """
        Obtém tendência diária de downloads
        
        Args:
            period_days: Período em dias para análise
            
        Returns:
            Dict com listas de datas e contagens
        """
        cache_key = f"daily_trend_{period_days}"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        try:
            start_date = datetime.now() - timedelta(days=period_days)
            start_date_str = start_date.strftime('%Y-%m-%d')
            
            query = """
            SELECT DATE(download_date) as date, COUNT(*) as count
            FROM downloads 
            WHERE DATE(download_date) >= ?
            GROUP BY DATE(download_date)
            ORDER BY date
            """
            
            results = self.db_manager.execute_query(query, (start_date_str,))
            
            dates = []
            counts = []
            
            if results:
                for row in results:
                    dates.append(row['date'])
                    counts.append(row['count'])
            
            trend_data = {
                'dates': dates,
                'counts': counts
            }
            
            self._update_cache(cache_key, trend_data)
            return trend_data
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao obter tendência diária: {e}")
            return {'dates': [], 'counts': []}
    
    def get_top_channels(self, period_days: int = 30, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Obtém os canais mais baixados
        
        Args:
            period_days: Período em dias para análise
            limit: Número máximo de canais a retornar
            
        Returns:
            Lista de tuplas (canal, quantidade)
        """
        cache_key = f"top_channels_{period_days}_{limit}"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        try:
            start_date = datetime.now() - timedelta(days=period_days)
            start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
            
            query = """
            SELECT uploader, COUNT(*) as count
            FROM downloads 
            WHERE download_date >= ? AND status = 'completed' AND uploader IS NOT NULL
            GROUP BY uploader
            ORDER BY count DESC
            LIMIT ?
            """
            
            results = self.db_manager.execute_query(query, (start_date_str, limit))
            
            top_channels = []
            if results:
                for row in results:
                    channel = row['uploader'] if row['uploader'] else 'Canal Desconhecido'
                    count = row['count']
                    top_channels.append((channel, count))
            
            self._update_cache(cache_key, top_channels)
            return top_channels
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao obter top canais: {e}")
            return []
    
    def get_hourly_distribution(self, period_days: int = 30) -> Dict[int, int]:
        """
        Obtém distribuição de downloads por hora do dia
        
        Args:
            period_days: Período em dias para análise
            
        Returns:
            Dict com hora (0-23) e quantidade de downloads
        """
        cache_key = f"hourly_dist_{period_days}"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        try:
            start_date = datetime.now() - timedelta(days=period_days)
            start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
            
            query = """
            SELECT CAST(strftime('%H', download_date) AS INTEGER) as hour, COUNT(*) as count
            FROM downloads 
            WHERE download_date >= ?
            GROUP BY hour
            ORDER BY hour
            """
            
            results = self.db_manager.execute_query(query, (start_date_str,))
            
            # Inicializar todas as horas com 0
            distribution = {hour: 0 for hour in range(24)}
            
            if results:
                for row in results:
                    hour = row['hour']
                    count = row['count']
                    distribution[hour] = count
            
            self._update_cache(cache_key, distribution)
            return distribution
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao obter distribuição por hora: {e}")
            return {hour: 0 for hour in range(24)}
    
    def get_storage_analysis(self) -> Dict[str, Any]:
        """
        Analisa o uso de armazenamento por downloads
        
        Returns:
            Dict com análise de armazenamento
        """
        cache_key = "storage_analysis"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        try:
            # Análise por resolução
            query_resolution = """
            SELECT resolution, 
                   COUNT(*) as count,
                   SUM(CASE WHEN file_size IS NOT NULL THEN CAST(file_size AS INTEGER) ELSE 0 END) as total_size,
                   AVG(CASE WHEN file_size IS NOT NULL THEN CAST(file_size AS INTEGER) ELSE 0 END) as avg_size
            FROM downloads 
            WHERE status = 'completed' AND file_size IS NOT NULL
            GROUP BY resolution
            ORDER BY total_size DESC
            """
            
            resolution_results = self.db_manager.execute_query(query_resolution)
            
            # Análise por tipo (áudio/vídeo)
            query_type = """
            SELECT 
                CASE WHEN resolution LIKE '%music%' THEN 'Áudio' ELSE 'Vídeo' END as type,
                COUNT(*) as count,
                SUM(CASE WHEN file_size IS NOT NULL THEN CAST(file_size AS INTEGER) ELSE 0 END) as total_size
            FROM downloads 
            WHERE status = 'completed' AND file_size IS NOT NULL
            GROUP BY (CASE WHEN resolution LIKE '%music%' THEN 'Áudio' ELSE 'Vídeo' END)
            """
            
            type_results = self.db_manager.execute_query(query_type)
            
            analysis = {
                'by_resolution': [],
                'by_type': [],
                'total_files': 0,
                'total_size_gb': 0
            }
            
            total_size = 0
            total_files = 0
            
            if resolution_results:
                for row in resolution_results:
                    resolution = row['resolution'] if row['resolution'] else 'Desconhecida'
                    count = row['count']
                    size = row['total_size'] or 0
                    avg_size = row['avg_size'] or 0
                    
                    total_files += count
                    total_size += size
                    
                    analysis['by_resolution'].append({
                        'resolution': resolution,
                        'count': count,
                        'total_size_mb': round(size / (1024**2), 2),
                        'avg_size_mb': round(avg_size / (1024**2), 2)
                    })
            
            if type_results:
                for row in type_results:
                    type_name = row['type']
                    count = row['count']
                    size = row['total_size'] or 0
                    
                    analysis['by_type'].append({
                        'type': type_name,
                        'count': count,
                        'total_size_mb': round(size / (1024**2), 2)
                    })
            
            analysis['total_files'] = total_files
            analysis['total_size_gb'] = round(total_size / (1024**3), 2)
            
            self._update_cache(cache_key, analysis)
            return analysis
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao analisar armazenamento: {e}")
            return {
                'by_resolution': [],
                'by_type': [],
                'total_files': 0,
                'total_size_gb': 0
            }
    
    def clear_cache(self) -> None:
        """
        Limpa todo o cache de análise
        """
        self.cache.clear()
        self.last_cache_update.clear()
        self.log_manager.log_info("Cache de análise limpo")

class RecommendationEngine:
    """
    Motor de recomendações baseado no histórico de downloads
    """
    
    def __init__(self, analytics_manager, database_manager, log_manager):
        """
        Inicializa o motor de recomendações
        
        Args:
            analytics_manager: Instância do AnalyticsManager
            database_manager: Instância do DatabaseManager
            log_manager: Instância do LogManager
        """
        self.analytics = analytics_manager
        self.db_manager = database_manager
        self.log_manager = log_manager
    
    def get_resolution_recommendation(self) -> Dict[str, Any]:
        """
        Recomenda resolução baseada no histórico
        
        Returns:
            Dict com recomendação de resolução
        """
        try:
            distribution = self.analytics.get_resolution_distribution(period_days=90)
            
            if not distribution:
                return {
                    'recommended_resolution': '720p',
                    'reason': 'Resolução padrão recomendada',
                    'confidence': 0.5
                }
            
            # Encontrar resolução mais usada
            most_used = max(distribution.items(), key=lambda x: x[1])
            total_downloads = sum(distribution.values())
            
            confidence = most_used[1] / total_downloads if total_downloads > 0 else 0
            
            return {
                'recommended_resolution': most_used[0],
                'reason': f'Resolução mais utilizada ({most_used[1]} downloads)',
                'confidence': round(confidence, 2),
                'usage_percentage': round(confidence * 100, 1)
            }
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao gerar recomendação de resolução: {e}")
            return {
                'recommended_resolution': '720p',
                'reason': 'Erro ao analisar histórico',
                'confidence': 0.5
            }
    
    def get_optimal_download_time(self) -> Dict[str, Any]:
        """
        Recomenda melhor horário para downloads
        
        Returns:
            Dict com recomendação de horário
        """
        try:
            hourly_dist = self.analytics.get_hourly_distribution(period_days=30)
            
            if not hourly_dist or sum(hourly_dist.values()) == 0:
                return {
                    'recommended_hours': [22, 23, 0, 1, 2],
                    'reason': 'Horários de menor uso da internet',
                    'peak_hour': 20
                }
            
            # Encontrar horário de pico
            peak_hour = max(hourly_dist.items(), key=lambda x: x[1])[0]
            
            # Recomendar horários com menos downloads (assumindo menos congestionamento)
            sorted_hours = sorted(hourly_dist.items(), key=lambda x: x[1])
            recommended_hours = [hour for hour, count in sorted_hours[:5]]
            
            return {
                'recommended_hours': recommended_hours,
                'reason': 'Horários com menor atividade de download',
                'peak_hour': peak_hour,
                'peak_downloads': hourly_dist[peak_hour]
            }
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao gerar recomendação de horário: {e}")
            return {
                'recommended_hours': [22, 23, 0, 1, 2],
                'reason': 'Erro ao analisar padrões',
                'peak_hour': 20
            }
    
    def get_storage_recommendations(self) -> List[Dict[str, Any]]:
        """
        Gera recomendações de gerenciamento de armazenamento
        
        Returns:
            Lista de recomendações
        """
        recommendations = []
        
        try:
            storage_analysis = self.analytics.get_storage_analysis()
            stats = self.analytics.get_download_statistics(period_days=90)
            
            # Recomendação baseada no tamanho total
            if storage_analysis['total_size_gb'] > 10:
                recommendations.append({
                    'type': 'storage_cleanup',
                    'priority': 'high',
                    'title': 'Limpeza de Armazenamento',
                    'description': f'Você tem {storage_analysis["total_size_gb"]} GB em downloads. Considere remover arquivos antigos.',
                    'action': 'cleanup_old_files'
                })
            
            # Recomendação baseada na taxa de falha
            if stats.get('success_rate', 100) < 80:
                recommendations.append({
                    'type': 'download_optimization',
                    'priority': 'medium',
                    'title': 'Otimização de Downloads',
                    'description': f'Taxa de sucesso de {stats["success_rate"]}%. Verifique sua conexão ou tente resoluções menores.',
                    'action': 'check_connection'
                })
            
            # Recomendação baseada em resolução
            resolution_dist = self.analytics.get_resolution_distribution()
            if resolution_dist:
                high_res_count = sum(count for res, count in resolution_dist.items() 
                                   if any(quality in res.lower() for quality in ['1080p', '1440p', '4k', '2160p']))
                total_count = sum(resolution_dist.values())
                
                if high_res_count / total_count > 0.7 if total_count > 0 else False:
                    recommendations.append({
                        'type': 'resolution_optimization',
                        'priority': 'low',
                        'title': 'Otimização de Resolução',
                        'description': 'Você baixa principalmente em alta resolução. Considere 720p para economizar espaço.',
                        'action': 'suggest_lower_resolution'
                    })
            
            return recommendations
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao gerar recomendações de armazenamento: {e}")
            return []
    
    def get_channel_recommendations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Recomenda canais baseado no histórico
        
        Args:
            limit: Número máximo de recomendações
            
        Returns:
            Lista de recomendações de canais
        """
        try:
            top_channels = self.analytics.get_top_channels(period_days=90, limit=limit)
            
            recommendations = []
            for channel, count in top_channels:
                recommendations.append({
                    'channel': channel,
                    'download_count': count,
                    'reason': f'Canal frequentemente baixado ({count} downloads)',
                    'suggestion': 'Considere verificar novos vídeos deste canal'
                })
            
            return recommendations
            
        except Exception as e:
            self.log_manager.log_error(f"Erro ao gerar recomendações de canais: {e}")
            return []