#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitários da API REST - YouTube Downloader
Funções auxiliares para formatação de respostas, validação e logging

Versão: 1.0
Data: 2024
"""

import json
import logging
import traceback
from datetime import datetime
from functools import wraps
from typing import Dict, Any, Optional, Union, List
from flask import request, jsonify, Response
from api_config import APIConfig

class APIResponse:
    """Classe para padronização de respostas da API"""
    
    @staticmethod
    def success(data: Any = None, message: str = "Success", status_code: int = 200) -> tuple[Dict[str, Any], int]:
        """
        Cria resposta de sucesso padronizada
        
        Args:
            data (Any): Dados a serem retornados
            message (str): Mensagem de sucesso
            status_code (int): Código de status HTTP
            
        Returns:
            tuple[Dict[str, Any], int]: (resposta, código de status)
        """
        response = {
            "status": "success",
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": data
        }
        return response, status_code
    
    @staticmethod
    def error(message: str, code: str = "GENERIC_ERROR", status_code: int = 400, details: Any = None) -> tuple[Dict[str, Any], int]:
        """
        Cria resposta de erro padronizada
        
        Args:
            message (str): Mensagem de erro
            code (str): Código do erro
            status_code (int): Código de status HTTP
            details (Any): Detalhes adicionais do erro
            
        Returns:
            tuple[Dict[str, Any], int]: (resposta, código de status)
        """
        response = {
            "status": "error",
            "error": {
                "code": code,
                "message": message,
                "details": details
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        return response, status_code
    
    @staticmethod
    def validation_error(errors: Dict[str, List[str]]) -> tuple[Dict[str, Any], int]:
        """
        Cria resposta de erro de validação
        
        Args:
            errors (Dict[str, List[str]]): Erros de validação por campo
            
        Returns:
            tuple[Dict[str, Any], int]: (resposta, código de status)
        """
        return APIResponse.error(
            message="Dados de entrada inválidos",
            code="VALIDATION_ERROR",
            status_code=APIConfig.HTTP_STATUS["BAD_REQUEST"],
            details={"validation_errors": errors}
        )

class APIValidator:
    """Classe para validação de dados de entrada"""
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Valida se a URL é válida para download
        
        Args:
            url (str): URL a ser validada
            
        Returns:
            bool: True se válida, False caso contrário
        """
        if not url or not isinstance(url, str):
            return False
        
        # Verificar se contém domínios suportados
        supported_domains = [
            "youtube.com", "youtu.be", "m.youtube.com",
            "www.youtube.com", "music.youtube.com"
        ]
        
        url_lower = url.lower()
        return any(domain in url_lower for domain in supported_domains)
    
    @staticmethod
    def validate_resolution(resolution: str) -> bool:
        """
        Valida se a resolução é suportada
        
        Args:
            resolution (str): Resolução a ser validada
            
        Returns:
            bool: True se válida, False caso contrário
        """
        if not resolution or not isinstance(resolution, str):
            return False
        
        valid_resolutions = [
            "144p", "240p", "360p", "480p", "720p", "1080p", "1440p", "2160p",
            "best", "worst", "bestaudio", "worstaudio"
        ]
        
        return resolution in valid_resolutions
    
    @staticmethod
    def validate_download_id(download_id: str) -> bool:
        """
        Valida se o ID do download é válido
        
        Args:
            download_id (str): ID do download
            
        Returns:
            bool: True se válido, False caso contrário
        """
        if not download_id or not isinstance(download_id, str):
            return False
        
        # ID deve ter pelo menos 1 caractere e ser alfanumérico
        return download_id.isalnum() and len(download_id) > 0
    
    @staticmethod
    def validate_pagination(page: int, per_page: int) -> tuple[bool, Optional[str]]:
        """
        Valida parâmetros de paginação
        
        Args:
            page (int): Número da página
            per_page (int): Items por página
            
        Returns:
            tuple[bool, Optional[str]]: (válido, mensagem de erro)
        """
        if not isinstance(page, int) or page < 1:
            return False, "Página deve ser um número inteiro maior que 0"
        
        if not isinstance(per_page, int) or per_page < 1 or per_page > 100:
            return False, "Items por página deve ser entre 1 e 100"
        
        return True, None

class APILogger:
    """Classe para logging específico da API"""
    
    def __init__(self, log_manager=None):
        """
        Inicializa o logger da API
        
        Args:
            log_manager: Instância do LogManager da aplicação
        """
        self.log_manager = log_manager
        self.logger = logging.getLogger("api")
    
    def log_request(self, endpoint: str, method: str, ip: str, user_agent: str = None):
        """
        Registra requisição da API
        
        Args:
            endpoint (str): Endpoint acessado
            method (str): Método HTTP
            ip (str): IP do cliente
            user_agent (str): User agent do cliente
        """
        message = f"API Request: {method} {endpoint} from {ip}"
        if user_agent:
            message += f" - {user_agent}"
        
        if self.log_manager:
            self.log_manager.log_info(message)
        else:
            self.logger.info(message)
    
    def log_response(self, endpoint: str, status_code: int, response_time: float):
        """
        Registra resposta da API
        
        Args:
            endpoint (str): Endpoint acessado
            status_code (int): Código de status da resposta
            response_time (float): Tempo de resposta em segundos
        """
        message = f"API Response: {endpoint} - {status_code} ({response_time:.3f}s)"
        
        if self.log_manager:
            if status_code >= 400:
                self.log_manager.log_error(message)
            else:
                self.log_manager.log_info(message)
        else:
            if status_code >= 400:
                self.logger.error(message)
            else:
                self.logger.info(message)
    
    def log_error(self, endpoint: str, error: Exception, request_data: Dict = None):
        """
        Registra erro da API
        
        Args:
            endpoint (str): Endpoint onde ocorreu o erro
            error (Exception): Exceção ocorrida
            request_data (Dict): Dados da requisição
        """
        error_message = f"API Error in {endpoint}: {str(error)}"
        if request_data:
            error_message += f" - Request data: {json.dumps(request_data, default=str)}"
        
        error_message += f"\nTraceback: {traceback.format_exc()}"
        
        if self.log_manager:
            self.log_manager.log_error(error_message)
        else:
            self.logger.error(error_message)

def log_api_request(log_manager=None):
    """
    Decorator para logging automático de requisições da API
    
    Args:
        log_manager: Instância do LogManager
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            api_logger = APILogger(log_manager)
            
            # Log da requisição
            endpoint = request.endpoint or "unknown"
            method = request.method
            ip = request.remote_addr or "unknown"
            user_agent = request.headers.get("User-Agent")
            
            api_logger.log_request(endpoint, method, ip, user_agent)
            
            try:
                # Executar função
                result = func(*args, **kwargs)
                
                # Calcular tempo de resposta
                end_time = datetime.utcnow()
                response_time = (end_time - start_time).total_seconds()
                
                # Determinar status code
                status_code = 200
                if isinstance(result, tuple) and len(result) >= 2:
                    status_code = result[1]
                elif hasattr(result, 'status_code'):
                    status_code = result.status_code
                
                # Log da resposta
                api_logger.log_response(endpoint, status_code, response_time)
                
                return result
                
            except Exception as e:
                # Log do erro
                request_data = {}
                if request.is_json:
                    request_data = request.get_json(silent=True) or {}
                elif request.form:
                    request_data = dict(request.form)
                
                api_logger.log_error(endpoint, e, request_data)
                
                # Re-raise a exceção
                raise
        
        return wrapper
    return decorator

def require_json():
    """
    Decorator que exige que a requisição tenha Content-Type application/json
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return APIResponse.error(
                    message="Content-Type deve ser application/json",
                    code="INVALID_CONTENT_TYPE",
                    status_code=APIConfig.HTTP_STATUS["BAD_REQUEST"]
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator

def handle_api_errors(func):
    """
    Decorator para tratamento automático de erros da API
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            return APIResponse.error(
                message=str(e),
                code="INVALID_INPUT",
                status_code=APIConfig.HTTP_STATUS["BAD_REQUEST"]
            )
        except KeyError as e:
            return APIResponse.error(
                message=f"Campo obrigatório ausente: {str(e)}",
                code="MISSING_FIELD",
                status_code=APIConfig.HTTP_STATUS["BAD_REQUEST"]
            )
        except Exception as e:
            # Temporariamente mostrar detalhes do erro para debug
            import traceback
            error_details = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc()
            }
            return APIResponse.error(
                message="Erro interno do servidor",
                code="INTERNAL_ERROR",
                status_code=APIConfig.HTTP_STATUS["INTERNAL_ERROR"],
                details=error_details
            )
    return wrapper

def format_download_data(download_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formata dados de download para resposta da API
    
    Args:
        download_data (Dict[str, Any]): Dados brutos do download
        
    Returns:
        Dict[str, Any]: Dados formatados
    """
    if not download_data:
        return {}
    
    # Converter timestamps para ISO format
    formatted_data = download_data.copy()
    
    timestamp_fields = ['download_date', 'created_at', 'updated_at']
    for field in timestamp_fields:
        if field in formatted_data and formatted_data[field]:
            if isinstance(formatted_data[field], str):
                try:
                    # Tentar converter string para datetime e depois para ISO
                    dt = datetime.fromisoformat(formatted_data[field].replace('Z', '+00:00'))
                    formatted_data[field] = dt.isoformat() + "Z"
                except:
                    pass  # Manter valor original se conversão falhar
    
    # Garantir que campos numéricos sejam números
    numeric_fields = ['file_size', 'duration', 'download_id']
    for field in numeric_fields:
        if field in formatted_data and formatted_data[field] is not None:
            try:
                if field == 'file_size' or field == 'duration':
                    formatted_data[field] = float(formatted_data[field])
                else:
                    formatted_data[field] = int(formatted_data[field])
            except (ValueError, TypeError):
                pass  # Manter valor original se conversão falhar
    
    return formatted_data

def format_video_info(video_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formata informações de vídeo para resposta da API
    
    Args:
        video_info (Dict[str, Any]): Informações brutas do vídeo
        
    Returns:
        Dict[str, Any]: Informações formatadas
    """
    if not video_info:
        return {}
    
    formatted_info = {
        "title": video_info.get("title", "Título não disponível"),
        "duration": video_info.get("duration", 0),
        "uploader": video_info.get("uploader", "Desconhecido"),
        "upload_date": video_info.get("upload_date"),
        "view_count": video_info.get("view_count", 0),
        "like_count": video_info.get("like_count", 0),
        "description": video_info.get("description", ""),
        "thumbnail": video_info.get("thumbnail"),
        "formats": video_info.get("formats", []),
        "url": video_info.get("webpage_url", video_info.get("url", ""))
    }
    
    # Formatar data de upload
    if formatted_info["upload_date"]:
        try:
            upload_date = datetime.strptime(str(formatted_info["upload_date"]), "%Y%m%d")
            formatted_info["upload_date"] = upload_date.isoformat() + "Z"
        except:
            formatted_info["upload_date"] = None
    
    return formatted_info