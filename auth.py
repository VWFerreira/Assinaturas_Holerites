import os
from dotenv import load_dotenv
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
def get_sheets_service():
    return build('sheets', 'v4', credentials=credentials)

def get_drive_service():
    return build('drive', 'v3', credentials=credentials)
