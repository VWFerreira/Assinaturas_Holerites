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
except json.JSONDecodeError as e:
    st.error(f"Erro ao parsear as credenciais JSON: {str(e)}")
    st.stop()

try:
    creds = service_account.Credentials.from_service_account_info(credentials_dict)
except ValueError as e:
    st.error(f"Erro ao criar credenciais: {str(e)}")
    st.stop()

SPREADSHEET_ID = '1Um6fj1K9n-Ks8_qOEeT4tiu8xqTAX5hU751bvtRjEFk'
RANGE_NAME = 'A1:K'

sheets_service = build('sheets', 'v4', credentials=creds)
drive_service = build('drive', 'v3', credentials=creds)

def ler_dados_da_planilha():
    result = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])
    if not values:
        return None
    df = pd.DataFrame(values[1:], columns=values[0])
    return df

def atualizar_link_na_planilha(nome_funcionario, link_assinado):
    try:
        result = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range='A:A').execute()
        valores = result.get('values', [])
        linha = None
        for i, row in enumerate(valores):
            if i > 0 and row and row[0] == nome_funcionario:
                linha = i + 1
                break
        if linha:
            range_to_update = f'H{linha}'
            valores_para_atualizar = [[link_assinado]]
            body = {'values': valores_para_atualizar}
            result = sheets_service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=range_to_update,
                valueInputOption='RAW',
                body=body
            ).execute()
            return True
        else:
            st.error(f"Não foi possível encontrar a linha para o funcionário {nome_funcionario}")
            return False
    except Exception as e:
        st.error(f"Erro ao atualizar a planilha: {str(e)}")
        return False

def baixar_pdf(file_id):
    request = drive_service.files().get_media(fileId=file_id)
    file = io.BytesIO()
    downloader = MediaIoBaseDownload(file, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    file.seek(0)
    return file

def salvar_assinatura_em_temp_file(assinatura):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
        assinatura_imagem = Image.fromarray(assinatura)
        assinatura_imagem.save(temp_file, format='PNG')
        temp_file_path = temp_file.name
    return temp_file_path

def compartilhar_arquivo(file_id, email):
    try:
        permission = {'type': 'user', 'role': 'reader', 'emailAddress': email}
        drive_service.permissions().create(fileId=file_id, body=permission, sendNotificationEmail=False).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao compartilhar o arquivo: {str(e)}")
        return False

def enviar_pdf_assinado(pdf_assinado, nome_arquivo):
    try:
        folder_id = '1gSBcV5EPYYO4mIMh7yNqNs9-GshaR-jR'
        file_metadata = {'name': nome_arquivo, 'parents': [folder_id]}
        media = MediaIoBaseUpload(pdf_assinado, mimetype='application/pdf', resumable=True)
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        return file.get('id'), file.get('webViewLink')
    except Exception as e:
        st.error(f"Erro ao enviar o arquivo: {str(e)}")
        return None, None

def verificar_senha(senha_digitada, senha_armazenada):
    return senha_digitada == senha_armazenada

st.markdown("<h1 style='text-align: center;'>📄 Assinatura de Holerites</h1>", unsafe_allow_html=True)

try:
    instrucao_cell = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range='K2').execute()
    instrucao_texto = instrucao_cell.get('values', [['']])[0][0]
    if instrucao_texto:
        st.info(f"ℹ️ {instrucao_texto}")
except Exception as e:
    st.warning(f"Não foi possível carregar a instrução (K2): {str(e)}")

st.markdown("""
<div style="background-color: #8B0000; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
    <h4> 🛈 Instruções:</h4>
    <ul>
        <li>🧑‍💼 Selecione seu nome na lista.</li>
        <li>🔐 Digite sua senha corretamente.</li>
        <li>🖊️ Desenhe sua assinatura com clareza.</li>
        <li>✅ Clique em <strong>\"Assinar PDF\"</strong> para finalizar.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

if 'df' not in st.session_state:
    st.session_state.df = ler_dados_da_planilha()
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'funcionario_selecionado' not in st.session_state:
    st.session_state.funcionario_selecionado = None
if 'link_holerite' not in st.session_state:
    st.session_state.link_holerite = None
if 'file_id' not in st.session_state:
    st.session_state.file_id = None
if 'pdf_file' not in st.session_state:
    st.session_state.pdf_file = None

df = st.session_state.df

def autenticar_usuario():
    dados_funcionario = df[df['NOME'] == st.session_state.funcionario_selecionado].iloc[0]
    senha_armazenada = dados_funcionario.iloc[8]
    if verificar_senha(st.session_state.senha, senha_armazenada):
        st.session_state.autenticado = True
        st.session_state.link_holerite = dados_funcionario.iloc[5]

        # Verifica se o link está presente e bem formatado
        link = st.session_state.link_holerite
        if link and "drive.google.com" in link and "/" in link:
            partes = link.split('/')
            if len(partes) >= 6:
                st.session_state.file_id = partes[-2]
                st.session_state.pdf_file = baixar_pdf(st.session_state.file_id)
            else:
                st.error("O link do holerite está mal formatado.")
                st.session_state.autenticado = False
        else:
            st.error("Link do holerite inválido ou ausente.")
            st.session_state.autenticado = False
    else:
        st.session_state.autenticado = False
        st.error('Senha incorreta.')


with st.container():
    if not st.session_state.autenticado:
        if df is not None:
            with st.form(key='login_form'):
                st.session_state.funcionario_selecionado = st.selectbox('🧑 Selecione seu nome:', df['NOME'].tolist())
                st.session_state.senha = st.text_input('🔒 Digite sua senha:', type='password')
                submit_button = st.form_submit_button(label='🔓 Entrar')
                if submit_button:
                    autenticar_usuario()
        else:
            st.warning('Não foram encontrados dados na planilha.')
    else:
        st.success(f"Bem-vindo(a), {st.session_state.funcionario_selecionado}!")
        st.markdown(f"""
        <div style="padding: 10px; border-radius: 5px; border: 1px solid #e6e6e6; margin-bottom: 10px;">
            <h4>Seu holerite está disponível</h4>
            <p>Link: <a href="{st.session_state.link_holerite}" target="_blank">Visualizar holerite original</a></p>
        </div>
        """, unsafe_allow_html=True)
        st.subheader('Assine aqui:')
        st.markdown("""
        <p style="color: #666; font-size: 0.9em;">
            Use o mouse ou toque para desenhar sua assinatura no campo abaixo. 
            Certifique-se de que a assinatura esteja clara e completa.
        </p>
        """, unsafe_allow_html=True)
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
            st.session_state.signature = canvas_result.image_data
        if canvas_result.image_data is not None and st.button('🖊️ Assinar e Enviar PDF'):
            with st.spinner('Processando assinatura...'):
                try:
                    cpf = df[df['NOME'] == st.session_state.funcionario_selecionado].iloc[0]['CPF']
                    pdf_assinado = assinar_pdf(temp_pdf_path, assinatura_temp_file_path, cpf)
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf_file:
                        temp_pdf_file.write(st.session_state.pdf_file.read())
                        temp_pdf_path = temp_pdf_file.name
                    pdf_assinado = assinar_pdf(temp_pdf_path, assinatura_temp_file_path)
                    nome_arquivo = f"{st.session_state.funcionario_selecionado}_holerite_assinado.pdf"
                    file_id_assinado, web_link = enviar_pdf_assinado(pdf_assinado, nome_arquivo)
                    if file_id_assinado and web_link:
                        if atualizar_link_na_planilha(st.session_state.funcionario_selecionado, web_link):
                            st.success("Holerite assinado com sucesso e link atualizado na planilha!")
                            st.markdown(f"""
                            <div style="padding: 15px; border-radius: 5px; border: 1px solid #d4edda; background-color: #d4edda; margin: 10px 0;">
                                <h4 style="color: #155724;">Documento assinado com sucesso!</h4>
                                <p style="margin: 5px 0;"><a href="{web_link}" target="_blank">Abrir documento assinado</a></p>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.warning("Holerite assinado com sucesso, mas não foi possível atualizar o link na planilha.")
                            st.markdown(f"**Link para visualização:** [Abrir documento]({web_link})")
                    else:
                        st.error("Não foi possível salvar o arquivo assinado.")
                    try:
                        os.unlink(assinatura_temp_file_path)
                        os.unlink(temp_pdf_path)
                    except:
                        pass
                except Exception as e:
                    st.error(f"Ocorreu um erro durante o processo de assinatura: {str(e)}")
        if st.button('↩️ Sair'):
            st.session_state.clear()
            st.rerun()

st.markdown("""
<hr>
<div style='text-align: center; color: gray; font-size: 0.85em;'>
    <p><strong>GENPAC</strong> © 2025 | Todos os direitos reservados.</p>
    <p>Desenvolvido para uso interno - Gestão de Progetos</p>
</div>
""", unsafe_allow_html=True)
