from doctest import debug
import time
import threading
from typing import Dict, List, Optional, Union
from datetime import datetime
import logging
from database_manager import DatabaseManager

class BandwidthTracker:
    """
    Classe para rastrear e armazenar dados de velocidade de download
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.current_download_data = {}
        self.speed_samples = []
        self.download_start_time = None
        self.lock = threading.Lock()
        
    def start_tracking(self, download_id: str):
        """
        Inicia o rastreamento de velocidade para um download
        
        Args:
            download_id: ID único do download
        """
        with self.lock:
            self.current_download_data[download_id] = {
                'start_time': time.time(),
                'speeds': [],
                'peak_speed': 0.0,
                'total_bytes': 0,
                'downloaded_bytes': 0
            }
            logging.info(f"Iniciado rastreamento de velocidade para download {download_id}")
    
    def update_speed(self, download_id: str, speed_str: Union[str, float, int], downloaded_bytes: int = 0, total_bytes: int = 0):
        """
        Atualiza os dados de velocidade para um download
        
        Args:
            download_id: ID do download
            speed_str: String de velocidade (ex: "1.5MiB/s") ou valor numérico em bytes/s
            downloaded_bytes: Bytes baixados até agora
            total_bytes: Total de bytes do arquivo
        """
        if download_id not in self.current_download_data:
            logging.warning(f"Download ID {download_id} não encontrado no rastreamento")
            return
            
        try:
            # Log da entrada para debug
            logging.debug(f"update_speed chamado: download_id={download_id}, speed_str={speed_str}, downloaded={downloaded_bytes}, total={total_bytes}")
            
            if isinstance(speed_str, (int, float)):
                # Converter bytes/s para Mbps
                speed_mbps = (speed_str * 8) / 1_000_000
                logging.debug(f"Velocidade numérica convertida: {speed_str} bytes/s → {speed_mbps:.2f} Mbps")
            else:
                # Converter string de velocidade para Mbps
                speed_mbps = self._parse_speed_string(speed_str)
                logging.debug(f"Velocidade string convertida: '{speed_str}' → {speed_mbps:.2f} Mbps")
            
            # Só adicionar velocidades válidas (> 0) para evitar distorcer a média
            if speed_mbps > 0:
                with self.lock:
                    data = self.current_download_data[download_id]
                    data['speeds'].append(speed_mbps)
                    data['downloaded_bytes'] = downloaded_bytes
                    data['total_bytes'] = total_bytes
                    
                    # Atualizar velocidade de pico
                    if speed_mbps > data['peak_speed']:
                        data['peak_speed'] = speed_mbps
                    
                    logging.debug(f"Velocidade adicionada: {speed_mbps:.2f} Mbps. Total de amostras: {len(data['speeds'])}")
            else:
                logging.debug(f"Velocidade inválida ignorada: {speed_mbps} Mbps (entrada: {speed_str})")
                    
        except Exception as e:
            logging.error(f"Erro ao atualizar velocidade: {e}")
            import traceback
            logging.error(traceback.format_exc())
    
    def finish_tracking(self, download_id: str, db_download_id: int):
        """
        Finaliza o rastreamento e salva os dados no banco
        
        Args:
            download_id: ID do download
            db_download_id: ID do download no banco de dados
        """
        logging.debug(f"finish_tracking chamado: download_id={download_id}, db_download_id={db_download_id}")
        
        if download_id not in self.current_download_data:
            logging.warning(f"Download ID {download_id} não encontrado no rastreamento ao finalizar")
            return
            
        try:
            with self.lock:
                data = self.current_download_data[download_id]
                logging.warning(f"finish_tracking XXX: data={data}")
                end_time = time.time()
                duration = end_time - data['start_time']
                
                logging.debug(f"Dados do download antes de finalizar: speeds={len(data['speeds'])} amostras, peak_speed={data['peak_speed']:.2f} Mbps")
                
                # Calcular estatísticas
                speeds = data['speeds']
                avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
                peak_speed = data['peak_speed']
                
                if speeds:
                    logging.debug(f"Estatísticas calculadas: avg_speed={avg_speed:.2f} Mbps, peak_speed={peak_speed:.2f} Mbps")
                else:
                    logging.warning(f"Nenhuma amostra de velocidade encontrada para download {download_id}")
                
                logging.debug(f"Duração do download: {duration:.2f} segundos")
                
                # Salvar no banco de dados
                logging.debug(f"Salvando no banco: db_download_id={db_download_id}, avg_speed={avg_speed:.2f}, peak_speed={peak_speed:.2f}, duration={duration:.2f}")
                self._save_bandwidth_data(
                    db_download_id,
                    avg_speed,
                    peak_speed,
                    duration
                )
                
                # Limpar dados temporários
                del self.current_download_data[download_id]
                
                logging.info(f"Dados de velocidade salvos para download {download_id}: "
                           f"Avg: {avg_speed:.2f} Mbps, Peak: {peak_speed:.2f} Mbps, "
                           f"Duration: {duration:.1f}s")
                logging.debug(f"Rastreamento finalizado com sucesso para download {download_id}")
                
        except Exception as e:
            logging.error(f"Erro ao finalizar rastreamento: {e}")
            import traceback
            logging.error(traceback.format_exc())
    
    def _parse_speed_string(self, speed_str: str) -> float:
        """
        Converte string de velocidade para Mbps
        
        Args:
            speed_str: String como "1.5MiB/s", "2.3MB/s", etc.
            
        Returns:
            Velocidade em Mbps
        """
        if not speed_str or speed_str == 'N/A':
            return 0.0
            
        try:
            # Remover espaços e converter para minúsculo
            speed_str = speed_str.strip().lower()
            
            # Extrair número
            import re
            number_match = re.search(r'([0-9.]+)', speed_str)
            if not number_match:
                return 0.0
                
            speed_value = float(number_match.group(1))
            
            # Converter para Mbps baseado na unidade
            if 'kib/s' in speed_str or 'kb/s' in speed_str:
                # KiB/s para Mbps (1 KiB = 1024 bytes, 1 Mbps = 1,000,000 bits)
                return (speed_value * 1024 * 8) / 1_000_000
            elif 'mib/s' in speed_str:
                # MiB/s para Mbps (1 MiB = 1,048,576 bytes)
                return (speed_value * 1_048_576 * 8) / 1_000_000
            elif 'mb/s' in speed_str:
                # MB/s para Mbps (1 MB = 1,000,000 bytes)
                return speed_value * 8
            elif 'gib/s' in speed_str:
                # GiB/s para Mbps
                return (speed_value * 1_073_741_824 * 8) / 1_000_000
            elif 'gb/s' in speed_str:
                # GB/s para Mbps
                return speed_value * 8000
            else:
                # Assumir bytes/s se não especificado
                return (speed_value * 8) / 1_000_000
                
        except Exception as e:
            logging.error(f"Erro ao converter velocidade '{speed_str}': {e}")
            return 0.0
    
    def _save_bandwidth_data(self, download_id: int, avg_speed: float, peak_speed: float, duration: float):
        """
        Salva os dados de largura de banda no banco de dados
        
        Args:
            download_id: ID do download no banco
            avg_speed: Velocidade média em Mbps
            peak_speed: Velocidade de pico em Mbps
            duration: Duração do download em segundos
        """
        try:
            logging.debug(f"_save_bandwidth_data: Iniciando salvamento para download_id={download_id}")
            logging.debug(f"Valores a serem salvos: avg_speed={avg_speed:.2f}, peak_speed={peak_speed:.2f}, duration={duration:.2f}")
            
            import sqlite3
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE downloads 
                SET avg_speed_mbps = ?, 
                    peak_speed_mbps = ?, 
                    download_duration_seconds = ?,
                    download_speed_mbps = ?
                WHERE id = ?
            """, (avg_speed, peak_speed, int(duration), avg_speed, download_id))
            
            rows_affected = cursor.rowcount
            logging.debug(f"Linhas afetadas pela atualização: {rows_affected}")
            
            conn.commit()
            logging.info(f"Dados de largura de banda salvos para download {download_id}: avg={avg_speed:.2f} Mbps, peak={peak_speed:.2f} Mbps, duration={duration:.2f}s")
            
            # Verificar se os dados foram realmente salvos
            cursor.execute("SELECT avg_speed_mbps, peak_speed_mbps, download_duration_seconds, download_speed_mbps FROM downloads WHERE id = ?", (download_id,))
            result = cursor.fetchone()
            if result:
                logging.debug(f"Verificação pós-salvamento: avg_speed_mbps={result[0]}, peak_speed_mbps={result[1]}, download_duration_seconds={result[2]}, download_speed_mbps={result[3]}")
            else:
                logging.error(f"Download {download_id} não encontrado após tentativa de salvamento")
            
            conn.close()
            
        except Exception as e:
            logging.error(f"Erro ao salvar dados de largura de banda: {e}")
            import traceback
            logging.error(traceback.format_exc())
    
    def get_bandwidth_statistics(self, period_days: int = 30) -> Dict:
        """
        Obtém estatísticas de velocidade dos últimos downloads
        
        Args:
            period_days: Período em dias para análise
            
        Returns:
            Dicionário com estatísticas de velocidade
        """
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            query = """
            SELECT 
                AVG(avg_speed_mbps) as avg_speed,
                MAX(peak_speed_mbps) as max_speed,
                MIN(avg_speed_mbps) as min_speed,
                COUNT(*) as total_downloads,
                AVG(download_duration_seconds) as avg_duration
            FROM downloads 
            WHERE avg_speed_mbps IS NOT NULL 
            AND download_date >= datetime('now', '-{} days')
            """.format(period_days)
            
            cursor.execute(query)
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] is not None:
                return {
                    'avg_speed': round(result[0], 2),
                    'max_speed': round(result[1], 2),
                    'min_speed': round(result[2], 2),
                    'total_downloads': result[3],
                    'avg_duration': round(result[4], 1) if result[4] else 0
                }
            else:
                return {
                    'avg_speed': 0,
                    'max_speed': 0,
                    'min_speed': 0,
                    'total_downloads': 0,
                    'avg_duration': 0
                }
                
        except Exception as e:
            logging.error(f"Erro ao obter estatísticas de velocidade: {e}")
            return {
                'avg_speed': 0,
                'max_speed': 0,
                'min_speed': 0,
                'total_downloads': 0,
                'avg_duration': 0
            }
    
    def get_speed_trend_data(self, period_days: int = 30) -> Dict:
        """
        Obtém dados de tendência de velocidade ao longo do tempo
        
        Args:
            period_days: Período em dias
            
        Returns:
            Dicionário com dados de tendência
        """
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            query = """
            SELECT 
                DATE(download_date) as date,
                AVG(avg_speed_mbps) as avg_speed,
                MAX(peak_speed_mbps) as max_speed,
                COUNT(*) as download_count
            FROM downloads 
            WHERE avg_speed_mbps IS NOT NULL 
            AND download_date >= datetime('now', '-{} days')
            GROUP BY DATE(download_date)
            ORDER BY date
            """.format(period_days)
            
            cursor.execute(query)
            results = cursor.fetchall()
            conn.close()
            
            dates = []
            avg_speeds = []
            max_speeds = []
            counts = []
            
            for row in results:
                dates.append(row[0])
                avg_speeds.append(round(row[1], 2) if row[1] else 0)
                max_speeds.append(round(row[2], 2) if row[2] else 0)
                counts.append(row[3])
            
            return {
                'dates': dates,
                'avg_speeds': avg_speeds,
                'max_speeds': max_speeds,
                'counts': counts
            }
            
        except Exception as e:
            logging.error(f"Erro ao obter dados de tendência: {e}")
            return {
                'dates': [],
                'avg_speeds': [],
                'max_speeds': [],
                'counts': []
            }