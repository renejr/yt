#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modelos e Schemas da API REST - YouTube Downloader
Schemas Marshmallow para validação e serialização de dados

Versão: 1.0
Data: 2024
"""

from marshmallow import Schema, fields, validate, validates, ValidationError, post_load
from typing import Dict, Any, Optional
from api_utils import APIValidator

class HealthSchema(Schema):
    """Schema para resposta do endpoint de health check"""
    
    status = fields.Str(required=True, validate=validate.OneOf(["healthy", "unhealthy"]))
    timestamp = fields.DateTime(required=True, format="iso")
    version = fields.Str(required=True)
    uptime = fields.Float(required=True)
    services = fields.Dict(keys=fields.Str(), values=fields.Str(), required=False)

class DownloadRequestSchema(Schema):
    """Schema para requisição de download"""
    
    url = fields.Url(required=True, error_messages={
        "required": "URL é obrigatória",
        "invalid": "URL deve ser válida"
    })
    
    resolution = fields.Str(
        required=False,
        load_default="best",
        validate=validate.OneOf([
            "144p", "240p", "360p", "480p", "720p", "1080p", "1440p", "2160p",
            "best", "worst", "bestaudio", "worstaudio"
        ]),
        error_messages={
            "invalid": "Resolução deve ser uma das opções válidas"
        }
    )
    
    audio_only = fields.Bool(
        required=False,
        load_default=False,
        error_messages={
            "invalid": "audio_only deve ser true ou false"
        }
    )
    
    output_path = fields.Str(
        required=False,
        allow_none=True,
        validate=validate.Length(max=500),
        error_messages={
            "invalid": "Caminho de saída muito longo (máximo 500 caracteres)"
        }
    )
    
    custom_name = fields.Str(
        required=False,
        allow_none=True,
        validate=validate.Length(max=255),
        error_messages={
            "invalid": "Nome personalizado muito longo (máximo 255 caracteres)"
        }
    )
    
    @validates("url")
    def validate_url(self, value, **kwargs):
        """Valida se a URL é suportada pelo YouTube downloader"""
        if not APIValidator.validate_url(value):
            raise ValidationError("URL deve ser do YouTube ou serviços suportados")
    
    @post_load
    def process_data(self, data, **kwargs):
        """Processa dados após validação"""
        # Se audio_only for True, forçar resolução para bestaudio
        if data.get("audio_only", False):
            data["resolution"] = "bestaudio"
        
        return data

class DownloadResponseSchema(Schema):
    """Schema para resposta de download"""
    
    download_id = fields.Str(required=True)
    status = fields.Str(required=True, validate=validate.OneOf([
        "pending", "downloading", "completed", "failed", "cancelled"
    ]))
    url = fields.Url(required=True)
    title = fields.Str(required=False, allow_none=True)
    resolution = fields.Str(required=True)
    audio_only = fields.Bool(required=True)
    progress = fields.Float(required=False, validate=validate.Range(min=0, max=100))
    file_path = fields.Str(required=False, allow_none=True)
    file_size = fields.Float(required=False, allow_none=True)
    duration = fields.Float(required=False, allow_none=True)
    download_speed = fields.Str(required=False, allow_none=True)
    eta = fields.Str(required=False, allow_none=True)
    error_message = fields.Str(required=False, allow_none=True)
    created_at = fields.DateTime(required=True, format="iso")
    updated_at = fields.DateTime(required=False, format="iso")
    completed_at = fields.DateTime(required=False, format="iso", allow_none=True)

class VideoInfoSchema(Schema):
    """Schema para informações de vídeo"""
    
    title = fields.Str(required=True)
    duration = fields.Float(required=False, allow_none=True)
    uploader = fields.Str(required=False, allow_none=True)
    upload_date = fields.DateTime(required=False, format="iso", allow_none=True)
    view_count = fields.Int(required=False, allow_none=True)
    like_count = fields.Int(required=False, allow_none=True)
    description = fields.Str(required=False, allow_none=True)
    thumbnail = fields.Url(required=False, allow_none=True)
    url = fields.Url(required=True)
    formats = fields.List(fields.Dict(), required=False, load_default=[])

class VideoInfoRequestSchema(Schema):
    """Schema para requisição de informações de vídeo"""
    
    url = fields.Url(required=True, error_messages={
        "required": "URL é obrigatória",
        "invalid": "URL deve ser válida"
    })
    
    @validates("url")
    def validate_url(self, value, **kwargs):
        """Valida se a URL é suportada"""
        if not APIValidator.validate_url(value):
            raise ValidationError("URL deve ser do YouTube ou serviços suportados")

class DownloadStatusSchema(Schema):
    """Schema para status de download"""
    
    download_id = fields.Str(required=True)
    status = fields.Str(required=True)
    progress = fields.Float(required=False, validate=validate.Range(min=0, max=100))
    download_speed = fields.Str(required=False, allow_none=True)
    eta = fields.Str(required=False, allow_none=True)
    error_message = fields.Str(required=False, allow_none=True)
    updated_at = fields.DateTime(required=True, format="iso")

class DownloadHistorySchema(Schema):
    """Schema para histórico de downloads"""
    
    downloads = fields.List(fields.Nested(DownloadResponseSchema), required=True)
    total = fields.Int(required=True)
    page = fields.Int(required=True)
    per_page = fields.Int(required=True)
    pages = fields.Int(required=True)

class PaginationSchema(Schema):
    """Schema para parâmetros de paginação"""
    
    page = fields.Int(
        required=False,
        load_default=1,
        validate=validate.Range(min=1),
        error_messages={
            "invalid": "Página deve ser um número inteiro maior que 0"
        }
    )
    
    per_page = fields.Int(
        required=False,
        load_default=20,
        validate=validate.Range(min=1, max=100),
        error_messages={
            "invalid": "Items por página deve ser entre 1 e 100"
        }
    )
    
    status = fields.Str(
        required=False,
        allow_none=True,
        validate=validate.OneOf([
            "pending", "downloading", "completed", "failed", "cancelled"
        ]),
        error_messages={
            "invalid": "Status deve ser um dos valores válidos"
        }
    )
    
    search = fields.Str(
        required=False,
        allow_none=True,
        validate=validate.Length(max=255),
        error_messages={
            "invalid": "Termo de busca muito longo (máximo 255 caracteres)"
        }
    )

class ConfigSchema(Schema):
    """Schema para configurações da aplicação"""
    
    api_enabled = fields.Bool(required=False, load_default=True)
    api_host = fields.Str(
        required=False,
        load_default="localhost",
        validate=validate.Length(max=255)
    )
    api_port = fields.Int(
        required=False,
        load_default=5000,
        validate=validate.Range(min=1, max=65535)
    )
    api_debug = fields.Bool(required=False, load_default=False)
    default_resolution = fields.Str(
        required=False,
        load_default="best",
        validate=validate.OneOf([
            "144p", "240p", "360p", "480p", "720p", "1080p", "1440p", "2160p",
            "best", "worst", "bestaudio", "worstaudio"
        ])
    )
    auto_open_folder = fields.Bool(required=False, load_default=True)
    theme = fields.Str(
        required=False,
        load_default="light",
        validate=validate.OneOf(["light", "dark"])
    )

class ErrorSchema(Schema):
    """Schema para respostas de erro"""
    
    status = fields.Str(required=True, validate=validate.Equal("error"))
    error = fields.Dict(required=True, keys=fields.Str(), values=fields.Raw())
    timestamp = fields.DateTime(required=True, format="iso")

class SuccessSchema(Schema):
    """Schema para respostas de sucesso"""
    
    status = fields.Str(required=True, validate=validate.Equal("success"))
    message = fields.Str(required=True)
    timestamp = fields.DateTime(required=True, format="iso")
    data = fields.Raw(required=False, allow_none=True)

class DownloadCancelSchema(Schema):
    """Schema para cancelamento de download"""
    
    download_id = fields.Str(required=True, error_messages={
        "required": "ID do download é obrigatório"
    })
    
    @validates("download_id")
    def validate_download_id(self, value, **kwargs):
        """Valida se o ID do download é válido"""
        if not APIValidator.validate_download_id(value):
            raise ValidationError("ID do download deve ser alfanumérico")

class PlaylistInfoSchema(Schema):
    """Schema para informações de playlist"""
    
    title = fields.Str(required=True)
    uploader = fields.Str(required=False, allow_none=True)
    description = fields.Str(required=False, allow_none=True)
    video_count = fields.Int(required=True)
    url = fields.Url(required=True)
    videos = fields.List(fields.Nested(VideoInfoSchema), required=False, load_default=[])

class BulkDownloadSchema(Schema):
    """Schema para download em lote"""
    
    urls = fields.List(
        fields.Url(),
        required=True,
        validate=validate.Length(min=1, max=50),
        error_messages={
            "required": "Lista de URLs é obrigatória",
            "invalid": "Máximo de 50 URLs por requisição"
        }
    )
    
    resolution = fields.Str(
        required=False,
        load_default="best",
        validate=validate.OneOf([
            "144p", "240p", "360p", "480p", "720p", "1080p", "1440p", "2160p",
            "best", "worst", "bestaudio", "worstaudio"
        ])
    )
    
    audio_only = fields.Bool(required=False, load_default=False)
    output_path = fields.Str(
        required=False,
        allow_none=True,
        validate=validate.Length(max=500)
    )
    
    @validates("urls")
    def validate_urls(self, value, **kwargs):
        """Valida se todas as URLs são suportadas"""
        for url in value:
            if not APIValidator.validate_url(url):
                raise ValidationError(f"URL não suportada: {url}")

class SystemStatsSchema(Schema):
    """Schema para estatísticas do sistema"""
    
    total_downloads = fields.Int(required=True)
    completed_downloads = fields.Int(required=True)
    failed_downloads = fields.Int(required=True)
    active_downloads = fields.Int(required=True)
    total_size_downloaded = fields.Float(required=True)
    uptime = fields.Float(required=True)
    memory_usage = fields.Dict(required=False)
    disk_usage = fields.Dict(required=False)

# Instâncias dos schemas para uso na API
health_schema = HealthSchema()
download_request_schema = DownloadRequestSchema()
download_response_schema = DownloadResponseSchema()
video_info_schema = VideoInfoSchema()
video_info_request_schema = VideoInfoRequestSchema()
download_status_schema = DownloadStatusSchema()
download_history_schema = DownloadHistorySchema()
pagination_schema = PaginationSchema()
config_schema = ConfigSchema()
error_schema = ErrorSchema()
success_schema = SuccessSchema()
download_cancel_schema = DownloadCancelSchema()
playlist_info_schema = PlaylistInfoSchema()
bulk_download_schema = BulkDownloadSchema()
system_stats_schema = SystemStatsSchema()

# Função auxiliar para validar dados de entrada
def validate_request_data(schema: Schema, data: Dict[str, Any]) -> tuple[bool, Dict[str, Any], Optional[Dict]]:
    """
    Valida dados de requisição usando schema Marshmallow
    
    Args:
        schema (Schema): Schema para validação
        data (Dict[str, Any]): Dados a serem validados
        
    Returns:
        tuple[bool, Dict[str, Any], Optional[Dict]]: (válido, dados_validados, erros)
    """
    try:
        validated_data = schema.load(data)
        return True, validated_data, None
    except ValidationError as e:
        return False, {}, e.messages

# Função auxiliar para serializar dados de resposta
def serialize_response_data(schema: Schema, data: Any) -> Dict[str, Any]:
    """
    Serializa dados de resposta usando schema Marshmallow
    
    Args:
        schema (Schema): Schema para serialização
        data (Any): Dados a serem serializados
        
    Returns:
        Dict[str, Any]: Dados serializados
    """
    try:
        return schema.dump(data)
    except Exception:
        # Em caso de erro na serialização, retornar dados originais
        return data if isinstance(data, dict) else {}