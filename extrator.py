
import fitz
import re


def extrair_dados(caminho_pdf):

    documento = fitz.open(caminho_pdf)

    try:
        texto = ""

        for pagina in documento:
            texto += pagina.get_text()

    finally:
        documento.close()

    texto = texto.replace("\xa0", " ")

    # 1. Fornecedor
    fornecedor = re.search(
        r"RECEBEMOS DE\s+(.+?)\s+OS PRODUTOS",
        texto,
        re.IGNORECASE | re.DOTALL
    )

    if not fornecedor:
        fornecedor = re.search(
            r"IDENTIFICAÇÃO DO EMITENTE\s+(.+?)\s+DANFE",
            texto,
            re.IGNORECASE | re.DOTALL
        )

    # 2. Data de emissão
    data = re.search(
        r"(?:EMISSÃO|DATA DA EMISSÃO)\s*:?\s*(\d{2}/\d{2}/\d{4})",
        texto,
        re.IGNORECASE
    )

    # 3. Valor total
    valor = re.search(
        r"VALOR TOTAL:\s*R?\$?\s*([\d.]+,\d{2})",
        texto,
        re.IGNORECASE
    )

    if not valor:
        valor = re.search(
            r"VALOR TOTAL DA NOTA\s*:?\s*R?\$?\s*([\d.]+,\d{2})",
            texto,
            re.IGNORECASE
        )

    # 4. Número da nota fiscal
    numero = re.search(
        r"N[º°o]\s*\.?\s*(\d[\d.]*)",
        texto,
        re.IGNORECASE
    )

    nome_fornecedor = None

    if fornecedor:
        nome_fornecedor = re.sub(
            r"\s+",
            " ",
            fornecedor.group(1)
        ).strip()

    numero_nota = None

    if numero:
        numero_nota = numero.group(1).replace(".", "").lstrip("0")

    return {
        "fornecedor": nome_fornecedor,
        "numero": numero_nota,
        "data": data.group(1) if data else None,
        "valor": valor.group(1) if valor else None
    }
