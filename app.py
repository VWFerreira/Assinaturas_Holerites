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
    # Caminho para o logo (local ou URL)
    logo_path = "logo.png"
    
  # Criando 3 colunas (uma centralizada)
    col1, col2, col3 = st.columns([3, 4, 2])
    
    # Exibindo a imagem na coluna do meio
    with col2:
        st.image(logo_path, width=200)
except Exception as e:
    st.warning(f"Não foi possível carregar o logo: {str(e)}")

# Acessar as credenciais armazenadas nos segredos do Streamlit
credentials_content = st.secrets["google"]["credentials_file"]

# Parse the JSON string into a dictionary
try:
    credentials_dict = json.loads(credentials_content)
except json.JSONDecodeError as e:
    st.error(f"Erro ao parsear as credenciais JSON: {str(e)}")
    st.stop()

# Criar as credenciais do Google usando o dicionário parsed
try:
    creds = service_account.Credentials.from_service_account_info(credentials_dict)
except ValueError as e:
    st.error(f"Erro ao criar credenciais: {str(e)}")
    st.stop()

SPREADSHEET_ID = '1Um6fj1K9n-Ks8_qOEeT4tiu8xqTAX5hU751bvtRjEFk'
RANGE_NAME = 'A1:I'  # Inclui a coluna de senha

# Inicializa as APIs do Google Sheets e Google Drive
sheets_service = build('sheets', 'v4', credentials=creds)
drive_service = build('drive', 'v3', credentials=creds)

# Função para ler os dados da planilha
def ler_dados_da_planilha():
    result = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])
    if not values:
        return None
    df = pd.DataFrame(values[1:], columns=values[0])
    return df

# Função para atualizar o link do documento assinado na planilha
def atualizar_link_na_planilha(nome_funcionario, link_assinado):
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='A:A'
        ).execute()
        
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

# Função para baixar o arquivo PDF do Google Drive
def baixar_pdf(file_id):
    request = drive_service.files().get_media(fileId=file_id)
    file = io.BytesIO()
    downloader = MediaIoBaseDownload(file, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    file.seek(0)
    return file

# Função para salvar a assinatura em um arquivo temporário
def salvar_assinatura_em_temp_file(assinatura):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
        assinatura_imagem = Image.fromarray(assinatura)
        assinatura_imagem.save(temp_file, format='PNG')
        temp_file_path = temp_file.name
    return temp_file_path

# Função para compartilhar o arquivo no Google Drive
def compartilhar_arquivo(file_id, email):
    try:
        permission = {'type': 'user', 'role': 'reader', 'emailAddress': email}
        drive_service.permissions().create(fileId=file_id, body=permission, sendNotificationEmail=False).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao compartilhar o arquivo: {str(e)}")
        return False

# Função para enviar o PDF assinado para o Google Drive
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

# Função para verificar a senha
def verificar_senha(senha_digitada, senha_armazenada):
    return senha_digitada == senha_armazenada


# Interface Streamlit
st.markdown("<h1 style='text-align: center;'>Assinatura de Holerites</h1>", unsafe_allow_html=True)

# Aplicar CSS para melhorar a aparência
st.markdown("""
<style>
    .main {
        padding: 1rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
    }
    .footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        text-align: center;
        padding: 10px;
        background-color: white;
    }
</style>
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

if 'senha' not in st.session_state:
    st.session_state.senha = None


df = st.session_state.df

def autenticar_usuario():
    if st.session_state.funcionario_selecionado not in df['NOME'].values:
        st.error("Funcionário não encontrado na planilha. Verifique o nome selecionado.")
        return

    dados_funcionario = df[df['NOME'] == st.session_state.funcionario_selecionado].iloc[0]
    senha_armazenada = dados_funcionario.iloc[8]  # Coluna I com a senha

    if verificar_senha(st.session_state.senha, senha_armazenada):
        st.session_state.autenticado = True
        st.session_state.funcionario_selecionado = dados_funcionario.iloc[0]  # Nome

        st.session_state.link_holerite = dados_funcionario.iloc[5]  # Coluna F
        if not st.session_state.link_holerite or 'drive.google.com' not in st.session_state.link_holerite:
            st.warning("⚠️ Aguarde! Ainda não há holerite disponível para você.")
            return

        st.session_state.file_id = st.session_state.link_holerite.split('/')[-2]
        st.session_state.pdf_file = baixar_pdf(st.session_state.file_id)
    else:
        st.session_state.autenticado = False
        st.error('Senha incorreta.')


with st.container():
    if not st.session_state.autenticado:
        if df is not None:
            with st.form(key='login_form'):
                st.session_state.funcionario_selecionado = st.selectbox('👤 Selecione seu nome:', df['NOME'].tolist())
                st.session_state.senha = st.text_input('🔒 Digite sua senha:', type='password')
                if st.form_submit_button('Entrar'):
                    autenticar_usuario()
        else:
            st.warning('⚠️ Não foram encontrados dados na planilha.')

    else:
        st.success(f"Bem-vindo(a), {st.session_state.funcionario_selecionado}!")

        st.markdown(f"""
        <div style="padding: 10px; border-radius: 5px; border: 1px solid #e6e6e6; margin-bottom: 10px;">
            <h4>📄 Seu holerite está disponível</h4>
            <p>🔗 <a href="{st.session_state.link_holerite}" target="_blank">Visualizar holerite original</a></p>
        </div>
        """, unsafe_allow_html=True)

        st.subheader('🖊️ Assine aqui:')
        st.markdown("<p style='color: #666;'>Use o mouse ou toque para desenhar sua assinatura abaixo.</p>", unsafe_allow_html=True)

        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",  
            stroke_width=2,
            stroke_color="#000000",
            background_color="#FFFFFF",
            height=150,
            width=300,
            drawing_mode="freedraw",
            key="canvas"
        )

        if canvas_result.image_data is not None:
            st.session_state.signature = canvas_result.image_data

        if canvas_result.image_data is not None and st.button('✍️ Assinar e Enviar Holerite', use_container_width=True):
            with st.spinner('Processando assinatura...'):
                try:
                    assinatura_temp_file_path = salvar_assinatura_em_temp_file(st.session_state.signature)
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf_file:
                        temp_pdf_file.write(st.session_state.pdf_file.read())
                        temp_pdf_path = temp_pdf_file.name

                    pdf_assinado = assinar_pdf(temp_pdf_path, assinatura_temp_file_path)
                    nome_arquivo = f"{st.session_state.funcionario_selecionado}_holerite_assinado.pdf"
                    file_id_assinado, web_link = enviar_pdf_assinado(pdf_assinado, nome_arquivo)

                    if file_id_assinado and web_link:
                        if atualizar_link_na_planilha(st.session_state.funcionario_selecionado, web_link):
                            st.success("✅ Holerite assinado com sucesso e link atualizado!")
                            st.markdown(f"<a href='{web_link}' target='_blank'>📎 Abrir holerite assinado</a>", unsafe_allow_html=True)
                        else:
                            st.warning("Holerite assinado, mas não foi possível atualizar a planilha.")
                    else:
                        st.error("Erro ao salvar o arquivo assinado.")

                    os.unlink(assinatura_temp_file_path)
                    os.unlink(temp_pdf_path)

                except Exception as e:
                    st.error(f"Erro ao processar a assinatura: {str(e)}")

        if st.button('🚪 Sair'):
            st.session_state.clear()
            st.experimental_rerun()

st.markdown("""
<hr>
<div style='text-align: center; color: gray; font-size: 0.9em; margin-top: 10px;'>
    Desenvolvido com 💻 por <strong>GENPAC</strong> • Sistema de Assinatura de Holerites • © 2025<br>
    <a href='mailto:suporte@genpac.com.br' style='color: #888;'>suporte@genpac.com.br</a>
</div>
""", unsafe_allow_html=True)


