#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Meridian Fintech ERP - Suite B2B Multi-Tenant Corporativa
Cargos Padronizados:
- ADMIN (Proprietário / Admin Global)
- MERCHANT (Diretor / Gerente de Unidade)
- AUDITOR (Supervisor / Auditoria)
- PARTNER (Vendedor / Especialista Comissionado)
- STAFF (Atendente / Operador de Caixa)
"""

import sys
import uuid
import importlib
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import ui_components
import auth_engine
importlib.reload(ui_components)
importlib.reload(auth_engine)

from fintech_engine import (
    create_fintech_engine,
    generate_transaction_id,
    IntegrityError,
    SplitRule,
    MoneyCalculator
)
from monitor_engine import IntegrityMonitor
from excel_conciliador import (
    export_accounting_report,
    import_transactions_from_excel
)
from fintech_agents import MeridianAgentHub
from auth_engine import MeridianAuthManager, LGPDMasker
from ui_components import (
    apply_meridian_theme,
    render_hero_banner,
    render_kpi_card,
    render_virtual_wallet_card,
    render_security_radar,
    render_transaction_timeline_item,
    render_receipt_card,
    render_payout_receipt_card,
    render_whatsapp_invoice_card,
    render_multi_split_visual_card,
    generate_executive_statement_html,
    render_plotly_neon_charts
)


def init_fintech_session():
    if "integrity_monitor" not in st.session_state:
        st.session_state.integrity_monitor = IntegrityMonitor()

    if "fintech_engine" not in st.session_state:
        st.session_state.fintech_engine = create_fintech_engine(db_dir=".")

    if "agent_hub" not in st.session_state:
        st.session_state.agent_hub = MeridianAgentHub(
            engine=st.session_state.fintech_engine,
            monitor=st.session_state.integrity_monitor
        )

    if "auth_manager" not in st.session_state:
        st.session_state.auth_manager = MeridianAuthManager(
            engine=st.session_state.fintech_engine,
            monitor=st.session_state.integrity_monitor
        )

    return (
        st.session_state.fintech_engine,
        st.session_state.integrity_monitor,
        st.session_state.agent_hub,
        st.session_state.auth_manager
    )


def get_active_user(auth: MeridianAuthManager) -> dict:
    user = st.session_state.get("user_session")
    if not user:
        users = auth._load_users()
        return users.get("admin", {
            "username": "admin",
            "nome_exibicao": "Diretoria / Proprietario (Master Admin)",
            "role": "ADMIN",
            "cargo": "Admin / Proprietario",
            "clinica_id": "ALL",
            "vendedor_id": "ALL",
            "chave_pix": "tesouraria@meridian.com.br",
            "api_key": "mrd_live_master"
        })
    return user


# =============================================================================
# ABA 1: CHECKOUT CORPORATIVO UNIFICADO
# =============================================================================

def render_tab_checkout(engine, hub, auth, user, lgpd_active: bool):
    col_form, col_recent = st.columns([1.8, 1.2])
    is_admin = (user.get("role") == "ADMIN" or user.get("vendedor_id") == "ALL")

    with col_form:
        st.markdown("#### Emissao de Ordem de Pagamento & Split Instantaneo")
        c1, c2 = st.columns(2)
        with c1:
            valor = st.number_input("Valor Bruto da Venda / Contrato (R$)", min_value=0.01, max_value=999999.99, value=250.00, step=10.00)
            metodo_pagamento = st.selectbox("Metodo de Pagamento", ["PIX", "CARTAO", "BOLETO"])
        with c2:
            comprador = st.text_input("Nome / CPF ou CNPJ do Cliente", value="Carlos Eduardo CPF 412.889.301-15")
            if is_admin:
                vendedor_id = st.text_input("ID da Carteira da Unidade", value="VENDEDOR_B")
            else:
                vendedor_id = st.text_input(
                    "Carteira Recebedora Vinculada",
                    value=user.get("vendedor_id", "VENDEDOR_B"),
                    disabled=True
                )

        usar_antifraude = st.checkbox("Ativar Inspecao do Agente Antifraude em Tempo Real", value=True)

        if st.button("Processar Pagamento & Assinar Ledger", use_container_width=True):
            try:
                tx_data = {
                    "id": generate_transaction_id(),
                    "valor_bruto": valor,
                    "metodo_pagamento": metodo_pagamento,
                    "status": "PENDING",
                    "comprador": comprador.strip() or "ANONIMO",
                    "vendedor_id": vendedor_id.strip() or "VENDEDOR_B",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "operador": user.get("username", "sistema"),
                        "cargo_operador": user.get("cargo", "Operador"),
                        "pii_hash_lgpd": LGPDMasker.pii_audit_hash(comprador)
                    }
                }

                if usar_antifraude:
                    outcome = hub.process_guarded_checkout(tx_data)
                    fraud_info = outcome["fraud_analysis"]

                    if not outcome["approved"]:
                        render_security_radar(
                            is_healthy=False,
                            title=f"TRANSACAO BLOQUEADA PELO ANTIFRAUDE (Score: {fraud_info['risk_score']}/100)",
                            detail=f"Motivo: {fraud_info['reason']}"
                        )
                        return

                    result = outcome["transaction"]
                    st.toast(f"Aprovado no Antifraude (Score: {fraud_info['risk_score']}/100)")
                else:
                    result = engine.create_transaction(tx_data)

                split_result = engine.wallet_manager.calculate_split(result)
                render_receipt_card(result, split_result)

            except IntegrityError as e:
                render_security_radar(False, "VIOLACAO DE INTEGRIDADE DETECTADA", str(e))
            except Exception as e:
                st.error(f"Erro ao processar pagamento: {e}")

    with col_recent:
        st.markdown("#### Ultimas Transacoes da Unidade")
        tenant_tx = auth.get_tenant_transactions(user)
        recent = list(reversed(tenant_tx[-5:]))
        if recent:
            for tx in recent:
                render_transaction_timeline_item(LGPDMasker.sanitize_transaction(tx, mask_active=lgpd_active))
        else:
            st.info("Nenhuma transacao registrada para esta conta.")


# =============================================================================
# ABA 2: MOTOR DE SPLIT MULTI-BENEFICIÁRIOS (EMPRESA, SUPERVISOR E COMISSIONADOS)
# =============================================================================

def render_tab_multi_split(hub, auth, user):
    st.markdown("#### Motor de Split Multi-Beneficiarios (Empresa, Supervisores, Vendedores & Parceiros)")
    st.caption(
        "Ao liquidar uma venda ou contrato aqui, a comissao liquida de cada colaborador ou parceiro "
        "cai instantaneamente na carteira individual dele para consulta e Saque Pix."
    )

    col_cfg, col_preview = st.columns([1.55, 1.45])

    with col_cfg:
        preset_split = st.selectbox(
            "Modelo de Split Corporativo Pre-Configurado:",
            [
                "Operacao Comercial & Vendas (Empresa 50% + Vendedor Comissionado 35% + Supervisor 10% + Plataforma 5%)",
                "Rede de Franquias & Filiais (Unidade Franqueada 75% + Matriz Royalties 15% + Fundo Mkt 5% + Plataforma 5%)",
                "Servicos & Consultoria B2B (Empresa 65% + Especialista Executor 20% + Pre-Venda SDR 10% + Plataforma 5%)"
            ]
        )

        if "Operacao Comercial" in preset_split:
            d_b1, d_p1, d_v1 = "VENDEDOR_B", "Empresa Matriz", 50.0
            d_b2, d_p2, d_v2 = "DR_CIRURGIAO", "Vendedor / Comissionado", 35.0
            d_b3, d_p3, d_v3 = "LAB_ANALISES", "Supervisor Operacional", 10.0
            d_desc = "Contrato Comercial Corporativo #8490"
        elif "Franquias" in preset_split:
            d_b1, d_p1, d_v1 = "VENDEDOR_A", "Unidade Franqueada", 75.0
            d_b2, d_p2, d_v2 = "FRANQUEADORA_HQ", "Royalties Matriz", 15.0
            d_b3, d_p3, d_v3 = "FUNDO_PROPAGANDA", "Fundo de Marketing", 5.0
            d_desc = "Venda de Licenca Regional"
        else:
            d_b1, d_p1, d_v1 = "VENDEDOR_A", "Empresa Matriz", 65.0
            d_b2, d_p2, d_v2 = "EXEC_VENDAS", "Comissao Closer", 20.0
            d_b3, d_p3, d_v3 = "SDR_PREVENDA", "Comissao Pre-Venda", 10.0
            d_desc = "Fechamento de Contrato Anual B2B"

        m1, m2, m3 = st.columns(3)
        with m1:
            valor_ms = st.number_input("Valor Total da Venda / Contrato (R$)", min_value=10.0, value=1200.00, step=100.0)
        with m2:
            metodo_ms = st.selectbox("Metodo de Pagamento", ["PIX", "CARTAO", "BOLETO"], key="ms_met")
        with m3:
            taxa_plat_ms = st.number_input("Taxa Plataforma (%)", min_value=0.0, max_value=30.0, value=5.0, step=0.5)

        comprador_ms = st.text_input("Cliente / Empresa Pagadora", value="Patricia Mendes CPF 309.112.448-90")
        contrato_ms = st.text_input("Identificacao do Pedido / Contrato", value=d_desc)

        st.markdown("**Participantes e Percentuais do Split:**")
        b1_c1, b1_c2, b1_c3 = st.columns([1.3, 1.3, 1])
        with b1_c1:
            vid_1 = st.text_input("Carteira Beneficiario 1", value=d_b1)
        with b1_c2:
            rol_1 = st.text_input("Cargo / Papel 1", value=d_p1)
        with b1_c3:
            pct_1 = st.number_input("% Benef. 1", min_value=0.0, max_value=100.0, value=d_v1, step=1.0)

        b2_c1, b2_c2, b2_c3 = st.columns([1.3, 1.3, 1])
        with b2_c1:
            vid_2 = st.text_input("Carteira Beneficiario 2", value=d_b2)
        with b2_c2:
            rol_2 = st.text_input("Cargo / Papel 2", value=d_p2)
        with b2_c3:
            pct_2 = st.number_input("% Benef. 2", min_value=0.0, max_value=100.0, value=d_v2, step=1.0)

        b3_c1, b3_c2, b3_c3 = st.columns([1.3, 1.3, 1])
        with b3_c1:
            vid_3 = st.text_input("Carteira Beneficiario 3", value=d_b3)
        with b3_c2:
            rol_3 = st.text_input("Cargo / Papel 3", value=d_p3)
        with b3_c3:
            pct_3 = st.number_input("% Benef. 3", min_value=0.0, max_value=100.0, value=d_v3, step=1.0)

    with col_preview:
        soma_pct = round(taxa_plat_ms + pct_1 + pct_2 + pct_3, 2)
        render_kpi_card(
            "Validacao Matematica da Regra Multi-Split",
            f"{soma_pct:.2f}% / 100.00%",
            "Pronto para liquidacao atomica" if soma_pct == 100.0 else "Ajuste os percentuais para fechar em 100%",
            badge="SPLIT EXATO" if soma_pct == 100.0 else "AJUSTAR %",
            badge_type="paid" if soma_pct == 100.0 else "pending"
        )

        if st.button("Liquidar Venda & Creditar Carteiras da Equipe", use_container_width=True):
            try:
                lista_benef = [
                    {"vendedor_id": vid_1, "papel": rol_1, "percentual": pct_1},
                    {"vendedor_id": vid_2, "papel": rol_2, "percentual": pct_2},
                    {"vendedor_id": vid_3, "papel": rol_3, "percentual": pct_3},
                ]
                lista_benef = [b for b in lista_benef if float(b["percentual"]) > 0]
                res_ms = auth.execute_multi_beneficiary_split(
                    valor_bruto=valor_ms,
                    metodo_pagamento=metodo_ms,
                    comprador=comprador_ms,
                    descricao_contrato=contrato_ms,
                    taxa_plataforma_pct=taxa_plat_ms,
                    beneficiarios=lista_benef
                )
                hub.save_agent_audit_log("MULTI_SPLIT_EXECUTED", {"tx_id": res_ms["transaction_id"], "by": user.get("username")})
                render_multi_split_visual_card(res_ms)
            except Exception as e:
                st.error(f"Erro no Multi-Split: {e}")


# =============================================================================
# ABA 3: CARTEIRAS DIGITAIS 3D E ASSINATURAS (MRR)
# =============================================================================

def render_tab_wallets(engine, auth, user):
    role = user.get("role", "MERCHANT")
    col_w, col_sub = st.columns([1.8, 1.2])

    with col_w:
        st.markdown("#### Cartoes Corporativos & Saldos Liquidos Disponiveis")
        wallets = auth.get_tenant_wallets(user)

        if wallets:
            w_cols = st.columns(2 if len(wallets) > 1 else 1)
            for idx, (seller_id, balance) in enumerate(wallets.items()):
                with w_cols[idx % len(w_cols)]:
                    label_card = "COMMISSION WALLET" if role == "PARTNER" else "CORPORATE WALLET"
                    render_virtual_wallet_card(seller_id, float(balance), label=label_card)
        else:
            st.info("Nenhuma carteira ativa para este perfil.")

        if role in ("ADMIN", "MERCHANT"):
            subs = engine.db.load_subscriptions() if hasattr(engine, "db") else []
            mrr_ativo = sum(float(s.get("mrr_bruto", 0)) for s in subs if s.get("status") == "ACTIVE")
            mrr_plat = sum(float(s.get("mrr_plataforma", 0)) for s in subs if s.get("status") == "ACTIVE")

            m1, m2, m3 = st.columns(3)
            with m1:
                render_kpi_card("Assinaturas Ativas", str(sum(1 for s in subs if s.get("status") == "ACTIVE")), "Contratos recorrentes")
            with m2:
                render_kpi_card("MRR Bruto Mensal", f"R$ {mrr_ativo:,.2f}", "Faturamento recorrente")
            with m3:
                render_kpi_card("MRR Plataforma", f"R$ {mrr_plat:,.2f}", "Receita liquida")

    with col_sub:
        if role in ("ADMIN", "MERCHANT"):
            st.markdown("#### Novo Plano / Contrato Recorrente (MRR)")
            sub_id = st.text_input("Codigo do Contrato", value=f"SUB_{uuid.uuid4().hex[:6].upper()}")
            preco_mrr = st.number_input("Valor Mensal Contratado (R$)", min_value=1.00, value=149.90, step=10.00)
            dias_ciclo = st.selectbox("Ciclo de Renovacao", options=[30, 180, 365], format_func=lambda d: f"Ciclo de {d} dias")

            if st.button("Ativar Assinatura MRR", use_container_width=True):
                try:
                    prox_data = (datetime.now(timezone.utc) + timedelta(days=dias_ciclo)).isoformat()
                    nova_sub = engine.process_subscription({
                        "subscription_id": sub_id,
                        "mrr": preco_mrr,
                        "status": "ACTIVE",
                        "next_billing_date": prox_data
                    })
                    st.success(f"Contrato {nova_sub.subscription_id} ativado com sucesso.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao ativar assinatura: {e}")
        else:
            render_security_radar(
                True,
                f"CONTA INDIVIDUAL DE COMISSIONADO ({user.get('vendedor_id')})",
                f"Cargo: {user.get('cargo')} • Comissao padrao configurada: {user.get('comissao_padrao_pct', '0')}%"
            )


# =============================================================================
# ABA 4: SAQUES PIX & ANTECIPAÇÃO DE RECEBÍVEIS
# =============================================================================

def render_tab_payouts(engine, hub, auth, user):
    role = user.get("role", "MERCHANT")
    wallets = auth.get_tenant_wallets(user)

    col_pay, col_hist = st.columns([1.5, 1.5])

    with col_pay:
        st.markdown("#### Solicitar Saque Pix ou Antecipacao de Comissoes")
        opcoes_vendedores = list(wallets.keys()) if wallets else [user.get("vendedor_id", "VENDEDOR_B")]
        vendedor_alvo = st.selectbox(
            "Carteira de Origem",
            options=opcoes_vendedores,
            disabled=(role == "PARTNER")
        )

        saldo_disp = float(wallets.get(vendedor_alvo, Decimal("0.00")))
        render_kpi_card(
            f"Saldo Disponivel para Saque ({vendedor_alvo})",
            f"R$ {saldo_disp:,.2f}",
            "Liquidavel via Pix com assinatura SHA-256 no Ledger",
            badge="DISPONIVEL" if saldo_disp > 0 else "ZERADO",
            badge_type="paid" if saldo_disp > 0 else "pending"
        )

        valor_saque = st.number_input(
            "Valor Desejado para Saque (R$)",
            min_value=1.00,
            max_value=max(saldo_disp, 1.00),
            value=min(50.00, max(saldo_disp, 1.00)),
            step=10.00
        )
        chave_pix = st.text_input("Sua Chave Pix de Destino", value=user.get("chave_pix", "pix@empresa.com.br"))

        antecipar = st.checkbox("Receber em 3 Segundos (Antecipacao Expressa: Taxa 2.5%)", value=True)
        taxa_simulada = round(valor_saque * 0.025, 2) if antecipar else 0.00
        liquido_simulado = round(valor_saque - taxa_simulada, 2)

        st.info(
            f"Resumo: Solicitado: `R$ {valor_saque:,.2f}` | "
            f"Taxa (2.5%): `R$ {taxa_simulada:,.2f}` | **Liquido no seu Pix: `R$ {liquido_simulado:,.2f}`**"
        )

        if st.button("Confirmar Saque e Transferir para Meu Pix", use_container_width=True):
            try:
                payout_obj = auth.request_payout(
                    vendedor_id=vendedor_alvo,
                    valor=valor_saque,
                    chave_pix=chave_pix,
                    antecipacao_imediata=antecipar
                )
                hub.save_agent_audit_log("PIX_PAYOUT_EXECUTED", payout_obj.model_dump())
                render_payout_receipt_card(payout_obj)
            except Exception as e:
                st.error(f"Falha no saque: {e}")

    with col_hist:
        st.markdown("#### Historico de Saques e Liquidacoes Pix")
        filtro_vid = "ALL" if user.get("role") == "ADMIN" else user.get("vendedor_id")
        historico_saques = auth.load_payouts(vendedor_id=filtro_vid)

        if historico_saques:
            df_pay = pd.DataFrame([
                {
                    "Protocolo": p.get("payout_id"),
                    "Titular": p.get("vendedor_id"),
                    "Solicitado": f"R$ {float(p.get('valor_solicitado', 0)):,.2f}",
                    "Taxa (2.5%)": f"R$ {float(p.get('taxa_antecipacao', 0)):,.2f}",
                    "Liquido Pix": f"R$ {float(p.get('valor_liquido_pix', 0)):,.2f}",
                    "Modalidade": p.get("modalidade"),
                    "Status": p.get("status")
                }
                for p in reversed(historico_saques)
            ])
            st.dataframe(df_pay, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum saque realizado para esta carteira ate o momento.")


# =============================================================================
# ABA 5: GERADOR DE LINKS DE PAGAMENTO & FATURA WHATSAPP
# =============================================================================

def render_tab_payment_links(hub, auth, user):
    is_admin = (user.get("role") == "ADMIN" or user.get("vendedor_id") == "ALL")
    col_create, col_list = st.columns([1.45, 1.55])

    with col_create:
        st.markdown("#### Criar Link de Pagamento & Fatura para WhatsApp")
        c1, c2 = st.columns(2)
        with c1:
            cli_nome = st.text_input("Nome do Cliente / Empresa", value="Roberto Almeida")
            cli_whats = st.text_input("WhatsApp do Cliente (com DDD)", value="11999998888")
        with c2:
            valor_cob = st.number_input("Valor da Cobranca (R$)", min_value=1.00, value=380.00, step=20.00)
            metodo_pref = st.selectbox("Metodo Principal do Link", ["PIX", "CARTAO", "BOLETO"])

        desc_servico = st.text_input("Descricao do Pedido / Servico / Contrato", value="Licenca Corporativa + Setup")
        d1, d2 = st.columns(2)
        with d1:
            venc = st.selectbox("Prazo de Vencimento", ["24 horas", "48 horas", "5 dias uteis", "A vista"])
        with d2:
            if is_admin:
                vend_link = st.text_input("Carteira Emissora", value="VENDEDOR_B")
            else:
                vend_link = st.text_input("Carteira Emissora", value=user.get("vendedor_id", "VENDEDOR_B"), disabled=True)

        if st.button("Gerar Link de Pagamento & Fatura WhatsApp", use_container_width=True):
            try:
                fatura = auth.create_payment_link(
                    vendedor_id=vend_link,
                    cliente_nome=cli_nome,
                    cliente_whatsapp=cli_whats,
                    descricao=desc_servico,
                    valor=valor_cob,
                    metodo_preferencial=metodo_pref,
                    vencimento=venc
                )
                hub.save_agent_audit_log("PAYMENT_LINK_CREATED", {"link_id": fatura.link_id, "by": user.get("username")})
                render_whatsapp_invoice_card(fatura)
            except Exception as e:
                st.error(f"Erro ao gerar link de cobranca: {e}")

    with col_list:
        st.markdown("#### Faturas Emitidas & Confirmacao Rapida")
        filtro_vid = "ALL" if is_admin else user.get("vendedor_id")
        links = auth.load_payment_links(vendedor_id=filtro_vid)

        if links:
            pendentes = [lnk for lnk in links if lnk.get("status") == "PENDING"]
            if pendentes:
                opcoes_liq = {
                    f"{lnk['link_id']} | {lnk['cliente_nome']} — R$ {float(lnk['valor']):,.2f} ({lnk['descricao']})": lnk["transaction_id"]
                    for lnk in reversed(pendentes)
                }
                escolhido = st.selectbox("Simular pagamento recebido do cliente:", list(opcoes_liq.keys()))
                if st.button("Confirmar Recebimento Pix Agora", use_container_width=True):
                    tx_settled = auth.settle_pending_transaction(opcoes_liq[escolhido])
                    hub.save_agent_audit_log("WEBHOOK_PAYMENT_CONFIRMED", {"transaction_id": tx_settled["id"]})
                    st.success(f"Fatura liquidada. Saldo de `{tx_settled['vendedor_id']}` creditado.")
                    st.rerun()

            df_links = pd.DataFrame([
                {
                    "Link ID": lnk.get("link_id"),
                    "Cliente": lnk.get("cliente_nome"),
                    "Descricao": lnk.get("descricao"),
                    "Valor": f"R$ {float(lnk.get('valor', 0)):,.2f}",
                    "Status": lnk.get("status"),
                    "Carteira": lnk.get("vendedor_id")
                }
                for lnk in reversed(links)
            ])
            st.dataframe(df_links, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum link de cobranca emitido ainda.")


# =============================================================================
# ABA 6: PLAYGROUND DE API & SERVIDOR FASTAPI REAL
# =============================================================================

def render_tab_api_playground(engine, hub, auth, user):
    st.markdown("#### Developer Portal — Playground de API (`X-Meridian-Key`) & Webhooks")
    col_api, col_wh = st.columns([1.45, 1.55])

    with col_api:
        st.markdown("##### 1. Testar Requisicao `POST /v1/transactions/checkout`")
        api_key_input = st.text_input("Header `X-Meridian-Key`", value=user.get("api_key", ""))
        c_a1, c_a2 = st.columns(2)
        with c_a1:
            api_valor = st.number_input("Payload `valor_bruto`", min_value=1.00, value=499.90, step=50.00)
            api_metodo = st.selectbox("Payload `metodo_pagamento`", ["PIX", "CARTAO", "BOLETO"], key="api_met")
        with c_a2:
            api_comprador = st.text_input("Payload `comprador`", value="CLIENTE_CORP_9042")
            api_mode = st.selectbox("Modo de Liquidacao", ["Aprovacao Instantanea (PAID)", "Aguardar Webhook (PENDING)"])

        if st.button("Disparar Chamada de API Real no Motor", use_container_width=True):
            owner = auth.get_user_by_api_key(api_key_input)
            if not owner:
                render_security_radar(False, "HTTP 401 UNAUTHORIZED", "A chave X-Meridian-Key informada e invalida.")
            else:
                vid_target = owner.get("vendedor_id") if owner.get("vendedor_id") != "ALL" else "VENDEDOR_B"
                if "PENDING" in api_mode:
                    fatura_api = auth.create_payment_link(
                        vendedor_id=vid_target,
                        cliente_nome=api_comprador,
                        cliente_whatsapp="5511999999999",
                        descricao="Pedido via API REST",
                        valor=api_valor,
                        metodo_preferencial=api_metodo
                    )
                    st.success(f"HTTP 201 CREATED — Cobranca `{fatura_api.transaction_id}` aguardando Webhook.")
                else:
                    outcome = hub.process_guarded_checkout({
                        "id": generate_transaction_id(),
                        "valor_bruto": api_valor,
                        "metodo_pagamento": api_metodo,
                        "status": "PENDING",
                        "comprador": api_comprador,
                        "vendedor_id": vid_target,
                        "metadata": {"origem": "api_rest_v1", "authenticated_user": owner.get("username")}
                    })
                    if outcome["approved"]:
                        st.success("HTTP 200 OK — Transacao aprovada e assinada com SHA-256.")

    with col_wh:
        st.markdown("##### 2. Simulador de Webhook Bancario (`PAYMENT_CONFIRMED`)")
        tenant_txs = auth.get_tenant_transactions(user)
        pendentes_wh = [t for t in tenant_txs if t.get("status") == "PENDING"]

        if pendentes_wh:
            wh_options = {
                f"{t['id'][:10]}... | R$ {float(t['valor_bruto']):,.2f} | {t['comprador']}": t["id"]
                for t in reversed(pendentes_wh)
            }
            wh_sel = st.selectbox("Transacao PENDING aguardando confirmacao:", list(wh_options.keys()))
            tx_id_wh = wh_options[wh_sel]

            if st.button("Disparar Evento Webhook & Liquidar Transacao", use_container_width=True):
                settled = auth.settle_pending_transaction(tx_id_wh)
                hub.save_agent_audit_log("BANK_WEBHOOK_SETTLED", {"transaction_id": tx_id_wh})
                render_security_radar(
                    True,
                    f"WEBHOOK PROCESSADO COM SUCESSO (TX {tx_id_wh[:8]}...)",
                    f"Repasse liquido creditado na carteira de {settled.get('vendedor_id')}."
                )
        else:
            render_security_radar(True, "FILA DE WEBHOOKS LIMPA", "Todas as transacoes atuais ja estao liquidadas (PAID).")


# =============================================================================
# ABA 7: EXTRATO EXECUTIVO (HTML/PDF) & CONCILIAÇÃO EXCEL
# =============================================================================

def render_tab_excel_and_statements(engine, auth, user, lgpd_active: bool):
    role = user.get("role", "MERCHANT")
    raw_txs = auth.get_tenant_transactions(user)
    tenant_txs = [LGPDMasker.sanitize_transaction(t, mask_active=lgpd_active) for t in raw_txs]
    wallets = auth.get_tenant_wallets(user)
    filtro_vid = "ALL" if role == "ADMIN" else user.get("vendedor_id")
    payouts = auth.load_payouts(vendedor_id=filtro_vid)
    saldo_total = float(wallets.get(user.get("vendedor_id"), 0.0)) if role == "PARTNER" else sum(float(v) for v in wallets.values())

    st.markdown(f"#### Extrato Executivo de Repasses & Comissoes — {user.get('nome_exibicao')}")
    html_report = generate_executive_statement_html(
        user=user,
        transactions=tenant_txs,
        payouts=payouts,
        balance=saldo_total
    )

    c_p1, c_p2 = st.columns(2)
    with c_p1:
        mostrar_preview = st.checkbox("Exibir Pre-Visualizacao do Meu Extrato na Tela", value=False)
    with c_p2:
        nome_html = f"extrato_{user.get('vendedor_id', 'meridian').lower()}.html"
        st.download_button(
            label=f"Baixar Meu Extrato Oficial ({nome_html}) — Pronto para PDF",
            data=html_report.encode("utf-8"),
            file_name=nome_html,
            mime="text/html",
            use_container_width=True
        )

    if mostrar_preview:
        components.html(html_report, height=560, scrolling=True)

    if role in ("ADMIN", "MERCHANT", "AUDITOR"):
        st.divider()
        col_exp, col_imp = st.columns(2)
        with col_exp:
            render_kpi_card("Automacao Contabil Multi-Abas (.xlsx)", "DRE + Fluxo + MRR", "Exportacao Decimal com hash SHA-256")
            nome_arquivo = st.text_input("Arquivo de Fechamento Contabil", value="fechamento_contabil.xlsx")

            if st.button("Gerar e Blindar Fechamento Excel", use_container_width=True):
                try:
                    caminho_gerado = export_accounting_report(output_file=nome_arquivo, engine=engine)
                    render_security_radar(True, f"PLANILHA '{caminho_gerado.name}' ASSINADA VIA SHA-256", "Pronta para envio contabil.")
                except Exception as e:
                    st.error(f"Falha ao exportar Excel: {e}")

            arquivo_local = Path(Path(nome_arquivo).name)
            if arquivo_local.exists():
                with open(arquivo_local, "rb") as f:
                    st.download_button(
                        label=f"Baixar Planilha ({arquivo_local.name})",
                        data=f.read(),
                        file_name=arquivo_local.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

        with col_imp:
            render_kpi_card("Importacao de Lote Validada (Pydantic v2)", "CSV / XLSX -> Ledger", "Converte planilhas em transacoes auditadas")
            uploaded_file = st.file_uploader("Arraste sua planilha .xlsx ou .csv", type=["xlsx", "csv"])
            if uploaded_file is not None:
                if st.button("Validar Schema e Importar Lote", use_container_width=True):
                    temp_path = Path(uploaded_file.name)
                    try:
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        importadas = import_transactions_from_excel(str(temp_path), engine=engine)
                        st.success(f"{len(importadas)} transacoes importadas no Ledger.")
                    except Exception as e:
                        st.error(f"Erro na importacao: {e}")


# =============================================================================
# ABA 8: AGENTES IA, GRÁFICOS E SANDBOX DO CFO
# =============================================================================

def render_tab_agents(engine, monitor, hub, auth, user):
    is_admin = (user.get("role") == "ADMIN" or user.get("vendedor_id") == "ALL")
    tenant_tx = auth.get_tenant_transactions(user)

    diag = hub.run_full_diagnostics()
    cfo_data = diag["cfo_report"]

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card("Volume Auditado", f"{len(tenant_tx)} TXs", "Transacoes visiveis no perfil")
    with k2:
        render_kpi_card("Receita Bruta Global", f"R$ {float(cfo_data['gross_revenue']):,.2f}", "Total movimentado")
    with k3:
        render_kpi_card("Receita Plataforma", f"R$ {float(cfo_data['platform_revenue']):,.2f}", f"Margem: {cfo_data['net_margin_pct']}%")
    with k4:
        render_kpi_card("Ticket Medio", f"R$ {float(cfo_data['average_ticket']):,.2f}", f"{len(cfo_data['anomalies_detected'])} anomalias")

    render_plotly_neon_charts(tenant_tx)

    if is_admin:
        st.divider()
        st.markdown("#### Sandbox do CFO — Configurador Ao Vivo de Taxas de Split (Exclusivo Admin)")
        regras_atuais = engine.wallet_manager.split_rules
        s1, s2, s3 = st.columns(3)
        with s1:
            nova_taxa_plat = st.slider("Taxa da Plataforma (%)", min_value=0.5, max_value=30.0, value=float(regras_atuais.taxa_plataforma_pct), step=0.5)
        with s2:
            novo_custo_forn = st.slider("Custo de Fornecedor (%)", min_value=0.0, max_value=50.0, value=float(regras_atuais.custo_fornecedor_pct), step=1.0)
        with s3:
            nova_comissao_vend = round(max(0.0, 100.0 - nova_taxa_plat - novo_custo_forn), 2)
            render_kpi_card("Repasse Liquido Titular (%)", f"{nova_comissao_vend:.2f}%", f"Em R$ 1.000: Plataforma R$ {nova_taxa_plat * 10:.2f}")

        if st.button("Aplicar Nova Regra de Split no Motor", use_container_width=True):
            nova_regra = SplitRule(
                taxa_plataforma_pct=MoneyCalculator.to_decimal(nova_taxa_plat),
                comissao_vendedor_pct=MoneyCalculator.to_decimal(nova_comissao_vend),
                custo_fornecedor_pct=MoneyCalculator.to_decimal(novo_custo_forn)
            )
            engine.split_rules = nova_regra
            engine.payment_processor.split_rules = nova_regra
            engine.wallet_manager.split_rules = nova_regra
            st.success(f"Regra de Split atualizada: Plataforma {nova_taxa_plat}% | Titular {nova_comissao_vend}%")


# =============================================================================
# ABA 9: AUDITORIA SHA-256, ANONIMIZAÇÃO LGPD & CENTRAL DE ESTORNOS
# =============================================================================

def render_tab_audit(engine, hub, auth, user, lgpd_active: bool):
    role = user.get("role", "MERCHANT")
    is_admin = (role == "ADMIN" or user.get("vendedor_id") == "ALL")
    integro = engine.verify_ledger_integrity()

    if integro:
        render_security_radar(
            True,
            "LIVRO-RAZAO (LEDGER) 100% INTEGRO • CONFORMIDADE LGPD ATIVA",
            "Todas as assinaturas SHA-256 conferem e os tokens de anonimizacao PII estao vinculados."
        )
    else:
        render_security_radar(
            False,
            "ALERTA CRITICO: VIOLACAO DE HASH SHA-256 DETECTADA NO LEDGER",
            "Um ou mais arquivos financeiros sofreram modificacao nao autorizada fora do motor."
        )

    col_ledger, col_refund = st.columns([1.85, 1.15])
    transactions = auth.get_tenant_transactions(user)

    with col_ledger:
        c_head, c_toggle = st.columns([1.5, 1])
        with c_head:
            st.markdown("#### Livro-Razao Auditado (SHA-256 & LGPD)")
        with c_toggle:
            desmascarar = st.checkbox(
                "Revelar PII Original (Acesso Auditado)",
                value=not lgpd_active,
                disabled=not is_admin
            )

        mask_now = not desmascarar
        if transactions:
            rows = []
            for tx in reversed(transactions):
                tx_safe = LGPDMasker.sanitize_transaction(tx, mask_active=mask_now)
                sp = tx_safe.get("split", {})
                rows.append({
                    "ID": tx_safe.get("id", "")[:10] + "...",
                    "Bruto Venda": f"R$ {float(tx_safe.get('valor_bruto', 0)):,.2f}",
                    "Seu Repasse Liquido": f"R$ {float(sp.get('vendedor', 0)):,.2f}",
                    "Metodo": tx_safe.get("metodo_pagamento", ""),
                    "Status": tx_safe.get("status", ""),
                    "Cliente (LGPD)": tx_safe.get("comprador", ""),
                    "Carteira": tx_safe.get("vendedor_id", "")
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma transacao encontrada para este perfil.")

    with col_refund:
        st.markdown("#### Central de Estornos (Refund Engine)")
        if role in ("ADMIN", "MERCHANT"):
            tx_pagas = [t for t in transactions if t.get("status") == "PAID"]
            if tx_pagas:
                opcoes_estorno = {
                    f"{t['id'][:8]}... | R$ {float(t['valor_bruto']):,.2f} ({t['metodo_pagamento']})": t["id"]
                    for t in reversed(tx_pagas)
                }
                selecionada_label = st.selectbox("Selecione uma transacao paga para estornar:", list(opcoes_estorno.keys()))
                tx_id_alvo = opcoes_estorno[selecionada_label]

                if st.button("Executar Estorno e Debitar Carteira", use_container_width=True):
                    res = engine.refund_transaction(tx_id_alvo)
                    if res:
                        hub.save_agent_audit_log("TRANSACTION_REFUNDED", {"transaction_id": tx_id_alvo, "by": user.get("username")})
                        st.success(f"Transacao `{tx_id_alvo[:8]}...` estornada com sucesso.")
                        st.rerun()
                    else:
                        st.error("Nao foi possivel estornar a transacao selecionada.")
            else:
                st.info("Nenhuma transacao com status PAID disponivel para estorno.")
        else:
            st.info("Apenas o Proprietario / Admin pode executar estornos bancarios.")


def render_pagamentos():
    engine, monitor, hub, auth = init_fintech_session()
    wl_config = auth.load_whitelabel_config()
    user = get_active_user(auth)
    apply_meridian_theme(wl_config, is_logged_in=True)
    role = user.get("role", "MERCHANT")

    render_hero_banner(
        title=f"{wl_config.brand_name} — {user.get('nome_exibicao')}",
        subtitle=f"Cargo: {user.get('cargo', role)} • Carteira Vinculada: {user.get('vendedor_id')} • Unidade: {user.get('clinica_id', 'MATRIZ')}",
        badge_text=f"NIVEL RBAC: {role} • SHA-256 VERIFIED"
    )

    if role == "STAFF":
        t_chk, t_ms, t_wa = st.tabs([
            "1. Checkout Atendimento",
            "2. Lancar Venda Multi-Split",
            "3. Enviar Fatura WhatsApp"
        ])
        with t_chk:
            render_tab_checkout(engine, hub, auth, user, wl_config.lgpd_masking_default)
        with t_ms:
            render_tab_multi_split(hub, auth, user)
        with t_wa:
            render_tab_payment_links(hub, auth, user)

    elif role == "PARTNER":
        t_wal, t_pay, t_ext, t_aud, t_wa = st.tabs([
            "1. Minha Carteira 3D",
            "2. Meus Saques Pix",
            "3. Meu Extrato de Comissoes (PDF)",
            "4. Minhas Vendas Auditadas",
            "5. Emitir Link WhatsApp"
        ])
        with t_wal:
            render_tab_wallets(engine, auth, user)
        with t_pay:
            render_tab_payouts(engine, hub, auth, user)
        with t_ext:
            render_tab_excel_and_statements(engine, auth, user, wl_config.lgpd_masking_default)
        with t_aud:
            render_tab_audit(engine, hub, auth, user, wl_config.lgpd_masking_default)
        with t_wa:
            render_tab_payment_links(hub, auth, user)

    elif role == "AUDITOR":
        t_ext, t_aud, t_ag = st.tabs([
            "1. DRE, Extratos PDF & Excel",
            "2. Livro-Razao Auditado (LGPD)",
            "3. Indicadores & Graficos"
        ])
        with t_ext:
            render_tab_excel_and_statements(engine, auth, user, wl_config.lgpd_masking_default)
        with t_aud:
            render_tab_audit(engine, hub, auth, user, wl_config.lgpd_masking_default)
        with t_ag:
            render_tab_agents(engine, monitor, hub, auth, user)

    else:
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
            "1. Checkout",
            "2. Multi-Split",
            "3. Carteiras & MRR",
            "4. Saques Pix",
            "5. Links WhatsApp",
            "6. FastAPI & Webhooks",
            "7. Extrato PDF & Excel",
            "8. Graficos & CFO",
            "9. Ledger LGPD & Estornos"
        ])
        with tab1:
            render_tab_checkout(engine, hub, auth, user, wl_config.lgpd_masking_default)
        with tab2:
            render_tab_multi_split(hub, auth, user)
        with tab3:
            render_tab_wallets(engine, auth, user)
        with tab4:
            render_tab_payouts(engine, hub, auth, user)
        with tab5:
            render_tab_payment_links(hub, auth, user)
        with tab6:
            render_tab_api_playground(engine, hub, auth, user)
        with tab7:
            render_tab_excel_and_statements(engine, auth, user, wl_config.lgpd_masking_default)
        with tab8:
            render_tab_agents(engine, monitor, hub, auth, user)
        with tab9:
            render_tab_audit(engine, hub, auth, user, wl_config.lgpd_masking_default)


if __name__ == "__main__":
    render_pagamentos()
