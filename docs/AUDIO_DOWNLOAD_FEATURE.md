# Funcionalidade de Download de Áudio

## Visão Geral

Esta documentação descreve a implementação da funcionalidade de download apenas de áudio na aplicação YouTube Downloader.

## Funcionalidades Implementadas

### 1. Interface de Usuário

- **Checkbox "Baixar apenas áudio"**: Permite alternar entre download de vídeo e áudio
- **Seletor de qualidade de áudio**: Dropdown com opções de qualidade quando áudio está selecionado
- **Botão dinâmico**: O texto do botão muda entre "Baixar vídeo" e "Baixar áudio"

### 2. Qualidades de Áudio Disponíveis

- **best**: Melhor qualidade disponível
- **320**: 320 kbps
- **256**: 256 kbps
- **192**: 192 kbps
- **128**: 128 kbps

### 3. Comportamento da Interface

#### Quando "Baixar apenas áudio" está marcado:
- Lista de resoluções fica desabilitada
- Opções de qualidade de áudio ficam visíveis
- Botão muda para "Baixar áudio"
- Não é necessário selecionar resolução de vídeo

#### Quando "Baixar apenas áudio" está desmarcado:
- Lista de resoluções fica habilitada
- Opções de qualidade de áudio ficam ocultas
- Botão volta para "Baixar vídeo"
- É necessário selecionar uma resolução

## Implementação Técnica

### 1. Constantes Adicionadas (utils.py)

```python
SUPPORTED_AUDIO_FORMAT = 'mp3'
AUDIO_QUALITIES = ['best', '320', '256', '192', '128']
DEFAULT_AUDIO_QUALITY = 'best'
```

### 2. Modificações no DownloadManager

#### Método `start_download`
- Adicionados parâmetros `audio_only` e `audio_quality`
- Suporte para download exclusivo de áudio

#### Método `_get_download_options`
- Configuração condicional para áudio ou vídeo
- Para áudio: formato `bestaudio/best` com codec mp3
- Para vídeo: mantém configuração original

### 3. Modificações na Interface (ui_components.py)

#### Novos Widgets
- `audio_only_checkbox`: Checkbox para ativar modo áudio
- `audio_quality_combo`: Combobox para seleção de qualidade
- `audio_frame`: Frame container para widgets de áudio

#### Novos Métodos
- `on_audio_only_change()`: Gerencia mudança entre modos
- Atualização de `enable_download_if_ready()`: Considera modo áudio
- Atualização de `start_download()`: Passa parâmetros de áudio

## Fluxo de Download de Áudio

1. **Usuário marca "Baixar apenas áudio"**
   - Interface se adapta automaticamente
   - Lista de resoluções é desabilitada
   - Opções de qualidade aparecem

2. **Usuário seleciona qualidade de áudio**
   - Qualidade padrão é "best"
   - Outras opções disponíveis no dropdown

3. **Download é iniciado**
   - `yt-dlp` usa formato `bestaudio/best`
   - Arquivo é convertido para MP3
   - Qualidade especificada é aplicada

4. **Arquivo final**
   - Formato: MP3
   - Qualidade: Conforme selecionado
   - Local: Diretório de download configurado

## Configurações do yt-dlp para Áudio

```python
if audio_only:
    options.update({
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': AppConstants.SUPPORTED_AUDIO_FORMAT,
            'preferredquality': audio_quality if audio_quality != 'best' else None,
        }]
    })
```

## Validações

- **Modo áudio**: Não requer seleção de resolução
- **Modo vídeo**: Mantém validação original de resolução
- **Diretório**: Sempre obrigatório
- **URL**: Sempre obrigatória

## Benefícios

1. **Economia de espaço**: Arquivos de áudio são menores
2. **Velocidade**: Download mais rápido
3. **Flexibilidade**: Múltiplas qualidades disponíveis
4. **Usabilidade**: Interface intuitiva e responsiva

## Compatibilidade

- **Formatos suportados**: Todos os formatos suportados pelo yt-dlp
- **Plataformas**: YouTube e outras plataformas suportadas
- **Qualidade**: Dependente da qualidade original do vídeo

## Notas Técnicas

- Requer FFmpeg instalado para conversão de áudio
- Qualidade "best" usa a melhor qualidade disponível
- Qualidades numéricas são aplicadas durante pós-processamento
- Arquivos são salvos com extensão .mp3