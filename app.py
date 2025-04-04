import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import io
import tempfile
from PIL import Image
from assinatura_pdf import assinar_pdf
from streamlit_drawable_canvas import st_canvas
import json
import os

# Configuração do título da página
st.set_page_config(page_title="Assinatura de Holerites", page_icon="📄")

# Tentativa de exibir o logo com tratamento de erro
try:
    logo_path = "logo.png"
    col1, col2, col3 = st.columns([3, 4, 2])
    with col2:
        st.image(logo_path, width=200)
except Exception as e:
    st.warning(f"Não foi possível carregar o logo: {str(e)}")

credentials_content = st.secrets["google"]["credentials_file"]
try:
    credentials_dict = json.loads(credentials_content)
    creds = service_account.Credentials.from_service_account_info(credentials_dict)
except Exception as e:
    st.error(f"Erro nas credenciais: {str(e)}")
    st.stop()

SPREADSHEET_ID = '1Um6fj1K9n-Ks8_qOEeT4tiu8xqTAX5hU751bvtRjEFk'
RANGE_NAME = 'A1:I'
FOLDER_ID = '1gSBcV5EPYYO4mIMh7yNqNs9-GshaR-jR'

sheets_service = build('sheets', 'v4', credentials=creds)
drive_service = build('drive', 'v3', credentials=creds)

def ler_dados_da_planilha():
    values = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute().get('values', [])
    return pd.DataFrame(values[1:], columns=values[0]) if values else None

def atualizar_link_na_planilha(nome_funcionario, link):
    valores = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range='A:A').execute().get('values', [])
    for i, row in enumerate(valores):
        if i > 0 and row and row[0] == nome_funcionario:
            sheets_service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f'G{i+1}',
                valueInputOption='RAW',
                body={'values': [[link]]}
            ).execute()
            return True
    return False

def baixar_pdf(file_id):
    request = drive_service.files().get_media(fileId=file_id)
    file = io.BytesIO()
    downloader = MediaIoBaseDownload(file, request)
    while not downloader.next_chunk()[1]: pass
    file.seek(0)
    return file

def salvar_assinatura_em_temp_file(assinatura):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp:
        Image.fromarray(assinatura).save(temp, format='PNG')
        return temp.name

def enviar_pdf_assinado(pdf_assinado, nome_arquivo):
    media = MediaIoBaseUpload(pdf_assinado, mimetype='application/pdf', resumable=True)
    file_metadata = {'name': nome_arquivo, 'parents': [FOLDER_ID]}
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return file.get('id'), file.get('webViewLink')

def verificar_senha(senha_digitada, senha_certa):
    return senha_digitada == senha_certa

if 'df' not in st.session_state:
    st.session_state.df = ler_dados_da_planilha()
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

st.markdown("<h1 style='text-align: center;'>Assinatura de Holerites</h1>", unsafe_allow_html=True)

if not st.session_state.autenticado:
    df = st.session_state.df
    if df is not None:
        with st.form("login"):
            nome = st.selectbox("Selecione seu nome:", df['NOME'])
            senha = st.text_input("Digite sua senha:", type='password')
            submit = st.form_submit_button("Entrar")
            if submit:
                dados = df[df['NOME'] == nome].iloc[0]
                if verificar_senha(senha, dados['SENHA']):
                    st.session_state.autenticado = True
                    st.session_state.nome = nome
                    st.session_state.link = dados[5]  # Coluna F
                    st.session_state.file_id = dados[5].split("/")[-2]  # Coluna F
                    st.session_state.pdf = baixar_pdf(st.session_state.file_id)
                else:
                    st.error("Senha incorreta")
    else:
        st.warning("Planilha vazia")
else:
    st.success(f"Bem-vindo(a), {st.session_state.nome}!")
    st.markdown(f"<p><b>Visualizar holerite:</b> <a href='{st.session_state.link}' target='_blank'>Clique aqui</a></p>", unsafe_allow_html=True)

    st.subheader("Assine aqui")
    st.markdown("<p style='color:gray;'>Use o mouse ou toque para assinar abaixo:</p>", unsafe_allow_html=True)

    canvas = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=2,
        stroke_color="#000000",
        background_color="#FFFFFF",
        height=150,
        width=400,
        drawing_mode="freedraw",
        key="canvas"
    )

    if canvas.image_data is not None:
        assinatura_path = salvar_assinatura_em_temp_file(canvas.image_data)

        if st.button("✍️ Assinar e Enviar Holerite", use_container_width=True):
            with st.spinner("Processando..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp:
                        temp.write(st.session_state.pdf.read())
                        pdf_path = temp.name

                    pdf_assinado = assinar_pdf(pdf_path, assinatura_path)
                    nome_arquivo = f"{st.session_state.nome}_holerite_assinado.pdf"
                    file_id, web_link = enviar_pdf_assinado(pdf_assinado, nome_arquivo)

                    if file_id and web_link:
                        if atualizar_link_na_planilha(st.session_state.nome, web_link):
                            st.success("Assinado e atualizado com sucesso!")
                            st.markdown(f"<a href='{web_link}' target='_blank'>📄 Abrir holerite assinado</a>", unsafe_allow_html=True)
                        else:
                            st.warning("Assinado, mas falha ao atualizar link.")
                except Exception as e:
                    st.error(f"Erro: {str(e)}")

    if st.button("Sair"):
        st.session_state.clear()
        st.experimental_rerun()

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>By GENPAC 2025</p>", unsafe_allow_html=True)
