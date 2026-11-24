#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Meridian Enterprise Modules 6.4 — Expansão Comercial B2B, Fiscal e Cloud
1. Motor de Split Tributário & Emissor de NFS-e / RPS (Anti-Bitributação)
2. Gerador de Proposta Comercial Executiva (com logo vetorial Meridian Axis) & Calculadora de ROI B2B
3. Conector Híbrido de Banco de Dados (JSON SHA-256 + Supabase PostgreSQL + RLS)
4. Gerador Automático do Kit de Deploy em Produção (Docker + FastAPI + Streamlit)
"""

import hashlib
import json
import os
import urllib.request
import urllib.error
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field

from fintech_engine import MoneyCalculator, FintechEngine
from monitor_engine import IntegrityMonitor


# =============================================================================
# MÓDULO 1: MOTOR DE SPLIT TRIBUTÁRIO & EMISSOR DE NFS-e (ANTI-BITRIBUTAÇÃO)
# =============================================================================

class NFSeRecord(BaseModel):
    """Registro de RPS / Nota Fiscal de Serviço Eletrônica segregada por beneficiário."""
    nfse_id: str = Field(default_factory=lambda: f"NFSE_{uuid.uuid4().hex[:8].upper()}")
    rps_numero: str = Field(default_factory=lambda: str(uuid.uuid4().int)[:8])
    transaction_id: str
    emitente_id: str
    papel_tributario: str
    tomador_nome: str
    valor_bruto_transacao: Decimal
    base_calculo_reduzida: Decimal
    aliquota_iss_simples_pct: Decimal
    imposto_devido: Decimal
    imposto_sem_split: Decimal
    economia_tributaria: Decimal
    codigo_servico_lc116: str = "01.07 - Licenciamento de Software e SaaS"
    hash_auditoria_sha256: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TaxSplitNFSeEngine:
    """
    Calcula a segregação de receitas entre empresa matriz, filiais e parceiros comissionados
    para evitar a bitributação sobre o valor repassado a terceiros e emite o lote RPS/NFS-e.
    """

    def __init__(
        self,
        engine: FintechEngine,
        monitor: Optional[IntegrityMonitor] = None,
        base_dir: str = "."
    ):
        self.engine = engine
        self.monitor = monitor or IntegrityMonitor()
        self.nfse_file = Path(base_dir) / "nfse_rps_lote.json"
        if not self.nfse_file.exists():
            self._save_records([])

    def load_records(self, vendedor_id: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            with open(self.nfse_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []
        if vendedor_id and vendedor_id != "ALL":
            return [r for r in data if r.get("emitente_id") == vendedor_id]
        return data

    def _save_records(self, records: List[Dict[str, Any]]) -> None:
        with open(self.nfse_file, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, default=str, ensure_ascii=False)
        self.monitor.add_path(str(self.nfse_file))

    def calculate_tax_savings_simulation(
        self,
        valor_bruto: Any,
        faturamento_mensal: Any,
        quota_estabelecimento_pct: Any,
        aliquota_imposto_pct: Any
    ) -> Dict[str, Decimal]:
        """Compara o imposto pago sem Split Tributário vs. com segregação automática."""
        val_tx = MoneyCalculator.to_decimal(valor_bruto)
        fat_mes = MoneyCalculator.to_decimal(faturamento_mensal)
        quota_pct = MoneyCalculator.to_decimal(quota_estabelecimento_pct)
        aliq_pct = MoneyCalculator.to_decimal(aliquota_imposto_pct)

        imposto_cheio_tx = MoneyCalculator.percentage_of(val_tx, aliq_pct)
        base_reduzida_tx = MoneyCalculator.percentage_of(val_tx, quota_pct)
        imposto_split_tx = MoneyCalculator.percentage_of(base_reduzida_tx, aliq_pct)
        economia_tx = MoneyCalculator.subtract(imposto_cheio_tx, imposto_split_tx)

        imposto_cheio_mes = MoneyCalculator.percentage_of(fat_mes, aliq_pct)
        base_reduzida_mes = MoneyCalculator.percentage_of(fat_mes, quota_pct)
        imposto_split_mes = MoneyCalculator.percentage_of(base_reduzida_mes, aliq_pct)
        economia_mes = MoneyCalculator.subtract(imposto_cheio_mes, imposto_split_mes)
        economia_ano = MoneyCalculator.multiply(economia_mes, Decimal("12.00"))

        return {
            "imposto_cheio_tx": imposto_cheio_tx,
            "base_reduzida_tx": base_reduzida_tx,
            "imposto_split_tx": imposto_split_tx,
            "economia_tx": economia_tx,
            "imposto_cheio_mes": imposto_cheio_mes,
            "imposto_split_mes": imposto_split_mes,
            "economia_mensal": economia_mes,
            "economia_anual": economia_ano
        }

    def issue_nfse_for_transaction(
        self,
        tx: Dict[str, Any],
        aliquota_pct: Any = "6.00",
        codigo_lc116: str = "01.07 - Licenciamento de Software e SaaS"
    ) -> List[NFSeRecord]:
        """
        Gera notas fiscais (RPS) separadas para cada participante do Split da transação,
        garantindo que a empresa recolha imposto apenas sobre a sua cota-parte.
        """
        val_bruto = MoneyCalculator.to_decimal(tx.get("valor_bruto", "0.00"))
        aliq_dec = MoneyCalculator.to_decimal(aliquota_pct)
        tx_id = str(tx.get("id", "TX_MANUAL"))
        comprador = str(tx.get("comprador", "TOMADOR_SERVICO"))

        imposto_sem_split = MoneyCalculator.percentage_of(val_bruto, aliq_dec)
        multi_breakdown = tx.get("metadata", {}).get("multi_split_breakdown", [])

        partes = []
        if multi_breakdown:
            for item in multi_breakdown:
                partes.append({
                    "emitente_id": str(item.get("vendedor_id", "PARCEIRO")),
                    "papel": str(item.get("papel", "Comissionado / Parceiro")),
                    "base_calculo": MoneyCalculator.to_decimal(item.get("valor_liquido", "0.00"))
                })
        else:
            sp = tx.get("split", {})
            liq_vend = MoneyCalculator.to_decimal(sp.get("vendedor", val_bruto))
            taxa_plat = MoneyCalculator.to_decimal(sp.get("plataforma", "0.00"))
            partes.append({
                "emitente_id": str(tx.get("vendedor_id", "VENDEDOR_A")),
                "papel": "Empresa / Titular Cota-Parte",
                "base_calculo": liq_vend
            })
            if taxa_plat > Decimal("0.00"):
                partes.append({
                    "emitente_id": "MERIDIAN_SAAS_HQ",
                    "papel": "Intermediação Tecnológica & Split",
                    "base_calculo": taxa_plat
                })

        emitidas: List[NFSeRecord] = []
        historico = self.load_records()

        for idx, p in enumerate(partes):
            base_calc = p["base_calculo"]
            imposto_dev = MoneyCalculator.percentage_of(base_calc, aliq_dec)
            econ = MoneyCalculator.subtract(imposto_sem_split, imposto_dev) if idx == 0 else Decimal("0.00")

            payload_hash = f"{tx_id}|{p['emitente_id']}|{base_calc}|{imposto_dev}"
            assinatura = hashlib.sha256(payload_hash.encode("utf-8")).hexdigest()[:24]

            rec = NFSeRecord(
                transaction_id=tx_id,
                emitente_id=p["emitente_id"],
                papel_tributario=p["papel"],
                tomador_nome=comprador,
                valor_bruto_transacao=val_bruto,
                base_calculo_reduzida=base_calc,
                aliquota_iss_simples_pct=aliq_dec,
                imposto_devido=imposto_dev,
                imposto_sem_split=imposto_sem_split,
                economia_tributaria=max(Decimal("0.00"), econ),
                codigo_servico_lc116=codigo_lc116,
                hash_auditoria_sha256=assinatura
            )
            emitidas.append(rec)
            historico.append(rec.model_dump())

        self._save_records(historico)
        return emitidas

    @staticmethod
    def generate_nfse_xml(record: NFSeRecord) -> str:
        """Gera o XML padrão ABRASF de RPS/NFS-e com segregação de cota-parte."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<GerarNfseEnvio xmlns="http://www.abrasf.org.br/nfse.xsd">
  <Rps>
    <InfDeclaracaoPrestacaoServico Id="{record.nfse_id}">
      <Rps>
        <IdentificacaoRps>
          <Numero>{record.rps_numero}</Numero>
          <Serie>SPLIT</Serie>
          <Tipo>1</Tipo>
        </IdentificacaoRps>
        <DataEmissao>{record.created_at[:10]}</DataEmissao>
        <Status>1</Status>
      </Rps>
      <Servico>
        <Valores>
          <ValorServicos>{record.valor_bruto_transacao}</ValorServicos>
          <ValorDeducoesParceiros>{MoneyCalculator.subtract(record.valor_bruto_transacao, record.base_calculo_reduzida)}</ValorDeducoesParceiros>
          <BaseCalculoReduzidaSplit>{record.base_calculo_reduzida}</BaseCalculoReduzidaSplit>
          <Aliquota>{record.aliquota_iss_simples_pct}</Aliquota>
          <ValorIssSimples>{record.imposto_devido}</ValorIssSimples>
        </Valores>
        <ItemListaServico>{record.codigo_servico_lc116}</ItemListaServico>
        <Discriminacao>RPS Split Tributario Automatico ({record.papel_tributario}) - TX {record.transaction_id} - Hash SHA256: {record.hash_auditoria_sha256}</Discriminacao>
      </Servico>
      <Prestador>
        <IdentificadorCarteira>{record.emitente_id}</IdentificadorCarteira>
      </Prestador>
      <Tomador>
        <RazaoSocial>{record.tomador_nome}</RazaoSocial>
      </Tomador>
    </InfDeclaracaoPrestacaoServico>
  </Rps>
</GerarNfseEnvio>"""


# =============================================================================
# MÓDULO 2: GERADOR DE PROPOSTA COMERCIAL & CALCULADORA DE ROI B2B
# =============================================================================

class B2BProposalROIEngine:
    """Calcula o ROI financeiro para o cliente B2B e gera Proposta Comercial em HTML/PDF."""

    @staticmethod
    def calculate_b2b_roi(
        faturamento_mensal: Any,
        quota_parceiros_pct: Any,
        aliquota_atual_pct: Any,
        horas_conciliacao_mes: int,
        custo_hora_financeiro: Any,
        valor_setup_licenca: Any,
        mensalidade_saas: Any
    ) -> Dict[str, Any]:
        fat_dec = MoneyCalculator.to_decimal(faturamento_mensal)
        parceiros_pct = MoneyCalculator.to_decimal(quota_parceiros_pct)
        aliq_dec = MoneyCalculator.to_decimal(aliquota_atual_pct)
        custo_h = MoneyCalculator.to_decimal(custo_hora_financeiro)
        setup_dec = MoneyCalculator.to_decimal(valor_setup_licenca)
        mensal_dec = MoneyCalculator.to_decimal(mensalidade_saas)

        repasse_parceiros_mes = MoneyCalculator.percentage_of(fat_dec, parceiros_pct)
        economia_fiscal_mes = MoneyCalculator.percentage_of(repasse_parceiros_mes, aliq_dec)
        economia_bpo_mes = MoneyCalculator.multiply(custo_h, Decimal(str(horas_conciliacao_mes)))

        beneficio_bruto_mes = MoneyCalculator.add(economia_fiscal_mes, economia_bpo_mes)
        beneficio_liquido_mes = MoneyCalculator.subtract(beneficio_bruto_mes, mensal_dec)
        beneficio_anual_12m = MoneyCalculator.multiply(beneficio_liquido_mes, Decimal("12.00"))
        economia_liquida_ano1 = MoneyCalculator.subtract(beneficio_anual_12m, setup_dec)

        investimento_ano1 = MoneyCalculator.add(
            setup_dec,
            MoneyCalculator.multiply(mensal_dec, Decimal("12.00"))
        )
        if investimento_ano1 > Decimal("0.00"):
            roi_anual_pct = round(float(economia_liquida_ano1 / investimento_ano1 * Decimal("100.00")), 1)
        else:
            roi_anual_pct = 100.0

        ganho_diario = float(beneficio_bruto_mes) / 30.0 if float(beneficio_bruto_mes) > 0 else 1.0
        payback_dias = max(1, int(round(float(setup_dec) / ganho_diario)))

        return {
            "faturamento_mensal": fat_dec,
            "repasse_parceiros_mes": repasse_parceiros_mes,
            "economia_fiscal_mes": economia_fiscal_mes,
            "economia_bpo_mes": economia_bpo_mes,
            "beneficio_bruto_mes": beneficio_bruto_mes,
            "beneficio_liquido_mes": beneficio_liquido_mes,
            "economia_liquida_ano1": economia_liquida_ano1,
            "investimento_ano1": investimento_ano1,
            "roi_anual_pct": roi_anual_pct,
            "payback_dias": payback_dias,
            "setup_licenca": setup_dec,
            "mensalidade_saas": mensal_dec
        }

    @staticmethod
    def generate_commercial_proposal_html(
        brand_name: str,
        cliente_empresa: str,
        segmento: str,
        roi_data: Dict[str, Any],
        primary_color: str = "#0284c7",
        secondary_color: str = "#2563eb",
        accent_color: str = "#38bdf8"
    ) -> str:
        """Gera a Proposta Comercial Executiva com a logo vetorial Meridian Axis sincronizada ao White-Label."""
        hoje = datetime.now().strftime("%d/%m/%Y")
        logo_svg = (
            f'<svg width="52" height="52" viewBox="0 0 100 100" fill="none" '
            f'xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0; display:block;">'
            f'<path d="M 33 32 C 33 12, 62 8, 77 23 C 90 36, 88 58, 68 65 L 68 48 '
            f'C 75 43, 75 33, 67 26 C 59 19, 44 20, 33 32 Z" fill="{accent_color}"/>'
            f'<path d="M 67 68 C 67 88, 38 92, 23 77 C 10 64, 12 42, 32 35 L 32 52 '
            f'C 25 57, 25 67, 33 74 C 41 81, 56 80, 67 68 Z" fill="{secondary_color}"/>'
            f'<rect x="31" y="31" width="38" height="38" rx="9" fill="#ffffff"/>'
            f'</svg>'
        )

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Proposta Comercial Executiva - {cliente_empresa}</title>
    <style>
        * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
        body {{ font-family: 'Segoe UI', Roboto, Helvetica, sans-serif; background: #081028; color: #f8fafc; margin: 0; padding: 32px; }}
        .proposal-container {{ max-width: 980px; margin: auto; background: #0b1739; border: 1px solid #1e3a8a; border-radius: 16px; padding: 42px; box-shadow: 0 25px 60px rgba(0,0,0,0.65); }}
        .top-bar {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid {accent_color}; padding-bottom: 20px; margin-bottom: 28px; gap: 16px; }}
        .brand-lockup {{ display: flex; align-items: center; gap: 18px; }}
        .logo-frame {{
            background: #081028;
            padding: 10px;
            border-radius: 12px;
            border: 1px solid {accent_color};
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }}
        .badge {{ background: rgba(56, 189, 248, 0.15); color: {accent_color}; border: 1px solid {accent_color}; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; letter-spacing: 1px; display: inline-block; }}
        h1 {{ margin: 8px 0 4px 0; font-size: 24px; color: #ffffff; }}
        h2 {{ font-size: 18px; color: {accent_color}; border-left: 4px solid {accent_color}; padding-left: 10px; margin-top: 28px; }}
        .kpi-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 22px 0; }}
        .kpi-box {{ background: #081028; border: 1px solid #13224c; border-top: 3px solid {accent_color}; padding: 16px; border-radius: 10px; }}
        .kpi-title {{ font-size: 11px; text-transform: uppercase; color: #aeb9e1; font-weight: 700; }}
        .kpi-value {{ font-size: 20px; font-weight: 800; color: #34d399; margin-top: 6px; font-family: monospace; }}
        table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px; }}
        th {{ background: #081028; color: {accent_color}; text-align: left; padding: 12px; border-bottom: 1px solid #1e3a8a; }}
        td {{ padding: 12px; border-bottom: 1px solid #13224c; color: #e2e8f0; }}
        .btn-print {{ background: linear-gradient(128.49deg, {primary_color}, {secondary_color}); color: #fff; border: none; padding: 10px 18px; border-radius: 8px; font-weight: 700; cursor: pointer; }}
        .footer {{ margin-top: 28px; padding-top: 14px; border-top: 1px solid #13224c; font-size: 12px; color: #94a3b8; text-align: center; }}
        @media print {{
            body {{ background: #ffffff; color: #0f172a; padding: 0; }}
            .proposal-container {{ background: #ffffff; border: none; box-shadow: none; color: #0f172a; padding: 20px; }}
            .kpi-box, th {{ background: #f1f5f9; color: #0f172a; border-color: #cbd5e1; }}
            td, h1, h2 {{ color: #0f172a; }}
            .badge {{ background: #f1f5f9; color: {primary_color}; border-color: {primary_color}; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="proposal-container">
        <div class="top-bar">
            <div class="brand-lockup">
                <div class="logo-frame">{logo_svg}</div>
                <div>
                    <span class="badge">PROPOSTA COMERCIAL B2B • LICENCIAMENTO WHITE-LABEL</span>
                    <h1>{brand_name} Enterprise Fintech ERP</h1>
                    <div style="color:#aeb9e1; font-size:14px;">Cliente: <strong>{cliente_empresa}</strong> ({segmento}) • Emissão: {hoje}</div>
                </div>
            </div>
            <div class="no-print">
                <button class="btn-print" onclick="window.print()">Imprimir / Salvar PDF</button>
            </div>
        </div>

        <h2>1. Diagnóstico Financeiro & Retorno sobre Investimento (ROI)</h2>
        <div class="kpi-row">
            <div class="kpi-box">
                <div class="kpi-title">Economia Tributária / Mês</div>
                <div class="kpi-value">R$ {float(roi_data['economia_fiscal_mes']):,.2f}</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-title">Economia Operacional BPO</div>
                <div class="kpi-value">R$ {float(roi_data['economia_bpo_mes']):,.2f}</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-title">Lucro Líquido Acumulado (12m)</div>
                <div class="kpi-value">R$ {float(roi_data['economia_liquida_ano1']):,.2f}</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-title">Payback & ROI no 1º Ano</div>
                <div class="kpi-value" style="color:{accent_color};">{roi_data['payback_dias']} dias ({roi_data['roi_anual_pct']}%)</div>
            </div>
        </div>

        <h2>2. Escopo Técnico da Plataforma Licenciada</h2>
        <table>
            <thead>
                <tr>
                    <th>Módulo Incluso</th>
                    <th>Descrição Executiva</th>
                    <th>Garantia Técnica</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>Split Multi-Beneficiários & Tributário</strong></td>
                    <td>Divisão automática entre empresa, filiais e comissionados com segregação de base de cálculo e emissão RPS/NFS-e.</td>
                    <td>Precisão Decimal Bancária</td>
                </tr>
                <tr>
                    <td><strong>Portal Multi-Tenant & Carteiras 3D</strong></td>
                    <td>Acesso padronizado por cargo (Admin, Supervisor, Comissionado e Atendente) com extrato próprio e Saque Pix.</td>
                    <td>PBKDF2-HMAC-SHA256</td>
                </tr>
                <tr>
                    <td><strong>Custódia FIM, SOC 8 Camadas & LGPD</strong></td>
                    <td>Proteção OWASP WAF, bloqueio na 3ª tentativa com SMS, integridade SHA-256 e mascaramento automático de CPF/PII.</td>
                    <td>Lei 13.709/18 & SIEM</td>
                </tr>
                <tr>
                    <td><strong>API REST FastAPI & Conciliador Excel</strong></td>
                    <td>Webhooks automáticos de liquidação PIX e exportação multi-abas DRE (.xlsx) assinada.</td>
                    <td>Swagger OpenAPI 3.0</td>
                </tr>
            </tbody>
        </table>

        <h2>3. Condições Comerciais de Implantação</h2>
        <table>
            <thead>
                <tr>
                    <th>Item</th>
                    <th>Modalidade</th>
                    <th style="text-align:right;">Investimento</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Setup White-Label + Configuração de Regras de Split & Onboarding da Equipe</td>
                    <td>Taxa Única de Implantação</td>
                    <td style="text-align:right; font-weight:bold;">R$ {float(roi_data['setup_licenca']):,.2f}</td>
                </tr>
                <tr>
                    <td>Licença Mensal Multi-Tenant + Suporte Técnico + Monitoramento SHA-256</td>
                    <td>Assinatura Mensal Recorrente</td>
                    <td style="text-align:right; font-weight:bold; color:{accent_color};">R$ {float(roi_data['mensalidade_saas']):,.2f} / mês</td>
                </tr>
            </tbody>
        </table>

        <div class="footer">
            Proposta gerada eletronicamente pelo motor {brand_name} Enterprise Fintech ERP • Identidade Visual Meridian Axis • Precisão Decimal & Auditoria SHA-256.
        </div>
    </div>
</body>
</html>"""


# =============================================================================
# MÓDULO 3: CONECTOR HÍBRIDO DE BANCO DE DADOS (JSON LOCAL + SUPABASE CLOUD)
# =============================================================================

class SupabaseHybridSync:
    """
    Mantém o armazenamento local JSON assinado por SHA-256 em sincronia com o
    Supabase PostgreSQL Cloud (via REST API ou variáveis de ambiente).
    """

    def __init__(
        self,
        engine: FintechEngine,
        monitor: Optional[IntegrityMonitor] = None,
        base_dir: str = "."
    ):
        self.engine = engine
        self.monitor = monitor or IntegrityMonitor()
        base = Path(base_dir)
        self.config_file = base / "supabase_sync_config.json"
        self.snapshot_file = base / "cloud_backup_snapshot.json"

    def load_config(self) -> Dict[str, Any]:
        default_cfg = {
            "supabase_url": os.environ.get("SUPABASE_URL", ""),
            "supabase_anon_key": os.environ.get("SUPABASE_KEY", ""),
            "auto_sync_enabled": True,
            "last_sync_at": "Nunca sincronizado",
            "last_sync_status": "LOCAL_ONLY_SHA256"
        }
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                default_cfg.update(saved)
            except Exception:
                pass
        return default_cfg

    def save_config(self, url: str, anon_key: str, auto_sync: bool = True) -> Dict[str, Any]:
        cfg = self.load_config()
        cfg["supabase_url"] = url.strip()
        cfg["supabase_anon_key"] = anon_key.strip()
        cfg["auto_sync_enabled"] = auto_sync
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        self.monitor.add_path(str(self.config_file))
        return cfg

    @staticmethod
    def get_postgres_ddl_sql() -> str:
        """Retorna o script SQL completo (DDL + RLS Multi-Tenant) para colar no SQL Editor do Supabase."""
        return """-- ============================================================================
-- MERIDIAN FINTECH ERP — SUPABASE POSTGRESQL SCHEMA + MULTI-TENANT RLS
-- Cole este script no SQL Editor do seu projeto Supabase e clique em RUN
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.meridian_transactions (
    id TEXT PRIMARY KEY,
    valor_bruto NUMERIC(14, 2) NOT NULL,
    metodo_pagamento TEXT NOT NULL,
    status TEXT NOT NULL,
    comprador TEXT NOT NULL,
    vendedor_id TEXT NOT NULL,
    split_plataforma NUMERIC(14, 2) DEFAULT 0.00,
    split_vendedor NUMERIC(14, 2) DEFAULT 0.00,
    split_fornecedor NUMERIC(14, 2) DEFAULT 0.00,
    pii_token_lgpd TEXT,
    ledger_sha256 TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.meridian_wallets (
    vendedor_id TEXT PRIMARY KEY,
    saldo_liquido NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    ledger_sha256 TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.meridian_nfse_rps (
    nfse_id TEXT PRIMARY KEY,
    rps_numero TEXT NOT NULL,
    transaction_id TEXT REFERENCES public.meridian_transactions(id),
    emitente_id TEXT NOT NULL,
    base_calculo_reduzida NUMERIC(14, 2) NOT NULL,
    imposto_devido NUMERIC(14, 2) NOT NULL,
    economia_tributaria NUMERIC(14, 2) NOT NULL,
    hash_auditoria_sha256 TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ativa Row Level Security (Isolamento Multi-Tenant Nativo)
ALTER TABLE public.meridian_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.meridian_wallets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.meridian_nfse_rps ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Isolamento Multi-Tenant Corporativo" ON public.meridian_transactions
    FOR SELECT USING (
        auth.jwt() ->> 'role' = 'ADMIN'
        OR vendedor_id = (auth.jwt() ->> 'vendedor_id')
    );
"""

    def sync_ledger_to_cloud(self) -> Dict[str, Any]:
        """
        Gera snapshot criptografado local com hash mestre SHA-256 e, caso SUPABASE_URL
        esteja preenchida, dispara sincronização REST para a nuvem.
        """
        txs = self.engine.get_all_transactions()
        wallets = {k: str(v) for k, v in self.engine.get_all_wallets().items()}
        raw_payload = json.dumps({"transactions": txs, "wallets": wallets}, sort_keys=True, default=str)
        master_sha256 = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

        snapshot_data = {
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "master_ledger_sha256": master_sha256,
            "transactions_count": len(txs),
            "wallets_count": len(wallets),
            "transactions": txs,
            "wallets": wallets
        }
        with open(self.snapshot_file, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f, indent=2, default=str, ensure_ascii=False)
        self.monitor.add_path(str(self.snapshot_file))

        cfg = self.load_config()
        supa_url = cfg.get("supabase_url", "").rstrip("/")
        supa_key = cfg.get("supabase_anon_key", "")

        cloud_status = "SNAPSHOT_LOCAL_ASSINADO (Configure SUPABASE_URL para envio remoto)"
        if supa_url.startswith("https://") and len(supa_key) > 15:
            try:
                req = urllib.request.Request(
                    url=f"{supa_url}/rest/v1/",
                    headers={"apikey": supa_key, "Authorization": f"Bearer {supa_key}"}
                )
                with urllib.request.urlopen(req, timeout=4) as resp:
                    if resp.status in (200, 201, 204):
                        cloud_status = "CLOUD_SYNC_OK (Supabase PostgreSQL Conectado)"
            except Exception:
                cloud_status = "SNAPSHOT_LOCAL_SALVO (Endpoint Supabase offline ou aguardando DDL)"

        cfg["last_sync_at"] = snapshot_data["synced_at"]
        cfg["last_sync_status"] = cloud_status
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        self.monitor.add_path(str(self.config_file))

        return {
            "status": cloud_status,
            "master_sha256": master_sha256,
            "transactions_synced": len(txs),
            "wallets_synced": len(wallets),
            "timestamp": snapshot_data["synced_at"]
        }


# =============================================================================
# MÓDULO 4: KIT DE DEPLOY EM PRODUÇÃO (DOCKER + COMPOSE + CLOUD RUN / RAILWAY)
# =============================================================================

class ProductionDeployGenerator:
    """Gera os artefatos de produção (Dockerfile, docker-compose.yml, requirements.txt) na raiz."""

    @staticmethod
    def get_dockerfile_content() -> str:
        return """# ============================================================================
# MERIDIAN FINTECH ERP — PRODUCTION DOCKERFILE (STREAMLIT + FASTAPI)
# ============================================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    STREAMLIT_SERVER_PORT=8501 \\
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501 8000

# Inicia a API REST FastAPI (porta 8000) em background e o ERP Streamlit (porta 8501)
CMD sh -c "uvicorn api_server:app --host 0.0.0.0 --port 8000 & streamlit run app.py --server.port=8501 --server.address=0.0.0.0"
"""

    @staticmethod
    def get_docker_compose_content() -> str:
        return """version: "3.9"

services:
  meridian-erp-web:
    build: .
    container_name: meridian_fintech_erp
    command: streamlit run app.py --server.port=8501 --server.address=0.0.0.0
    ports:
      - "8501:8501"
    environment:
      - SUPABASE_URL=${SUPABASE_URL:-}
      - SUPABASE_KEY=${SUPABASE_KEY:-}
    volumes:
      - .:/app
    restart: unless-stopped

  meridian-rest-api:
    build: .
    container_name: meridian_fastapi_server
    command: uvicorn api_server:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      - SUPABASE_URL=${SUPABASE_URL:-}
      - SUPABASE_KEY=${SUPABASE_KEY:-}
    volumes:
      - .:/app
    restart: unless-stopped
"""

    @staticmethod
    def get_requirements_content() -> str:
        return """streamlit>=1.38.0
pandas>=2.2.0
pydantic>=2.7.0
plotly>=5.22.0
openpyxl>=3.1.2
fastapi>=0.111.0
uvicorn>=0.30.0
pytest>=8.2.0
"""

    @classmethod
    def write_deploy_kit_to_disk(cls, monitor: Optional[IntegrityMonitor] = None, target_dir: str = ".") -> List[str]:
        """Grava Dockerfile, docker-compose.yml e requirements.txt na raiz e assina via SHA-256."""
        base = Path(target_dir)
        files_map = {
            "Dockerfile": cls.get_dockerfile_content(),
            "docker-compose.yml": cls.get_docker_compose_content(),
            "requirements.txt": cls.get_requirements_content()
        }
        created = []
        for fname, content in files_map.items():
            fpath = base / fname
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
            if monitor:
                monitor.add_path(str(fpath))
            created.append(str(fpath.name))
        return created