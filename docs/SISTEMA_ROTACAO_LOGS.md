# Sistema de Rotação de Logs com Compactação 7z

## Visão Geral

O sistema de rotação de logs foi implementado para gerenciar automaticamente o crescimento do arquivo `youtube_downloader.log`, evitando que ele se torne muito grande e consuma espaço desnecessário em disco.

## Funcionalidades Implementadas

### 1. Verificação Automática de Tamanho
- **Limite**: 250MB por arquivo de log
- **Trigger**: Verificação após cada download concluído
- **Função**: `verificar_tamanho_log()`

### 2. Compactação com 7z
- **Algoritmo**: 7-Zip (LZMA2) para máxima compressão
- **Taxa esperada**: 30-70% de redução de tamanho
- **Formato do arquivo**: `log_backup_YYYYMMDD_HHMMSS.7z`
- **Função**: `comprimir_e_rotacionar_log()`

### 3. Limpeza Automática
- **Retenção**: 30 dias (configurável)
- **Ação**: Remove automaticamente backups antigos
- **Função**: `limpar_logs_antigos(dias_manter=30)`

## Como Funciona

1. **Durante o download**: O sistema registra todas as atividades no arquivo `youtube_downloader.log`

2. **Após cada download**: 
   - Verifica se o arquivo de log excedeu 250MB
   - Se sim, inicia o processo de rotação

3. **Processo de rotação**:
   - Comprime o arquivo atual em formato 7z
   - Remove o arquivo original
   - Cria um novo arquivo de log limpo
   - Registra estatísticas da compressão

4. **Limpeza automática**:
   - Remove backups com mais de 30 dias
   - Mantém o histórico organizado

## Vantagens

- **Economia de espaço**: Compressão de 30-70% do tamanho original
- **Organização temporal**: Arquivos nomeados com timestamp
- **Automático**: Não requer intervenção manual
- **Configurável**: Fácil ajuste de parâmetros
- **Histórico preservado**: Logs antigos mantidos em formato comprimido

## Configurações

### Tamanho limite do log
```python
# Modificar na função verificar_tamanho_log()
tamanho_mb >= 250  # Alterar valor conforme necessário
```

### Dias de retenção
```python
# Modificar na chamada da função
limpar_logs_antigos(30)  # Alterar número de dias
```

## Arquivos Gerados

- `youtube_downloader.log` - Log atual em uso
- `log_backup_YYYYMMDD_HHMMSS.7z` - Backups comprimidos
- `requirements.txt` - Dependências do projeto

## Dependências

- `py7zr>=0.20.6` - Biblioteca para compressão 7z

## Instalação da Dependência

```bash
pip install py7zr
```

Ou usando o arquivo de requisitos:

```bash
pip install -r requirements.txt
```

## Logs de Sistema

O sistema registra suas próprias atividades:

- Início da rotação
- Estatísticas de compressão
- Arquivos removidos na limpeza
- Erros durante o processo

## Exemplo de Log de Rotação

```
2024-01-15 14:30:25 - INFO - Arquivo de log excedeu 250MB, iniciando rotação...
2024-01-15 14:30:26 - INFO - Rotação de log realizada: log_backup_20240115_143026.7z
2024-01-15 14:30:26 - INFO - Tamanho original: 251.45MB
2024-01-15 14:30:26 - INFO - Tamanho comprimido: 45.23MB
2024-01-15 14:30:26 - INFO - Taxa de compressão: 82.0%
2024-01-15 14:30:26 - INFO - Limpeza concluída: 2 arquivo(s) de log antigo(s) removido(s)
```

## Monitoramento

Para verificar o status do sistema:

1. **Tamanho atual do log**: Verificar `youtube_downloader.log`
2. **Backups existentes**: Listar arquivos `log_backup_*.7z`
3. **Logs de rotação**: Verificar entradas no arquivo de log atual

## Troubleshooting

### Erro na instalação do py7zr
```bash
pip install --upgrade pip
pip install py7zr
```

### Erro de permissão
- Verificar se o diretório tem permissões de escrita
- Executar como administrador se necessário

### Falha na compressão
- Verificar espaço em disco disponível
- Verificar se o arquivo de log não está sendo usado por outro processo