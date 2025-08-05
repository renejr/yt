# Funcionalidade de Download de Playlists

## Visão Geral
Esta funcionalidade permite o download completo de playlists do YouTube, seguindo as mesmas regras de seleção de pasta e resolução aplicadas aos downloads individuais.

## Implementação

### 1. Detecção de Playlists
- **Método `is_playlist_url`**: Verifica se uma URL é de playlist através de padrões específicos
- **Integração no `extract_video_info`**: Redirecionamento automático para extração de playlist

### 2. Extração de Informações
- **Método `extract_playlist_info`**: Extrai metadados da playlist usando yt-dlp
- **Limitação de Performance**: Máximo de 50 vídeos por playlist para evitar sobrecarga
- **Informações Extraídas**:
  - Título da playlist
  - Número total de vídeos
  - Lista de vídeos com metadados básicos

### 3. Interface do Usuário

#### Novos Elementos
- **Indicador de Tipo de Conteúdo**: Mostra se é vídeo individual ou playlist
- **Checkbox de Playlist**: Permite escolher entre download individual ou completo
- **Rótulo de Informações**: Exibe contagem de vídeos da playlist

#### Layout Atualizado
```
Linha 0: URL Entry
Linha 1: Content Type Label
Linha 2: Extract Button
Linha 3: Playlist Frame (Checkbox + Info Label)
Linha 4: Resolutions Frame + Metadata Frame
Linha 5: Download Button
Linha 6: Mini Player
Linha 7: Progress Frame
Linhas 8-10: Directory/Exit Buttons
```

### 4. Lógica de Download

#### Download de Playlist
- **Método `start_playlist_download`**: Inicia download em thread separada
- **Worker `_playlist_download_worker`**: Processa cada item da playlist
- **Organização de Arquivos**: Criação de subpasta com nome da playlist

#### Configurações por Tipo
- **Vídeo**: Resolução selecionada + áudio incorporado
- **Áudio**: Qualidade selecionada, apenas áudio

### 5. Estrutura de Pastas
```
Diretório de Download/
└── Nome da Playlist/
    ├── Video 1.mp4
    ├── Video 2.mp4
    └── ...
```

## Funcionalidades

### Detecção Automática
- Reconhecimento automático de URLs de playlist
- Atualização da interface baseada no tipo de conteúdo
- Habilitação/desabilitação do checkbox de playlist

### Controles de Interface
- **Modo Individual**: Checkbox desabilitado, download de vídeo único
- **Modo Playlist**: Checkbox habilitado, opção de download completo
- **Texto Dinâmico**: Botão de download adapta-se ao modo selecionado

### Validações
- Verificação de diretório de download
- Validação de resolução selecionada (para vídeo)
- Confirmação de informações extraídas

## Configurações do yt-dlp

### Para Vídeos
```python
'format': f'best[height<={resolution_height}]+bestaudio/best[height<={resolution_height}]'
'merge_output_format': 'mp4'
```

### Para Áudios
```python
'format': 'bestaudio/best'
'postprocessors': [{
    'key': 'FFmpegExtractAudio',
    'preferredcodec': 'mp3',
    'preferredquality': quality
}]
```

## Tratamento de Erros
- Logs detalhados para cada etapa do processo
- Callbacks de erro específicos para playlists
- Fallback para download individual em caso de falha

## Limitações
- Máximo de 50 vídeos por playlist (configurável)
- Dependência do yt-dlp para extração
- Tempo de processamento proporcional ao tamanho da playlist

## Melhorias Futuras
- Seleção de vídeos específicos da playlist
- Download paralelo de múltiplos vídeos
- Resumo de downloads com estatísticas
- Configuração de limite de vídeos por usuário