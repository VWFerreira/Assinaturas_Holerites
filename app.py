import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import io
import tempfile
from PIL import Image
from assinatura_pdf import assinar_pdf  # Importando a função de assinatura
from streamlit_drawable_canvas import st_canvas

# Acessar as credenciais armazenadas nos segredos
credentials_content = st.secrets["google"]["credentials_file"]

SPREADSHEET_ID = '1Um6fj1K9n-Ks8_qOEeT4tiu8xqTAX5hU751bvtRjEFk'
RANGE_NAME = 'A1:H'  # Inclui a coluna de senha

# Carrega as credenciais do Google
creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)

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
            range_to_update = f'G{linha}'
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
st.title('Assinatura Eletrônica de Holerites')

# Inicializa o estado da sessão
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
    senha_armazenada = dados_funcionario.iloc[7]  # Coluna H com a senha armazenada
    
    if verificar_senha(st.session_state.senha, senha_armazenada):
        st.session_state.autenticado = True
        st.session_state.link_holerite = dados_funcionario.iloc[4]  # Coluna E com o link do holerite
        st.session_state.file_id = st.session_state.link_holerite.split('/')[-2]  # Extrai o file_id do link
        st.session_state.pdf_file = baixar_pdf(st.session_state.file_id)
    else:
        st.session_state.autenticado = False
        st.error('Senha incorreta.')

# Página de login se não estiver autenticado
if not st.session_state.autenticado:
    if df is not None:
        st.session_state.funcionario_selecionado = st.selectbox('Selecione seu nome:', df['NOME'].tolist())
        st.session_state.senha = st.text_input('Digite sua senha:', type='password')
        
        if st.button('Entrar'):
            autenticar_usuario()
    else:
        st.warning('Não foram encontrados dados na planilha.')
# Página após autenticação
else:
    st.success(f"Bem-vindo(a), {st.session_state.funcionario_selecionado}!")
    st.write(f"Link do holerite: {st.session_state.link_holerite}")
    
    st.subheader('Assine aqui:')
    
    # Criar o canvas para assinatura
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

    # Salvar a assinatura desenhada
    if canvas_result.image_data is not None:
        st.session_state.signature = canvas_result.image_data

    # Se já existe uma assinatura, exiba o botão para assinar o PDF
    if canvas_result.image_data is not None and st.button('Assinar PDF'):
        try:
            # Salva a assinatura como arquivo temporário
            assinatura_temp_file_path = salvar_assinatura_em_temp_file(st.session_state.signature)
            
            # Agora a assinatura é salva em um arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf_file:
                # Salve o PDF original em um arquivo temporário
                temp_pdf_file.write(st.session_state.pdf_file.read())
                temp_pdf_path = temp_pdf_file.name
            
            # Chama a função para assinar o PDF com a assinatura
            pdf_assinado = assinar_pdf(temp_pdf_path, assinatura_temp_file_path)
            
            nome_arquivo = f"{st.session_state.funcionario_selecionado}_holerite_assinado.pdf"
            
            # Envia o PDF assinado para o Google Drive e pega o link
            file_id_assinado, web_link = enviar_pdf_assinado(pdf_assinado, nome_arquivo)
            
            if file_id_assinado and web_link:
                # Atualiza o link do documento assinado na planilha
                if atualizar_link_na_planilha(st.session_state.funcionario_selecionado, web_link):
                    st.success(f"Holerite assinado com sucesso e link atualizado na planilha!")
                    st.markdown(f"**ID do arquivo:** {file_id_assinado}")
                    st.markdown(f"**Link para visualização:** [Abrir documento]({web_link})")
                else:
                    st.warning("Holerite assinado com sucesso, mas não foi possível atualizar o link na planilha.")
                    st.markdown(f"**Link para visualização:** [Abrir documento]({web_link})")
            else:
                st.error("Não foi possível salvar o arquivo assinado.")
        except Exception as e:
            st.error(f"Ocorreu um erro durante o processo de assinatura: {str(e)}")
    
    if st.button('Sair'):
        # Limpa o estado da sessão
        st.session_state.clear()  # Limpa o estado da sessão





