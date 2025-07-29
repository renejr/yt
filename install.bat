@echo off
chcp 65001 > nul

echo ===================================
echo Instalador - Baixador de Videos YouTube
echo ===================================
echo.

:: Verificar se Python está instalado
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [31mERRO: Python não encontrado![0m
    echo Por favor, instale o Python 3.7 ou superior.
    echo Você pode baixá-lo em: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Executar script de instalação
echo Iniciando instalação...
echo.
python install.py

if %errorlevel% neq 0 (
    echo.
    echo [31mA instalação falhou. Por favor, verifique os erros acima.[0m
    pause
    exit /b 1
)

echo.
echo [32mPressione qualquer tecla para sair...[0m
pause >nul