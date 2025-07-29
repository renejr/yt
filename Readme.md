# YouTube Video Downloader

Um aplicativo desktop em Python para baixar vídeos do YouTube com interface gráfica amigável.

## Funcionalidades

- Interface gráfica intuitiva usando Tkinter
- Download de vídeos do YouTube em várias resoluções
- Extração automática de informações do vídeo (título, descrição, visualizações, duração)
- Sistema de histórico de downloads
- Configurações personalizáveis (tema claro/escuro, resolução padrão)
- Sistema de rotação de logs com compactação 7z
- Suporte a múltiplos formatos de vídeo

## Requisitos

- Python 3.x
- FFmpeg (incluído no repositório)
- Bibliotecas Python listadas em `requirements.txt`

## Instalação

1. Clone o repositório:
```bash
git clone [URL_DO_REPOSITORIO]
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Execute o instalador:
```bash
python install.py
```

## Uso

Execute o arquivo principal:
```bash
python yt.py
```

## Estrutura do Projeto

```
├── yt.py                    # Arquivo principal
├── database_manager.py      # Gerenciador do banco de dados
├── install.py              # Script de instalação
├── requirements.txt        # Dependências do projeto
├── ffmpeg.exe             # Binário do FFmpeg
├── ffplay.exe             # Player do FFmpeg
├── ffprobe.exe            # Analisador de mídia do FFmpeg
├── logs/                  # Diretório de logs
└── docs/                  # Documentação
```

## Contribuição

Contribuições são bem-vindas! Por favor, sinta-se à vontade para enviar pull requests.

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## Autor

Desenvolvido com ❤️ por [SEU_NOME]