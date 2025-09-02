#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servidor da API REST - YouTube Downloader
Implementação do servidor Flask com rotas e gerenciamento

Versão: 1.0
Data: 2024
"""

import threading
import uuid
from datetime import datetime
from flask import Flask, request
from flask_cors import CORS

# Imports locais
from api_config import APIConfig
from api_utils import APIResponse, APILogger, log_api_request, handle_api_errors
from api_models import (
    health_schema, download_request_schema, video_info_request_schema,
    pagination_schema, validate_request_data
)

class APIServer:
    """Classe principal do servidor Flask da API"""
    
    def __init__(self, config_manager=None, download_manager=None, 
                 history_manager=None, log_manager=None):
        self.config_manager = config_manager
        self.download_manager = download_manager
        self.history_manager = history_manager
        self.log_manager = log_manager

        if self.download_manager and not self.download_manager.download_directory:
            self.download_manager.set_download_directory("downloads")
        
        self.active_downloads = {}
        self.download_lock = threading.Lock()
        
        self.app = Flask(__name__)
        self.app.config['JSON_SORT_KEYS'] = False
        self.app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
        
        cors_config = APIConfig.get_cors_config()
        CORS(self.app, **cors_config)
        
        self.api_logger = APILogger(self.log_manager)
        self.start_time = datetime.utcnow()
        
        self._register_routes()
        self._register_error_handlers()

    # ----------------------------
    # Métodos auxiliares conectados ao DownloadManager e HistoryManager
    # ----------------------------

    def _get_video_info_from_url(self, url: str) -> dict:
        video_info = self.download_manager.extract_info(url, download=False)
        return {
            "title": video_info.get("title"),
            "duration": video_info.get("duration"),
            "uploader": video_info.get("uploader"),
            "upload_date": video_info.get("upload_date"),
            "view_count": video_info.get("view_count"),
            "like_count": video_info.get("like_count"),
            "description": video_info.get("description"),
            "thumbnail": video_info.get("thumbnail"),
            "url": video_info.get("webpage_url"),
            "formats": video_info.get("formats", [])
        }

    def _start_download_process(self, data: dict) -> dict:
        download_id = f"dl_{uuid.uuid4().hex[:12]}"

        self.download_manager.start_download(
            download_id=download_id,
            url=data["url"],
            resolution=data.get("resolution", "best"),
            audio_only=data.get("audio_only", False),
            output_path=data.get("output_path"),
            custom_name=data.get("custom_name")
        )

        if self.history_manager:
            self.history_manager.add_download_entry(download_id, {
                "url": data["url"],
                "status": "queued",
                "created_at": datetime.utcnow().isoformat() + "Z"
            })

        return {
            "download_id": download_id,
            "url": data["url"],
            "status": "queued",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "format": "mp3" if data.get("audio_only") else "mp4",
            "resolution": data.get("resolution", "best")
        }

    def _get_download_status(self, download_id: str) -> dict:
        return self.download_manager.get_download_status(download_id)

    def _get_download_progress(self, download_id: str) -> dict:
        return self.download_manager.get_download_progress(download_id)

    def _get_paginated_history(self, params: dict) -> dict:
        page = int(params.get("page", 1))
        per_page = int(params.get("per_page", 20))
        history, total = self.history_manager.get_paginated_history(page, per_page)
        return {
            "downloads": history,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page
        }

    # ----------------------------
    # Rotas
    # ----------------------------

    def _register_routes(self):
        @self.app.route(f"{APIConfig.API_PREFIX}/health", methods=['GET'])
        @log_api_request(self.log_manager)
        @handle_api_errors
        def health_check():
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
            services = {
                "database": "healthy" if self._check_database() else "unhealthy",
                "download_manager": "healthy" if self._check_download_manager() else "unhealthy",
                "config_manager": "healthy" if self._check_config_manager() else "unhealthy"
            }
            overall_status = "healthy" if all(s == "healthy" for s in services.values()) else "unhealthy"
            health_data = {
                "status": overall_status,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": APIConfig.API_VERSION,
                "uptime": uptime,
                "services": services
            }
            return APIResponse.success(data=health_data, message="API está funcionando")

        @self.app.route(f"{APIConfig.API_PREFIX}/video/info", methods=['POST'])
        @log_api_request(self.log_manager)
        @handle_api_errors
        def get_video_info():
            request_data = request.get_json() or {}
            is_valid, validated_data, errors = validate_request_data(video_info_request_schema, request_data)
            if not is_valid:
                return APIResponse.validation_error(errors)
            url = validated_data['url']
            if not self.download_manager:
                return APIResponse.error("Serviço de download não disponível", code="SERVICE_UNAVAILABLE", status_code=APIConfig.HTTP_STATUS["SERVICE_UNAVAILABLE"])
            video_info = self._get_video_info_from_url(url)
            return APIResponse.success(data=video_info, message="Informações do vídeo obtidas com sucesso")

        @self.app.route(f"{APIConfig.API_PREFIX}/download", methods=['POST'])
        @log_api_request(self.log_manager)
        @handle_api_errors
        def start_download():
            request_data = request.get_json() or {}
            is_valid, validated_data, errors = validate_request_data(download_request_schema, request_data)
            if not is_valid:
                return APIResponse.validation_error(errors)
            if not self.download_manager:
                return APIResponse.error("Serviço de download não disponível", code="SERVICE_UNAVAILABLE", status_code=APIConfig.HTTP_STATUS["SERVICE_UNAVAILABLE"])
            download_result = self._start_download_process(validated_data)
            return APIResponse.success(data=download_result, message="Download iniciado com sucesso", status_code=APIConfig.HTTP_STATUS["CREATED"])

        @self.app.route(f"{APIConfig.API_PREFIX}/download/<download_id>/status", methods=['GET'])
        @log_api_request(self.log_manager)
        @handle_api_errors
        def get_download_status(download_id):
            if not download_id or not str(download_id).strip():
                return APIResponse.error("Parâmetro download_id ausente ou inválido", code="INVALID_DOWNLOAD_ID", status_code=APIConfig.HTTP_STATUS["BAD_REQUEST"])
            if not self.download_manager:
                return APIResponse.error("Serviço de download não disponível", code="SERVICE_UNAVAILABLE", status_code=APIConfig.HTTP_STATUS["SERVICE_UNAVAILABLE"])
            status_data = self._get_download_status(download_id)
            if not status_data:
                return APIResponse.error("Download não encontrado", code="DOWNLOAD_NOT_FOUND", status_code=APIConfig.HTTP_STATUS["NOT_FOUND"])
            return APIResponse.success(data=status_data, message="Status do download obtido com sucesso")

        @self.app.route(f"{APIConfig.API_PREFIX}/download/<download_id>/progress", methods=['GET'])
        @log_api_request(self.log_manager)
        @handle_api_errors
        def get_download_progress(download_id):
            if not download_id or not str(download_id).strip():
                return APIResponse.error("Parâmetro download_id ausente ou inválido", code="INVALID_DOWNLOAD_ID", status_code=APIConfig.HTTP_STATUS["BAD_REQUEST"])
            if not self.download_manager:
                return APIResponse.error("Serviço de download não disponível", code="SERVICE_UNAVAILABLE", status_code=APIConfig.HTTP_STATUS["SERVICE_UNAVAILABLE"])
            progress_data = self._get_download_progress(download_id)
            if not progress_data:
                return APIResponse.error("Download não encontrado", code="DOWNLOAD_NOT_FOUND", status_code=APIConfig.HTTP_STATUS["NOT_FOUND"])
            return APIResponse.success(data=progress_data, message="Progresso do download obtido com sucesso")

        @self.app.route(f"{APIConfig.API_PREFIX}/downloads", methods=['GET'])
        @log_api_request(self.log_manager)
        @handle_api_errors
        def get_download_history():
            query_params = dict(request.args)
            is_valid, validated_params, errors = validate_request_data(pagination_schema, query_params)
            if not is_valid:
                return APIResponse.validation_error(errors)
            if self.history_manager:
                history_data = self._get_paginated_history(validated_params)
            else:
                history_data = {"downloads": [], "total": 0, "page": validated_params.get('page', 1), "per_page": validated_params.get('per_page', 20), "pages": 0}
            return APIResponse.success(data=history_data, message="Histórico obtido com sucesso")

    def _register_error_handlers(self):
        @self.app.errorhandler(404)
        def not_found(e):
            return APIResponse.error("Endpoint não encontrado", code="NOT_FOUND", status_code=404)

        @self.app.errorhandler(500)
        def internal_error(e):
            return APIResponse.error("Erro interno do servidor", code="INTERNAL_ERROR", status_code=500)
