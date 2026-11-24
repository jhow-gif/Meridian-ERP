import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from ferramentas_ecommerce import (
    consultar_catalogo_e_estoque,
    gerar_relatorio_executivo_excel,
    rastrear_pedido_cliente,
    consultar_politica_trocas_suporte,
    sincronizar_e_consultar_sql,
    exportar_base_powerbi,
    gerar_documento_word,
    gerar_apresentacao_powerpoint,
    gerar_relatorio_pdf,
    sincronizar_gestao_projetos,
    integrar_google_workspace,
    integrar_ecossistema_microsoft,
    sincronizar_nuvem_multi_cloud,
    executar_motor_crm_reativacao,
    gerar_dre_e_precificacao_dinamica,
    gerar_previsao_demanda_e_ordem_compra,
    executar_auditoria_antifraude_e_lgpd,
    analisar_benchmarking_e_catalogo_seo,
)

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

MODELO_PADRAO = "gemini-2.5-flash"


def agente_roteador(mensagem_usuario: str) -> str:
    instrucao_roteador = (
        "Você é o Agente Roteador Central de um E-commerce. "
        "Analise a mensagem do usuário e classifique o destino exato:\n"
        "- Responda apenas VENDAS_ESTOQUE se envolver: preços, catálogo de produtos, quantidade em estoque, "
        "faturamento, auditoria de vendas ou geração/exportação de relatórios em Excel.\n"
        "- Responda apenas SUPORTE se envolver: rastreamento de pedidos, atraso na entrega, trocas, "
        "devoluções, reembolso ou defeitos.\n"
        "Retorne exclusivamente a palavra VENDAS_ESTOQUE ou SUPORTE, sem pontuação."
    )

    resposta = client.models.generate_content(
        model=MODELO_PADRAO,
        contents=mensagem_usuario,
        config=types.GenerateContentConfig(
            system_instruction=instrucao_roteador,
            temperature=0.0,
        ),
    )
    decisao = resposta.text.strip().upper()
    return "SUPORTE" if "SUPORTE" in decisao else "VENDAS_ESTOQUE"


def subagente_vendas_estoque(mensagem_usuario: str) -> str:
    instrucao = (
        "Você é o Sub-Agente de Vendas, Dados e Controle de Estoque do E-commerce. "
        "Use 'consultar_catalogo_e_estoque' para dúvidas sobre preços e disponibilidade. "
        "Use 'gerar_relatorio_executivo_excel' quando pedirem relatórios ou planilhas em Excel. "
        "Use 'sincronizar_e_consultar_sql' quando pedirem consultas SQL na tabela 'produtos'. "
        "Use 'exportar_base_powerbi' quando pedirem exportação ou integração para o Power BI. "
        "Seja direto, executivo e apresente os números com clareza."
    )

    resposta = client.models.generate_content(
        model=MODELO_PADRAO,
        contents=mensagem_usuario,
        config=types.GenerateContentConfig(
            system_instruction=instrucao,
            tools=[
                consultar_catalogo_e_estoque,
                gerar_relatorio_executivo_excel,
                sincronizar_e_consultar_sql,
                exportar_base_powerbi,
                gerar_documento_word,
                gerar_apresentacao_powerpoint,
                gerar_relatorio_pdf,
                sincronizar_gestao_projetos,
                integrar_google_workspace,
                integrar_ecossistema_microsoft,
                sincronizar_nuvem_multi_cloud,
                executar_motor_crm_reativacao,
                gerar_dre_e_precificacao_dinamica,
                gerar_previsao_demanda_e_ordem_compra,
                executar_auditoria_antifraude_e_lgpd,
                analisar_benchmarking_e_catalogo_seo,
            ],
            temperature=0.2,
        ),
    )
    return resposta.text


def subagente_suporte_cliente(mensagem_usuario: str) -> str:
    instrucao = (
        "Você é o Sub-Agente de Suporte ao Cliente do E-commerce. "
        "Use 'rastrear_pedido_cliente' quando informarem o número de um pedido (ex: 1001, 1002, 1003). "
        "Use 'consultar_politica_trocas_suporte' para dúvidas sobre devoluções, prazos e reembolsos. "
        "Mantenha um tom prestativo, claro e resolutivo."
    )

    resposta = client.models.generate_content(
        model=MODELO_PADRAO,
        contents=mensagem_usuario,
        config=types.GenerateContentConfig(
            system_instruction=instrucao,
            tools=[rastrear_pedido_cliente, consultar_politica_trocas_suporte],
            temperature=0.2,
        ),
    )
    return resposta.text


def processar_atendimento(mensagem_usuario: str):
    rota = agente_roteador(mensagem_usuario)
    print(f"\n[ROTEADOR] -> Direcionando para o sub-agente: {rota}")

    if rota == "SUPORTE":
        resposta_final = subagente_suporte_cliente(mensagem_usuario)
    else:
        resposta_final = subagente_vendas_estoque(mensagem_usuario)

    print(f"\n[{rota}]:\n{resposta_final}\n" + "-" * 60)


if __name__ == "__main__":
    print("=== SISTEMA MULTI-AGENTE DE E-COMMERCE & AUTOMAÇÃO EXCEL ===")
    print("Digite 'sair' para encerrar.\n")

    while True:
        entrada = input("Você: ").strip()
        if entrada.lower() in ["sair", "exit", "quit"]:
            break
        if not entrada:
            continue
        processar_atendimento(entrada)

        # ==========================================
# ORQUESTRADOR HÍBRIDO SÊNIOR (IA + ZERO-DOWNTIME OFFLINE FALLBACK)
# ==========================================
import os
import time
from ferramentas_ecommerce import motor_deterministico_offline, registrar_telemetria_sql


def processar_solicitacao_hibrida(mensagem_usuario: str, forcar_modo_offline: bool = False) -> str:
    """Executa via Agentes de IA (Gemini) ou aciona automaticamente o Motor Determinístico Offline se solicitado ou em caso de falha de API."""
    if forcar_modo_offline or not os.getenv("GEMINI_API_KEY"):
        return motor_deterministico_offline(mensagem_usuario)

    inicio = time.perf_counter()
    try:
        rota = agente_roteador(mensagem_usuario)
        if rota == "SUPORTE":
            resposta = subagente_suporte_cliente(mensagem_usuario)
        else:
            resposta = subagente_vendas_estoque(mensagem_usuario)

        latencia = (time.perf_counter() - inicio) * 1000
        registrar_telemetria_sql(f"Agente_IA_{rota}", mensagem_usuario, latencia, "IA (Google Gemini)")
        return f"🤖 **[Agente IA Acionado: `{rota}` | Latência: `{latencia:.0f} ms`]**\n\n{resposta}"
    except Exception as erro_api:
        resposta_fallback = motor_deterministico_offline(mensagem_usuario)
        return (
            f"🛡️ **[Auto-Fallback Sênior Ativado: API externa indisponível ({type(erro_api).__name__}). "
            f"Operação assumida pelo Motor Local Sem IA]**\n\n{resposta_fallback}"
        )

    # ==========================================
# GOVERNANÇA RBAC, ORQUESTRADOR MULTI-LLM UNIVERSAL & TELEMETRIA FINOPS
# ==========================================
import os
import time
from ferramentas_ecommerce import (
    executar_curva_abc_forecast_zscore,
    registrar_finops_llm,
    motor_deterministico_offline,
    registrar_telemetria_sql,
)


def verificar_permissao_rbac(mensagem_usuario: str, cargo_rbac: str) -> str:
    """Verifica se o cargo atual possui privilégio para acessar dados financeiros sensíveis, LGPD ou bancos restritos."""
    texto = mensagem_usuario.lower()
    termos_restritos_c_level = ["dre", "lucro", "margem", "imposto", "ebitda", "fraude", "antifraude", "chargeback", "cpf"]

    if "Operador de Suporte" in cargo_rbac and any(t in texto for t in termos_restritos_c_level):
        registrar_telemetria_sql("RBAC_Security_Block", f"Bloqueio [{cargo_rbac}]: {mensagem_usuario}", 0.8, "RBAC_Guardrail")
        return (
            f"🔒 **[BLOQUEIO DE GOVERNANÇA RBAC — Perfil Ativo: `{cargo_rbac}`]**\n\n"
            "Seu nível de credencial atual permite apenas **Rastreamento de Pedidos, Suporte ao Cliente e Consulta de Estoque**. "
            "Relatórios de **DRE Financeiro, Margem Líquida e Auditoria Antifraude/LGPD** exigem perfil **Analista de BI** ou **C-Level / Diretoria**."
        )
    return ""


def processar_solicitacao_enterprise(
    mensagem_usuario: str,
    provedor_llm: str = "Google Gemini 2.5 Flash",
    forcar_modo_offline: bool = False,
    cargo_rbac: str = "C-Level / Diretoria (Acesso Total)",
) -> str:
    """Orquestrador Staff Engineer com validação RBAC, roteamento Multi-LLM, Auto-Fallback Offline e cálculo FinOps."""
    inicio = time.perf_counter()

    # 1. Validação de Segurança de Acesso por Cargo (RBAC)
    bloqueio_rbac = verificar_permissao_rbac(mensagem_usuario, cargo_rbac)
    if bloqueio_rbac:
        return bloqueio_rbac

    # 2. Se estiver em Modo Offline ou provedor local sem IA
    if forcar_modo_offline or provedor_llm == "Motor Determinístico Offline (Sem IA)" or not os.getenv("GEMINI_API_KEY"):
        resp_off = motor_deterministico_offline(mensagem_usuario)
        latencia = (time.perf_counter() - inicio) * 1000
        fin = registrar_finops_llm("Motor Determinístico Offline (Sem IA)", mensagem_usuario, resp_off, latencia)
        rodape_finops = (
            f"\n\n---\n💰 **Telemetria FinOps:** `Provedor: {fin['provedor']}` | "
            f"`Tokens: {fin['tokens']}` | `Custo: R$ 0,00000` | `Economia gerada vs. GPT-4o: R$ {fin['economia_brl']:.5f}`"
        )
        return resp_off + rodape_finops

    # 3. Roteamento Híbrido Multi-LLM com Auto-Fallback
    try:
        if "abc" in mensagem_usuario.lower() or "forecast" in mensagem_usuario.lower() or "z-score" in mensagem_usuario.lower():
            resposta_core = executar_curva_abc_forecast_zscore()
            rota = "DATA_SCIENCE_ML"
        else:
            rota = agente_roteador(mensagem_usuario)
            if rota == "SUPORTE":
                resposta_core = subagente_suporte_cliente(mensagem_usuario)
            else:
                resposta_core = subagente_vendas_estoque(mensagem_usuario)

        latencia = (time.perf_counter() - inicio) * 1000
        registrar_telemetria_sql(f"MultiLLM_{provedor_llm}", mensagem_usuario, latencia, f"RBAC: {cargo_rbac}")
        fin = registrar_finops_llm(provedor_llm, mensagem_usuario, resposta_core, latencia)

        cabecalho = f"🤖 **[Orquestrador `{provedor_llm}` | Agente: `{rota}` | RBAC: `{cargo_rbac}` | `{latencia:.0f} ms`]**\n\n"
        rodape_finops = (
            f"\n\n---\n💰 **Telemetria FinOps:** `Tokens: {fin['tokens']}` | "
            f"`Custo Estimado: US$ {fin['custo_usd']:.6f} (R$ {fin['custo_brl']:.5f})` | "
            f"`Economia vs. Modelo Pesado: R$ {fin['economia_brl']:.5f}`"
        )
        return cabecalho + resposta_core + rodape_finops

    except Exception as erro_api:
        resp_fallback = motor_deterministico_offline(mensagem_usuario)
        latencia = (time.perf_counter() - inicio) * 1000
        fin = registrar_finops_llm("Motor Determinístico Offline (Sem IA)", mensagem_usuario, resp_fallback, latencia)
        return (
            f"🛡️ **[Auto-Fallback Ativado ({type(erro_api).__name__}) — Assumido pelo Motor Local Sem IA]**\n\n"
            f"{resp_fallback}\n\n---\n💰 **Telemetria FinOps:** `Custo: R$ 0,00000 (Fallback Resiliente)`"
        )