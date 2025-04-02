# app.py

import streamlit as st
from auth import get_sheets_service  # Importa a função para obter o serviço do Sheets

# Inicializa o serviço do Google Sheets
sheets_service = get_sheets_service()

# Definir o ID da planilha e o intervalo
SPREADSHEET_ID = '1gSBcV5EPYYO4mIMh7yNqNs9-GshaR-jR'
RANGE_NAME = 'Sheet1!A1:H'

# Exemplo de como acessar a planilha
result = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
values = result.get('values', [])

if not values:
    st.warning("Nenhum dado encontrado na planilha.")
else:
    # Processar os dados da planilha conforme necessário
    st.write(values)

