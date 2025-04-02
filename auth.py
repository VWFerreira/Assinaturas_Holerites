import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Carregar as credenciais do Google armazenadas na variável de ambiente
google_credentials_json = os.getenv('GOOGLE_CREDENTIALS')

# Verificar se a variável de ambiente está definida corretamente
if google_credentials_json is None:
    raise ValueError("A variável GOOGLE_CREDENTIALS não está definida!")

# Carregar as credenciais do serviço a partir da string JSON
google_credentials = json.loads(google_credentials_json)

# Agora você pode usar as credenciais para acessar a API do Google
credentials = service_account.Credentials.from_service_account_info(google_credentials)

# Criar o serviço da API do Sheets
sheets_service = build('sheets', 'v4', credentials=credentials)

# Exemplo de acesso à planilha
SPREADSHEET_ID = '1gSBcV5EPYYO4mIMh7yNqNs9-GshaR-jR'
RANGE_NAME = 'Sheet1!A1:H'

result = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()

