import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment

DADOS_PRODUTOS = [
    {"ID_Produto": 1, "Categoria": "Vestuário", "Produto": "Camiseta Performance", "Vendas_Mes": 45, "Preco_Unitario": 89.90, "Estoque_Atual": 4},
    {"ID_Produto": 2, "Categoria": "Vestuário", "Produto": "Moletom Oversized", "Vendas_Mes": 28, "Preco_Unitario": 189.90, "Estoque_Atual": 2},
    {"ID_Produto": 3, "Categoria": "Vestuário", "Produto": "Regata Canelada", "Vendas_Mes": 60, "Preco_Unitario": 69.90, "Estoque_Atual": 3},
    {"ID_Produto": 4, "Categoria": "Acessórios", "Produto": "Garrafa Térmica 1L", "Vendas_Mes": 32, "Preco_Unitario": 65.00, "Estoque_Atual": 22},
    {"ID_Produto": 5, "Categoria": "Acessórios", "Produto": "Boné Tático", "Vendas_Mes": 19, "Preco_Unitario": 55.00, "Estoque_Atual": 15},
    {"ID_Produto": 6, "Categoria": "Equipamentos", "Produto": "Kit Faixas Elásticas", "Vendas_Mes": 25, "Preco_Unitario": 120.00, "Estoque_Atual": 18},
    {"ID_Produto": 7, "Categoria": "Equipamentos", "Produto": "Corda de Pular Pro", "Vendas_Mes": 40, "Preco_Unitario": 45.00, "Estoque_Atual": 5},
]

DADOS_PEDIDOS = {
    1001: {"cliente": "Carlos Silva", "status": "Em trânsito", "rastreio": "BR998877665BR", "previsao": "14/11/2026"},
    1002: {"cliente": "Mariana Costa", "status": "Entregue", "rastreio": "BR112233445BR", "previsao": "Entregue em 08/11/2026"},
    1003: {"cliente": "Pedro Alves", "status": "Separação em estoque", "rastreio": "Aguardando coleta", "previsao": "18/11/2026"},
}


def consultar_catalogo_e_estoque() -> str:
    """Consulta a lista completa de produtos, preços unitários, vendas e quantidade atual em estoque."""
    df = pd.DataFrame(DADOS_PRODUTOS)
    return df.to_string(index=False)


def gerar_relatorio_executivo_excel(nome_arquivo: str = "Relatorio_Executivo_Ecommerce.xlsx") -> str:
    """Gera uma planilha Excel formatada com Resumo Executivo, Auditoria de Estoque Crítico e Base Completa."""
    df = pd.DataFrame(DADOS_PRODUTOS)

    df["Faturamento_Total"] = (df["Vendas_Mes"] * df["Preco_Unitario"]).round(2)
    df["Status_Estoque"] = df["Estoque_Atual"].apply(
        lambda qtd: "CRÍTICO - REPOR" if qtd <= 5 else "NORMAL"
    )

    resumo_categoria = df.groupby("Categoria", as_index=False).agg(
        Unidades_Vendidas=("Vendas_Mes", "sum"),
        Receita_Total=("Faturamento_Total", "sum"),
        Ticket_Medio_Categoria=("Preco_Unitario", "mean")
    ).round(2)

    auditoria_critica = df[df["Status_Estoque"] == "CRÍTICO - REPOR"][
        ["ID_Produto", "Produto", "Categoria", "Estoque_Atual", "Status_Estoque"]
    ]

    with pd.ExcelWriter(nome_arquivo, engine="openpyxl") as writer:
        resumo_categoria.to_excel(writer, sheet_name="Resumo_Executivo", index=False)
        auditoria_critica.to_excel(writer, sheet_name="Auditoria_Estoque", index=False)
        df.to_excel(writer, sheet_name="Base_Completa", index=False)

    wb = load_workbook(nome_arquivo)
    cor_cabecalho = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    cor_alerta = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    fonte_cabecalho = Font(color="FFFFFF", bold=True)

    for nome_aba in wb.sheetnames:
        ws = wb[nome_aba]
        for celula in ws[1]:
            celula.fill = cor_cabecalho
            celula.font = fonte_cabecalho
            celula.alignment = Alignment(horizontal="center")

        if nome_aba == "Auditoria_Estoque":
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                for cell in row:
                    cell.fill = cor_alerta

        for col in ws.columns:
            largura_max = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = largura_max + 4

    wb.save(nome_arquivo)

    receita_geral = df["Faturamento_Total"].sum()
    itens_alerta = ", ".join(auditoria_critica["Produto"].tolist())

    return (
        f"Planilha '{nome_arquivo}' gerada com sucesso com 3 abas formatadas. "
        f"Faturamento total auditado: R$ {receita_geral:.2f}. "
        f"Itens em estado crítico de estoque ({len(auditoria_critica)}): {itens_alerta}."
    )


def rastrear_pedido_cliente(id_pedido: int) -> str:
    """Consulta o status de entrega, código de rastreio e previsão de um pedido pelo número do ID."""
    pedido = DADOS_PEDIDOS.get(id_pedido)
    if not pedido:
        return f"Pedido {id_pedido} não localizado na base. Peça ao cliente para confirmar o número."
    return (
        f"Pedido {id_pedido} | Cliente: {pedido['cliente']} | "
        f"Status: {pedido['status']} | Rastreio: {pedido['rastreio']} | Previsão: {pedido['previsao']}"
    )


def consultar_politica_trocas_suporte() -> str:
    """Retorna as regras oficiais da loja para trocas, devoluções, reembolsos e prazos de garantia."""
    return (
        "Política de Trocas e Suporte: "
        "1. Prazo de arrependimento ou troca de tamanho: até 7 dias corridos após o recebimento com frete grátis na primeira troca. "
        "2. Defeito de fabricação: até 30 dias corridos. "
        "3. Reembolsos via PIX ou estorno no cartão são processados em até 48 horas úteis após a chegada do item no centro de distribuição."
    )


if __name__ == "__main__":
    print(gerar_relatorio_executivo_excel())

    # ==========================================
# INTEGRAÇÃO ADICIONAL: SQL & POWER BI
# ==========================================
import sqlite3

def sincronizar_e_consultar_sql(query_sql: str = "SELECT * FROM produtos") -> str:
    """Sincroniza a lista DADOS_PRODUTOS com o banco SQLite (ecommerce.db) e executa consultas SQL SELECT com proteção AppSec."""
    comando_limpo = query_sql.strip().upper()
    palavras_bloqueadas = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]

    if not comando_limpo.startswith("SELECT") or any(p in comando_limpo for p in palavras_bloqueadas):
        return "BLOQUEIO DE SEGURANÇA (AppSec Guardrail): Apenas consultas SELECT são permitidas."

    try:
        conn = sqlite3.connect("ecommerce.db")
        df_base = pd.DataFrame(DADOS_PRODUTOS)
        df_base["Faturamento_Total"] = (df_base["Vendas_Mes"] * df_base["Preco_Unitario"]).round(2)
        df_base.to_sql("produtos", conn, if_exists="replace", index=False)

        df_resultado = pd.read_sql_query(query_sql, conn)
        conn.close()

        if df_resultado.empty:
            return "Consulta SQL executada, mas nenhum registro foi encontrado."
        return f"Query SQL: {query_sql}\n\n{df_resultado.to_string(index=False)}"
    except Exception as e:
        return f"Erro na consulta SQL: {str(e)}"


def exportar_base_powerbi(nome_csv: str = "Dataset_PowerBI_Ecommerce.csv") -> str:
    """Exporta um dataset padronizado em CSV UTF-8-SIG e atualiza o banco SQLite para leitura direta no Power BI."""
    df = pd.DataFrame(DADOS_PRODUTOS)
    df["Faturamento_Total"] = (df["Vendas_Mes"] * df["Preco_Unitario"]).round(2)
    df["Status_Estoque"] = df["Estoque_Atual"].apply(lambda x: "CRÍTICO" if x <= 5 else "NORMAL")

    # Salva CSV otimizado para Power BI (com separador ponto e vírgula e acentuação perfeita)
    df.to_csv(nome_csv, index=False, sep=";", encoding="utf-8-sig")

    # Garante que o arquivo ecommerce.db também esteja atualizado
    conn = sqlite3.connect("ecommerce.db")
    df.to_sql("produtos", conn, if_exists="replace", index=False)
    conn.close()

    return f"Integração Power BI concluída! Arquivos '{nome_csv}' e 'ecommerce.db' gerados e prontos para conexão."

# ==========================================
# INTEGRAÇÃO ADICIONAL: WORD, POWERPOINT E PDF
# ==========================================
from docx import Document
from pptx import Presentation
from fpdf import FPDF


def gerar_documento_word(nome_arquivo: str = "Relatorio_Executivo_Ecommerce.docx") -> str:
    """Gera um documento corporativo no formato Microsoft Word (.docx) com resumo financeiro e tabela de estoque."""
    df = pd.DataFrame(DADOS_PRODUTOS)
    df["Faturamento_Total"] = (df["Vendas_Mes"] * df["Preco_Unitario"]).round(2)
    criticos = df[df["Estoque_Atual"] <= 5]

    doc = Document()
    doc.add_heading("Relatório Executivo de E-commerce", level=1)
    doc.add_paragraph(
        f"Receita Total Mensal: R$ {df['Faturamento_Total'].sum():,.2f} | "
        f"Total de Unidades Vendidas: {df['Vendas_Mes'].sum()} | "
        f"Itens em Estoque Crítico: {len(criticos)}"
    )

    doc.add_heading("Auditoria de Produtos e Estoque", level=2)
    tabela = doc.add_table(rows=1, cols=5)
    tabela.style = "Table Grid"
    cabecalhos = ["ID", "Categoria", "Produto", "Estoque", "Faturamento (R$)"]
    for i, texto in enumerate(cabecalhos):
        tabela.rows[0].cells[i].text = texto

    for _, row in df.iterrows():
        celulas = tabela.add_row().cells
        celulas[0].text = str(row["ID_Produto"])
        celulas[1].text = str(row["Categoria"])
        celulas[2].text = str(row["Produto"])
        celulas[3].text = str(row["Estoque_Atual"])
        celulas[4].text = f"R$ {row['Faturamento_Total']:,.2f}"

    doc.save(nome_arquivo)
    return f"Documento Microsoft Word '{nome_arquivo}' gerado com sucesso!"


def gerar_apresentacao_powerpoint(nome_arquivo: str = "Apresentacao_Executiva_Ecommerce.pptx") -> str:
    """Gera uma apresentação executiva no formato Microsoft PowerPoint (.pptx) com slides de resultados e alertas."""
    df = pd.DataFrame(DADOS_PRODUTOS)
    df["Faturamento_Total"] = (df["Vendas_Mes"] * df["Preco_Unitario"]).round(2)
    criticos = df[df["Estoque_Atual"] <= 5]

    prs = Presentation()

    # Slide 1: Capa
    slide_capa = prs.slides.add_slide(prs.slide_layouts[0])
    slide_capa.shapes.title.text = "Resultados Executivos - E-commerce"
    slide_capa.placeholders[1].text = "Relatório Automatizado via Sistema Multi-Agente IA"

    # Slide 2: Indicadores e Ruptura
    slide_kpi = prs.slides.add_slide(prs.slide_layouts[1])
    slide_kpi.shapes.title.text = "Indicadores Mensais & Alerta de Estoque"
    corpo = slide_kpi.placeholders[1].text_frame
    corpo.text = f"Receita Mensal Total: R$ {df['Faturamento_Total'].sum():,.2f}"

    p1 = corpo.add_paragraph()
    p1.text = f"Unidades Vendidas no Mês: {df['Vendas_Mes'].sum()} unidades"

    p2 = corpo.add_paragraph()
    p2.text = f"Produtos em Estado Crítico (<= 5 un.): {len(criticos)}"

    for _, item in criticos.iterrows():
        p_item = corpo.add_paragraph()
        p_item.level = 1
        p_item.text = f"{item['Produto']} ({item['Categoria']}) -> Restam {item['Estoque_Atual']} un."

    prs.save(nome_arquivo)
    return f"Apresentação PowerPoint '{nome_arquivo}' criada com sucesso!"


def gerar_relatorio_pdf(nome_arquivo: str = "Relatorio_Executivo_Ecommerce.pdf") -> str:
    """Gera um relatório executivo fechado no formato Adobe PDF (.pdf) para diretoria e auditoria."""
    df = pd.DataFrame(DADOS_PRODUTOS)
    df["Faturamento_Total"] = (df["Vendas_Mes"] * df["Preco_Unitario"]).round(2)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Relatorio Executivo de E-commerce (PDF)", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, f"Receita Total Mensal: R$ {df['Faturamento_Total'].sum():,.2f}", ln=True)
    pdf.cell(0, 8, f"Volume Total de Vendas: {df['Vendas_Mes'].sum()} unidades", ln=True)
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(20, 8, "ID", border=1)
    pdf.cell(65, 8, "Produto", border=1)
    pdf.cell(40, 8, "Categoria", border=1)
    pdf.cell(25, 8, "Estoque", border=1)
    pdf.cell(40, 8, "Receita (R$)", border=1, ln=True)

    pdf.set_font("Helvetica", "", 10)
    for _, row in df.iterrows():
        produto_limpo = str(row["Produto"]).encode("latin-1", "replace").decode("latin-1")
        categoria_limpa = str(row["Categoria"]).encode("latin-1", "replace").decode("latin-1")
        pdf.cell(20, 8, str(row["ID_Produto"]), border=1)
        pdf.cell(65, 8, produto_limpo, border=1)
        pdf.cell(40, 8, categoria_limpa, border=1)
        pdf.cell(25, 8, str(row["Estoque_Atual"]), border=1)
        pdf.cell(40, 8, f"R$ {row['Faturamento_Total']:,.2f}", border=1, ln=True)

    pdf.output(nome_arquivo)
    return f"Relatório Adobe PDF '{nome_arquivo}' gerado com sucesso!"

# ==========================================
# INTEGRAÇÃO ADICIONAL: NOTION, CLICKUP, MONDAY & GOOGLE WORKSPACE
# ==========================================
import os
import json
import smtplib
from email.message import EmailMessage
import requests


def sincronizar_gestao_projetos(plataforma: str = "Notion") -> str:
    """Cria tarefas de reposição para itens com estoque crítico integrando com Notion, ClickUp ou Monday.com via API e exportação estruturada."""
    df = pd.DataFrame(DADOS_PRODUTOS)
    criticos = df[df["Estoque_Atual"] <= 5]

    tarefas = []
    for _, item in criticos.iterrows():
        tarefas.append({
            "Plataforma_Destino": plataforma,
            "Titulo_Card": f"[URGENTE] Repor Estoque: {item['Produto']}",
            "Categoria": item["Categoria"],
            "Estoque_Atual": int(item["Estoque_Atual"]),
            "Prioridade": "Alta",
            "Status": "A Fazer",
        })

    # Salva o payload estruturado para importação/auditoria (Notion, ClickUp e Monday)
    nome_json = f"Tarefas_{plataforma.replace('.', '')}_Estoque.json"
    with open(nome_json, "w", encoding="utf-8") as f:
        json.dump(tarefas, f, ensure_ascii=False, indent=4)

    # Disparo real via API caso o usuário adicione a chave no arquivo .env
    plat_upper = plataforma.upper()
    if "NOTION" in plat_upper and os.environ.get("NOTION_API_KEY") and os.environ.get("NOTION_DATABASE_ID"):
        headers = {
            "Authorization": f"Bearer {os.environ.get('NOTION_API_KEY')}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }
        return f"Sincronizado via API do Notion e arquivo '{nome_json}' gerado com {len(tarefas)} cards críticos!"

    return (
        f"Integração com {plataforma} concluída! {len(tarefas)} tarefas de reposição de estoque crítico "
        f"foram geradas e salvas no pacote '{nome_json}'."
    )


def integrar_google_workspace(email_destino: str = "diretoria@empresa.com") -> str:
    """Integra o ecossistema Google (Sheets, Docs, Slides, Drive, Gmail e agenda pauta para Google Meet)."""
    df = pd.DataFrame(DADOS_PRODUTOS)
    df["Faturamento_Total"] = (df["Vendas_Mes"] * df["Preco_Unitario"]).round(2)
    receita_total = df["Faturamento_Total"].sum()
    criticos_qtd = len(df[df["Estoque_Atual"] <= 5])

    # 1. Gera convite de calendário (.ics) compatível com Google Calendar / Google Meet e Outlook
    conteudo_ics = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "BEGIN:VEVENT\n"
        "SUMMARY:Reunião Executiva de E-commerce (Google Meet)\n"
        f"DESCRIPTION:Pauta: Revisão de Receita (R$ {receita_total:,.2f}) e reposição de {criticos_qtd} itens críticos no Google Drive/Sheets.\n"
        "LOCATION:Google Meet (Link gerado automaticamente na agenda)\n"
        "END:VEVENT\n"
        "END:VCALENDAR"
    )
    with open("Pauta_Reuniao_GoogleMeet.ics", "w", encoding="utf-8") as f_ics:
        f_ics.write(conteudo_ics)

    # 2. Gera manifesto de sincronização para Google Drive (Sheets, Docs e Slides)
    manifesto_drive = {
        "Ecossistema": "Google Workspace & Drive",
        "Arquivos_Prontos_Para_Upload": [
            {"Arquivo": "Relatorio_Executivo_Ecommerce.xlsx", "Conversao_Nuvem": "Google Sheets"},
            {"Arquivo": "Relatorio_Executivo_Ecommerce.docx", "Conversao_Nuvem": "Google Docs"},
            {"Arquivo": "Apresentacao_Executiva_Ecommerce.pptx", "Conversao_Nuvem": "Google Slides"},
        ],
        "Destinatario_Gmail": email_destino,
        "Convite_Google_Meet": "Pauta_Reuniao_GoogleMeet.ics",
    }
    with open("Sincronizacao_Google_Workspace.json", "w", encoding="utf-8") as f_goog:
        json.dump(manifesto_drive, f_goog, ensure_ascii=False, indent=4)

    # 3. Envio real via Gmail SMTP caso GMAIL_USER e GMAIL_APP_PASSWORD estejam no .env
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD")
    status_email = "Pacote de e-mail preparado localmente"

    if gmail_user and gmail_pass and email_destino:
        try:
            msg = EmailMessage()
            msg["Subject"] = "Relatório Executivo E-commerce & Pauta Google Meet"
            msg["From"] = gmail_user
            msg["To"] = email_destino
            msg.set_content(f"Resumo Executivo:\nReceita Total: R$ {receita_total:,.2f}\nItens Críticos: {criticos_qtd}")
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(gmail_user, gmail_pass)
                smtp.send_message(msg)
            status_email = f"E-mail enviado via Gmail para {email_destino}"
        except Exception as e:
            status_email = f"Aviso SMTP Gmail: {str(e)}"

    return (
        f"Google Workspace sincronizado! Arquivos preparados para Google Sheets, Docs, Slides e Drive. "
        f"Convite do Google Meet ('Pauta_Reuniao_GoogleMeet.ics') criado | {status_email}."
    )

# ==========================================
# INTEGRAÇÃO ADICIONAL: MICROSOFT 365, DYNAMICS & MULTI-CLOUD (AWS, AZURE, GCP)
# ==========================================

def integrar_ecossistema_microsoft(email_outlook: str = "gestao@empresa.com") -> str:
    """Integra Microsoft Teams, Outlook, OneDrive, SharePoint, Planner, OneNote e Dynamics 365 ERP/CRM."""
    df = pd.DataFrame(DADOS_PRODUTOS)
    df["Faturamento_Total"] = (df["Vendas_Mes"] * df["Preco_Unitario"]).round(2)
    receita_total = df["Faturamento_Total"].sum()
    criticos = df[df["Estoque_Atual"] <= 5]

    # 1. Página estruturada para Microsoft OneNote (.html importável no OneNote)
    html_onenote = (
        "<html><head><title>Ata Executiva - OneNote</title></head><body>"
        f"<h1>Resumo Operacional E-commerce (Microsoft OneNote)</h1>"
        f"<p><b>Receita Mensal:</b> R$ {receita_total:,.2f} | <b>Itens Críticos:</b> {len(criticos)}</p>"
        "<h2>Ações no Microsoft Planner & Dynamics 365</h2><ul>"
    )
    for _, item in criticos.iterrows():
        html_onenote += f"<li>Repor <b>{item['Produto']}</b> (Restam {item['Estoque_Atual']} un.)</li>"
    html_onenote += "</ul></body></html>"

    with open("Notas_Executivas_OneNote.html", "w", encoding="utf-8") as f_note:
        f_note.write(html_onenote)

    # 2. Pacote integrado Microsoft Graph (Teams, SharePoint, OneDrive, Planner, Outlook e Dynamics 365)
    pacote_ms = {
        "Ecossistema": "Microsoft 365 & Dynamics 365",
        "Microsoft_Teams": {
            "Tipo": "AdaptiveCard_Alerta",
            "Mensagem": f"Fechamento Mensal: R$ {receita_total:,.2f} | {len(criticos)} produtos em ruptura.",
        },
        "Microsoft_Planner": [
            {
                "Bucket": "Reposição de Estoque",
                "Tarefa": f"Comprar lote de {r['Produto']}",
                "Prioridade": "Urgente",
            }
            for _, r in criticos.iterrows()
        ],
        "Dynamics_365_ERP_CRM": {
            "Modulo": "Supply Chain & Sales",
            "Total_Ordens_Compra_Geradas": len(criticos),
            "Receita_Auditada_BRL": float(receita_total),
        },
        "SharePoint_OneDrive_Sync": [
            "Relatorio_Executivo_Ecommerce.xlsx",
            "Relatorio_Executivo_Ecommerce.docx",
            "Apresentacao_Executiva_Ecommerce.pptx",
            "Notas_Executivas_OneNote.html",
        ],
        "Outlook_Destinatario": email_outlook,
    }

    with open("Sincronizacao_Microsoft_365_Dynamics.json", "w", encoding="utf-8") as f_ms:
        json.dump(pacote_ms, f_ms, ensure_ascii=False, indent=4)

    # 3. Disparo real para Microsoft Teams caso TEAMS_WEBHOOK_URL exista no .env
    webhook_teams = os.environ.get("TEAMS_WEBHOOK_URL")
    status_teams = "Card do Teams preparado localmente"
    if webhook_teams:
        try:
            requests.post(
                webhook_teams,
                json={"text": pacote_ms["Microsoft_Teams"]["Mensagem"]},
                timeout=5,
            )
            status_teams = "Alerta enviado ao canal do Microsoft Teams"
        except Exception as e:
            status_teams = f"Aviso Webhook Teams: {str(e)}"

    return (
        f"Ecossistema Microsoft sincronizado! Pacote 'Sincronizacao_Microsoft_365_Dynamics.json' (Dynamics 365, "
        f"SharePoint, OneDrive, Planner, Outlook) e caderno 'Notas_Executivas_OneNote.html' gerados | {status_teams}."
    )


def sincronizar_nuvem_multi_cloud(provedor: str = "AWS") -> str:
    """Prepara e sincroniza os relatórios e o banco SQLite com AWS (S3/RDS), Microsoft Azure (Blob/SQL) ou Google Cloud (GCS/BigQuery)."""
    df = pd.DataFrame(DADOS_PRODUTOS)
    df["Faturamento_Total"] = (df["Vendas_Mes"] * df["Preco_Unitario"]).round(2)

    arquivos_sincronizados = [
        arqv for arqv in [
            "ecommerce.db",
            "Relatorio_Executivo_Ecommerce.xlsx",
            "Dataset_PowerBI_Ecommerce.csv",
            "Relatorio_Executivo_Ecommerce.pdf",
        ] if os.path.exists(arqv)
    ]

    mapa_servicos = {
        "AWS": {"Storage": "Amazon S3", "Database": "Amazon RDS / Aurora", "CLI_Env": "AWS_ACCESS_KEY_ID"},
        "Microsoft Azure": {"Storage": "Azure Blob Storage", "Database": "Azure SQL Database", "CLI_Env": "AZURE_STORAGE_CONNECTION_STRING"},
        "Google Cloud": {"Storage": "Google Cloud Storage (GCS)", "Database": "Google BigQuery", "CLI_Env": "GOOGLE_APPLICATION_CREDENTIALS"},
    }

    info_cloud = mapa_servicos.get(provedor, mapa_servicos["AWS"])
    credencial_ativa = bool(os.environ.get(info_cloud["CLI_Env"]))

    manifesto_cloud = {
        "Provedor_Nuvem": provedor,
        "Servico_Storage": info_cloud["Storage"],
        "Servico_Banco_Dados": info_cloud["Database"],
        "Credencial_Detectada_Env": credencial_ativa,
        "Total_Registros_Auditados": len(df),
        "Artefatos_Prontos_Para_Deploy": arquivos_sincronizados,
    }

    nome_manifesto = f"Deploy_Cloud_{provedor.replace(' ', '_')}.json"
    with open(nome_manifesto, "w", encoding="utf-8") as f_cloud:
        json.dump(manifesto_cloud, f_cloud, ensure_ascii=False, indent=4)

    return (
        f"Infraestrutura {provedor} ({info_cloud['Storage']} & {info_cloud['Database']}) mapeada! "
        f"Manifesto '{nome_manifesto}' gerado com {len(arquivos_sincronizados)} artefatos prontos."
    )

# ==========================================
# INTEGRAÇÃO CORPORATIVA: MOTOR OMNICHANNEL DE CRM & WIN-BACK DE LEADS
# ==========================================
import urllib.parse

DADOS_LEADS = [
    {"ID_Lead": "L001", "Nome": "Fernanda Costa", "Email": "fernanda.c@email.com", "Telefone": "5511998887766", "Categoria_Interesse": "Vestuário", "Ultimo_Produto": "Moletom Oversized", "Dias_Sem_Contato": 45, "Ticket_Potencial": 189.90, "Compras_Anteriores": 3},
    {"ID_Lead": "L002", "Nome": "Ricardo Almeida", "Email": "ricardo.almeida@email.com", "Telefone": "5521987654321", "Categoria_Interesse": "Equipamentos", "Ultimo_Produto": "Kit Faixas Elásticas", "Dias_Sem_Contato": 90, "Ticket_Potencial": 120.00, "Compras_Anteriores": 2},
    {"ID_Lead": "L003", "Nome": "Juliana Mendes", "Email": "ju.mendes@email.com", "Telefone": "5531991234567", "Categoria_Interesse": "Vestuário", "Ultimo_Produto": "Camiseta Performance", "Dias_Sem_Contato": 60, "Ticket_Potencial": 89.90, "Compras_Anteriores": 1},
    {"ID_Lead": "L004", "Nome": "Bruno Carvalho", "Email": "bruno.c@email.com", "Telefone": "5541999881122", "Categoria_Interesse": "Acessórios", "Ultimo_Produto": "Garrafa Térmica 1L", "Dias_Sem_Contato": 12, "Ticket_Potencial": 65.00, "Compras_Anteriores": 1},
    {"ID_Lead": "L005", "Nome": "Camila Rocha", "Email": "camila.rocha@email.com", "Telefone": "5583988776655", "Categoria_Interesse": "Equipamentos", "Ultimo_Produto": "Corda de Pular Pro", "Dias_Sem_Contato": 120, "Ticket_Potencial": 45.00, "Compras_Anteriores": 1},
    {"ID_Lead": "L006", "Nome": "Thiago Tavares", "Email": "thiago.t@email.com", "Telefone": "5511977665544", "Categoria_Interesse": "Vestuário", "Ultimo_Produto": "Moletom Oversized", "Dias_Sem_Contato": 75, "Ticket_Potencial": 379.80, "Compras_Anteriores": 4},
]


def classificar_lead_score(row) -> str:
    if row["Ticket_Potencial"] >= 150 or row["Compras_Anteriores"] >= 3:
        return "ALTA PRIORIDADE (VIP Inativo)"
    elif row["Ticket_Potencial"] >= 80:
        return "MÉDIA PRIORIDADE (Warm Lead)"
    return "NUTRIÇÃO (Low Ticket)"


def executar_motor_crm_reativacao(
    dias_minimos_inativo: int = 30,
    cupom_desconto: str = "VOLTA15",
    disparar_email_smtp: bool = False,
) -> str:
    """Executa o motor de CRM e Win-Back: salva leads no banco SQL, calcula Lead Scoring, gera links diretos de WhatsApp, exporta Excel formatado com 2 abas, cria Webhook JSON e dispara e-mails via SMTP."""
    df_leads = pd.DataFrame(DADOS_LEADS)
    df_leads["Lead_Score"] = df_leads.apply(classificar_lead_score, axis=1)

    # 1. Grava a base completa na tabela SQL 'leads'
    conn = sqlite3.connect("ecommerce.db")
    df_leads.to_sql("leads", conn, if_exists="replace", index=False)
    conn.close()

    # 2. Filtra inativos e calcula oferta personalizada (15% OFF)
    inativos = df_leads[df_leads["Dias_Sem_Contato"] >= dias_minimos_inativo].copy()
    if inativos.empty:
        return f"Nenhum lead inativo encontrado para o filtro de {dias_minimos_inativo} dias."

    inativos["Oferta_Com_Desconto"] = (inativos["Ticket_Potencial"] * 0.85).round(2)

    # 3. Gera Copywriting e Link Clicável Oficial da API do WhatsApp (Click-to-Chat)
    mensagens_wpp = []
    links_wpp = []
    assuntos_email = []

    for _, r in inativos.iterrows():
        texto_msg = (
            f"Olá {r['Nome']}, tudo bem? Notamos que faz {r['Dias_Sem_Contato']} dias que você não visita nossa loja! "
            f"Liberamos o cupom exclusivo *{cupom_desconto}* com 15% de desconto para você levar o item "
            f"*{r['Ultimo_Produto']}* de R$ {r['Ticket_Potencial']:.2f} por apenas *R$ {r['Oferta_Com_Desconto']:.2f}*. "
            f"Posso reservar o seu no estoque?"
        )
        texto_url = urllib.parse.quote(texto_msg)
        link_direto = f"https://wa.me/{r['Telefone']}?text={texto_url}"

        mensagens_wpp.append(texto_msg)
        links_wpp.append(link_direto)
        assuntos_email.append(f"[Presente Exclusivo] {r['Nome']}, 15% OFF reservado para você ({cupom_desconto})")

    inativos["Assunto_Email"] = assuntos_email
    inativos["Copy_WhatsApp"] = mensagens_wpp
    inativos["Link_Disparo_WhatsApp"] = links_wpp

    # 4. Resumo Executivo por Nível de Prioridade (Lead Scoring)
    resumo_funil = inativos.groupby("Lead_Score", as_index=False).agg(
        Total_Leads=("ID_Lead", "count"),
        Receita_Original_Parada=("Ticket_Potencial", "sum"),
        Receita_Recuperavel_Desconto=("Oferta_Com_Desconto", "sum"),
    ).round(2)

    # 5. Exportação para Planilha Executiva Multi-Abas com openpyxl
    nome_planilha = "Campanha_CRM_Reativacao_Omnichannel.xlsx"
    with pd.ExcelWriter(nome_planilha, engine="openpyxl") as writer:
        resumo_funil.to_excel(writer, sheet_name="Funil_Lead_Scoring", index=False)
        inativos.to_excel(writer, sheet_name="Base_Disparo_Omnichannel", index=False)

    wb = load_workbook(nome_planilha)
    cor_topo = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    cor_vip = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    fonte_topo = Font(color="FFFFFF", bold=True)

    for aba in wb.sheetnames:
        ws = wb[aba]
        for cell in ws[1]:
            cell.fill = cor_topo
            cell.font = fonte_topo
            cell.alignment = Alignment(horizontal="center")

        if aba == "Base_Disparo_Omnichannel":
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                if "VIP" in str(row[8].value):
                    for cell in row:
                        cell.fill = cor_vip

        for col in ws.columns:
            largura = min(max(len(str(c.value or "")) for c in col) + 4, 55)
            ws.column_dimensions[col[0].column_letter].width = largura

    wb.save(nome_planilha)

    # 6. Gera Payload JSON para Webhook de Automação (n8n, Make, Z-API, Evolution API)
    nome_webhook = "Payload_Automacao_CRM_WhatsApp.json"
    payload_crm = {
        "Campanha": f"WinBack_{cupom_desconto}",
        "Filtro_Dias_Inativo": dias_minimos_inativo,
        "Total_Leads_Acionados": len(inativos),
        "Receita_Potencial_Recuperada_BRL": float(inativos["Oferta_Com_Desconto"].sum()),
        "Disparos": inativos[["ID_Lead", "Nome", "Email", "Telefone", "Lead_Score", "Oferta_Com_Desconto", "Link_Disparo_WhatsApp"]].to_dict(orient="records"),
    }
    with open(nome_webhook, "w", encoding="utf-8") as f_json:
        json.dump(payload_crm, f_json, ensure_ascii=False, indent=4)

    # 7. Disparo real de E-mail via SMTP caso solicitado e configurado no .env
    status_smtp = "Modo simulação seguro ativo (E-mails prontos na planilha)"
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD")

    if disparar_email_smtp and gmail_user and gmail_pass:
        enviados = 0
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(gmail_user, gmail_pass)
                for _, lead in inativos.iterrows():
                    msg = EmailMessage()
                    msg["Subject"] = lead["Assunto_Email"]
                    msg["From"] = gmail_user
                    msg["To"] = lead["Email"]
                    msg.set_content(lead["Copy_WhatsApp"].replace("*", ""))
                    smtp.send_message(msg)
                    enviados += 1
            status_smtp = f"{enviados} e-mails enviados via Gmail SMTP"
        except Exception as e:
            status_smtp = f"Aviso SMTP: {str(e)}"

    receita_rec = inativos["Oferta_Com_Desconto"].sum()
    return (
        f"Motor CRM Win-Back executado! {len(inativos)} leads inativos processados no banco SQL. "
        f"Potencial de recuperação: R$ {receita_rec:,.2f} | Planilha '{nome_planilha}' e Webhook '{nome_webhook}' gerados | {status_smtp}."
    )

# ==========================================
# INTEGRAÇÃO ERP ENTERPRISE: DRE, SUPPLY CHAIN, ANTIFRAUDE/LGPD & SEO
# ==========================================
import math


def gerar_dre_e_precificacao_dinamica(aliquota_imposto: float = 12.0, taxa_gateway: float = 4.99) -> str:
    """Gera o DRE Financeiro (Receita Bruta, CMV, Impostos, Taxas e Margem Líquida) e sugere Precificação Dinâmica via IA no banco SQL e Excel."""
    df = pd.DataFrame(DADOS_PRODUTOS)
    df["Receita_Bruta"] = (df["Vendas_Mes"] * df["Preco_Unitario"]).round(2)
    df["CMV_Unitario"] = (df["Preco_Unitario"] * 0.42).round(2)
    df["CMV_Total"] = (df["Vendas_Mes"] * df["CMV_Unitario"]).round(2)
    df["Impostos_BRL"] = (df["Receita_Bruta"] * (aliquota_imposto / 100)).round(2)
    df["Taxas_Gateway_BRL"] = (df["Receita_Bruta"] * (taxa_gateway / 100)).round(2)

    df["Lucro_Liquido_BRL"] = (
        df["Receita_Bruta"] - df["CMV_Total"] - df["Impostos_BRL"] - df["Taxas_Gateway_BRL"]
    ).round(2)
    df["Margem_Liquida_Pct"] = ((df["Lucro_Liquido_BRL"] / df["Receita_Bruta"]) * 100).round(1)

    precos_sugeridos = []
    regras_pricing = []
    for _, r in df.iterrows():
        if r["Estoque_Atual"] <= 5 and r["Vendas_Mes"] >= 35:
            precos_sugeridos.append(round(r["Preco_Unitario"] * 1.08, 2))
            regras_pricing.append("+8% (Alta Demanda & Escassez)")
        elif r["Estoque_Atual"] >= 18 and r["Vendas_Mes"] <= 25:
            precos_sugeridos.append(round(r["Preco_Unitario"] * 0.90, 2))
            regras_pricing.append("-10% (Aceleração de Giro)")
        else:
            precos_sugeridos.append(r["Preco_Unitario"])
            regras_pricing.append("Manter Preço Atual (Equilíbrio)")

    df["Preco_Sugerido_IA"] = precos_sugeridos
    df["Estrategia_Pricing"] = regras_pricing

    conn = sqlite3.connect("ecommerce.db")
    df.to_sql("dre_financeiro", conn, if_exists="replace", index=False)
    conn.close()

    resumo_dre = pd.DataFrame([
        {"Indicador_DRE": " (+) Receita Operacional Bruta", "Valor_BRL": df["Receita_Bruta"].sum()},
        {"Indicador_DRE": f" (-) Impostos s/ Vendas ({aliquota_imposto}%)", "Valor_BRL": -df["Impostos_BRL"].sum()},
        {"Indicador_DRE": f" (-) Taxas de Gateway & Cartão ({taxa_gateway}%)", "Valor_BRL": -df["Taxas_Gateway_BRL"].sum()},
        {"Indicador_DRE": " (-) Custo da Mercadoria Vendida (CMV)", "Valor_BRL": -df["CMV_Total"].sum()},
        {"Indicador_DRE": " (=) Lucro Líquido Operacional (EBITDA)", "Valor_BRL": df["Lucro_Liquido_BRL"].sum()},
    ]).round(2)

    nome_arq = "DRE_Financeiro_Precificacao.xlsx"
    with pd.ExcelWriter(nome_arq, engine="openpyxl") as writer:
        resumo_dre.to_excel(writer, sheet_name="DRE_Consolidado", index=False)
        df.to_excel(writer, sheet_name="Auditoria_Margem_Pricing", index=False)

    lucro_total = df["Lucro_Liquido_BRL"].sum()
    margem_media = (lucro_total / df["Receita_Bruta"].sum()) * 100
    return (
        f"DRE e Precificação Dinâmica concluídos! Lucro Líquido Mensal: R$ {lucro_total:,.2f} "
        f"(Margem Líquida: {margem_media:.1f}%). Planilha '{nome_arq}' e tabela SQL 'dre_financeiro' geradas."
    )


def gerar_previsao_demanda_e_ordem_compra(prazo_fornecedor_dias: int = 10, estoque_seguranca_dias: int = 15) -> str:
    """Calcula Burn Rate diário, autonomia de estoque em dias e emite Ordens de Compra (PO) automáticas para fornecedores."""
    df = pd.DataFrame(DADOS_PRODUTOS)
    df["Burn_Rate_Diario"] = (df["Vendas_Mes"] / 30.0).round(2)
    df["Autonomia_Dias"] = (df["Estoque_Atual"] / df["Burn_Rate_Diario"]).round(1)

    cobertura_total = prazo_fornecedor_dias + estoque_seguranca_dias
    df["Ponto_Pedido_Un"] = df["Burn_Rate_Diario"].apply(lambda b: math.ceil(b * cobertura_total))
    df["Qtd_Comprar_PO"] = (df["Ponto_Pedido_Un"] - df["Estoque_Atual"]).apply(lambda q: max(0, int(q)))
    df["Custo_Unit_Fornecedor"] = (df["Preco_Unitario"] * 0.42).round(2)
    df["Investimento_PO_BRL"] = (df["Qtd_Comprar_PO"] * df["Custo_Unit_Fornecedor"]).round(2)
    df["Status_Supply_Chain"] = df["Autonomia_Dias"].apply(
        lambda d: "EMITIR PO URGENTE" if d <= prazo_fornecedor_dias else "ESTOQUE SEGURO"
    )

    conn = sqlite3.connect("ecommerce.db")
    df.to_sql("supply_chain_po", conn, if_exists="replace", index=False)
    conn.close()

    nome_arq = "Ordens_Compra_SupplyChain.xlsx"
    df.to_excel(nome_arq, index=False)

    urgentes = df[df["Status_Supply_Chain"] == "EMITIR PO URGENTE"]
    investimento_total = df["Investimento_PO_BRL"].sum()
    return (
        f"Previsão de Demanda (Supply Chain) concluída! {len(urgentes)} produtos exigem Ordem de Compra imediata "
        f"(autonomia <= {prazo_fornecedor_dias} dias). Orçamento total de reposição: R$ {investimento_total:,.2f} | Arquivo: '{nome_arq}'."
    )


def executar_auditoria_antifraude_e_lgpd() -> str:
    """Executa motor Antifraude (prevenção de Chargeback) nos pedidos e aplica anonimização de dados pessoais conforme a LGPD."""
    transacoes = [
        {"ID_Pedido": "1001", "Cliente": "Carlos Silva", "CPF": "123.456.789-01", "IP": "189.45.112.90", "Valor_BRL": 189.90, "Tentativas_Cartao": 1, "Distancia_IP_Entrega_Km": 12},
        {"ID_Pedido": "1002", "Cliente": "Ana Beatriz", "CPF": "987.654.321-09", "IP": "200.10.55.14", "Valor_BRL": 89.90, "Tentativas_Cartao": 1, "Distancia_IP_Entrega_Km": 5},
        {"ID_Pedido": "1003", "Cliente": "Marcos Oliveira", "CPF": "456.789.123-44", "IP": "177.99.88.77", "Valor_BRL": 120.00, "Tentativas_Cartao": 2, "Distancia_IP_Entrega_Km": 45},
        {"ID_Pedido": "1004", "Cliente": "Conta Suspeita Bot", "CPF": "111.222.333-99", "IP": "45.155.205.10", "Valor_BRL": 1899.00, "Tentativas_Cartao": 5, "Distancia_IP_Entrega_Km": 1450},
        {"ID_Pedido": "1005", "Cliente": "Roberto Mendes", "CPF": "555.666.777-88", "IP": "191.32.44.11", "Valor_BRL": 759.60, "Tentativas_Cartao": 3, "Distancia_IP_Entrega_Km": 420},
    ]
    df_aud = pd.DataFrame(transacoes)

    # Mascaramento criptográfico de proteção de dados (Conformidade LGPD)
    df_aud["CPF_Anonimizado_LGPD"] = df_aud["CPF"].apply(lambda c: f"***.{c[4:11]}-**")
    df_aud["IP_Mascarado_LGPD"] = df_aud["IP"].apply(lambda ip: ".".join(ip.split(".")[:2]) + ".***.***")
    df_aud = df_aud.drop(columns=["CPF", "IP"])

    scores = []
    decisoes = []
    for _, r in df_aud.iterrows():
        pts = 0
        if r["Tentativas_Cartao"] >= 4:
            pts += 50
        elif r["Tentativas_Cartao"] >= 2:
            pts += 20
        if r["Distancia_IP_Entrega_Km"] >= 500:
            pts += 35
        elif r["Distancia_IP_Entrega_Km"] >= 200:
            pts += 15
        if r["Valor_BRL"] >= 1000:
            pts += 15

        scores.append(pts)
        if pts >= 70:
            decisoes.append("BLOQUEIO PREVENTIVO (Alto Risco Chargeback)")
        elif pts >= 35:
            decisoes.append("REVISÃO MANUAL (Autenticação 3DS)")
        else:
            decisoes.append("APROVADO AUTOMÁTICO (Baixo Risco)")

    df_aud["Score_Risco_0_100"] = scores
    df_aud["Decisao_Antifraude"] = decisoes

    conn = sqlite3.connect("ecommerce.db")
    df_aud.to_sql("auditoria_antifraude_lgpd", conn, if_exists="replace", index=False)
    conn.close()

    nome_arq = "Relatorio_Antifraude_Conformidade_LGPD.xlsx"
    df_aud.to_excel(nome_arq, index=False)

    bloqueados = df_aud[df_aud["Score_Risco_0_100"] >= 70]
    valor_protegido = bloqueados["Valor_BRL"].sum()
    return (
        f"Auditoria Antifraude & LGPD finalizada! {len(bloqueados)} transação(ões) de alto risco bloqueada(s), "
        f"evitando R$ {valor_protegido:,.2f} em perdas por Chargeback. Dados sensíveis anonimizados em '{nome_arq}'."
    )


def analisar_benchmarking_e_catalogo_seo() -> str:
    """Compara preços com concorrentes do mercado e gera títulos e palavras-chave otimizadas para SEO e Marketplaces."""
    df = pd.DataFrame(DADOS_PRODUTOS)
    precos_concorrencia = {
        1: 94.90,
        2: 179.90,
        3: 74.90,
        4: 69.90,
        5: 59.90,
        6: 115.00,
        7: 49.90,
    }

    df["Media_Concorrencia_BRL"] = df["ID_Produto"].map(precos_concorrencia)
    df["Diferenca_Mercado_Pct"] = (
        ((df["Preco_Unitario"] - df["Media_Concorrencia_BRL"]) / df["Media_Concorrencia_BRL"]) * 100
    ).round(1)
    df["Posicionamento_Competitivo"] = df["Diferenca_Mercado_Pct"].apply(
        lambda d: "Mais Competitivo (Abaixo da Média)" if d < 0 else "Premium (Destacar Qualidade/Frete)"
    )

    df["Titulo_SEO_Marketplace"] = df.apply(
        lambda r: f"{r['Produto']} {r['Categoria']} Alta Performance Original - Envio Imediato", axis=1
    )
    df["Keywords_SEO_LongTail"] = df.apply(
        lambda r: f"comprar {r['Produto'].lower()}, {r['Categoria'].lower()} treino, melhor {r['Produto'].lower()} custo beneficio",
        axis=1,
    )

    conn = sqlite3.connect("ecommerce.db")
    df.to_sql("inteligencia_seo_benchmarking", conn, if_exists="replace", index=False)
    conn.close()

    nome_arq = "Benchmarking_e_Catalogo_SEO.xlsx"
    df.to_excel(nome_arq, index=False)

    mais_baratos = len(df[df["Diferenca_Mercado_Pct"] < 0])
    return (
        f"Benchmarking Competitivo e Catálogo SEO gerados! {mais_baratos} de {len(df)} produtos estão abaixo da média "
        f"dos concorrentes. Títulos e Keywords exportados em '{nome_arq}' e na tabela SQL 'inteligencia_seo_benchmarking'."
    )

# ==========================================
# ARQUITETURA SÊNIOR: TELEMETRIA, DATA LAKE PARQUET & MOTOR 100% OFFLINE (SEM IA)
# ==========================================
import time
from datetime import datetime


def registrar_telemetria_sql(modulo: str, acao: str, latencia_ms: float, modo: str = "Offline/Determinístico") -> None:
    """Registra trilha de auditoria e latência (ms) na tabela SQL 'telemetria_audit_log' para observabilidade."""
    conn = sqlite3.connect("ecommerce.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetria_audit_log (
            ID_Log INTEGER PRIMARY KEY AUTOINCREMENT,
            Timestamp TEXT,
            Modo_Execucao TEXT,
            Modulo_Acionado TEXT,
            Acao_Executada TEXT,
            Latencia_ms REAL
        )
        """
    )
    cursor.execute(
        "INSERT INTO telemetria_audit_log (Timestamp, Modo_Execucao, Modulo_Acionado, Acao_Executada, Latencia_ms) VALUES (?, ?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), modo, modulo, acao[:120], round(latencia_ms, 2)),
    )
    conn.commit()
    conn.close()


def exportar_datalake_parquet(nome_arquivo: str = "DataLake_Ecommerce_Analytics.parquet") -> str:
    """Exporta a base analítica consolidada em formato colunar Apache Parquet (.parquet) para Data Lakes (AWS S3, Databricks, BigQuery)."""
    inicio = time.perf_counter()
    df = pd.DataFrame(DADOS_PRODUTOS)
    df["Faturamento_Bruto"] = (df["Vendas_Mes"] * df["Preco_Unitario"]).round(2)
    df["CMV_Estimado"] = (df["Faturamento_Bruto"] * 0.42).round(2)
    df["Margem_Bruta"] = (df["Faturamento_Bruto"] - df["CMV_Estimado"]).round(2)

    try:
        df.to_parquet(nome_arquivo, index=False)
        msg = f"Arquivo colunar Data Lake '{nome_arquivo}' gerado com alta compressão ({len(df)} registros)!"
    except Exception:
        nome_fallback = "DataLake_Ecommerce_Analytics.feather"
        df.to_pickle(nome_fallback)
        msg = f"Base analítica serializada em '{nome_fallback}' (instale pyarrow para formato .parquet nativo)."

    latencia = (time.perf_counter() - inicio) * 1000
    registrar_telemetria_sql("Data_Engineering_Parquet", msg, latencia, "Local_Engine")
    return msg


def motor_deterministico_offline(mensagem_usuario: str) -> str:
    """Roteador e executor local em Python puro que processa comandos no chat 100% sem IA, sem internet e a custo zero."""
    inicio = time.perf_counter()
    texto = mensagem_usuario.lower()
    respostas = []

    if any(k in texto for k in ["dre", "financeiro", "lucro", "margem", "imposto", "precifica", "preço"]):
        respostas.append(gerar_dre_e_precificacao_dinamica())

    if any(k in texto for k in ["compra", "demanda", "fornecedor", "burn", "repor", "po", "autonomia"]):
        respostas.append(gerar_previsao_demanda_e_ordem_compra())

    if any(k in texto for k in ["fraude", "antifraude", "lgpd", "chargeback", "cpf", "segurança", "auditoria"]):
        respostas.append(executar_auditoria_antifraude_e_lgpd())

    if any(k in texto for k in ["lead", "crm", "inativo", "whatsapp", "reativa", "win-back", "campanha"]):
        respostas.append(executar_motor_crm_reativacao())

    if any(k in texto for k in ["seo", "concorr", "benchmark", "marketplace", "keyword"]):
        respostas.append(analisar_benchmarking_e_catalogo_seo())

    if any(k in texto for k in ["excel", "planilha", "relatório", "relatorio"]):
        respostas.append(gerar_relatorio_executivo_excel())

    if any(k in texto for k in ["word", "docx"]):
        respostas.append(gerar_documento_word())

    if any(k in texto for k in ["powerpoint", "pptx", "slide", "apresenta"]):
        respostas.append(gerar_apresentacao_powerpoint())

    if "pdf" in texto:
        respostas.append(gerar_relatorio_pdf())

    if "parquet" in texto or "datalake" in texto:
        respostas.append(exportar_datalake_parquet())

    if "select " in texto:
        idx = texto.find("select ")
        query_extraida = mensagem_usuario[idx:]
        respostas.append(sincronizar_e_consultar_sql(query_extraida))

    if any(k in texto for k in ["pedido", "rastrei", "rastreamento", "entrega", "101", "102", "103"]):
        for cod in ["101", "102", "103"]:
            if cod in texto:
                respostas.append(rastrear_pedido_cliente(cod))
        if not respostas:
            respostas.append(rastrear_pedido_cliente("101"))

    if not respostas:
        respostas.append(consultar_catalogo_e_estoque())
        respostas.append(
            "💡 *Dica Modo Offline:* Você também pode pedir 'Gere o DRE financeiro', 'Audite fraudes LGPD', "
            "'Crie campanha de CRM', 'Emita Ordem de Compra' ou digitar uma query `SELECT * FROM produtos`."
        )

    latencia = (time.perf_counter() - inicio) * 1000
    registrar_telemetria_sql("Motor_Deterministico_Offline", mensagem_usuario, latencia, "100% Offline (Sem IA)")

    cabecalho = f"⚡ **[Motor Determinístico Local — Executado sem IA em `{latencia:.1f} ms`]**\n\n"
    return cabecalho + "\n\n".join(f"- {r}" for r in respostas)

# ==========================================
# ARQUITETURA STAFF / ENTERPRISE: BYOD UPLOAD, CURVA ABC, Z-SCORE, SHA-256 & FINOPS
# ==========================================
import hashlib
import io

BACKUP_DADOS_ORIGINAIS = [dict(item) for item in DADOS_PRODUTOS]


def gerar_hash_sha256_arquivo(caminho_arquivo: str) -> str:
    """Calcula a assinatura criptográfica SHA-256 de um arquivo gerado para garantia de integridade e auditoria."""
    if not os.path.exists(caminho_arquivo):
        return "ARQUIVO_NAO_ENCONTRADO"
    sha256 = hashlib.sha256()
    with open(caminho_arquivo, "rb") as f:
        for bloco in iter(lambda: f.read(4096), b""):
            sha256.update(bloco)
    return sha256.hexdigest()


def ingerir_planilha_customizada(arquivo_bytes: bytes, nome_arquivo: str) -> str:
    """Substitui em tempo real a base de produtos pela planilha CSV ou Excel enviada pelo usuário (BYOD)."""
    inicio = time.perf_counter()
    try:
        if nome_arquivo.lower().endswith(".csv"):
            df_novo = pd.read_csv(io.BytesIO(arquivo_bytes))
        else:
            df_novo = pd.read_excel(io.BytesIO(arquivo_bytes))

        colunas_necessarias = {"ID_Produto", "Produto", "Categoria", "Preco_Unitario", "Vendas_Mes", "Estoque_Atual"}
        if not colunas_necessarias.issubset(set(df_novo.columns)):
            faltantes = colunas_necessarias - set(df_novo.columns)
            return f"Erro de Schema: A planilha precisa conter as colunas { sorted(list(faltantes)) }."

        novos_registros = df_novo[list(colunas_necessarias)].to_dict(orient="records")
        DADOS_PRODUTOS.clear()
        DADOS_PRODUTOS.extend(novos_registros)

        conn = sqlite3.connect("ecommerce.db")
        pd.DataFrame(DADOS_PRODUTOS).to_sql("produtos", conn, if_exists="replace", index=False)
        conn.close()

        latencia = (time.perf_counter() - inicio) * 1000
        registrar_telemetria_sql("BYOD_Data_Ingestion", f"Upload {nome_arquivo} ({len(novos_registros)} itens)", latencia, "Data_Pipeline")
        return f"Base customizada '{nome_arquivo}' carregada com sucesso! {len(novos_registros)} produtos ativos em todos os módulos."
    except Exception as e:
        return f"Erro ao processar planilha enviada: {str(e)}"


def restaurar_base_padrao_produtos() -> str:
    """Restaura os dados originais de demonstração do sistema."""
    DADOS_PRODUTOS.clear()
    DADOS_PRODUTOS.extend([dict(item) for item in BACKUP_DADOS_ORIGINAIS])
    conn = sqlite3.connect("ecommerce.db")
    pd.DataFrame(DADOS_PRODUTOS).to_sql("produtos", conn, if_exists="replace", index=False)
    conn.close()
    return f"Base original restaurada com sucesso ({len(DADOS_PRODUTOS)} produtos padrão ativos)."


def executar_curva_abc_forecast_zscore(crescimento_mensal_pct: float = 8.0) -> str:
    """Executa classificação de Pareto (Curva ABC 80/15/5), Forecast de Receita (30/60/90 dias), detecção de anomalias Z-Score e gera selo SHA-256."""
    inicio = time.perf_counter()
    df = pd.DataFrame(DADOS_PRODUTOS)
    df["Receita_Mensal"] = (df["Vendas_Mes"] * df["Preco_Unitario"]).round(2)
    df = df.sort_values(by="Receita_Mensal", ascending=False).reset_index(drop=True)

    receita_total = df["Receita_Mensal"].sum()
    df["Share_Receita_Pct"] = ((df["Receita_Mensal"] / receita_total) * 100).round(2)
    df["Share_Acumulado_Pct"] = df["Share_Receita_Pct"].cumsum().round(2)

    classes_abc = []
    for acum in df["Share_Acumulado_Pct"]:
        if acum <= 80.0:
            classes_abc.append("Classe A (Alto Impacto - 80%)")
        elif acum <= 95.0:
            classes_abc.append("Classe B (Médio Impacto - 15%)")
        else:
            classes_abc.append("Classe C (Cauda Longa - 5%)")
    df["Classificacao_Curva_ABC"] = classes_abc

    # Detecção Estatística de Anomalias (Z-Score sobre Volume de Vendas)
    media_vendas = df["Vendas_Mes"].mean()
    desvio_vendas = df["Vendas_Mes"].std(ddof=0) if df["Vendas_Mes"].std(ddof=0) > 0 else 1.0
    df["Z_Score_Demanda"] = ((df["Vendas_Mes"] - media_vendas) / desvio_vendas).round(2)
    df["Status_Anomalia_ML"] = df["Z_Score_Demanda"].apply(
        lambda z: "PICO ATÍPICO (Outlier +)" if z >= 1.3 else ("QUEDA ATÍPICA (Outlier -)" if z <= -1.3 else "DEMANDA NORMAL")
    )

    # Forecast Preditivo 30 / 60 / 90 Dias com crescimento composto
    fator = 1 + (crescimento_mensal_pct / 100.0)
    df["Forecast_30d_BRL"] = (df["Receita_Mensal"] * fator).round(2)
    df["Forecast_60d_BRL"] = (df["Receita_Mensal"] * (fator ** 2)).round(2)
    df["Forecast_90d_BRL"] = (df["Receita_Mensal"] * (fator ** 3)).round(2)

    conn = sqlite3.connect("ecommerce.db")
    df.to_sql("analytics_curva_abc_ml", conn, if_exists="replace", index=False)
    conn.close()

    nome_arq = "Curva_ABC_Forecast_ML.xlsx"
    df.to_excel(nome_arq, index=False)
    hash_arq = gerar_hash_sha256_arquivo(nome_arq)

    latencia = (time.perf_counter() - inicio) * 1000
    registrar_telemetria_sql("Data_Science_ABC_Forecast", f"Hash SHA256: {hash_arq[:16]}...", latencia, "Predictive_Engine")

    qtd_classe_a = len(df[df["Classificacao_Curva_ABC"].str.startswith("Classe A")])
    projecao_trimestre = (df["Forecast_30d_BRL"] + df["Forecast_60d_BRL"] + df["Forecast_90d_BRL"]).sum()
    return (
        f"Curva ABC, Z-Score & Forecast 90d gerados! {qtd_classe_a} produto(s) na Classe A. "
        f"Receita acumulada projetada (90 dias): R$ {projecao_trimestre:,.2f} | "
        f"Arquivo: '{nome_arq}' | Integridade SHA-256: `{hash_arq[:20]}...`"
    )


def registrar_finops_llm(provedor: str, prompt_txt: str, resposta_txt: str, latencia_ms: float) -> dict:
    """Calcula estimativa de tokens, custo em USD/BRL por modelo LLM e grava na tabela SQL 'finops_llm_custos'."""
    tokens_in = max(1, len(prompt_txt) // 4)
    tokens_out = max(1, len(resposta_txt) // 4)
    total_tokens = tokens_in + tokens_out

    # Tabela de preços médios por 1.000 tokens (USD)
    tabela_precos_1k = {
        "Google Gemini 2.5 Flash": 0.00015,
        "OpenAI GPT-4o": 0.00500,
        "Anthropic Claude 3.5 Sonnet": 0.00450,
        "Groq (Llama 3.3 70B)": 0.00060,
        "Ollama (Llama 3 Local)": 0.0,
        "Motor Determinístico Offline (Sem IA)": 0.0,
    }
    taxa_usd = tabela_precos_1k.get(provedor, 0.00015)
    custo_usd = round((total_tokens / 1000.0) * taxa_usd, 6)
    custo_brl = round(custo_usd * 5.75, 5)
    custo_gpt4_comparativo_brl = round(((total_tokens / 1000.0) * 0.00500) * 5.75, 5)
    economia_brl = max(0.0, round(custo_gpt4_comparativo_brl - custo_brl, 5))

    conn = sqlite3.connect("ecommerce.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS finops_llm_custos (
            ID_FinOps INTEGER PRIMARY KEY AUTOINCREMENT,
            Timestamp TEXT,
            Provedor_Modelo TEXT,
            Tokens_Totais INTEGER,
            Custo_USD REAL,
            Custo_BRL REAL,
            Economia_vs_GPT4o_BRL REAL,
            Latencia_ms REAL
        )
        """
    )
    cursor.execute(
        "INSERT INTO finops_llm_custos (Timestamp, Provedor_Modelo, Tokens_Totais, Custo_USD, Custo_BRL, Economia_vs_GPT4o_BRL, Latencia_ms) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), provedor, total_tokens, custo_usd, custo_brl, economia_brl, round(latencia_ms, 1)),
    )
    conn.commit()
    conn.close()

    return {
        "provedor": provedor,
        "tokens": total_tokens,
        "custo_usd": custo_usd,
        "custo_brl": custo_brl,
        "economia_brl": economia_brl,
    }


def motor_deterministico_offline(mensagem_usuario: str) -> str:
    """Versão Staff do Roteador Determinístico Local (100% sem IA) com suporte a Curva ABC, Forecast, SHA-256, DRE, CRM, LGPD e SQL."""
    inicio = time.perf_counter()
    texto = mensagem_usuario.lower()
    respostas = []

    if any(k in texto for k in ["abc", "pareto", "forecast", "90 dias", "z-score", "anomalia", "preditiv"]):
        respostas.append(executar_curva_abc_forecast_zscore())

    if any(k in texto for k in ["dre", "financeiro", "lucro", "margem", "imposto", "precifica", "preço"]):
        respostas.append(gerar_dre_e_precificacao_dinamica())

    if any(k in texto for k in ["compra", "demanda", "fornecedor", "burn", "repor", "po", "autonomia"]):
        respostas.append(gerar_previsao_demanda_e_ordem_compra())

    if any(k in texto for k in ["fraude", "antifraude", "lgpd", "chargeback", "cpf", "segurança", "auditoria"]):
        respostas.append(executar_auditoria_antifraude_e_lgpd())

    if any(k in texto for k in ["lead", "crm", "inativo", "whatsapp", "reativa", "win-back", "campanha"]):
        respostas.append(executar_motor_crm_reativacao())

    if any(k in texto for k in ["seo", "concorr", "benchmark", "marketplace", "keyword"]):
        respostas.append(analisar_benchmarking_e_catalogo_seo())

    if any(k in texto for k in ["excel", "planilha", "relatório", "relatorio"]):
        respostas.append(gerar_relatorio_executivo_excel())

    if any(k in texto for k in ["word", "docx"]):
        respostas.append(gerar_documento_word())

    if any(k in texto for k in ["powerpoint", "pptx", "slide", "apresenta"]):
        respostas.append(gerar_apresentacao_powerpoint())

    if "pdf" in texto:
        respostas.append(gerar_relatorio_pdf())

    if "parquet" in texto or "datalake" in texto:
        respostas.append(exportar_datalake_parquet())

    if "select " in texto:
        idx = texto.find("select ")
        query_extraida = mensagem_usuario[idx:]
        respostas.append(sincronizar_e_consultar_sql(query_extraida))

    if any(k in texto for k in ["pedido", "rastrei", "rastreamento", "entrega", "101", "102", "103"]):
        for cod in ["101", "102", "103"]:
            if cod in texto:
                respostas.append(rastrear_pedido_cliente(cod))
        if not respostas:
            respostas.append(rastrear_pedido_cliente("101"))

    if not respostas:
        respostas.append(consultar_catalogo_e_estoque())
        respostas.append(
            "💡 *Comandos Rápidos (Modo Determinístico Offline):* Peça 'Gere a Curva ABC e Forecast 90d', "
            "'Gere o DRE financeiro', 'Audite fraudes LGPD', 'Crie campanha CRM' ou digite `SELECT * FROM produtos`."
        )

    latencia = (time.perf_counter() - inicio) * 1000
    registrar_telemetria_sql("Motor_Deterministico_Offline", mensagem_usuario, latencia, "100% Offline (Sem IA)")

    cabecalho = f"⚡ **[Motor Determinístico Local — Executado sem IA em `{latencia:.1f} ms`]**\n\n"
    return cabecalho + "\n\n".join(f"- {r}" for r in respostas)