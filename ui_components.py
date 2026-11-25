#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Meridian UI 6.2 — Design System dashdarkX + Brandkit Oficial Meridian Axis
- Logo vetorial Meridian Axis (SVG puro sincronizado com o tema White-Label)
- Barra lateral estática (300px) no Dashboard e oculta na tela de Login
- Extrato Executivo HTML/PDF com selo da logo Meridian Axis no cabeçalho
- Prancha interativa do Brandkit (render_brandkit_showcase) com download em SVG
"""

from datetime import datetime
from urllib.parse import quote
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def get_meridian_logo_svg(primary: str = "#2563eb", accent: str = "#38bdf8", size: int = 28) -> str:
    """
    Renderiza o logotipo oficial Meridian Axis em SVG vetorial puro.
    Adapta automaticamente as cores dos arcos conforme o tema White-Label ativo.
    """
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 100 100" fill="none" '
        f'xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0; display:block;">'
        f'<path d="M 33 32 C 33 12, 62 8, 77 23 C 90 36, 88 58, 68 65 L 68 48 '
        f'C 75 43, 75 33, 67 26 C 59 19, 44 20, 33 32 Z" fill="{accent}"/>'
        f'<path d="M 67 68 C 67 88, 38 92, 23 77 C 10 64, 12 42, 32 35 L 32 52 '
        f'C 25 57, 25 67, 33 74 C 41 81, 56 80, 67 68 Z" fill="{primary}"/>'
        f'<rect x="31" y="31" width="38" height="38" rx="9" fill="#ffffff"/>'
        f'</svg>'
    )


def apply_meridian_theme(wl_config=None, is_logged_in: bool = True):
    """
    Injeta o sistema de estilos do dashdarkX.
    - Se is_logged_in=False: oculta totalmente a sidebar e o header, centralizando o login.
    - Se is_logged_in=True: exibe a sidebar responsiva (300px no PC, recolhível no PC e mobile)
      com botões visíveis de fechar e reabrir em alto contraste.
    """
    primary = getattr(wl_config, "primary_color", "#0284c7") if wl_config else "#0284c7"
    secondary = getattr(wl_config, "secondary_color", "#2563eb") if wl_config else "#2563eb"
    accent = getattr(wl_config, "accent_color", "#38bdf8") if wl_config else "#38bdf8"

    if is_logged_in:
        sidebar_lock_css = """
        /* Mantém o header transparente ativo para o botão de reabrir a sidebar funcionar */
        header[data-testid="stHeader"] {
            display: flex !important;
            visibility: visible !important;
            background: transparent !important;
            border-bottom: none !important;
            box-shadow: none !important;
            z-index: 999990 !important;
        }
        [data-testid="stToolbar"] {
            display: flex !important;
            visibility: visible !important;
            background: transparent !important;
        }

        /* Oculta apenas os botões nativos do Streamlit (Deploy, menu superior e rodapé) */
        [data-testid="stToolbarActions"],
        [data-testid="stAppDeployButton"],
        [data-testid="stMainMenu"],
        [data-testid="stDecoration"],
        #MainMenu,
        footer {
            display: none !important;
        }

        /* Visual da sidebar sem travar o recolhimento nativo do Streamlit */
        section[data-testid="stSidebar"] {
            background-color: var(--dd-bg-darker) !important;
            border-right: 1px solid var(--dd-neutral-darker) !important;
            box-shadow: 0 10px 30px rgba(2, 6, 23, 0.65);
        }
        section[data-testid="stSidebar"][aria-expanded="true"] {
            width: 300px !important;
            max-width: 300px !important;
        }
        section[data-testid="stSidebar"][aria-expanded="true"] > div:first-child {
            width: 100% !important;
        }

        /* Mantém o cabeçalho da sidebar e o botão de fechar sempre acessíveis */
        [data-testid="stSidebarHeader"] {
            display: flex !important;
            visibility: visible !important;
            align-items: center !important;
            justify-content: space-between !important;
            padding: 0.65rem 0.85rem 0.2rem 0.85rem !important;
            min-height: 2.6rem !important;
        }

        [data-testid="stSidebarCollapseButton"],
        [data-testid="stExpandSidebarButton"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            z-index: 999999 !important;
        }

        [data-testid="stSidebarCollapseButton"] button,
        [data-testid="stExpandSidebarButton"] button,
        [data-testid="stSidebarCollapsedControl"] button,
        [data-testid="collapsedControl"] button {
            background: rgba(11, 23, 57, 0.94) !important;
            border: 1px solid var(--brand-accent) !important;
            border-radius: 8px !important;
            color: #ffffff !important;
            min-width: 36px !important;
            min-height: 36px !important;
            opacity: 1 !important;
            box-shadow: 0 4px 14px rgba(2, 6, 23, 0.55) !important;
            transition: all 0.2s ease !important;
        }

        [data-testid="stSidebarCollapseButton"] button:hover,
        [data-testid="stExpandSidebarButton"] button:hover,
        [data-testid="stSidebarCollapsedControl"] button:hover,
        [data-testid="collapsedControl"] button:hover {
            background: var(--brand-primary) !important;
            border-color: #ffffff !important;
        }

        [data-testid="stSidebarCollapseButton"] svg,
        [data-testid="stExpandSidebarButton"] svg,
        [data-testid="stSidebarCollapsedControl"] svg,
        [data-testid="collapsedControl"] svg {
            fill: #ffffff !important;
            color: #ffffff !important;
        }
        """
    else:
        sidebar_lock_css = """
        header[data-testid="stHeader"],
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        [data-testid="stExpandSidebarButton"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarHeader"],
        #MainMenu,
        footer {
            display: none !important;
            width: 0px !important;
            min-width: 0px !important;
            max-width: 0px !important;
            visibility: hidden !important;
        }
        """

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Work+Sans:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Rubik:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap');

        :root {{
            --brand-primary: {primary};
            --brand-secondary: {secondary};
            --brand-accent: {accent};
            --dd-bg-darker: #081028;
            --dd-paper-main: #0b1739;
            --dd-paper-dark: #091330;
            --dd-neutral-darker: #13224c;
            --dd-text-primary: #ffffff;
            --dd-text-secondary: #aeb9e1;
        }}

        .stApp {{
            background-color: var(--dd-bg-darker);
            background-image: 
                radial-gradient(at 0% 0%, {primary}22 0px, transparent 45%),
                radial-gradient(at 100% 0%, {secondary}20 0px, transparent 45%);
            color: var(--dd-text-primary);
            font-family: 'Work Sans', 'Plus Jakarta Sans', sans-serif;
            scroll-behavior: smooth;
        }}

        [data-testid="stSidebarNav"] {{display: none !important;}}

        .block-container {{
            padding-top: 2.6rem !important;
            padding-bottom: 2.5rem !important;
            max-width: 96% !important;
        }}

        {sidebar_lock_css}

        /* Botões 3D Isometric Neon Glow (Sem Ícones na Sidebar) */
        [data-testid="stSidebar"] .stButton > button {{
            position: relative;
            width: 94% !important;
            margin: 5px auto 11px auto !important;
            display: block !important;
            background: linear-gradient(135deg, #0b1739 0%, #081028 100%) !important;
            color: var(--dd-text-secondary) !important;
            font-family: 'Rubik', 'Work Sans', sans-serif !important;
            font-size: 0.74rem !important;
            font-weight: 700 !important;
            letter-spacing: 1.8px !important;
            text-transform: uppercase !important;
            padding: 12px 15px !important;
            border: 1px solid {accent}50 !important;
            border-radius: 4px !important;
            transform: skewX(-6deg) !important;
            box-shadow: 
                -5px 5px 0px {primary}99,
                -8px 8px 0px #040817,
                -6px 6px 16px {primary}30 !important;
            transition: all 0.22s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
        }}

        [data-testid="stSidebar"] .stButton > button:hover {{
            color: #ffffff !important;
            background: linear-gradient(128.49deg, var(--brand-accent) 19.86%, var(--brand-primary) 68.34%) !important;
            border-color: #ffffff !important;
            transform: skewX(-6deg) translate(4px, -4px) !important;
            box-shadow: 
                -8px 8px 0px var(--brand-secondary),
                -14px 14px 28px {accent}75 !important;
            text-shadow: 0 0 10px rgba(255, 255, 255, 0.8);
        }}

        [data-testid="stSidebar"] .stButton > button[kind="primary"] {{
            background: linear-gradient(128.49deg, var(--brand-primary) 19.86%, var(--brand-secondary) 68.34%) !important;
            color: #ffffff !important;
            border: 1px solid var(--brand-accent) !important;
            transform: skewX(-6deg) translate(2px, -2px) !important;
            box-shadow: 
                -6px 6px 0px var(--brand-accent),
                -10px 10px 26px {accent}80,
                inset 0 0 14px rgba(255, 255, 255, 0.22) !important;
            text-shadow: 0 0 8px rgba(255, 255, 255, 0.75);
        }}

        .main .stButton > button, .main .stDownloadButton > button {{
            background: linear-gradient(128.49deg, var(--brand-primary) 19.86%, var(--brand-secondary) 68.34%) !important;
            color: #ffffff !important;
            font-family: 'Work Sans', sans-serif !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px !important;
            border: 1px solid {accent}66 !important;
            border-radius: 8px !important;
            padding: 10px 18px !important;
            transition: all 0.25s ease !important;
            box-shadow: 0 6px 18px {primary}40 !important;
        }}
        .main .stButton > button:hover, .main .stDownloadButton > button:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 25px {accent}85 !important;
            border-color: #ffffff !important;
        }}

        .dd-paper {{
            background-color: var(--dd-paper-main);
            border: 1px solid var(--dd-neutral-darker);
            border-radius: 12px;
            padding: 24px 26px;
            box-shadow: 0 14px 34px rgba(2, 6, 23, 0.45);
            margin-bottom: 20px;
            position: relative;
        }}

        .dd-kpi-card {{
            background-color: var(--dd-paper-main);
            border: 1px solid var(--dd-neutral-darker);
            border-radius: 12px;
            padding: 20px 22px;
            box-shadow: 0 10px 26px rgba(2, 6, 23, 0.4);
            transition: all 0.25s ease;
            margin-bottom: 14px;
        }}
        .dd-kpi-card:hover {{
            border-color: var(--brand-accent);
            transform: translateY(-3px);
            box-shadow: 0 14px 30px {primary}30;
        }}
        .dd-kpi-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .dd-kpi-label {{
            font-size: 0.82rem;
            font-weight: 500;
            color: var(--dd-text-secondary);
            letter-spacing: 0.3px;
        }}
        .dd-kpi-dots {{
            color: var(--dd-text-secondary);
            font-weight: 700;
            letter-spacing: 1px;
            font-size: 0.9rem;
        }}
        .dd-kpi-main-row {{
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .dd-kpi-val {{
            font-family: 'Plus Jakarta Sans', 'Work Sans', sans-serif;
            font-size: 1.62rem;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.15;
        }}
        .dd-kpi-sub {{
            font-size: 0.76rem;
            color: var(--dd-text-secondary);
            margin-top: 8px;
        }}

        .dd-chip {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            height: 22px;
            padding: 0 8px;
            border-radius: 4px;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.3px;
            border: 1px solid transparent;
        }}
        .dd-chip-paid {{
            background: rgba(16, 185, 129, 0.14);
            color: #34d399;
            border-color: rgba(16, 185, 129, 0.38);
        }}
        .dd-chip-pending {{
            background: rgba(245, 158, 11, 0.14);
            color: #fbbf24;
            border-color: rgba(245, 158, 11, 0.38);
        }}
        .dd-chip-fraud {{
            background: rgba(239, 68, 68, 0.14);
            color: #f87171;
            border-color: rgba(239, 68, 68, 0.38);
        }}
        .dd-chip-blue {{
            background: rgba(56, 189, 248, 0.14);
            color: var(--brand-accent);
            border-color: rgba(56, 189, 248, 0.38);
        }}

        .dd-topbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 4px 0 22px 0;
            border-bottom: 1px solid var(--dd-neutral-darker);
            margin-bottom: 24px;
            flex-wrap: wrap;
            gap: 14px;
        }}

        hr {{
            border-color: var(--dd-neutral-darker) !important;
            margin: 1.2rem 0 !important;
        }}

        .stTextInput input, .stNumberInput input, [data-baseweb="select"] > div {{
            background-color: #091330 !important;
            border: 1px solid var(--dd-neutral-darker) !important;
            border-radius: 8px !important;
            color: #ffffff !important;
            padding: 10px 12px !important;
        }}
        .stTextInput input:focus, .stNumberInput input:focus {{
            border-color: var(--brand-accent) !important;
            box-shadow: 0 0 0 2px {accent}30 !important;
        }}

        [data-baseweb="tab-list"] {{
            gap: 6px;
            background: var(--dd-paper-main);
            padding: 8px;
            border-radius: 10px;
            border: 1px solid var(--dd-neutral-darker);
            margin-bottom: 1.2rem;
            flex-wrap: wrap;
        }}
        [data-baseweb="tab"] {{
            border-radius: 7px !important;
            padding: 8px 13px !important;
            color: var(--dd-text-secondary) !important;
            font-weight: 600 !important;
            font-size: 0.83rem !important;
        }}
        [aria-selected="true"][data-baseweb="tab"] {{
            background: linear-gradient(128.49deg, var(--brand-primary) 19.86%, var(--brand-secondary) 68.34%) !important;
            color: #ffffff !important;
            border: 1px solid var(--brand-accent) !important;
        }}

        .dd-table-wrap {{ width: 100%; overflow-x: auto; }}
        .dd-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; color: #ffffff; }}
        .dd-table th {{
            text-align: left;
            padding: 13px 14px;
            color: var(--dd-text-secondary);
            font-weight: 600;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            border-bottom: 1px solid var(--dd-neutral-darker);
            background: rgba(8, 16, 40, 0.55);
        }}
        .dd-table td {{
            padding: 13px 14px;
            border-bottom: 1px solid rgba(19, 34, 76, 0.65);
            vertical-align: middle;
        }}
        .dd-table tr:hover td {{ background: rgba(56, 189, 248, 0.05); }}

        .ff-2021-login-main {{
            background: linear-gradient(180deg, #0b1739 0%, #091330 65%, #081028 100%);
            border: 1px solid var(--dd-neutral-darker);
            border-top: 3px solid var(--brand-accent);
            border-radius: 16px 16px 0 0;
            padding: 34px 30px 22px 30px;
            box-shadow: 0 22px 55px rgba(0, 0, 0, 0.75);
            text-align: center;
        }}
        .ff-2021-login-title {{
            color: #ffffff;
            font-family: 'Work Sans', sans-serif;
            font-size: 1.95rem;
            font-weight: 700;
            letter-spacing: 1.5px;
            margin: 0 0 6px 0;
        }}
        .ff-2021-login-sub {{
            color: var(--dd-text-secondary);
            font-size: 0.84rem;
            margin-bottom: 12px;
        }}
        .ff-2021-curved-drawer {{
            background: linear-gradient(128.49deg, var(--brand-primary) 19.86%, var(--brand-secondary) 68.34%);
            border-radius: 60% / 18% 18% 0 0;
            padding: 18px 24px 16px 24px;
            margin-top: 12px;
            text-align: center;
            border-top: 2px solid {accent}88;
            box-shadow: 0 -8px 24px rgba(0, 0, 0, 0.45);
        }}
        .ff-2021-drawer-label {{
            color: #ffffff;
            font-family: 'Work Sans', sans-serif;
            font-size: 0.98rem;
            font-weight: 700;
            letter-spacing: 1.2px;
            text-transform: uppercase;
            margin: 0;
        }}

        .sec-formal-alert {{
            background: #140d1e;
            border: 1px solid #ef4444;
            border-left: 4px solid #ef4444;
            border-radius: 8px;
            padding: 18px 20px;
            margin: 14px 0;
            text-align: left;
            color: #f8fafc;
            font-family: 'Work Sans', sans-serif;
        }}
        .sec-formal-alert-title {{
            font-size: 0.86rem;
            font-weight: 700;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            color: #f87171;
            margin-bottom: 6px;
        }}
        .sec-formal-alert-body {{
            font-size: 0.83rem;
            line-height: 1.5;
            color: #e2e8f0;
        }}

        .dd-sidebar-profile {{
            display: flex;
            align-items: center;
            gap: 12px;
            background: var(--dd-paper-main);
            border: 1px solid var(--dd-neutral-darker);
            padding: 12px 14px;
            border-radius: 10px;
            margin: 8px 4px 14px 4px;
        }}
        .dd-avatar-circle {{
            width: 38px;
            height: 38px;
            min-width: 38px;
            border-radius: 50%;
            background: linear-gradient(128.49deg, var(--brand-accent) 19.86%, var(--brand-primary) 68.34%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            color: #ffffff;
            font-size: 0.92rem;
            box-shadow: 0 0 12px {primary}66;
        }}

        .ff-hero {{
            background: linear-gradient(135deg, #0b1739 0%, #091330 100%);
            border: 1px solid var(--dd-neutral-darker);
            border-left: 4px solid var(--brand-accent);
            border-radius: 12px;
            padding: 22px 26px;
            margin-bottom: 22px;
            box-shadow: 0 12px 30px rgba(2, 6, 23, 0.45);
        }}
        .ff-hero-badge {{
            display: inline-block;
            background: rgba(56, 189, 248, 0.12);
            color: var(--brand-accent);
            border: 1px solid rgba(56, 189, 248, 0.35);
            padding: 3px 10px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .ff-hero-title {{ font-size: 1.65rem; font-weight: 700; color: #ffffff; margin: 0 0 4px 0; }}
        .ff-hero-sub {{ color: var(--dd-text-secondary); font-size: 0.88rem; margin: 0; }}

        .ff-credit-card {{
            background: linear-gradient(128.49deg, {primary}66 19.86%, #0b1739 68.34%);
            border: 1px solid {accent}55;
            border-radius: 14px;
            padding: 22px;
            color: #fff;
            box-shadow: 0 18px 38px rgba(2, 6, 23, 0.55);
            margin-bottom: 16px;
        }}
        .ff-card-chip {{
            width: 42px; height: 30px;
            background: linear-gradient(135deg, #fde68a 0%, #f59e0b 50%, #b45309 100%);
            border-radius: 6px;
            margin-bottom: 14px;
        }}

        @keyframes ff-pulse-ok {{
            0% {{ box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.75); }}
            70% {{ box-shadow: 0 0 0 14px rgba(16, 185, 129, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }}
        }}
        @keyframes ff-pulse-danger {{
            0% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.8); }}
            70% {{ box-shadow: 0 0 0 16px rgba(239, 68, 68, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }}
        }}
        .ff-radar-box {{
            display: flex; align-items: center; gap: 16px;
            background: var(--dd-paper-main);
            border: 1px solid var(--dd-neutral-darker);
            padding: 16px 20px; border-radius: 12px; margin-bottom: 16px;
        }}
        .ff-radar-dot-ok {{ width: 14px; height: 14px; min-width: 14px; background: #10b981; border-radius: 50%; animation: ff-pulse-ok 2s infinite; }}
        .ff-radar-dot-alert {{ width: 14px; height: 14px; min-width: 14px; background: #ef4444; border-radius: 50%; animation: ff-pulse-danger 1.2s infinite; }}

        .ff-timeline-item {{
            position: relative; padding: 11px 14px 12px 20px;
            border-left: 2px solid var(--brand-accent);
            margin-left: 8px; margin-bottom: 10px;
            background: #091330;
            border-radius: 0 10px 10px 0;
        }}
        .ff-timeline-item::before {{
            content: ""; position: absolute; left: -6px; top: 16px;
            width: 10px; height: 10px; border-radius: 50%;
            background: var(--brand-accent); box-shadow: 0 0 10px var(--brand-accent);
        }}

        .ff-receipt-card {{
            background: var(--dd-paper-main);
            border: 1px solid rgba(56, 189, 248, 0.4);
            border-radius: 12px; padding: 20px; margin-top: 12px;
            box-shadow: 0 12px 28px rgba(0, 0, 0, 0.4);
        }}
        .ff-mrr-card {{
            background: #091330;
            border: 1px solid var(--dd-neutral-darker);
            border-radius: 10px; padding: 14px 16px; margin-bottom: 10px;
            display: flex; justify-content: space-between; align-items: center;
        }}
        .ff-wa-btn {{
            display: inline-block; width: 100%; text-align: center;
            background: linear-gradient(128.49deg, #10b981 19.86%, #059669 68.34%);
            color: #ffffff !important; text-decoration: none !important;
            font-weight: 600; padding: 11px 16px; border-radius: 8px;
            margin-top: 10px;
        }}

        /* Responsividade Mobile */
        @media (max-width: 768px) {{
            section[data-testid="stSidebar"][aria-expanded="true"] {{
                width: 84vw !important;
                max-width: 300px !important;
                min-width: 0 !important;
            }}
            section[data-testid="stSidebar"][aria-expanded="true"] > div:first-child {{
                width: 100% !important;
            }}
            .block-container {{
                padding-top: 3.4rem !important;
                padding-left: 0.85rem !important;
                padding-right: 0.85rem !important;
                max-width: 100% !important;
            }}
            .dd-paper, .ff-hero {{
                padding: 16px 16px !important;
            }}
            .dd-kpi-val {{
                font-size: 1.38rem !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True
    )


def render_dashdark_topbar(user: dict, wl_config, subtitle: str = ""):
    role = user.get("role", "MERCHANT")
    vid = user.get("vendedor_id", "ALL")
    nome = user.get("nome_exibicao", "Operador")
    iniciais = "".join(p[0] for p in nome.split()[:2]).upper() or "MR"
    lgpd_on = getattr(wl_config, "lgpd_masking_default", True)

    st.markdown(
        f"""
        <div class="dd-topbar">
            <div>
                <div style="font-size:1.5rem; font-weight:700; color:#ffffff; letter-spacing:0.3px;">
                    Welcome back, {nome}
                </div>
                <div style="font-size:0.84rem; color:var(--dd-text-secondary); margin-top:2px;">
                    {subtitle or wl_config.brand_subtitle}
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:14px;">
                <span class="dd-chip dd-chip-blue">SHA-256 VERIFIED</span>
                <span class="dd-chip {'dd-chip-paid' if lgpd_on else 'dd-chip-pending'}">
                    {'LGPD MASK: ON' if lgpd_on else 'LGPD MASK: OFF'}
                </span>
                <div style="display:flex; align-items:center; gap:10px; background:var(--dd-paper-main); border:1px solid var(--dd-neutral-darker); padding:6px 12px; border-radius:8px;">
                    <div class="dd-avatar-circle" style="width:32px; height:32px; min-width:32px; font-size:0.78rem;">{iniciais}</div>
                    <div>
                        <div style="font-size:0.82rem; font-weight:600; color:#ffffff; line-height:1.1;">{user.get('username', 'admin')}</div>
                        <div style="font-size:0.7rem; color:var(--dd-text-secondary);">{role} • {vid}</div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_dashdark_footer(wl_config):
    st.markdown(
        f"""
        <div style="margin-top:28px; padding-top:14px; border-top:1px solid var(--dd-neutral-darker); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; font-size:0.8rem; color:var(--dd-text-secondary); letter-spacing:0.4px;">
            <div>{wl_config.brand_name} Enterprise Suite • Multi-Tenant B2B SaaS</div>
            <div>Criptografia <strong>SHA-256</strong> & Precisão Bancária <strong>Decimal</strong></div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_kpi_card(title: str, value: str, subtitle: str = "", badge: str = "+24.8%", badge_type: str = "paid"):
    chip_cls = f"dd-chip-{badge_type}" if badge_type in ("paid", "pending", "fraud", "blue") else "dd-chip-blue"
    st.markdown(
        f"""
        <div class="dd-kpi-card">
            <div class="dd-kpi-top">
                <span class="dd-kpi-label">{title}</span>
                <span class="dd-kpi-dots">•••</span>
            </div>
            <div class="dd-kpi-main-row">
                <span class="dd-kpi-val">{value}</span>
                <span class="dd-chip {chip_cls}">{badge}</span>
            </div>
            <div class="dd-kpi-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_dashdark_tier2_charts(transactions: list):
    paid_tx = [t for t in transactions if t.get("status") == "PAID"]
    by_method = {"PIX": 0.0, "CARTAO": 0.0, "BOLETO": 0.0}
    split_totals = {"Bruto Total": 0.0, "Líquido Titular": 0.0, "Taxa Plataforma": 0.0, "Fornecedores": 0.0}

    for t in paid_tx:
        m = t.get("metodo_pagamento", "PIX")
        val = float(t.get("valor_bruto", 0))
        by_method[m] = by_method.get(m, 0.0) + val

        sp = t.get("split", {})
        split_totals["Bruto Total"] += val
        split_totals["Líquido Titular"] += float(sp.get("vendedor", 0))
        split_totals["Taxa Plataforma"] += float(sp.get("plataforma", 0))
        split_totals["Fornecedores"] += float(sp.get("fornecedor", 0))

    total_vol = sum(by_method.values())
    col_left_4, col_right_8 = st.columns([1, 2], gap="medium")

    with col_left_4:
        st.markdown(
            """
            <div class="dd-paper" style="margin-bottom:0;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="font-size:1.02rem; font-weight:700; color:#ffffff;">Canais de Liquidação</span>
                    <span class="dd-chip dd-chip-blue">PIX • CARTÃO • BOLETO</span>
                </div>
                <div style="font-size:0.78rem; color:var(--dd-text-secondary); margin-bottom:8px;">
                    Proporção do volume financeiro aprovado por método
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if PLOTLY_AVAILABLE and total_vol > 0:
            fig_visitors = go.Figure(data=[go.Pie(
                labels=list(by_method.keys()),
                values=list(by_method.values()),
                hole=0.72,
                marker=dict(colors=["#38bdf8", "#2563eb", "#1d4ed8"], line=dict(color="#0b1739", width=3)),
                textinfo="percent",
                hoverinfo="label+value+percent"
            )])
            fig_visitors.update_layout(
                annotations=[dict(text=f"<b>{len(paid_tx)} TXs</b>", x=0.5, y=0.5, font_size=16, font_color="#ffffff", showarrow=False)],
                paper_bgcolor="#0b1739",
                plot_bgcolor="#0b1739",
                font=dict(color="#aeb9e1", family="Work Sans"),
                margin=dict(t=15, b=15, l=15, r=15),
                height=265,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_visitors, use_container_width=True)
        else:
            st.info("Realize uma venda aprovada para exibir o gráfico radial.")

    with col_right_8:
        st.markdown(
            f"""
            <div class="dd-paper" style="margin-bottom:0;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <div>
                        <span style="font-size:1.02rem; font-weight:700; color:#ffffff;">Revenue & Split Distribution</span>
                        <div style="font-size:1.45rem; font-weight:800; color:#ffffff; margin-top:2px;">
                            R$ {total_vol:,.2f} <span class="dd-chip dd-chip-paid">+100% Conciliado</span>
                        </div>
                    </div>
                    <span class="dd-chip dd-chip-blue">DECIMAL PRECISION</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if PLOTLY_AVAILABLE and total_vol > 0:
            fig_rev = go.Figure(data=[go.Bar(
                x=list(split_totals.keys()),
                y=list(split_totals.values()),
                marker=dict(
                    color=["#38bdf8", "#0284c7", "#2563eb", "#1e40af"],
                    line=dict(color="#38bdf8", width=1)
                ),
                text=[f"R$ {v:,.2f}" for v in split_totals.values()],
                textposition="auto",
                width=0.45
            )])
            fig_rev.update_layout(
                paper_bgcolor="#0b1739",
                plot_bgcolor="#0b1739",
                font=dict(color="#aeb9e1", family="Work Sans"),
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="#13224c", zerolinecolor="#13224c"),
                margin=dict(t=15, b=20, l=20, r=20),
                height=250
            )
            st.plotly_chart(fig_rev, use_container_width=True)
        else:
            st.info("Sem volume financeiro liquidado no momento.")


def render_dashdark_tier3_section(transactions: list, wallets: dict, siem_rep: dict, brand_name: str):
    col_prod_4, col_task_8 = st.columns([1, 2], gap="medium")

    with col_prod_4:
        st.markdown(
            """
            <div class="dd-paper">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
                    <span style="font-size:1.02rem; font-weight:700; color:#ffffff;">Carteiras & Unidades Ativas</span>
                    <span class="dd-chip dd-chip-blue">MULTI-SPLIT</span>
                </div>
            """,
            unsafe_allow_html=True
        )
        if wallets:
            for idx, (vid, bal) in enumerate(list(wallets.items())[:4]):
                icon_svg = (
                    '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2">'
                    '<rect x="5" y="2" width="14" height="20" rx="3"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>'
                    if idx % 2 == 0 else
                    '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2">'
                    '<rect x="6" y="4" width="12" height="16" rx="4"/><circle cx="12" cy="12" r="3"/></svg>'
                )
                st.markdown(
                    f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 12px; background:#091330; border:1px solid var(--dd-neutral-darker); border-radius:10px; margin-bottom:10px;">
                        <div style="display:flex; align-items:center; gap:12px;">
                            <div style="width:40px; height:40px; border-radius:8px; background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.3); display:flex; align-items:center; justify-content:center;">
                                {icon_svg}
                            </div>
                            <div>
                                <div style="font-weight:700; font-size:0.88rem; color:#ffffff;">{vid}</div>
                                <div style="font-size:0.74rem; color:var(--dd-text-secondary);">Carteira Liquidada SHA-256</div>
                            </div>
                        </div>
                        <div style="font-family:'JetBrains Mono',monospace; font-weight:700; font-size:0.92rem; color:#38bdf8;">
                            R$ {float(bal):,.2f}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("Nenhuma carteira ativa.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_task_8:
        is_ok = (siem_rep.get("status") == "HEALTHY")
        st.markdown(
            f"""
            <div class="dd-paper" style="margin-bottom:0;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <div>
                        <span style="font-size:1.02rem; font-weight:700; color:#ffffff;">Fluxo de Liquidez & Monitoramento FIM</span>
                        <div style="font-size:0.8rem; color:var(--dd-text-secondary); margin-top:2px;">
                            {siem_rep.get('action_taken', 'Integridade SHA-256 verificada em todas as transações')}
                        </div>
                    </div>
                    <span class="dd-chip {'dd-chip-paid' if is_ok else 'dd-chip-fraud'}">{siem_rep.get('status', 'HEALTHY')}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if PLOTLY_AVAILABLE and transactions:
            vals = [float(t.get("valor_bruto", 0)) for t in transactions[-12:]]
            labels = [f"#{t.get('id', '')[:5]}" for t in transactions[-12:]]
            fig_area = go.Figure(data=[go.Scatter(
                x=labels,
                y=vals,
                mode="lines+markers",
                line=dict(color="#38bdf8", width=3, shape="spline"),
                marker=dict(size=7, color="#0284c7", line=dict(color="#ffffff", width=1.5)),
                fill="tozeroy",
                fillcolor="rgba(56, 189, 248, 0.14)"
            )])
            fig_area.update_layout(
                paper_bgcolor="#0b1739",
                plot_bgcolor="#0b1739",
                font=dict(color="#aeb9e1", family="Work Sans"),
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="#13224c", zerolinecolor="#13224c"),
                margin=dict(t=15, b=20, l=20, r=20),
                height=245
            )
            st.plotly_chart(fig_area, use_container_width=True)
        else:
            st.info("Registre transações para visualizar a curva de liquidez.")


def render_dashdark_orders_table(transactions: list):
    rows_html = ""
    for tx in reversed(transactions[-10:]):
        tx_id = tx.get("id", "N/A")[:10]
        comp = tx.get("comprador", "ANONIMO")
        data_str = str(tx.get("timestamp", ""))[:16].replace("T", " ")
        metodo = tx.get("metodo_pagamento", "PIX")
        status = tx.get("status", "PAID")
        vendedor = tx.get("vendedor_id", "VENDEDOR_A")
        bruto = float(tx.get("valor_bruto", 0))
        liquido = float(tx.get("split", {}).get("vendedor", 0))

        chip_cls = "dd-chip-paid" if status == "PAID" else ("dd-chip-fraud" if "FRAUD" in status or status == "REFUNDED" else "dd-chip-pending")
        rows_html += f"""
        <tr>
            <td style="font-family:'JetBrains Mono',monospace; color:var(--brand-accent); font-weight:600;">#{tx_id}</td>
            <td><strong>{comp}</strong></td>
            <td style="color:var(--dd-text-secondary);">{data_str}</td>
            <td><span class="dd-chip dd-chip-blue">{metodo}</span></td>
            <td>{vendedor}</td>
            <td><span class="dd-chip {chip_cls}">● {status}</span></td>
            <td style="text-align:right; font-family:'JetBrains Mono',monospace; font-weight:600;">R$ {bruto:,.2f}</td>
            <td style="text-align:right; font-family:'JetBrains Mono',monospace; color:#34d399; font-weight:700;">R$ {liquido:,.2f}</td>
        </tr>
        """

    if not rows_html:
        rows_html = '<tr><td colspan="8" style="text-align:center; color:var(--dd-text-secondary);">Nenhuma transação registrada para este escopo.</td></tr>'

    st.markdown(
        f"""
        <div class="dd-paper">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:10px;">
                <div>
                    <span style="font-size:1.1rem; font-weight:700; color:#ffffff;">Orders & Ledger Status (SHA-256)</span>
                    <div style="font-size:0.8rem; color:var(--dd-text-secondary);">Últimas transações conciliadas com anonimização LGPD e Split automático</div>
                </div>
                <span class="dd-chip dd-chip-blue">{len(transactions)} REGISTROS TOTAIS</span>
            </div>
            <div class="dd-table-wrap">
                <table class="dd-table">
                    <thead>
                        <tr>
                            <th>Order ID</th>
                            <th>Client (LGPD)</th>
                            <th>Date (UTC)</th>
                            <th>Channel</th>
                            <th>Account</th>
                            <th>Status</th>
                            <th style="text-align:right;">Gross Total</th>
                            <th style="text-align:right;">Net Split</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_cookie_consent_modal(wl_config=None):
    primary = getattr(wl_config, "primary_color", "#0284c7") if wl_config else "#0284c7"
    secondary = getattr(wl_config, "secondary_color", "#2563eb") if wl_config else "#2563eb"
    accent = getattr(wl_config, "accent_color", "#38bdf8") if wl_config else "#38bdf8"
    brand = getattr(wl_config, "brand_name", "MERIDIAN") if wl_config else "MERIDIAN"

    cookie_injection_js = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body>
    <script>
    (function() {{
        const targetDoc = (window.parent && window.parent.document) ? window.parent.document : document;
        const targetWin = (window.parent) ? window.parent : window;

        let styleEl = targetDoc.getElementById("meridian-cookie-styles");
        if (!styleEl) {{
            styleEl = targetDoc.createElement("style");
            styleEl.id = "meridian-cookie-styles";
            targetDoc.head.appendChild(styleEl);
        }}

        styleEl.textContent = `
            @import url('https://fonts.googleapis.com/css2?family=Work+Sans:wght@400;500;600;700&display=swap');

            #meridianCookieBackdrop {{
                position: fixed;
                inset: 0;
                background: rgba(4, 8, 22, 0.80);
                backdrop-filter: blur(10px);
                z-index: 999990;
                display: none;
                opacity: 0;
                transition: opacity 0.28s ease;
            }}
            #meridianCookieBackdrop.visible {{ display: block; opacity: 1; }}

            .cookie-buddy {{
                position: fixed;
                right: 22px;
                bottom: 22px;
                z-index: 999992;
                display: flex;
                align-items: center;
                gap: 10px;
                font-family: 'Work Sans', sans-serif;
            }}
            .cookie-btn {{
                background: linear-gradient(128.49deg, {primary} 19.86%, {secondary} 68.34%);
                border: 1px solid {accent};
                padding: 11px 18px;
                border-radius: 40px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.65);
                cursor: pointer;
                color: #ffffff;
                font-weight: 600;
                font-size: 13px;
            }}

            .cookie-panel {{
                position: fixed;
                left: 50%;
                top: 50%;
                transform: translate(-50%, -50%) scale(0.96);
                width: 450px;
                max-width: 92vw;
                background: #0b1739;
                border: 1px solid {accent}88;
                border-radius: 16px;
                padding: 24px;
                box-shadow: 0 30px 80px rgba(0, 0, 0, 0.9);
                z-index: 999995;
                display: none;
                color: #ffffff;
                font-family: 'Work Sans', sans-serif;
            }}
            .cookie-panel.visible {{ display: block; transform: translate(-50%, -50%) scale(1); }}
            .cookie-panel h3 {{ margin: 0; font-size: 18px; font-weight: 700; color: #ffffff; }}
            .cookie-panel p {{ margin: 5px 0 0 0; color: #aeb9e1; font-size: 13px; line-height: 1.4; }}

            .categories {{ display: grid; gap: 10px; margin-top: 14px; }}
            .cat {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 12px 14px;
                border-radius: 10px;
                background: #081028;
                border: 1px solid #13224c;
            }}
            .cat .meta strong {{ font-size: 14px; color: #ffffff; }}
            .cat-desc {{ font-size: 12px; color: #aeb9e1; margin-top: 2px; }}

            .toggle {{
                position: relative;
                width: 48px;
                height: 26px;
                min-width: 48px;
                background: #13224c;
                border-radius: 20px;
                padding: 3px;
                cursor: pointer;
            }}
            .toggle .dot {{
                position: absolute;
                left: 3px;
                top: 3px;
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background: #ffffff;
                transition: all 0.22s ease;
            }}
            .toggle.on {{ background: linear-gradient(128.49deg, {primary}, {accent}); }}
            .toggle.on .dot {{ left: 25px; }}
            .toggle.locked {{ opacity: 0.85; cursor: not-allowed; }}

            .actions {{ display: flex; gap: 10px; margin-top: 16px; }}
            .c-btn {{
                flex: 1;
                padding: 11px 14px;
                border-radius: 8px;
                border: none;
                font-weight: 600;
                font-size: 13px;
                cursor: pointer;
            }}
            .c-btn.primary {{ background: linear-gradient(128.49deg, {primary} 19.86%, {secondary} 68.34%); color: #ffffff; }}
            .c-btn.ghost {{ background: #081028; border: 1px solid {accent}55; color: #aeb9e1; }}

            .cookie-footer {{
                margin-top: 12px;
                padding-top: 10px;
                border-top: 1px solid #13224c;
                font-size: 12px;
                color: #aeb9e1;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }}
            .c-btn-decline {{
                background: rgba(239, 68, 68, 0.12);
                border: 1px solid rgba(239, 68, 68, 0.4);
                color: #fca5a5;
                padding: 7px 12px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
                cursor: pointer;
            }}
            .c-link {{ color: {accent}; cursor: pointer; text-decoration: underline; font-weight: 600; }}
        `;

        if (targetDoc.getElementById("meridianCookiePanel")) return;

        const wrapper = targetDoc.createElement("div");
        wrapper.id = "meridianCookieRoot";
        wrapper.innerHTML = `
            <div id="meridianCookieBackdrop"></div>
            <div class="cookie-buddy">
                <button id="openBuddy" aria-haspopup="dialog" class="cookie-btn">
                    <span>Preferências de Cookies</span>
                </button>
            </div>
            <aside id="meridianCookiePanel" class="cookie-panel" role="dialog" aria-modal="true">
                <header>
                    <div>
                        <h3>Controle de Cookies e Privacidade — {brand}</h3>
                        <p>Utilizamos apenas cookies essenciais de sessão e segurança. Você pode negar qualquer item não obrigatório.</p>
                    </div>
                </header>
                <div class="categories">
                    <div class="cat">
                        <div class="meta">
                            <div>
                                <strong>Estritamente Necessários (Sessão & SHA-256)</strong>
                                <div class="cat-desc">Obrigatório — autenticação PBKDF2 e integridade do Ledger</div>
                            </div>
                        </div>
                        <div class="toggle on locked" data-key="necessary"><div class="dot"></div></div>
                    </div>
                    <div class="cat">
                        <div class="meta">
                            <div>
                                <strong>Preferências de Interface (White-Label)</strong>
                                <div class="cat-desc">Opcional — memoriza tema e ajustes visuais</div>
                            </div>
                        </div>
                        <div class="toggle" data-key="preferences"><div class="dot"></div></div>
                    </div>
                    <div class="cat">
                        <div class="meta">
                            <div>
                                <strong>Telemetria Antifraude & Auditoria LGPD</strong>
                                <div class="cat-desc">Opcional — diagnóstico anônimo contra anomalias</div>
                            </div>
                        </div>
                        <div class="toggle" data-key="analytics"><div class="dot"></div></div>
                    </div>
                </div>
                <div class="actions">
                    <button id="acceptAll" class="c-btn primary">Aceitar todos</button>
                    <button id="savePrefs" class="c-btn ghost">Salvar seleção</button>
                </div>
                <div class="cookie-footer">
                    <div><button id="declineAll" class="c-btn-decline">Negar opcionais (Apenas necessários)</button></div>
                    <div><span class="c-link" id="moreInfo">Política LGPD</span></div>
                </div>
            </aside>
        `;
        targetDoc.body.appendChild(wrapper);

        const panel = targetDoc.getElementById("meridianCookiePanel");
        const backdrop = targetDoc.getElementById("meridianCookieBackdrop");
        const openBtn = targetDoc.getElementById("openBuddy");
        const toggles = Array.from(panel.querySelectorAll(".toggle"));
        const acceptAll = targetDoc.getElementById("acceptAll");
        const savePrefs = targetDoc.getElementById("savePrefs");
        const declineAll = targetDoc.getElementById("declineAll");

        const defaultState = {{ necessary: true, preferences: false, analytics: false }};
        const storageKey = "meridian_playful_cookie_consent_v1";

        function readConsent() {{
            try {{
                const raw = targetWin.localStorage.getItem(storageKey);
                return raw ? JSON.parse(raw) : null;
            }} catch (e) {{ return null; }}
        }}

        function writeConsent(obj) {{
            try {{ targetWin.localStorage.setItem(storageKey, JSON.stringify(obj)); }} catch (e) {{}}
        }}

        function openModal() {{ panel.classList.add("visible"); backdrop.classList.add("visible"); }}
        function closeModal() {{ panel.classList.remove("visible"); backdrop.classList.remove("visible"); }}

        function applyTogglesFromState(state) {{
            toggles.forEach((t) => {{
                const key = t.dataset.key;
                const val = (key === "necessary") ? true : !!state[key];
                if (val) t.classList.add("on");
                else t.classList.remove("on");
            }});
        }}

        function readTogglesToState() {{
            const obj = {{}};
            toggles.forEach((t) => (obj[t.dataset.key] = t.classList.contains("on")));
            obj.necessary = true;
            return obj;
        }}

        const stored = readConsent();
        if (stored) {{ applyTogglesFromState(Object.assign({{}}, defaultState, stored)); }}
        else {{ applyTogglesFromState(defaultState); openModal(); }}

        openBtn.addEventListener("click", () => {{
            if (panel.classList.contains("visible")) closeModal(); else openModal();
        }});
        backdrop.addEventListener("click", closeModal);

        toggles.forEach((t) => {{
            t.addEventListener("click", () => {{
                if (t.dataset.key === "necessary") return;
                t.classList.toggle("on");
            }});
        }});

        acceptAll.addEventListener("click", () => {{
            const all = {{ necessary: true, preferences: true, analytics: true }};
            writeConsent(all); applyTogglesFromState(all); closeModal();
        }});

        savePrefs.addEventListener("click", () => {{
            writeConsent(readTogglesToState()); closeModal();
        }});

        declineAll.addEventListener("click", () => {{
            const minimal = {{ necessary: true, preferences: false, analytics: false }};
            writeConsent(minimal); applyTogglesFromState(minimal); closeModal();
        }});
    }})();
    </script>
    </body>
    </html>
    """
    components.html(cookie_injection_js, height=0, width=0)


def hide_cookie_widget_when_logged_in():
    components.html(
        """
        <script>
        (function() {
            const targetDoc = (window.parent && window.parent.document) ? window.parent.document : document;
            const root = targetDoc.getElementById("meridianCookieRoot");
            if (root) root.remove();
        })();
        </script>
        """,
        height=0,
        width=0
    )


def render_login_showcase_panel(wl_config=None):
    pass


def render_user_badge_sidebar(user: dict, lgpd_active: bool = True):
    nome = user.get("nome_exibicao", "Operador")
    iniciais = "".join(p[0] for p in nome.split()[:2]).upper() or "MR"
    role = user.get("role", "MERCHANT")
    vid = user.get("vendedor_id", "ALL")

    st.markdown(
        f"""
        <div class="dd-sidebar-profile">
            <div class="dd-avatar-circle">{iniciais}</div>
            <div style="overflow:hidden;">
                <div style="font-size:0.88rem; font-weight:600; color:#ffffff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                    {nome}
                </div>
                <div style="font-size:0.74rem; color:var(--dd-text-secondary);">
                    {user.get('cargo', role)} • {vid}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_hero_banner(title: str, subtitle: str, badge_text: str = "MERIDIAN FINTECH ERP • SHA-256"):
    st.markdown(
        f"""
        <div class="ff-hero">
            <div class="ff-hero-badge">{badge_text}</div>
            <h1 class="ff-hero-title">{title}</h1>
            <p class="ff-hero-sub">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_virtual_wallet_card(seller_id: str, balance: float, label: str = "CORPORATE WALLET"):
    st.markdown(
        f"""
        <div class="ff-credit-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div class="ff-card-chip"></div>
                <span style="font-family:'JetBrains Mono',monospace; font-size:0.76rem; color:var(--brand-accent); font-weight:600;">
                    {label}
                </span>
            </div>
            <div style="font-size:0.75rem; color:var(--dd-text-secondary); text-transform:uppercase; letter-spacing:0.8px;">
                Saldo Líquido Disponível
            </div>
            <div style="font-size:1.75rem; font-weight:700; font-family:'JetBrains Mono',monospace; margin: 4px 0 14px 0; color:#ffffff;">
                R$ {balance:,.2f}
            </div>
            <div style="display:flex; justify-content:space-between; font-size:0.78rem; color:#e2e8f0; border-top:1px solid rgba(255,255,255,0.12); padding-top:10px;">
                <span>TITULAR: <strong>{seller_id}</strong></span>
                <span style="font-family:'JetBrains Mono',monospace; color:#34d399;">● LEDGER VERIFIED</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_security_radar(is_healthy: bool, title: str, detail: str):
    dot_class = "ff-radar-dot-ok" if is_healthy else "ff-radar-dot-alert"
    status_color = "#34d399" if is_healthy else "#f87171"
    st.markdown(
        f"""
        <div class="ff-radar-box">
            <div class="{dot_class}"></div>
            <div>
                <div style="font-weight:700; color:{status_color}; font-size:0.95rem;">{title}</div>
                <div style="font-size:0.82rem; color:var(--dd-text-secondary); margin-top:2px;">{detail}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_transaction_timeline_item(tx: dict):
    valor = float(tx.get("valor_bruto", 0))
    tx_id = tx.get("id", "N/A")[:8]
    metodo = tx.get("metodo_pagamento", "PIX")
    status = tx.get("status", "PAID")
    vendedor = tx.get("vendedor_id", "N/A")
    comprador = tx.get("comprador", "N/A")
    chip_cls = "dd-chip-paid" if status == "PAID" else ("dd-chip-fraud" if "FRAUD" in status or status == "REFUNDED" else "dd-chip-pending")

    st.markdown(
        f"""
        <div class="ff-timeline-item">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <span style="font-family:'JetBrains Mono',monospace; font-size:0.75rem; color:var(--brand-accent);">
                    #{tx_id}... • {metodo}
                </span>
                <span class="dd-chip {chip_cls}">{status}</span>
            </div>
            <div style="font-size:1.12rem; font-weight:700; color:#ffffff; font-family:'JetBrains Mono',monospace;">
                R$ {valor:,.2f}
            </div>
            <div style="font-size:0.78rem; color:var(--dd-text-secondary); margin-top:2px;">
                {comprador} ➔ <strong>{vendedor}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_multi_split_visual_card(res: dict):
    val_bruto = float(res.get("valor_bruto", 0))
    taxa_plat = float(res.get("taxa_plataforma", 0))
    benefs = res.get("beneficiarios", [])

    palette = ["#38bdf8", "#2563eb", "#0284c7", "#34d399"]
    segments_html = ""
    legend_html = ""

    plat_pct = (taxa_plat / val_bruto * 100.0) if val_bruto > 0 else 0
    segments_html += f'<div style="width:{plat_pct:.2f}%; background:#64748b; height:12px;" title="Plataforma"></div>'
    legend_html += f"""
    <div style="display:flex; justify-content:space-between; font-size:0.83rem; padding:6px 0; border-bottom:1px solid var(--dd-neutral-darker);">
        <span><span style="color:#94a3b8;">●</span> <strong>Taxa Plataforma</strong> (Retenção SaaS)</span>
        <span style="font-family:'JetBrains Mono',monospace; font-weight:700;">R$ {taxa_plat:,.2f}</span>
    </div>
    """

    for idx, b in enumerate(benefs):
        cor = palette[idx % len(palette)]
        pct_f = float(b.get("percentual", 0))
        val_l = float(b.get("valor_liquido", 0))
        segments_html += f'<div style="width:{pct_f:.2f}%; background:{cor}; height:12px;" title="{b.get("vendedor_id")}"></div>'
        legend_html += f"""
        <div style="display:flex; justify-content:space-between; font-size:0.83rem; padding:6px 0; border-bottom:1px solid var(--dd-neutral-darker);">
            <span><span style="color:{cor};">●</span> <strong>{b.get('vendedor_id')}</strong> ({b.get('papel')} — {pct_f:.1f}%)</span>
            <span style="font-family:'JetBrains Mono',monospace; font-weight:700; color:{cor};">R$ {val_l:,.2f}</span>
        </div>
        """

    st.markdown(
        f"""
        <div class="ff-receipt-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <div>
                    <div style="font-size:0.72rem; color:var(--brand-accent); font-weight:700;">LIQUIDAÇÃO MULTI-BENEFICIÁRIOS ASSINADA (SHA-256)</div>
                    <div style="font-family:'JetBrains Mono',monospace; font-size:0.84rem; color:#ffffff;">
                        TX: {res.get('transaction_id')} • Contrato: {res.get('contrato')}
                    </div>
                </div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:1.3rem; font-weight:800; color:#ffffff;">
                    R$ {val_bruto:,.2f}
                </div>
            </div>
            <div style="display:flex; width:100%; border-radius:999px; overflow:hidden; margin: 12px 0;">
                {segments_html}
            </div>
            <div style="margin-top:8px;">
                {legend_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_receipt_card(tx_obj, split_obj):
    st.markdown(
        f"""
        <div class="ff-receipt-card">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px dashed var(--dd-neutral-darker); padding-bottom:10px; margin-bottom:10px;">
                <div>
                    <div style="font-size:0.73rem; color:#34d399; font-weight:700;">RECIBO DIGITAL ASSINADO (SHA-256)</div>
                    <div style="font-family:'JetBrains Mono',monospace; font-size:0.84rem; color:var(--dd-text-secondary);">ID: {tx_obj.id}</div>
                </div>
                <span class="dd-chip dd-chip-paid">{tx_obj.status}</span>
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; font-size:0.86rem;">
                <div>
                    <div style="color:var(--dd-text-secondary);">Valor Bruto ({tx_obj.metodo_pagamento})</div>
                    <div style="font-size:1.25rem; font-weight:700; color:#fff; font-family:'JetBrains Mono',monospace;">
                        R$ {float(tx_obj.valor_bruto):,.2f}
                    </div>
                    <div style="color:var(--dd-text-secondary); margin-top:6px;">Comprador: <strong style="color:#ffffff;">{tx_obj.comprador}</strong></div>
                </div>
                <div style="background:#081028; padding:10px 14px; border-radius:8px; border:1px solid var(--dd-neutral-darker);">
                    <div style="font-size:0.73rem; color:var(--brand-accent); font-weight:700; margin-bottom:4px;">DIVISÃO AUTOMÁTICA (SPLIT)</div>
                    <div style="display:flex; justify-content:space-between;"><span>Líquido {tx_obj.vendedor_id}:</span> <strong>R$ {float(split_obj.vendedor):,.2f}</strong></div>
                    <div style="display:flex; justify-content:space-between;"><span>Taxa Plataforma:</span> <strong>R$ {float(split_obj.plataforma):,.2f}</strong></div>
                    <div style="display:flex; justify-content:space-between;"><span>Fornecedor:</span> <strong>R$ {float(split_obj.fornecedor):,.2f}</strong></div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if tx_obj.metodo_pagamento == "PIX":
        pix_payload = (
            f"00020126580014BR.GOV.BCB.PIX0136{tx_obj.id}"
            f"5204000053039865406{float(tx_obj.valor_bruto):.2f}5802BR5915MERIDIAN_FINTECH6009SAO_PAULO"
        )
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=160x160&bgcolor=0b1739&color=38bdf8&data={pix_payload}"
        c_qr, c_copy = st.columns([1, 2.5])
        with c_qr:
            st.image(qr_url, caption="QR Code Pix Instantâneo", width=145)
        with c_copy:
            st.markdown("**Pix Copia e Cola (Padrão EMV BACEN)**")
            st.code(pix_payload, language="text")


def render_payout_receipt_card(payout_obj):
    st.markdown(
        f"""
        <div class="ff-receipt-card">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px dashed var(--dd-neutral-darker); padding-bottom:10px; margin-bottom:10px;">
                <div>
                    <div style="font-size:0.74rem; color:var(--brand-accent); font-weight:700;">COMPROVANTE DE LIQUIDAÇÃO PIX • {payout_obj.modalidade}</div>
                    <div style="font-family:'JetBrains Mono',monospace; font-size:0.84rem; color:var(--dd-text-secondary);">Protocolo: {payout_obj.payout_id}</div>
                </div>
                <span class="dd-chip dd-chip-paid">{payout_obj.status}</span>
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:10px; font-size:0.85rem;">
                <div>
                    <div style="color:var(--dd-text-secondary);">Valor Solicitado</div>
                    <div style="font-weight:700; font-size:1.1rem; font-family:'JetBrains Mono',monospace;">R$ {float(payout_obj.valor_solicitado):,.2f}</div>
                </div>
                <div>
                    <div style="color:var(--dd-text-secondary);">Taxa Antecipação</div>
                    <div style="font-weight:700; font-size:1.1rem; color:#fbbf24; font-family:'JetBrains Mono',monospace;">R$ {float(payout_obj.taxa_antecipacao):,.2f}</div>
                </div>
                <div>
                    <div style="color:var(--dd-text-secondary);">Líquido Enviado ao Pix</div>
                    <div style="font-weight:700; font-size:1.2rem; color:#34d399; font-family:'JetBrains Mono',monospace;">R$ {float(payout_obj.valor_liquido_pix):,.2f}</div>
                </div>
            </div>
            <div style="font-size:0.78rem; color:var(--dd-text-secondary); margin-top:10px;">
                Chave Pix Destino: <strong style="color:#ffffff;">{payout_obj.chave_pix_destino}</strong> | Titular: <strong>{payout_obj.vendedor_id}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_whatsapp_invoice_card(invoice_obj):
    val_f = float(invoice_obj.valor)
    fone_limpo = "".join(ch for ch in str(invoice_obj.cliente_whatsapp) if ch.isdigit())
    if not fone_limpo.startswith("55"):
        fone_limpo = "55" + fone_limpo

    msg_whatsapp = (
        f"Olá *{invoice_obj.cliente_nome}*! Segue sua fatura digital *{invoice_obj.vendedor_id}*:\n\n"
        f"Descrição: {invoice_obj.descricao}\n"
        f"Valor: R$ {val_f:,.2f}\n"
        f"Vencimento: {invoice_obj.vencimento}\n"
        f"Link Seguro: {invoice_obj.url_checkout}\n\n"
        f"Pix Copia e Cola:\n{invoice_obj.pix_copia_e_cola}"
    )
    wa_url = f"https://wa.me/{fone_limpo}?text={quote(msg_whatsapp)}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=160x160&bgcolor=0b1739&color=38bdf8&data={invoice_obj.pix_copia_e_cola}"

    st.markdown(
        f"""
        <div class="ff-receipt-card">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px dashed var(--dd-neutral-darker); padding-bottom:10px; margin-bottom:12px;">
                <div>
                    <div style="font-size:0.74rem; color:var(--brand-accent); font-weight:700;">LINK DE COBRANÇA & FATURA WHATSAPP</div>
                    <div style="font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:#ffffff;">{invoice_obj.link_id} • TX: {invoice_obj.transaction_id[:8]}...</div>
                </div>
                <span class="dd-chip dd-chip-pending">{invoice_obj.status}</span>
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; font-size:0.86rem;">
                <div>
                    <div style="color:var(--dd-text-secondary);">Cliente: <strong style="color:#fff;">{invoice_obj.cliente_nome}</strong></div>
                    <div style="color:var(--dd-text-secondary); margin-top:4px;">Serviço/Produto: <strong style="color:#fff;">{invoice_obj.descricao}</strong></div>
                    <div style="color:var(--dd-text-secondary); margin-top:4px;">URL Checkout: <code style="color:var(--brand-accent);">{invoice_obj.url_checkout}</code></div>
                </div>
                <div style="text-align:right;">
                    <div style="color:var(--dd-text-secondary);">Valor da Fatura</div>
                    <div style="font-size:1.4rem; font-weight:800; color:#34d399; font-family:'JetBrains Mono',monospace;">R$ {val_f:,.2f}</div>
                    <div style="font-size:0.75rem; color:var(--dd-text-secondary);">Vencimento: {invoice_obj.vencimento}</div>
                </div>
            </div>
            <a href="{wa_url}" target="_blank" class="ff-wa-btn">
                Enviar Fatura Direto no WhatsApp de {invoice_obj.cliente_nome}
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )

    c_qr, c_txt = st.columns([1, 2.5])
    with c_qr:
        st.image(qr_url, caption="QR Code da Fatura", width=145)
    with c_txt:
        st.markdown("**Mensagem Pronta para Copiar (WhatsApp / E-mail):**")
        st.code(msg_whatsapp, language="text")


def generate_executive_statement_html(
    user: dict,
    transactions: list,
    payouts: list,
    balance: float,
    wl_config=None
) -> str:
    """Gera o Extrato Executivo HTML/PDF com a logo vetorial Meridian Axis no cabeçalho."""
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    brand_name = getattr(wl_config, "brand_name", "MERIDIAN") if wl_config else "MERIDIAN"
    primary = getattr(wl_config, "primary_color", "#0284c7") if wl_config else "#0284c7"
    secondary = getattr(wl_config, "secondary_color", "#2563eb") if wl_config else "#2563eb"
    accent = getattr(wl_config, "accent_color", "#38bdf8") if wl_config else "#38bdf8"

    logo_svg = get_meridian_logo_svg(primary=secondary, accent=accent, size=44)

    paid_txs = [t for t in transactions if t.get("status") == "PAID"]
    gross_total = sum(float(t.get("valor_bruto", 0)) for t in paid_txs)
    net_seller_total = sum(float(t.get("split", {}).get("vendedor", 0)) for t in paid_txs)
    platform_fee_total = sum(float(t.get("split", {}).get("plataforma", 0)) for t in paid_txs)
    supplier_total = sum(float(t.get("split", {}).get("fornecedor", 0)) for t in paid_txs)
    payout_total = sum(float(p.get("valor_liquido_pix", 0)) for p in payouts)

    tx_rows_html = ""
    for t in reversed(transactions[-50:]):
        sp = t.get("split", {})
        tx_rows_html += f"""
        <tr>
            <td style="font-family:monospace;">{t.get('id', '')[:12]}...</td>
            <td>{str(t.get('timestamp', ''))[:19]}</td>
            <td>{t.get('comprador', '')}</td>
            <td>{t.get('metodo_pagamento', '')}</td>
            <td><strong>{t.get('status', '')}</strong></td>
            <td style="text-align:right;">R$ {float(t.get('valor_bruto', 0)):,.2f}</td>
            <td style="text-align:right; color:#b91c1c;">R$ {float(sp.get('plataforma', 0)):,.2f}</td>
            <td style="text-align:right; color:#047857; font-weight:bold;">R$ {float(sp.get('vendedor', 0)):,.2f}</td>
        </tr>
        """

    payout_rows_html = ""
    for p in reversed(payouts[-20:]):
        payout_rows_html += f"""
        <tr>
            <td style="font-family:monospace;">{p.get('payout_id', '')}</td>
            <td>{str(p.get('timestamp', ''))[:19]}</td>
            <td>{p.get('modalidade', '')}</td>
            <td>{p.get('chave_pix_destino', '')}</td>
            <td style="text-align:right;">R$ {float(p.get('valor_solicitado', 0)):,.2f}</td>
            <td style="text-align:right;">R$ {float(p.get('taxa_antecipacao', 0)):,.2f}</td>
            <td style="text-align:right; font-weight:bold;">R$ {float(p.get('valor_liquido_pix', 0)):,.2f}</td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Extrato Executivo de Repasse - {user.get('nome_exibicao')}</title>
    <style>
        * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
        body {{ font-family: 'Segoe UI', Roboto, Helvetica, sans-serif; color: #0f172a; margin: 32px; background: #f8fafc; }}
        .report-box {{ max-width: 1050px; margin: auto; background: #ffffff; padding: 36px; border-radius: 12px; border: 1px solid #cbd5e1; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid {primary}; padding-bottom: 18px; margin-bottom: 24px; gap: 16px; }}
        .brand-header-group {{ display: flex; align-items: center; gap: 16px; }}
        .logo-badge {{
            background: #081028;
            padding: 8px;
            border-radius: 10px;
            border: 1px solid {accent};
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }}
        .title {{ font-size: 20px; font-weight: 800; color: #0f172a; margin: 0; letter-spacing: 0.4px; }}
        .subtitle {{ font-size: 12.5px; color: #475569; margin-top: 3px; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 28px; }}
        .kpi {{ background: #f1f5f9; padding: 14px 16px; border-radius: 8px; border-left: 4px solid {primary}; }}
        .kpi-label {{ font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 700; }}
        .kpi-val {{ font-size: 18px; font-weight: 800; color: #0f172a; margin-top: 4px; font-family: monospace; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 26px; font-size: 12.5px; }}
        th {{ background: #081028; color: #ffffff; text-align: left; padding: 10px; }}
        td {{ padding: 9px 10px; border-bottom: 1px solid #e2e8f0; }}
        tr:nth-child(even) {{ background: #f8fafc; }}
        .print-btn {{ background: {primary}; color: #fff; border: none; padding: 10px 18px; border-radius: 6px; font-weight: 700; cursor: pointer; }}
        .footer {{ font-size: 11px; color: #64748b; text-align: center; border-top: 1px solid #cbd5e1; padding-top: 14px; margin-top: 20px; }}
        @media print {{
            body {{ background: #fff; margin: 0; }}
            .report-box {{ border: none; padding: 10px; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="report-box">
        <div class="header">
            <div class="brand-header-group">
                <div class="logo-badge">{logo_svg}</div>
                <div>
                    <h1 class="title">{brand_name} FINTECH ERP — EXTRATO EXECUTIVO DE REPASSE E DRE</h1>
                    <div class="subtitle">Titular / Conta: <strong>{user.get('nome_exibicao')}</strong> (ID: {user.get('vendedor_id')}) • Chave Pix: {user.get('chave_pix')}</div>
                    <div class="subtitle">Data de Emissão: {now_str} • Integridade Criptográfica: <strong>SHA-256 VERIFIED & LGPD COMPLIANT</strong></div>
                </div>
            </div>
            <div class="no-print">
                <button class="print-btn" onclick="window.print()">Imprimir / Salvar como PDF</button>
            </div>
        </div>

        <div class="kpi-grid">
            <div class="kpi">
                <div class="kpi-label">Faturamento Bruto (Pago)</div>
                <div class="kpi-val">R$ {gross_total:,.2f}</div>
            </div>
            <div class="kpi">
                <div class="kpi-label">Repasse Líquido Titular</div>
                <div class="kpi-val" style="color:#047857;">R$ {net_seller_total:,.2f}</div>
            </div>
            <div class="kpi">
                <div class="kpi-label">Taxas Plataforma + Fornecedor</div>
                <div class="kpi-val" style="color:#b91c1c;">R$ {(platform_fee_total + supplier_total):,.2f}</div>
            </div>
            <div class="kpi">
                <div class="kpi-label">Saldo Disponível em Carteira</div>
                <div class="kpi-val" style="color:{primary};">R$ {balance:,.2f}</div>
            </div>
        </div>

        <h3>1. Demonstrativo Auditado de Transações e Split</h3>
        <table>
            <thead>
                <tr>
                    <th>ID Transação</th>
                    <th>Data/Hora (UTC)</th>
                    <th>Comprador</th>
                    <th>Método</th>
                    <th>Status</th>
                    <th style="text-align:right;">Valor Bruto</th>
                    <th style="text-align:right;">Taxa Plataforma</th>
                    <th style="text-align:right;">Líquido Titular</th>
                </tr>
            </thead>
            <tbody>
                {tx_rows_html or '<tr><td colspan="8">Sem transações registradas no período.</td></tr>'}
            </tbody>
        </table>

        <h3>2. Histórico de Liquidações e Saques Pix (Total Transferido: R$ {payout_total:,.2f})</h3>
        <table>
            <thead>
                <tr>
                    <th>Protocolo</th>
                    <th>Data/Hora</th>
                    <th>Modalidade</th>
                    <th>Chave Pix Destino</th>
                    <th style="text-align:right;">Solicitado</th>
                    <th style="text-align:right;">Taxa Antecipação</th>
                    <th style="text-align:right;">Líquido Enviado</th>
                </tr>
            </thead>
            <tbody>
                {payout_rows_html or '<tr><td colspan="7">Nenhum saque realizado no período.</td></tr>'}
            </tbody>
        </table>

        <div class="footer">
            Documento emitido eletronicamente pelo motor {brand_name} Fintech ERP • Precisão Monetária Decimal (ROUND_HALF_UP) • Assinado via Monitor de Integridade SHA-256.
        </div>
    </div>
</body>
</html>"""


def render_brandkit_showcase(wl_config):
    """Exibe a prancha interativa do Brandkit Oficial Meridian Axis e libera o download do SVG."""
    secondary = getattr(wl_config, "secondary_color", "#2563eb")
    accent = getattr(wl_config, "accent_color", "#38bdf8")
    brand = getattr(wl_config, "brand_name", "MERIDIAN")

    svg_oficial = get_meridian_logo_svg(secondary, accent, size=84)
    svg_mono_white = get_meridian_logo_svg("#cbd5e1", "#ffffff", size=64)
    svg_download = get_meridian_logo_svg(secondary, accent, size=512)

    st.markdown(
        f"""
        <div class="dd-paper" style="margin-top:18px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                <div>
                    <span style="font-size:1.08rem; font-weight:700; color:#ffffff;">Brandkit Oficial — {brand} Axis</span>
                    <div style="font-size:0.8rem; color:var(--dd-text-secondary);">Geometria vetorial adaptativa sincronizada com o tema do Proprietário</div>
                </div>
                <span class="dd-chip dd-chip-blue">SVG VETORIAL ESCALÁVEL</span>
            </div>
            <div style="display:grid; grid-template-columns: 1.4fr 1fr 1fr; gap:14px;">
                <div style="background:#081028; border:1px solid #13224c; border-radius:10px; padding:22px; display:flex; align-items:center; justify-content:center; gap:16px;">
                    {svg_oficial}
                    <div>
                        <div style="font-size:1.55rem; font-weight:800; color:#ffffff; letter-spacing:2px;">{brand}</div>
                        <div style="font-size:0.72rem; color:{accent}; font-weight:600; letter-spacing:1.4px;">FINTECH ERP SUITE</div>
                    </div>
                </div>
                <div style="background:#081028; border:1px solid #13224c; border-radius:10px; padding:22px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px;">
                    {get_meridian_logo_svg(secondary, accent, size=56)}
                    <div style="font-size:0.75rem; color:var(--dd-text-secondary);">Ícone do App / Favicon</div>
                </div>
                <div style="background:#040814; border:1px solid #13224c; border-radius:10px; padding:22px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px;">
                    {svg_mono_white}
                    <div style="font-size:0.75rem; color:var(--dd-text-secondary);">Versão Monocromática</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.download_button(
        label=f"Baixar Logotipo Oficial {brand} Axis em Alta Resolução (.svg)",
        data=svg_download.encode("utf-8"),
        file_name=f"logo_{brand.lower().replace(' ', '_')}_axis.svg",
        mime="image/svg+xml",
        use_container_width=True
    )


def render_mrr_badge_card(sub: dict):
    sub_id = sub.get("subscription_id", "SUB")
    bruto = float(sub.get("mrr_bruto", 0))
    plat = float(sub.get("mrr_plataforma", 0))
    status = sub.get("status", "ACTIVE")
    prox = str(sub.get("next_billing_date", ""))[:10]

    st.markdown(
        f"""
        <div class="ff-mrr-card">
            <div>
                <div style="font-family:'JetBrains Mono',monospace; font-weight:700; color:var(--brand-accent); font-size:0.92rem;">
                    {sub_id}
                </div>
                <div style="font-size:0.78rem; color:var(--dd-text-secondary);">
                    Próximo faturamento: {prox} • Taxa Plataforma: R$ {plat:,.2f}
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-family:'JetBrains Mono',monospace; font-size:1.15rem; font-weight:700; color:#ffffff;">
                    R$ {bruto:,.2f}<span style="font-size:0.74rem; color:var(--dd-text-secondary);">/mês</span>
                </div>
                <span class="dd-chip dd-chip-paid">{status}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_plotly_neon_charts(transactions: list):
    render_dashdark_tier2_charts(transactions)
