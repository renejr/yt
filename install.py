import sys
import subprocess
import os
import platform
from pathlib import Path

def check_python_version():
    """Verifica se a versão do Python é compatível"""
    required_version = (3, 7)
    current_version = sys.version_info
    
    if current_version < required_version:
        print(f"\033[91mERRO: Python {required_version[0]}.{required_version[1]} ou superior é necessário.")
        print(f"Versão atual: {current_version[0]}.{current_version[1]}\033[0m")
        return False
    return True

def install_requirements():
    """Instala as dependências do projeto"""
    try:
        print("\033[94mInstalando dependências...\033[0m")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("\033[92mDependências instaladas com sucesso!\033[0m")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\033[91mERRO ao instalar dependências: {e}\033[0m")
        return False

def check_ffmpeg():
    """Verifica se os arquivos do FFmpeg estão presentes"""
    required_files = ['ffmpeg.exe', 'ffprobe.exe', 'ffplay.exe']
    missing_files = []
    
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("\033[93mAVISO: Arquivos FFmpeg necessários não encontrados:")
        for file in missing_files:
            print(f"- {file}")
        print("Por favor, certifique-se de que os arquivos FFmpeg estão no diretório do projeto.\033[0m")
        return False
    return True

def setup_environment():
    """Configura o ambiente do projeto"""
    # Criar diretório de logs se não existir
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Verificar permissões de escrita
    try:
        test_file = log_dir / 'test.txt'
        test_file.touch()
        test_file.unlink()
        print("\033[92mDiretório de logs configurado com sucesso!\033[0m")
    except Exception as e:
        print(f"\033[91mERRO ao configurar diretório de logs: {e}\033[0m")
        return False
    return True

def main():
    print("\033[95m=== Instalador do Baixador de Vídeos YouTube ===")
    print("Verificando requisitos do sistema...\033[0m")
    
    # Verificar versão do Python
    if not check_python_version():
        return False
    
    # Instalar dependências
    if not install_requirements():
        return False
    
    # Verificar FFmpeg
    if not check_ffmpeg():
        print("\033[93mPor favor, baixe os arquivos FFmpeg e coloque-os no diretório do projeto.\033[0m")
    
    # Configurar ambiente
    if not setup_environment():
        return False
    
    print("\n\033[92m=== Instalação concluída com sucesso! ===\nVocê pode agora executar o programa usando: python yt_refactored.py\033[0m")
    return True

if __name__ == '__main__':
    try:
        success = main()
        if not success:
            print("\033[91m\nInstalação não foi concluída devido a erros.\033[0m")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\033[91mInstalação cancelada pelo usuário.\033[0m")
        sys.exit(1)
    except Exception as e:
        print(f"\033[91m\nErro inesperado durante a instalação: {e}\033[0m")
        sys.exit(1)