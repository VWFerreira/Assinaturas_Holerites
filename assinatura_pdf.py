from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime
import io
from PIL import Image

def remover_fundo(assinatura_path):
    img = Image.open(assinatura_path)
    img = img.convert("RGBA")
    datas = img.getdata()

    new_data = []
    for item in datas:
        if item[0] > 200 and item[1] > 200 and item[2] > 200:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)

    img.putdata(new_data)
    assinatura_sem_fundo_path = "assinatura_sem_fundo.png"
    img.save(assinatura_sem_fundo_path, "PNG")
    return assinatura_sem_fundo_path

def assinar_pdf(pdf_path, assinatura_path, cpf):
    assinatura_sem_fundo = remover_fundo(assinatura_path)
    pdf_reader = PdfReader(pdf_path)
    pdf_writer = PdfWriter()

    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    largura, altura = letter

    c.drawString(100, 250, "Assinatura do colaborador:")
    c.drawImage(assinatura_sem_fundo, 100, 180, width=200, height=50)

    now = datetime.now()
    data_hora = now.strftime("%d/%m/%Y %H:%M:%S")
    c.drawString(100, 140, f"Data e hora: {data_hora}")

    # ➕ Inserir CPF abaixo da data
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




