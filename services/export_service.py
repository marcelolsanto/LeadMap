from fpdf import FPDF
from datetime import datetime


def gerar_vcf_individual(row: dict) -> bytes:
    """Gera VCard para um único lead."""
    nome = str(row.get('Empresa') or 'Sem Nome')
    tel = str(row.get('Telefone') or '')
    email = str(row.get('Email') or '')
    cnpj = str(row.get('CNPJ') or '')
    end = str(row.get('Endereço') or row.get('Endereco') or '')
    site = str(row.get('Site') or '')
    razao = str(row.get('Razão Social') or row.get('Razao Social') or nome)

    vcf = "BEGIN:VCARD\nVERSION:3.0\n"
    vcf += f"FN:{nome}\n"
    vcf += f"ORG:{razao}\n"
    if tel and tel not in ('nan', 'None'):
        vcf += f"TEL;TYPE=CELL,VOICE:{tel}\n"
    if email and email not in ('nan', 'None'):
        vcf += f"EMAIL;TYPE=WORK:{email}\n"
    if end and end not in ('nan', 'None'):
        vcf += f"ADR;TYPE=WORK:;;{end};;;;\n"
    if site and site not in ('nan', 'None', 'Nao possui'):
        vcf += f"URL;TYPE=WORK:{site}\n"
    if cnpj and cnpj not in ('nan', 'None'):
        vcf += f"NOTE:CNPJ: {cnpj}\n"
    vcf += "END:VCARD\n"
    return vcf.encode('utf-8')


def gerar_vcf(dataframe):
    """Gera arquivo VCard consolidado para importar todos os contatos no celular."""
    vcf_total = ""
    for _, row in dataframe.iterrows():
        vcf_total += gerar_vcf_individual(row.to_dict()).decode('utf-8')
    return vcf_total.encode('utf-8')


def gerar_pdf(dataframe, termo):
    """Gera relatório PDF com colunas expandidas."""

    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 15)
            self.cell(0, 10, 'Relatório de Leads - LeadMap', 0, 1, 'C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    def limpar(txt):
        """Remove emojis e caracteres incompatíveis com latin-1"""
        if not txt or str(txt) == 'nan': return "-"
        return str(txt).replace("📞", "").replace("📍", "").encode('latin-1', 'ignore').decode('latin-1')

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    # Cabeçalho do Relatório
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt=limpar(f"Termo Buscado: {termo}"), ln=True)
    pdf.cell(0, 10, txt=f"Data: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(5)

    # Loop pelos leads
    for _, row in dataframe.iterrows():
        # Fundo cinza claro para destacar cada bloco
        pdf.set_fill_color(245, 245, 245)
        pdf.rect(pdf.get_x(), pdf.get_y(), 190, 28, 'F')

        # Linha 1: Nome da Empresa (Negrito)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(130, 8, txt=limpar(row['Empresa'])[:45], ln=0)
        pdf.set_font("Arial", '', 10)
        pdf.cell(60, 8, txt=limpar(row.get('CNPJ', '-')), ln=1, align='R')

        # Linha 2: Telefone e Email
        pdf.set_font("Arial", '', 10)
        tel = limpar(row['Telefone'])
        email = limpar(row.get('Email', '-'))
        pdf.cell(190, 6, txt=f"Tel: {tel} | Email: {email}", ln=1)

        # Linha 3: Endereço e Situação
        end = limpar(row['Endereço'])[:60]
        situacao = limpar(row.get('Situação', '-'))
        pdf.cell(190, 6, txt=f"End: {end} | Status: {situacao}", ln=1)

        # Espaçamento entre cards
        pdf.ln(8)

    return pdf.output(dest='S').encode('latin-1')
