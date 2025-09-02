#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuração da API REST - YouTube Downloader
Contém constantes, configurações padrão e validadores para a API

Versão: 1.0
Data: 2024
"""

import os
from typing import Dict, Any, Optional

class APIConfig:
    """Configurações e constantes da API REST"""
    
    # Versão da API
    API_VERSION = "v1"
    API_PREFIX = f"/api/{API_VERSION}"
    
    # Configurações padrão do servidor
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 5000
    DEFAULT_DEBUG = False
    DEFAULT_ENABLED = False
    
    # Configurações de segurança
    DEFAULT_API_KEY_LENGTH = 32
    DEFAULT_RATE_LIMIT = "100/hour"  # 100 requisições por hora
    
    # Timeouts
    DEFAULT_REQUEST_TIMEOUT = 30  # segundos
    DEFAULT_DOWNLOAD_TIMEOUT = 3600  # 1 hora
    
    # Limites
    MAX_CONCURRENT_DOWNLOADS = 5
    MAX_PLAYLIST_SIZE = 100
    
    # Headers padrão
    DEFAULT_HEADERS = {
        "Content-Type": "application/json",
        "X-API-Version": API_VERSION,
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-API-Key"
    }
    
    # Códigos de status HTTP personalizados
    HTTP_STATUS = {
        "SUCCESS": 200,
        "CREATED": 201,
        "ACCEPTED": 202,
        "BAD_REQUEST": 400,
        "UNAUTHORIZED": 401,
        "FORBIDDEN": 403,
        "NOT_FOUND": 404,
        "METHOD_NOT_ALLOWED": 405,
        "CONFLICT": 409,
        "RATE_LIMITED": 429,
        "INTERNAL_ERROR": 500,
        "SERVICE_UNAVAILABLE": 503
    }
    
    # Mensagens de erro padrão
    ERROR_MESSAGES = {
        "INVALID_URL": "URL inválida fornecida",
        "DOWNLOAD_FAILED": "Falha no download do vídeo",
        "VIDEO_NOT_FOUND": "Vídeo não encontrado",
        "INVALID_RESOLUTION": "Resolução inválida especificada",
        "DOWNLOAD_IN_PROGRESS": "Download já está em progresso",
        "DOWNLOAD_NOT_FOUND": "Download não encontrado",
        "INVALID_API_KEY": "Chave de API inválida",
        "RATE_LIMIT_EXCEEDED": "Limite de taxa excedido",
        "INTERNAL_ERROR": "Erro interno do servidor",
        "INVALID_PARAMETERS": "Parâmetros inválidos fornecidos",
        "SERVICE_UNAVAILABLE": "Serviço temporariamente indisponível"
    }
    
    # Configurações de logging
    LOG_CONFIG = {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "max_file_size": 10 * 1024 * 1024,  # 10MB
        "backup_count": 5
    }
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """
        Retorna configuração padrão da API
        
        Returns:
            Dict[str, Any]: Dicionário com configurações padrão
        """
        return {
            "api_enabled": cls.DEFAULT_ENABLED,
            "api_host": cls.DEFAULT_HOST,
            "api_port": cls.DEFAULT_PORT,
            "api_debug": cls.DEFAULT_DEBUG,
            "api_rate_limit": cls.DEFAULT_RATE_LIMIT,
            "api_request_timeout": cls.DEFAULT_REQUEST_TIMEOUT,
            "api_download_timeout": cls.DEFAULT_DOWNLOAD_TIMEOUT,
            "api_max_concurrent_downloads": cls.MAX_CONCURRENT_DOWNLOADS,
            "api_max_playlist_size": cls.MAX_PLAYLIST_SIZE
        }
    
    @classmethod
    def validate_host(cls, host: str) -> bool:
        """
        Valida se o host é válido
        
        Args:
            host (str): Host a ser validado
            
        Returns:
            bool: True se válido, False caso contrário
        """
        if not host or not isinstance(host, str):
            return False
        
        # Permitir localhost, 127.0.0.1 e 0.0.0.0
        valid_hosts = ["localhost", "127.0.0.1", "0.0.0.0"]
        return host in valid_hosts
    
    @classmethod
    def validate_port(cls, port: int) -> bool:
        """
        Valida se a porta é válida
        
        Args:
            port (int): Porta a ser validada
            
        Returns:
            bool: True se válida, False caso contrário
        """
        if not isinstance(port, int):
            return False
        
        # Portas válidas: 1024-65535 (evitar portas privilegiadas)
        return 1024 <= port <= 65535
    
    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Valida configuração completa da API
        
        Args:
            config (Dict[str, Any]): Configuração a ser validada
            
        Returns:
            tuple[bool, Optional[str]]: (válido, mensagem de erro)
        """
        required_keys = ["api_host", "api_port", "api_enabled"]
        
        # Verificar chaves obrigatórias
        for key in required_keys:
            if key not in config:
                return False, f"Chave obrigatória '{key}' não encontrada"
        
        # Validar host
        if not cls.validate_host(config["api_host"]):
            return False, f"Host inválido: {config['api_host']}"
        
        # Validar porta
        if not cls.validate_port(config["api_port"]):
            return False, f"Porta inválida: {config['api_port']}"
        
        # Validar tipo do enabled
        if not isinstance(config["api_enabled"], bool):
            return False, "'api_enabled' deve ser um valor booleano"
        
        return True, None
    
    @classmethod
    def get_endpoint_url(cls, host: str, port: int, endpoint: str) -> str:
        """
        Constrói URL completa para um endpoint
        
        Args:
            host (str): Host do servidor
            port (int): Porta do servidor
            endpoint (str): Endpoint (ex: '/health')
            
        Returns:
            str: URL completa
        """
        base_url = f"http://{host}:{port}"
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        
        return f"{base_url}{cls.API_PREFIX}{endpoint}"
    
    @classmethod
    def get_cors_config(cls) -> Dict[str, Any]:
        """
        Retorna configuração CORS para Flask-CORS
        
        Returns:
            Dict[str, Any]: Configuração CORS
        """
        return {
            "origins": ["*"],  # Em produção, especificar domínios específicos
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-API-Key"],
            "supports_credentials": False
        }

# Instância global para facilitar importação
api_config = APIConfig()