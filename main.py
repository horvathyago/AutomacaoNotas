
import os
import re
import json
import shutil
import pandas as pd

from datetime import datetime
from extrator import extrair_dados


# ==========================================
# CONFIGURAÇÃO DAS PASTAS
# ==========================================

PASTA_ENTRADA = "notas_entrada"
PASTA_PROCESSADAS = "notas_processadas"
PASTA_RELATORIOS = "relatorios"

ARQUIVO_CONTROLE = os.path.join(
    PASTA_PROCESSADAS,
    ".processados.json"
)


# ==========================================
# LIMPAR NOME DO ARQUIVO
# ==========================================

def limpar_nome(nome):

    nome = re.sub(r'[<>:"/\\|?*]', '', nome)

    return nome.strip().rstrip(".")


# ==========================================
# GERAR NOME DA NOTA
# ==========================================


def gerar_nome_arquivo(fornecedor, numero, data, valor):

    data_formatada = data.replace("/", "-")

    valor_formatado = valor.replace(".", "")

    nome = (
        f"NF - {numero} - "
        f"{fornecedor} - "
        f"{data_formatada} - "
        f"R$ {valor_formatado}"
    )

    return limpar_nome(nome) + ".pdf"



# ==========================================
# CARREGAR CONTROLE DE PROCESSAMENTO
# ==========================================

def carregar_controle():

    if os.path.exists(ARQUIVO_CONTROLE):

        try:
            with open(
                ARQUIVO_CONTROLE,
                "r",
                encoding="utf-8"
            ) as arquivo:

                return json.load(arquivo)

        except (json.JSONDecodeError, OSError):
            print("[AVISO] Controle anterior não pôde ser lido.")

    return {}


# ==========================================
# SALVAR CONTROLE DE PROCESSAMENTO
# ==========================================

def salvar_controle(controle):

    with open(
        ARQUIVO_CONTROLE,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            controle,
            arquivo,
            ensure_ascii=False,
            indent=4
        )


# ==========================================
# VERIFICAR SE JÁ FOI PROCESSADO
# ==========================================

def ja_processado(arquivo, caminho, controle):

    informacoes = os.stat(caminho)

    registro = controle.get(arquivo)

    if not registro:
        return False

    mesmo_arquivo = (
        registro.get("tamanho") == informacoes.st_size
        and registro.get("modificado") == informacoes.st_mtime_ns
    )

    if not mesmo_arquivo:
        return False

    arquivo_saida = os.path.join(
        PASTA_PROCESSADAS,
        registro.get("saida", "")
    )

    return os.path.isfile(arquivo_saida)


# ==========================================
# REGISTRAR PROCESSAMENTO
# ==========================================

def registrar_processamento(arquivo, caminho, saida, controle):

    informacoes = os.stat(caminho)

    controle[arquivo] = {
        "tamanho": informacoes.st_size,
        "modificado": informacoes.st_mtime_ns,
        "saida": os.path.basename(saida)
    }

    salvar_controle(controle)


# ==========================================
# PROCESSAR NOTAS FISCAIS
# ==========================================

def processar_notas():

    os.makedirs(PASTA_ENTRADA, exist_ok=True)
    os.makedirs(PASTA_PROCESSADAS, exist_ok=True)
    os.makedirs(PASTA_RELATORIOS, exist_ok=True)

    controle = carregar_controle()

    relatorio = []

    arquivos = sorted([
        arquivo
        for arquivo in os.listdir(PASTA_ENTRADA)
        if arquivo.lower().endswith(".pdf")
    ])

    print("\nINICIANDO PROCESSAMENTO")
    print("=" * 55)

    if not arquivos:
        print("Nenhum PDF encontrado.")
        return

    novas = 0
    ignoradas = 0
    erros = 0

    for arquivo in arquivos:

        caminho_original = os.path.join(
            PASTA_ENTRADA,
            arquivo
        )

        try:

            # Ignorar notas já processadas
            if ja_processado(arquivo, caminho_original, controle):

                print(f"\n[IGNORADO] {arquivo}")
                print("Esta nota já foi processada anteriormente.")

                ignoradas += 1
                continue

            dados = extrair_dados(caminho_original)

            fornecedor = dados["fornecedor"]
            numero = dados["numero"]
            data = dados["data"]
            valor = dados["valor"]

            if not all([fornecedor, numero, data, valor]):

                faltando = []

                if not fornecedor:
                    faltando.append("Fornecedor")

                if not numero:
                    faltando.append("Número da nota")

                if not data:
                    faltando.append("Data")

                if not valor:
                    faltando.append("Valor")

                raise ValueError(
                    "Campos não identificados: "
                    + ", ".join(faltando)
                )

            novo_nome = gerar_nome_arquivo(
                fornecedor,
                numero,
                data,
                valor
            )

            destino = os.path.join(
                PASTA_PROCESSADAS,
                novo_nome
            )

            # Verificar se já existe uma cópia
            if os.path.exists(destino):

                registrar_processamento(
                    arquivo,
                    caminho_original,
                    destino,
                    controle
                )

                print(f"\n[IGNORADO] {arquivo}")
                print("Uma cópia com esse nome já existe.")

                ignoradas += 1
                continue

            # Procurar cópia antiga sem número da nota
            nome_antigo = limpar_nome(
                f"{fornecedor} - {data.replace('/', '-')} - "
                f"{valor.replace('.', '')}"
            ) + ".pdf"

            caminho_antigo = os.path.join(
                PASTA_PROCESSADAS,
                nome_antigo
            )

            if os.path.exists(caminho_antigo):

                # Atualizar nome da cópia existente
                shutil.move(caminho_antigo, destino)

            else:

                # Criar cópia preservando o original
                shutil.copy2(caminho_original, destino)

            registrar_processamento(
                arquivo,
                caminho_original,
                destino,
                controle
            )

            novas += 1

            relatorio.append({
                "Arquivo original": arquivo,
                "Fornecedor": fornecedor,
                "Número da nota": numero,
                "Data de emissão": data,
                "Valor total": valor,
                "Novo arquivo": os.path.basename(destino),
                "Status": "Processado"
            })

            print(f"\n[OK] {arquivo}")
            print(f"Fornecedor: {fornecedor}")
            print(f"Número: {numero}")
            print(f"Data: {data}")
            print(f"Valor: R$ {valor}")
            print(f"Novo nome: {os.path.basename(destino)}")

        except Exception as erro:

            erros += 1

            relatorio.append({
                "Arquivo original": arquivo,
                "Fornecedor": None,
                "Número da nota": None,
                "Data de emissão": None,
                "Valor total": None,
                "Novo arquivo": None,
                "Status": f"Erro: {erro}"
            })

            print(f"\n[ERRO] {arquivo}")
            print(f"Motivo: {erro}")

    # ======================================
    # GERAR RELATÓRIO EXCEL
    # ======================================

    if relatorio:

        tabela = pd.DataFrame(relatorio)

        nome_relatorio = (
            "relatorio_notas_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".xlsx"
        )

        caminho_relatorio = os.path.join(
            PASTA_RELATORIOS,
            nome_relatorio
        )

        tabela.to_excel(
            caminho_relatorio,
            index=False
        )

        print(f"\nRelatório: {caminho_relatorio}")

    # ======================================
    # RESUMO FINAL
    # ======================================

    print("\n" + "=" * 55)
    print("PROCESSAMENTO FINALIZADO")
    print("=" * 55)

    print(f"PDFs encontrados: {len(arquivos)}")
    print(f"Novas notas processadas: {novas}")
    print(f"Notas ignoradas: {ignoradas}")
    print(f"Erros: {erros}")


# ==========================================
# EXECUTAR PROGRAMA
# ==========================================

if __name__ == "__main__":
    processar_notas()
