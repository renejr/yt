# Manual do Desenvolvedor - API REST YouTube Downloader

## Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura da API](#arquitetura-da-api)
3. [Configuração e Instalação](#configuração-e-instalação)
4. [Estrutura de Arquivos](#estrutura-de-arquivos)
5. [Endpoints da API](#endpoints-da-api)
6. [Modelos de Dados](#modelos-de-dados)
7. [Tratamento de Erros](#tratamento-de-erros)
8. [Logging e Monitoramento](#logging-e-monitoramento)
9. [Exemplos de Uso](#exemplos-de-uso)
10. [Desenvolvimento e Extensão](#desenvolvimento-e-extensão)
11. [Troubleshooting](#troubleshooting)

---

## Visão Geral

A API REST do YouTube Downloader é uma interface programática que permite:

- **Download de vídeos** do YouTube de forma automatizada
- **Obtenção de informações** de vídeos sem fazer download
- **Monitoramento de progresso** de downloads em tempo real
- **Histórico de downloads** com paginação
- **Validação robusta** de dados de entrada
- **Logging detalhado** de todas as operações

### Características Principais

- **RESTful**: Segue os princípios REST para facilitar integração
- **Assíncrona**: Suporte a downloads simultâneos
- **Validação**: Validação rigorosa de dados de entrada
- **Padronização**: Respostas padronizadas em JSON
- **Logging**: Sistema completo de logs para auditoria
- **CORS**: Suporte a Cross-Origin Resource Sharing

---

## Arquitetura da API

### Componentes Principais

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   APIManager    │────│   APIServer     │────│   Flask App     │
│                 │    │                 │    │                 │
│ - Gerencia      │    │ - Rotas         │    │ - Endpoints     │
│   ciclo de vida │    │ - Validação     │    │ - Middleware    │
│ - Configuração  │    │ - Serialização  │    │ - CORS          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ ConfigManager   │    │ DownloadManager │    │ LogManager      │
│                 │    │                 │    │                 │
│ - Configurações │    │ - Downloads     │    │ - Logs da API   │
│ - Persistência  │    │ - Progresso     │    │ - Auditoria     │
│ - Validação     │    │ - Histórico     │    │ - Debug         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Fluxo de Dados

1. **Requisição** → Middleware de logging
2. **Validação** → Schemas Marshmallow
3. **Processamento** → Managers específicos
4. **Resposta** → Formatação padronizada
5. **Logging** → Registro de auditoria

---

## Configuração e Instalação

### Pré-requisitos

```bash
# Python 3.8+
python --version

# Dependências principais
pip install flask flask-cors marshmallow
```

### Habilitação da API

```python
# Método 1: Via script
python enable_api.py

# Método 2: Via código
from config_manager import ConfigManager

config = ConfigManager()
config.save_config({
    'api_enabled': True,
    'api_host': '0.0.0.0',
    'api_port': 5000,
    'api_debug': False
})
```

### Configurações Disponíveis

| Configuração | Padrão | Descrição |
|-------------|--------|----------|
| `api_enabled` | `False` | Habilita/desabilita a API |
| `api_host` | `127.0.0.1` | Host do servidor |
| `api_port` | `5000` | Porta do servidor |
| `api_debug` | `False` | Modo debug do Flask |

---

## Estrutura de Arquivos

```
api/
├── api_server.py          # Servidor Flask principal
├── api_config.py          # Configurações e constantes
├── api_utils.py           # Utilitários e helpers
├── api_models.py          # Schemas de validação
├── config_manager.py      # Gerenciamento de configurações
├── enable_api.py          # Script de habilitação
└── docs/
    └── API_DEVELOPER_MANUAL.md  # Este manual
```

### Responsabilidades dos Arquivos

#### `api_server.py`
- **APIServer**: Classe principal do servidor Flask
- **APIManager**: Gerenciador do ciclo de vida da API
- **Rotas**: Definição de todos os endpoints
- **Error Handlers**: Tratamento de erros HTTP

#### `api_config.py`
- **Constantes**: URLs, códigos de status, limites
- **Configurações padrão**: Valores iniciais
- **Validadores**: Funções de validação de configuração

#### `api_utils.py`
- **APIResponse**: Padronização de respostas
- **APIValidator**: Validação de dados
- **APILogger**: Sistema de logging
- **Decorators**: Middleware para rotas

#### `api_models.py`
- **Schemas Marshmallow**: Validação e serialização
- **Modelos de dados**: Estruturas de entrada e saída

---

## Endpoints da API

### Base URL
```
http://localhost:5000/api/v1
```

### 1. Health Check

**Endpoint**: `GET /health`

**Descrição**: Verifica se a API está funcionando e retorna status dos componentes.

**Resposta de Sucesso**:
```json
{
  "status": "success",
  "message": "API está funcionando",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "api_version": "1.0",
    "status": "healthy",
    "uptime": "2h 30m 15s",
    "components": {
      "database": "connected",
      "download_manager": "available",
      "config_manager": "available"
    }
  }
}
```

### 2. Informações de Vídeo

**Endpoint**: `POST /video/info`

**Descrição**: Obtém informações de um vídeo sem fazer download.

**Corpo da Requisição**:
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Resposta de Sucesso**:
```json
{
  "status": "success",
  "message": "Informações do vídeo obtidas com sucesso",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "video_id": "VIDEO_ID",
    "title": "Título do Vídeo",
    "description": "Descrição do vídeo...",
    "duration": 300,
    "view_count": 1000000,
    "upload_date": "2024-01-10",
    "uploader": "Nome do Canal",
    "thumbnail": "https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg",
    "available_formats": [
      {
        "format_id": "22",
        "ext": "mp4",
        "resolution": "720p",
        "filesize": 52428800
      }
    ]
  }
}
```

### 3. Iniciar Download

**Endpoint**: `POST /download`

**Descrição**: Inicia um novo download de vídeo.

**Corpo da Requisição**:
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "format": "mp4",
  "resolution": "720p",
  "audio_only": false,
  "output_path": "/downloads/"
}
```

**Resposta de Sucesso**:
```json
{
  "status": "success",
  "message": "Download iniciado com sucesso",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "download_id": "dl_1705312200_abc123",
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "status": "queued",
    "created_at": "2024-01-15T10:30:00Z",
    "estimated_size": 52428800,
    "format": "mp4",
    "resolution": "720p"
  }
}
```

### 4. Status do Download

**Endpoint**: `GET /download/{download_id}/status`

**Descrição**: Obtém o status atual de um download específico.

**Resposta de Sucesso**:
```json
{
  "status": "success",
  "message": "Status do download obtido com sucesso",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "download_id": "dl_1705312200_abc123",
    "status": "downloading",
    "progress": 45.5,
    "speed": "1.2 MB/s",
    "eta": "00:02:30",
    "downloaded_bytes": 23887872,
    "total_bytes": 52428800,
    "started_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:32:15Z"
  }
}
```

### 5. Progresso Detalhado

**Endpoint**: `GET /download/{download_id}/progress`

**Descrição**: Obtém informações detalhadas de progresso de um download.

**Resposta de Sucesso**:
```json
{
  "status": "success",
  "message": "Progresso do download obtido com sucesso",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "download_id": "dl_1705312200_abc123",
    "status": "downloading",
    "progress": {
      "percentage": 45.5,
      "downloaded_bytes": 23887872,
      "total_bytes": 52428800,
      "speed": "1.2 MB/s",
      "eta": "00:02:30"
    },
    "video_info": {
      "title": "Título do Vídeo",
      "duration": 300,
      "format": "mp4",
      "resolution": "720p"
    },
    "timestamps": {
      "created_at": "2024-01-15T10:30:00Z",
      "started_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:32:15Z"
    }
  }
}
```

### 6. Histórico de Downloads

**Endpoint**: `GET /downloads`

**Descrição**: Obtém histórico de downloads com paginação.

**Parâmetros de Query**:
- `page` (int): Número da página (padrão: 1)
- `per_page` (int): Itens por página (padrão: 10, máximo: 100)
- `status` (string): Filtrar por status (opcional)

**Exemplo**: `GET /downloads?page=1&per_page=20&status=completed`

**Resposta de Sucesso**:
```json
{
  "status": "success",
  "message": "Histórico de downloads obtido com sucesso",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "downloads": [
      {
        "download_id": "dl_1705312200_abc123",
        "url": "https://www.youtube.com/watch?v=VIDEO_ID",
        "title": "Título do Vídeo",
        "status": "completed",
        "format": "mp4",
        "resolution": "720p",
        "file_size": 52428800,
        "created_at": "2024-01-15T10:30:00Z",
        "completed_at": "2024-01-15T10:33:45Z"
      }
    ],
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total_items": 150,
      "total_pages": 8,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

---

## Modelos de Dados

### Schemas de Validação

A API utiliza **Marshmallow** para validação e serialização de dados.

#### HealthSchema
```python
class HealthSchema(Schema):
    api_version = fields.Str(required=True)
    status = fields.Str(required=True)
    uptime = fields.Str(required=True)
    components = fields.Dict(required=True)
```

#### DownloadRequestSchema
```python
class DownloadRequestSchema(Schema):
    url = fields.Url(required=True)
    format = fields.Str(missing='mp4')
    resolution = fields.Str(missing='720p')
    audio_only = fields.Bool(missing=False)
    output_path = fields.Str(missing=None)
```

#### VideoInfoRequestSchema
```python
class VideoInfoRequestSchema(Schema):
    url = fields.Url(required=True)
```

#### PaginationSchema
```python
class PaginationSchema(Schema):
    page = fields.Int(missing=1, validate=validate.Range(min=1))
    per_page = fields.Int(missing=10, validate=validate.Range(min=1, max=100))
    status = fields.Str(missing=None)
```

### Status de Download

| Status | Descrição |
|--------|----------|
| `queued` | Download na fila de espera |
| `downloading` | Download em progresso |
| `completed` | Download concluído com sucesso |
| `failed` | Download falhou |
| `cancelled` | Download cancelado pelo usuário |
| `paused` | Download pausado |

---

## Tratamento de Erros

### Estrutura de Erro Padrão

```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Mensagem descritiva do erro",
    "details": {
      "additional_info": "Informações adicionais"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Códigos de Erro Comuns

| Código | Status HTTP | Descrição |
|--------|-------------|----------|
| `VALIDATION_ERROR` | 400 | Dados de entrada inválidos |
| `DOWNLOAD_NOT_FOUND` | 404 | Download não encontrado |
| `SERVICE_UNAVAILABLE` | 503 | Serviço temporariamente indisponível |
| `DOWNLOAD_START_ERROR` | 500 | Erro ao iniciar download |
| `VIDEO_INFO_ERROR` | 500 | Erro ao obter informações do vídeo |
| `INTERNAL_ERROR` | 500 | Erro interno do servidor |

### Exemplo de Erro de Validação

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Dados de entrada inválidos",
    "details": {
      "validation_errors": {
        "url": ["URL inválida ou não suportada"],
        "resolution": ["Resolução deve ser uma das: 144p, 240p, 360p, 480p, 720p, 1080p"]
      }
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## Logging e Monitoramento

### Sistema de Logging

A API possui um sistema completo de logging que registra:

- **Requisições**: Endpoint, método, IP, user-agent
- **Respostas**: Status code, tempo de resposta
- **Erros**: Stack trace, dados da requisição
- **Downloads**: Início, progresso, conclusão

### Configuração de Logs

```python
# Exemplo de configuração
api_logger = APILogger(log_manager)

# Log de requisição
api_logger.log_request(
    endpoint='/api/v1/download',
    method='POST',
    ip='192.168.1.100',
    user_agent='Mozilla/5.0...'
)

# Log de resposta
api_logger.log_response(
    endpoint='/api/v1/download',
    status_code=201,
    response_time=1.25
)

# Log de erro
api_logger.log_error(
    endpoint='/api/v1/download',
    error=exception_object,
    request_data={'url': 'invalid_url'}
)
```

### Decorators de Logging

```python
@log_api_request(log_manager)
@handle_api_errors
def my_endpoint():
    # Lógica do endpoint
    pass
```

---

## Exemplos de Uso

### Python (requests)

```python
import requests
import json

# Base URL da API
BASE_URL = 'http://localhost:5000/api/v1'

# 1. Verificar saúde da API
response = requests.get(f'{BASE_URL}/health')
print(f"Status: {response.status_code}")
print(f"Resposta: {response.json()}")

# 2. Obter informações de vídeo
video_data = {
    'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
}
response = requests.post(
    f'{BASE_URL}/video/info',
    json=video_data,
    headers={'Content-Type': 'application/json'}
)
video_info = response.json()
print(f"Título: {video_info['data']['title']}")

# 3. Iniciar download
download_data = {
    'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    'format': 'mp4',
    'resolution': '720p',
    'audio_only': False
}
response = requests.post(
    f'{BASE_URL}/download',
    json=download_data,
    headers={'Content-Type': 'application/json'}
)
download_result = response.json()
download_id = download_result['data']['download_id']
print(f"Download ID: {download_id}")

# 4. Monitorar progresso
import time

while True:
    response = requests.get(f'{BASE_URL}/download/{download_id}/progress')
    progress_data = response.json()
    
    if progress_data['status'] == 'success':
        progress = progress_data['data']['progress']['percentage']
        status = progress_data['data']['status']
        
        print(f"Status: {status}, Progresso: {progress}%")
        
        if status in ['completed', 'failed', 'cancelled']:
            break
    
    time.sleep(2)

# 5. Obter histórico
response = requests.get(f'{BASE_URL}/downloads?page=1&per_page=10')
history = response.json()
print(f"Total de downloads: {history['data']['pagination']['total_items']}")
```

### JavaScript (fetch)

```javascript
const BASE_URL = 'http://localhost:5000/api/v1';

// 1. Verificar saúde da API
async function checkHealth() {
    try {
        const response = await fetch(`${BASE_URL}/health`);
        const data = await response.json();
        console.log('API Status:', data);
        return data;
    } catch (error) {
        console.error('Erro ao verificar API:', error);
    }
}

// 2. Obter informações de vídeo
async function getVideoInfo(url) {
    try {
        const response = await fetch(`${BASE_URL}/video/info`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            console.log('Informações do vídeo:', data.data);
            return data.data;
        } else {
            console.error('Erro:', data.error);
        }
    } catch (error) {
        console.error('Erro na requisição:', error);
    }
}

// 3. Iniciar download
async function startDownload(url, format = 'mp4', resolution = '720p') {
    try {
        const response = await fetch(`${BASE_URL}/download`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url,
                format,
                resolution,
                audio_only: false
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            console.log('Download iniciado:', data.data.download_id);
            return data.data.download_id;
        } else {
            console.error('Erro ao iniciar download:', data.error);
        }
    } catch (error) {
        console.error('Erro na requisição:', error);
    }
}

// 4. Monitorar progresso
async function monitorProgress(downloadId) {
    const checkProgress = async () => {
        try {
            const response = await fetch(`${BASE_URL}/download/${downloadId}/progress`);
            const data = await response.json();
            
            if (data.status === 'success') {
                const { status, progress } = data.data;
                console.log(`Status: ${status}, Progresso: ${progress.percentage}%`);
                
                if (['completed', 'failed', 'cancelled'].includes(status)) {
                    console.log('Download finalizado!');
                    return;
                }
                
                // Continuar monitorando
                setTimeout(checkProgress, 2000);
            }
        } catch (error) {
            console.error('Erro ao verificar progresso:', error);
        }
    };
    
    checkProgress();
}

// 5. Exemplo de uso completo
async function downloadVideo(url) {
    // Verificar API
    await checkHealth();
    
    // Obter informações
    const videoInfo = await getVideoInfo(url);
    if (!videoInfo) return;
    
    // Iniciar download
    const downloadId = await startDownload(url);
    if (!downloadId) return;
    
    // Monitorar progresso
    await monitorProgress(downloadId);
}

// Usar a função
downloadVideo('https://www.youtube.com/watch?v=dQw4w9WgXcQ');
```

### cURL

```bash
# 1. Verificar saúde da API
curl -X GET http://localhost:5000/api/v1/health

# 2. Obter informações de vídeo
curl -X POST http://localhost:5000/api/v1/video/info \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'

# 3. Iniciar download
curl -X POST http://localhost:5000/api/v1/download \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "mp4",
    "resolution": "720p",
    "audio_only": false
  }'

# 4. Verificar status (substitua DOWNLOAD_ID)
curl -X GET http://localhost:5000/api/v1/download/DOWNLOAD_ID/status

# 5. Verificar progresso
curl -X GET http://localhost:5000/api/v1/download/DOWNLOAD_ID/progress

# 6. Obter histórico
curl -X GET "http://localhost:5000/api/v1/downloads?page=1&per_page=10"
```

---

## Desenvolvimento e Extensão

### Adicionando Novos Endpoints

1. **Definir o Schema** em `api_models.py`:

```python
class NewFeatureSchema(Schema):
    parameter1 = fields.Str(required=True)
    parameter2 = fields.Int(missing=0)
```

2. **Adicionar a Rota** em `api_server.py`:

```python
@self.app.route(f"{APIConfig.API_PREFIX}/new-feature", methods=['POST'])
@log_api_request(self.log_manager)
@handle_api_errors
def new_feature_endpoint():
    """Descrição do novo endpoint"""
    # Validar dados
    request_data = request.get_json() or {}
    is_valid, validated_data, errors = validate_request_data(
        new_feature_schema, request_data
    )
    
    if not is_valid:
        return APIResponse.validation_error(errors)
    
    try:
        # Lógica do endpoint
        result = self._process_new_feature(validated_data)
        
        return APIResponse.success(
            data=result,
            message="Operação realizada com sucesso"
        )
        
    except Exception as e:
        return APIResponse.error(
            message=f"Erro na operação: {str(e)}",
            code="NEW_FEATURE_ERROR",
            status_code=APIConfig.HTTP_STATUS["INTERNAL_ERROR"]
        )
```

3. **Implementar a Lógica** como método privado:

```python
def _process_new_feature(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """Processa a nova funcionalidade"""
    # Implementar lógica aqui
    return {
        "result": "success",
        "processed_data": data
    }
```

### Middleware Personalizado

```python
def custom_middleware(func):
    """Middleware personalizado"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Lógica antes da execução
        start_time = time.time()
        
        try:
            # Executar função
            result = func(*args, **kwargs)
            
            # Lógica após execução
            end_time = time.time()
            print(f"Tempo de execução: {end_time - start_time:.2f}s")
            
            return result
            
        except Exception as e:
            # Tratamento de erro
            print(f"Erro no middleware: {e}")
            raise
    
    return wrapper
```

### Validadores Customizados

```python
class CustomValidator:
    @staticmethod
    def validate_custom_field(value: str) -> bool:
        """Validador personalizado"""
        # Implementar lógica de validação
        return len(value) > 5 and value.isalnum()
    
    @staticmethod
    def validate_file_extension(filename: str) -> bool:
        """Valida extensão de arquivo"""
        allowed_extensions = ['.mp4', '.mp3', '.avi', '.mkv']
        return any(filename.lower().endswith(ext) for ext in allowed_extensions)
```

---

## Troubleshooting

### Problemas Comuns

#### 1. API não inicia

**Sintomas**: Erro ao executar `api_manager.start()`

**Possíveis causas**:
- Porta já em uso
- Configurações inválidas
- Dependências não instaladas

**Soluções**:
```python
# Verificar porta
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('localhost', 5000))
if result == 0:
    print("Porta 5000 já está em uso")
sock.close()

# Alterar porta
config_manager.save_config({'api_port': 5001})

# Verificar dependências
pip list | grep -E "flask|marshmallow|cors"
```

#### 2. Erro de validação

**Sintomas**: Status 400 com `VALIDATION_ERROR`

**Soluções**:
- Verificar formato dos dados enviados
- Consultar schemas em `api_models.py`
- Verificar tipos de dados (string, int, bool)

#### 3. Download não inicia

**Sintomas**: Status 503 com `SERVICE_UNAVAILABLE`

**Possíveis causas**:
- DownloadManager não inicializado
- Problemas de conectividade
- URL inválida

**Soluções**:
```python
# Verificar DownloadManager
if api_server.download_manager is None:
    print("DownloadManager não está disponível")

# Testar URL manualmente
import requests
response = requests.head(url)
print(f"Status da URL: {response.status_code}")
```

#### 4. Logs não aparecem

**Sintomas**: Ausência de logs da API

**Soluções**:
```python
# Verificar LogManager
if api_server.log_manager is None:
    print("LogManager não está disponível")

# Configurar logging manual
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Debug Mode

```python
# Habilitar debug
config_manager.save_config({'api_debug': True})

# Logs detalhados
api_logger.log_level = 'DEBUG'

# Traceback completo
import traceback
try:
    # código que pode falhar
    pass
except Exception as e:
    traceback.print_exc()
```

### Monitoramento de Performance

```python
import time
import psutil

def monitor_api_performance():
    """Monitora performance da API"""
    start_time = time.time()
    
    # CPU e memória
    cpu_percent = psutil.cpu_percent()
    memory_info = psutil.virtual_memory()
    
    print(f"CPU: {cpu_percent}%")
    print(f"Memória: {memory_info.percent}%")
    print(f"Uptime: {time.time() - start_time:.2f}s")
```

---

## Conclusão

Este manual fornece uma visão completa da API REST do YouTube Downloader. Para dúvidas específicas ou contribuições:

1. **Consulte os logs** da aplicação
2. **Verifique a documentação** dos schemas
3. **Teste endpoints** individualmente
4. **Monitore performance** em produção

### Recursos Adicionais

- **Código fonte**: Arquivos `api_*.py`
- **Configurações**: `config_manager.py`
- **Logs**: Diretório de logs da aplicação
- **Testes**: Implementar testes unitários

### Próximos Passos

1. **Implementar autenticação** (JWT, API Keys)
2. **Adicionar rate limiting**
3. **Criar testes automatizados**
4. **Documentação OpenAPI/Swagger**
5. **Métricas e monitoramento**

---

**Versão**: 1.0  
**Data**: Janeiro 2024  
**Autor**: Equipe de Desenvolvimento  
**Última atualização**: 15/01/2024