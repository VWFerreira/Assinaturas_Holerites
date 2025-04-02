import os
from dotenv import load_dotenv
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Carregar as variáveis de ambiente do arquivo .env
load_dotenv()

# Obter as credenciais do ambiente
google_credentials = os.getenv('GOOGLE_CREDENTIALS_JSON')

# Salvar as credenciais em um arquivo temporário
with open('credentials.json', 'w') as f:
    f.write(google_credentials)

# Carregar as credenciais
credentials = service_account.Credentials.from_service_account_file('credentials.json')

# Criar o serviço da API do Sheets
sheets_service = build('sheets', 'v4', credentials=credentials)

# Exemplo de como acessar a planilha
SPREADSHEET_ID = '1gSBcV5EPYYO4mIMh7yNqNs9-GshaR-jR'
RANGE_NAME = 'Sheet1!A1:H'

result = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
