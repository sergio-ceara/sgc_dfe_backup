@echo off
:: Força o script a ir para a pasta onde ele está salvo
cd /d "%~dp0"

:: Configura o prompt para usar codificação UTF-8
chcp 65001 > nul

echo ============================================================
echo   ATIVANDO AMBIENTE VIRTUAL
echo ============================================================
echo.

:: Ativa o ambiente virtual Python (pasta 'venv' ao lado do script)
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo   - Aviso: venv nao encontrado. Usando o Python do sistema.
)

echo.
echo ============================================================
echo   INICIANDO O PROCESSO DE LIMPEZA E COMPILAÇÃO (PyInstaller)
echo ============================================================

:: 1. Apagar as pastas 'build' e 'dist' se elas existirem
echo.
echo [1/3] Limpando pastas antigas...
if exist build (
    rmdir /s /q build
    echo   - Pasta 'build' removida.
)
if exist dist (
    rmdir /s /q dist
    echo   - Pasta 'dist' removida.
)

:: 2. Apagar arquivos com extensão .spec se existirem
echo.
echo [2/3] Removendo arquivos .spec antigos...
if exist *.spec (
    del /q *.spec
    echo   - Arquivos .spec removidos.
) else (
    echo   - Nenhum arquivo .spec encontrado.
)

echo.
echo ============================================================
echo   [3/3] GERANDO O EXECUTÁVEL COM PYINSTALLER
echo ============================================================
echo.

if exist sgc_icone1.ico (
    pyinstaller --clean --onefile --noconsole --icon=sgc_icone1.ico --name sgc_dfe_backup sgc_dfe_backup.py
) else (
    echo   - Aviso: sgc_icone1.ico não encontrado. Compilando sem ícone...
    pyinstaller --clean --onefile --noconsole --name sgc_dfe_backup sgc_dfe_backup.py
)

echo.
echo ============================================================
echo   PROCESSO CONCLUÍDO COM SUCESSO!
echo   O executável está na pasta 'dist'.
echo ============================================================
pause
