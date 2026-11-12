# SGC DFe Backup
# Sincroniza XMLs autorizados de NF-e (UniNFe) com uma pasta do Google Drive
# e registra cada execução em uma planilha de controle do Google Sheets.
#
# Ambiente:
#   python -m venv venv
#   venv\Scripts\activate
#   pip install -r requirements.txt
import os
import sys
import configparser
import logging
import fnmatch
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configuração de Logs Locais
logging.basicConfig(
    filename='sgc_dfe_backup.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# ==========================================
# CREDENCIAIS
# ==========================================
# A chave da conta de serviço NÃO fica no código-fonte.
# Ordem de busca:
#   1. Caminho informado em 'arquivo_credenciais' no .ini
#   2. Variável de ambiente GOOGLE_APPLICATION_CREDENTIALS
#   3. 'credenciais.json' na pasta de execução
ARQUIVO_CREDENCIAIS_PADRAO = 'credenciais.json'

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

def ler_configuracao():
    config = configparser.ConfigParser()
    caminho_ini = 'sgc_dfe_backup.ini'

    if not os.path.exists(caminho_ini):
        logging.error("Arquivo sgc_dfe_backup.ini não encontrado.")
        sys.exit(1)

    config.read(caminho_ini, encoding='utf-8')
    return {
        'empresa': config.get('CONFIGURACOES', 'empresa', fallback='Desconhecida'),
        'pasta_local': config.get('CONFIGURACOES', 'pasta_local', fallback=''),
        'pasta_nuvem_link': config.get('CONFIGURACOES', 'pasta_nuvem', fallback=''),
        'planilha_link': config.get('CONFIGURACOES', 'planilha_controle', fallback=''),
        'mascara': config.get('CONFIGURACOES', 'mascara', fallback='*.xml').strip(),
        'arquivo_credenciais': config.get('CONFIGURACOES', 'arquivo_credenciais', fallback='').strip()
    }

def extrair_id_drive(link):
    try:
        if 'folders/' in link:
            return link.split('folders/')[1].split('?')[0]
        elif 'd/' in link:
            return link.split('d/')[1].split('/')[0]
    except Exception as e:
        logging.error(f"Erro ao extrair ID do link do Drive/Planilha: {e}")
    return None

def localizar_credenciais(caminho_ini):
    candidatos = [
        caminho_ini,
        os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', ''),
        ARQUIVO_CREDENCIAIS_PADRAO
    ]
    for caminho in candidatos:
        if caminho and os.path.exists(caminho):
            return caminho
    return None

def autenticar_google(caminho_ini):
    caminho = localizar_credenciais(caminho_ini)
    if not caminho:
        logging.error("Arquivo de credenciais da conta de serviço não encontrado.")
        return None
    try:
        creds = service_account.Credentials.from_service_account_file(
            caminho, scopes=SCOPES
        )
        return creds
    except Exception as e:
        logging.error(f"Erro na autenticação das credenciais ({caminho}): {e}")
        return None

def listar_arquivos_nuvem(service, folder_id):
    arquivos_nuvem = set()
    page_token = None
    try:
        while True:
            query = f"'{folder_id}' in parents and trashed = false"
            response = service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(name)',
                pageToken=page_token
            ).execute()

            for file in response.get('files', []):
                arquivos_nuvem.add(file['name'])

            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
    except Exception as e:
        logging.error(f"Erro ao listar arquivos na nuvem: {e}")
    return arquivos_nuvem

def fazer_upload_arquivo(service, folder_id, caminho_arquivo, nome_arquivo):
    try:
        file_metadata = {
            'name': nome_arquivo,
            'parents': [folder_id]
        }
        media = MediaFileUpload(caminho_arquivo, resumable=True)
        service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        logging.info(f"Upload realizado: {nome_arquivo}")
    except Exception as e:
        logging.error(f"Erro ao enviar o arquivo {nome_arquivo}: {e}")

def registrar_na_planilha(sheets_service, planilha_id, dados):
    try:
        body = {
            'values': [dados]
        }
        sheets_service.spreadsheets().values().append(
            spreadsheetId=planilha_id,
            range='Página1!A:G',
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        logging.info("Registro de controle gravado na planilha com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao gravar dados na planilha Google Sheets: {e}")

def main():
    print("Iniciando rotina de sincronização e controle de DF-e...")
    config = ler_configuracao()

    pasta_local = config['pasta_local']
    folder_id = extrair_id_drive(config['pasta_nuvem_link'])
    planilha_id = extrair_id_drive(config['planilha_link'])
    mascara = config['mascara']

    if not os.path.exists(pasta_local):
        print(f"Pasta local não encontrada: {pasta_local}")
        return

    creds = autenticar_google(config['arquivo_credenciais'])
    if not creds:
        print("Erro ao processar credenciais de acesso.")
        return

    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)

    # 1. Contar existentes na nuvem
    arquivos_nuvem = listar_arquivos_nuvem(drive_service, folder_id)
    qtd_existentes = len(arquivos_nuvem)

    # 2. Varrer pasta local aplicando a máscara e filtrar novos
    qtd_copiadas = 0
    for root, dirs, files in os.walk(pasta_local):
        for file in files:
            # Aplica a máscara configurada (ex: *procNFe.xml)
            if fnmatch.fnmatch(file, mascara):
                caminho_completo = os.path.join(root, file)
                if file not in arquivos_nuvem:
                    print(f"Enviando XML autorizado: {file}")
                    fazer_upload_arquivo(drive_service, folder_id, caminho_completo, file)
                    qtd_copiadas += 1

    # 3. Registrar execução na planilha
    agora = datetime.now()
    data_execucao = agora.strftime('%d/%m/%Y')
    horario_execucao = agora.strftime('%H:%M:%S')

    dados_linha = [
        config['empresa'],
        config['pasta_local'],
        config['pasta_nuvem_link'],
        data_execucao,
        horario_execucao,
        qtd_existentes,
        qtd_copiadas
    ]

    registrar_na_planilha(sheets_service, planilha_id, dados_linha)

    print(f"Processo finalizado! Existentes na nuvem: {qtd_existentes} | Novos copiados: {qtd_copiadas}")

if __name__ == '__main__':
    main()
