from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime
import io
from PIL import Image

def remover_fundo(assinatura_path):
    """
    Remove o fundo da imagem de assinatura tornando-o transparente.
    """
    # Abre a imagem da assinatura
    img = Image.open(assinatura_path)

    # Converte a imagem para o formato RGBA (com canal alfa para transparência)
    img = img.convert("RGBA")

    # Carrega os dados da imagem
    datas = img.getdata()

    # Cria uma nova lista de pixels, onde o fundo será transparente
    new_data = []
    for item in datas:
        # Se o pixel for branco (fundo), torna-o transparente
        if item[0] > 200 and item[1] > 200 and item[2] > 200:  # Detectando o fundo branco (ajustável)
            new_data.append((255, 255, 255, 0))  # Torna o fundo transparente
        else:
            new_data.append(item)  # Mantém os outros pixels (assinatura) inalterados

    # Atualiza os dados da imagem com os novos valores
    img.putdata(new_data)

    # Salva a imagem com fundo transparente
    assinatura_sem_fundo_path = "assinatura_sem_fundo.png"
    img.save(assinatura_sem_fundo_path, "PNG")

    return assinatura_sem_fundo_path

def assinar_pdf(pdf_path, assinatura_path):
    """
    Assina um PDF adicionando a imagem da assinatura, texto e data no PDF original.
    """
    # Remove o fundo da assinatura
    assinatura_sem_fundo = remover_fundo(assinatura_path)

    # Lê o arquivo PDF original
    pdf_reader = PdfReader(pdf_path)
    pdf_writer = PdfWriter()

    # Cria um PDF temporário com a assinatura
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)

    # Obtém as dimensões da página original
    largura, altura = letter

    # Mover o texto "Assinatura do colaborador" para a direita
    texto_assinatura = "Assinatura do colaborador:"
    texto_assinatura_width = c.stringWidth(texto_assinatura, "Helvetica", 12)
    # Ajustando a posição 'x' para mover para a direita
    c.drawString(100, 250, texto_assinatura)  # '100' é o novo valor de 'x'

    # Mover a assinatura para a direita
    assinatura_width = 200
    assinatura_height = 50
    # Ajustando a posição 'x' para mover a assinatura para a direita
    c.drawImage(assinatura_sem_fundo, 100, 180, width=assinatura_width, height=assinatura_height)  # '100' é o novo valor de 'x'

    # Mover a data e hora para a direita
    now = datetime.now()
    data_hora = now.strftime("%d/%m/%Y %H:%M:%S")
    data_hora_width = c.stringWidth(data_hora, "Helvetica", 10)
    # Ajustando a posição 'x' para mover a data para a direita
    c.drawString(100, 140, f"Data e hora: {data_hora}")  # '100' é o novo valor de 'x'

    # Salva o conteúdo da assinatura no buffer
    c.save()

    # Volta ao início do buffer para criar o PDF
    packet.seek(0)

    # Lê o PDF temporário com a assinatura
    signature_pdf = PdfReader(packet)

    # Adiciona as páginas originais do PDF ao pdf_writer
    for i in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[i]

        # Para a primeira página, mescla a assinatura
        if i == 0:  # ou qualquer outra lógica para escolher a página a ser assinada
            page.merge_page(signature_pdf.pages[0])
        
        # Adiciona a página (com a assinatura ou sem a assinatura)
        pdf_writer.add_page(page)

    # Cria o PDF final com a assinatura
    output = io.BytesIO()
    pdf_writer.write(output)
    output.seek(0)

    return output


