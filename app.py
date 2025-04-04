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

st.set_page_config(page_title="Assinatura de Holerites", page_icon="logo.png")

# Carrega o logo
try:
    logo_path = "logo.png"
    col1, col2, col3 = st.columns([3, 4, 2])
    with col2:
        st.image(logo_path, width=200)
except Exception as e:
    st.warning(f"Não foi possível carregar o logo: {str(e)}")

# Autenticação Google
credentials_content = st.secrets["google"]["credentials_file"]
try:
    credentials_dict = json.loads(credentials_content)
    creds = service_account.Credentials.from_service_account_info(credentials_dict)
except Exception as e:
    st.error(f"Erro com as credenciais: {str(e)}")
    st.stop()

SPREADSHEET_ID = '1Um6fj1K9n-Ks8_qOEeT4tiu8xqTAX5hU751bvtRjEFk'
RANGE_NAME = 'A1:K'

sheets_service = build('sheets', 'v4', credentials=creds)
drive_service = build('drive', 'v3', credentials=creds)

# Funções auxiliares
def ler_dados_da_planilha():
    result = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])
    if not values:
        return None
    df = pd.DataFrame(values[1:], columns=values[0])
    return df

def atualizar_link_na_planilha(nome_funcionario, link_assinado):
    result = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range='A:A').execute()
    valores = result.get('values', [])
    for i, row in enumerate(valores):
        if i > 0 and row and row[0] == nome_funcionario:
            linha = i + 1
            range_to_update = f'H{linha}'
            body = {'values': [[link_assinado]]}
            sheets_service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=range_to_update,
                valueInputOption='RAW',
                body=body
            ).execute()
            return True
    return False

def baixar_pdf(file_id):
    request = drive_service.files().get_media(fileId=file_id)
    file = io.BytesIO()
    downloader = MediaIoBaseDownload(file, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    file.seek(0)
    return file

def salvar_assinatura_em_temp_file(assinatura):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
        Image.fromarray(assinatura).save(temp_file, format='PNG')
        return temp_file.name

def enviar_pdf_assinado(pdf_assinado, nome_arquivo):
    folder_id = '1gSBcV5EPYYO4mIMh7yNqNs9-GshaR-jR'
    file_metadata = {'name': nome_arquivo, 'parents': [folder_id]}
    media = MediaIoBaseUpload(pdf_assinado, mimetype='application/pdf', resumable=True)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return file.get('id'), file.get('webViewLink')

def verificar_senha(senha_digitada, senha_armazenada):
    return senha_digitada == senha_armazenada

# Inicializa estados
if 'df' not in st.session_state:
    st.session_state.df = ler_dados_da_planilha()
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

st.title("📄 Assinatura de Holerites")

try:
    instrucao_cell = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range='K2').execute()
    instrucao_texto = instrucao_cell.get('values', [['']])[0][0]
    if instrucao_texto:
        st.info(f"ℹ️ {instrucao_texto}")
except:
    pass

df = st.session_state.df

# Autenticação
if not st.session_state.autenticado:
    with st.form(key='login_form'):
        nome = st.selectbox('🧑 Selecione seu nome:', df['NOME'].tolist())
        senha = st.text_input('🔒 Digite sua senha:', type='password')
        if st.form_submit_button('🔓 Entrar'):
            dados_funcionario = df[df['NOME'] == nome].iloc[0]
            if verificar_senha(senha, dados_funcionario['SENHA']):
                st.session_state.autenticado = True
                st.session_state.funcionario = dados_funcionario
                st.session_state.pdf_file = baixar_pdf(dados_funcionario['LINK HOLERITE'].split('/')[-2])
            else:
                st.error("Senha incorreta.")

# Assinatura
if st.session_state.autenticado:
    st.success(f"Bem-vindo(a), {st.session_state.funcionario['NOME']}!")
    st.markdown(f"<p><a href='{st.session_state.funcionario['LINK HOLERITE']}' target='_blank'>🔗 Visualizar holerite original</a></p>", unsafe_allow_html=True)
    st.subheader('✍️ Assine abaixo:')

    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=2,
        stroke_color="#000000",
        background_color="#FFFFFF",
        height=150,
        width=300,
        drawing_mode="freedraw",
        key="canvas",
    )

    if canvas_result.image_data is not None:
        if st.button('🖊️ Assinar e Enviar PDF'):
            with st.spinner('Processando assinatura...'):
                try:
                    assinatura_path = salvar_assinatura_em_temp_file(canvas_result.image_data)
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf_file:
                        temp_pdf_file.write(st.session_state.pdf_file.read())
                        temp_pdf_path = temp_pdf_file.name

                    cpf = st.session_state.funcionario['CPF']
                    pdf_assinado = assinar_pdf(temp_pdf_path, assinatura_path, cpf)

                    nome_arquivo = f"{st.session_state.funcionario['NOME']}_holerite_assinado.pdf"
                    file_id_assinado, web_link = enviar_pdf_assinado(pdf_assinado, nome_arquivo)

                    if atualizar_link_na_planilha(st.session_state.funcionario['NOME'], web_link):
                        st.success("✅ Holerite assinado e link atualizado na planilha!")
                        st.markdown(f"[📄 Visualizar documento assinado]({web_link})")
                    else:
                        st.warning("Holerite assinado, mas falha ao atualizar a planilha.")

                    os.unlink(assinatura_path)
                    os.unlink(temp_pdf_path)

                except Exception as e:
                    st.error(f"Erro ao assinar o PDF: {str(e)}")

    if st.button('↩️ Sair'):
        st.session_state.clear()
        st.rerun()

st.markdown("""
<hr>
<div style='text-align: center; color: gray; font-size: 0.85em;'>
    <p><strong>GENPAC</strong> © 2025 | Todos os direitos reservados.</p>
    <p>Desenvolvido para uso interno - Gestão de Projetos</p>
</div>
""", unsafe_allow_html=True)
