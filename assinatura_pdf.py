from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime
import io
from PIL import Image
import pandas as pd

def remover_fundo(assinatura_path):
    img = Image.open(assinatura_path).convert("RGBA")
    datas = img.getdata()
    new_data = [
        (255, 255, 255, 0) if item[0] > 200 and item[1] > 200 and item[2] > 200 else item
        for item in datas
    ]
    img.putdata(new_data)
    assinatura_sem_fundo_path = "assinatura_sem_fundo.png"
    img.save(assinatura_sem_fundo_path, "PNG")
    return assinatura_sem_fundo_path

def obter_cpf(nome_colaborador, caminho_planilha):
    """
    Lê o CPF do funcionário com base no nome da planilha.
    A coluna E (índice 4) é considerada como CPF.
    """
    df = pd.read_excel(caminho_planilha, sheet_name="funcionarios")
    # Ajuste aqui conforme o nome da coluna de identificação do colaborador
    colaborador = df[df.iloc[:, 0].str.lower() == nome_colaborador.lower()]
    if not colaborador.empty:
        return colaborador.iloc[0, 4]  # Coluna E (índice 4)
    return "CPF não encontrado"

def assinar_pdf(pdf_path, assinatura_path, nome_colaborador, caminho_planilha):
    assinatura_sem_fundo = remover_fundo(assinatura_path)
    pdf_reader = PdfReader(pdf_path)
    pdf_writer = PdfWriter()

    cpf = obter_cpf(nome_colaborador, caminho_planilha)

    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    largura, altura = letter

    c.drawString(100, 250, "Assinatura do colaborador:")
    c.drawImage(assinatura_sem_fundo, 100, 180, width=200, height=50)
    
    now = datetime.now()
    data_hora = now.strftime("%d/%m/%Y %H:%M:%S")
    c.drawString(100, 140, f"Data e hora: {data_hora}")
    c.drawString(100, 120, f"CPF: {cpf}")

    c.save()
    packet.seek(0)
    signature_pdf = PdfReader(packet)

    for i in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[i]
        if i == 0:
            page.merge_page(signature_pdf.pages[0])
        pdf_writer.add_page(page)

    output = io.BytesIO()
    pdf_writer.write(output)
    output.seek(0)
    return output



