# SGC DFe Backup

> Backup automático de XMLs de NF-e autorizados para o **Google Drive**, com trilha de auditoria no **Google Sheets** — pensado para máquinas que passam a maior parte do tempo desligadas.

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-executável-0078D6?logo=windows&logoColor=white)
![Google Drive API](https://img.shields.io/badge/Google%20Drive-API%20v3-4285F4?logo=googledrive&logoColor=white)
![Google Sheets API](https://img.shields.io/badge/Google%20Sheets-API%20v4-34A853?logo=googlesheets&logoColor=white)
![PyInstaller](https://img.shields.io/badge/PyInstaller-onefile-555555)

---

## O problema

Um comércio de hortifrúti em uma central de abastecimento (Ceasa) emite NF-e por um sistema de vendas legado em **xHarbour/xBase**, integrado ao emissor **UniNFe**. A contabilidade precisava receber automaticamente as notas de saída, mas:

- o computador da loja é simples, com poucos recursos;
- ele **fica desligado a maior parte do tempo** e só é ligado para vender e emitir notas;
- robôs de captura que dependem do PC ligado 24h falhariam.

## A solução

Em vez de a contabilidade buscar as notas na máquina, a máquina **empurra** as notas para a nuvem sempre que é ligada:

```
┌─────────────────────┐      ┌──────────────────────┐      ┌───────────────────────┐
│ Sistema xHarbour    │      │  sgc_dfe_backup.exe  │      │  Google Drive         │
│ + UniNFe            │ ───▶ │  varre a pasta local │ ───▶ │  pasta compartilhada  │ ◀── Contabilidade
│ gera *procNFe.xml   │      │  envia só o que falta│      │  (disponível 24h)     │     (acesso 24h)
└─────────────────────┘      └──────────┬───────────┘      └───────────────────────┘
                                        │
                                        ▼
                             ┌──────────────────────┐
                             │  Google Sheets       │
                             │  1 linha por execução│
                             └──────────────────────┘
```

1. O UniNFe grava os XMLs autorizados (`*procNFe.xml`) no disco local.
2. O `sgc_dfe_backup.exe` é executado pontualmente (ao ligar o PC, por atalho ou pelo Agendador de Tarefas).
3. O programa lista o que já existe na pasta do Drive e envia **apenas os arquivos novos**.
4. Cada execução grava uma linha de auditoria na planilha de controle.

A contabilidade passa a ter acesso contínuo às notas, independentemente de a máquina da loja estar ligada.

## Funcionalidades

| Recurso | Descrição |
|---|---|
| **Sincronização incremental** | Compara pelo nome do arquivo; o que já está no Drive não é reenviado. |
| **Varredura recursiva** | Percorre a pasta de autorizados e todas as subpastas (`os.walk`). |
| **Filtro por máscara** | `*procNFe.xml` envia só o XML com protocolo oficial, evitando duplicar com o `-nfe.xml`. |
| **Paginação do Drive** | Lista pastas com qualquer quantidade de arquivos (`nextPageToken`). |
| **Upload resumível** | Usa `MediaFileUpload(resumable=True)`, mais tolerante a conexões instáveis. |
| **Auditoria em planilha** | Registra empresa, pastas, data, hora, total existente na nuvem e total enviado. |
| **Log local** | Erros e uploads ficam em `sgc_dfe_backup.log`. |
| **Execução silenciosa** | Executável único, sem janela de console (`--onefile --noconsole`). |
| **Configuração externa** | Todo o comportamento vem do `.ini`; um mesmo `.exe` atende várias empresas. |

### Planilha de controle

Cada execução acrescenta uma linha em `Página1!A:G`:

| Empresa | Pasta local | Pasta nuvem | Data | Hora | Existentes na nuvem | Novos copiados |
|---|---|---|---|---|---|---|
| Minha Empresa Ltda | C:\Unimake\UniNFe\…\Autorizados | https://drive.google.com/… | 12/11/2026 | 16:19:05 | 42 | 3 |

## Stack

- **Python 3.x**: `configparser`, `logging`, `fnmatch`, `os`, `datetime`
- **Google APIs**: `google-api-python-client`, `google-auth` (conta de serviço)
- **Empacotamento**: PyInstaller
- **Ambiente do cliente**: Windows, UniNFe, sistema legado xHarbour/xBase

## Como usar

### 1. Preparar o Google Cloud

1. Crie um projeto no Google Cloud e ative as APIs **Google Drive** e **Google Sheets**.
2. Crie uma **conta de serviço** e baixe a chave em JSON.
3. Salve a chave como `credenciais.json` ao lado do executável.
4. Compartilhe a **pasta do Drive** e a **planilha** com o e-mail da conta de serviço, como **Editor**.

### 2. Configurar

Copie `sgc_dfe_backup.ini.example` para `sgc_dfe_backup.ini` e preencha:

```ini
[CONFIGURACOES]
empresa = Minha Empresa Ltda
pasta_local = C:\Unimake\UniNFe\00000000000000\Enviado\Autorizados
pasta_nuvem = https://drive.google.com/drive/folders/ID_DA_PASTA
planilha_controle = https://docs.google.com/spreadsheets/d/ID_DA_PLANILHA/edit
mascara = *procNFe.xml
arquivo_credenciais = credenciais.json
```

| Chave | Função |
|---|---|
| `empresa` | Nome que identifica a empresa na planilha. |
| `pasta_local` | Pasta de XMLs autorizados do UniNFe. |
| `pasta_nuvem` | Link da pasta compartilhada do Google Drive. |
| `planilha_controle` | Link da planilha de auditoria. |
| `mascara` | Filtro de arquivos (padrão `*.xml`). |
| `arquivo_credenciais` | Opcional. Caminho do JSON da conta de serviço. |

As credenciais são procuradas nesta ordem: `arquivo_credenciais` do `.ini`, a variável de ambiente `GOOGLE_APPLICATION_CREDENTIALS` e, por fim, `credenciais.json` na pasta de execução.

### 3. Rodar a partir do código

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python sgc_dfe_backup.py
```

### 4. Gerar o executável

```bash
criar_executavel.cmd
```

O script ativa o `venv`, limpa `build/`, `dist/` e `.spec` antigos e gera `dist\sgc_dfe_backup.exe` com o ícone do projeto.

Para distribuir, coloque na mesma pasta:

```
sgc_dfe_backup.exe
sgc_dfe_backup.ini
credenciais.json
```

### 5. Automatizar (opcional)

Crie uma tarefa no **Agendador de Tarefas do Windows** com o gatilho "Ao fazer logon" ou em intervalos regulares, apontando para o `.exe` e com "Iniciar em" definido para a pasta dele (o `.ini`, o log e as credenciais são lidos da pasta de execução).

## Estrutura do repositório

```
├── sgc_dfe_backup.py           # Script principal
├── sgc_dfe_backup.ini.example  # Modelo de configuração
├── criar_executavel.cmd        # Build com PyInstaller
├── requirements.txt            # Dependências
└── sgc_icone1.ico              # Ícone do executável
```

## Segurança

- A chave da conta de serviço **não** fica no código nem no repositório (`credenciais.json` está no `.gitignore`).
- `sgc_dfe_backup.ini`, logs e XMLs também são ignorados: eles contêm CNPJ, chaves de acesso de NF-e e links privados.
- Dê à conta de serviço acesso apenas à pasta e à planilha usadas.

## Autor

**Sérgio Ceará** · [github.com/sergio-ceara](https://github.com/sergio-ceara)
