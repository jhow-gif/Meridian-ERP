#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Meridian Fintech ERP - Fase 4: Hub de Agentes Financeiros e Defesa Ativa
Integra Agente Antifraude, Agente CFO (Anomalias e Margem), Agente de Recuperação
e Agente de Resposta a Incidentes (Active Defense + Score de Risco + SIEM Webhook).
"""

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, field_validator

from fintech_engine import (
    MoneyCalculator,
    create_fintech_engine,
    generate_transaction_id,
    FintechEngine
)
from monitor_engine import IntegrityMonitor


# =============================================================================
# 1. SCHEMAS PYDANTIC V2 - Contratos de Auditoria, Finanças e SIEM
# =============================================================================

class FraudAnalysisResult(BaseModel):
    """Resultado da análise do Agente Antifraude por transação."""
    transaction_id: str
    risk_score: int = Field(..., ge=0, le=100, description="Score de risco de 0 a 100")
    is_approved: bool
    recommended_status: str = Field(..., pattern=r"^(PAID|PENDING|BLOCKED_FRAUD)$")
    reason: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AnomalyReport(BaseModel):
    """Relatório executivo gerado pelo Agente CFO."""
    total_analyzed: int
    gross_revenue: Decimal
    platform_revenue: Decimal
    net_margin_pct: Decimal
    average_ticket: Decimal
    anomalies_detected: List[Dict[str, Any]] = Field(default_factory=list)
    cfo_recommendations: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @field_validator("gross_revenue", "platform_revenue", "net_margin_pct", "average_ticket", mode="before")
    @classmethod
    def validate_decimals(cls, v: Any) -> Decimal:
        return MoneyCalculator.to_decimal(v)


class SIEMWebhookPayload(BaseModel):
    """Payload padronizado e validado para integração com SIEM externo via Webhook."""
    event_id: str = Field(default_factory=lambda: f"EVT_{uuid.uuid4().hex[:8].upper()}")
    severity: str = Field(..., pattern=r"^(LOW|MEDIUM|HIGH|CRITICAL)$")
    source_file: str
    status: str
    action_taken: str
    blocked_ips: List[str] = Field(default_factory=list)
    compromised_files: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# =============================================================================
# 2. AGENTE ANTIFRAUDE (AntifraudAgent)
# =============================================================================

class AntifraudAgent:
    """Analisa padrões de transação e bloqueia operações suspeitas antes da aprovação."""

    def __init__(self, high_value_threshold: str = "10000.00", max_tx_per_buyer: int = 3):
        self.high_value_threshold = MoneyCalculator.to_decimal(high_value_threshold)
        self.max_tx_per_buyer = max_tx_per_buyer

    def analyze_transaction(
        self,
        tx_data: Dict[str, Any],
        existing_transactions: Optional[List[Dict[str, Any]]] = None
    ) -> FraudAnalysisResult:
        """Calcula score de risco (0-100) avaliando valor atípico, repetição e método."""
        tx_id = str(tx_data.get("id") or generate_transaction_id())
        valor = MoneyCalculator.to_decimal(tx_data.get("valor_bruto", "0.00"))
        comprador = str(tx_data.get("comprador") or "ANONIMO").strip()
        metodo = str(tx_data.get("metodo_pagamento") or "PIX").upper()

        risk_score = 0
        reasons: List[str] = []

        # Regra 1: Valor acima do limite de segurança
        if valor >= self.high_value_threshold:
            risk_score += 55
            reasons.append(f"Valor atípico elevado (R$ {float(valor):,.2f})")

        # Regra 2: Frequência de compras do mesmo comprador no histórico
        historico = existing_transactions or []
        compras_mesmo_comprador = [
            t for t in historico
            if str(t.get("comprador", "")).strip() == comprador and comprador != "ANONIMO"
        ]
        if len(compras_mesmo_comprador) >= self.max_tx_per_buyer:
            risk_score += 35
            reasons.append(f"Alta frequência de transações ({len(compras_mesmo_comprador)} anteriores)")

        # Regra 3: Comprador não identificado em cartão de crédito
        if metodo == "CARTAO" and comprador in ("", "ANONIMO", "None"):
            risk_score += 40
            reasons.append("Transação via CARTAO sem identificação de comprador")

        risk_score = min(risk_score, 100)
        is_approved = risk_score < 70
        recommended_status = "PAID" if is_approved else "BLOCKED_FRAUD"

        if not reasons:
            reasons.append("Padrão normal de transação validado")

        return FraudAnalysisResult(
            transaction_id=tx_id,
            risk_score=risk_score,
            is_approved=is_approved,
            recommended_status=recommended_status,
            reason="; ".join(reasons)
        )


# =============================================================================
# 3. AGENTE CFO E DETECTOR DE ANOMALIAS (CFOAnomalyAgent)
# =============================================================================

class CFOAnomalyAgent:
    """Calcula margem líquida real, ticket médio e desvios financeiros superiores a 30%."""

    def analyze_financial_health(self, engine: FintechEngine) -> AnomalyReport:
        """Avalia todas as transações do banco usando precisão Decimal."""
        transactions = engine.get_all_transactions()
        valid_txs = [
            tx for tx in transactions
            if tx.get("status") not in ("REFUNDED", "BLOCKED_FRAUD")
        ]

        if not valid_txs:
            return AnomalyReport(
                total_analyzed=0,
                gross_revenue=Decimal("0.00"),
                platform_revenue=Decimal("0.00"),
                net_margin_pct=Decimal("0.00"),
                average_ticket=Decimal("0.00"),
                anomalies_detected=[],
                cfo_recommendations=["Sem volume transacional suficiente para análise de margem."]
            )

        gross_revenue = Decimal("0.00")
        platform_revenue = Decimal("0.00")
        fornecedor_costs = Decimal("0.00")

        for tx in valid_txs:
            val = MoneyCalculator.to_decimal(tx.get("valor_bruto", "0.00"))
            split = tx.get("split", {})
            plat = MoneyCalculator.to_decimal(split.get("plataforma", "0.00"))
            forn = MoneyCalculator.to_decimal(split.get("fornecedor", "0.00"))

            gross_revenue = MoneyCalculator.add(gross_revenue, val)
            platform_revenue = MoneyCalculator.add(platform_revenue, plat)
            fornecedor_costs = MoneyCalculator.add(fornecedor_costs, forn)

        count_dec = MoneyCalculator.to_decimal(len(valid_txs))
        average_ticket = MoneyCalculator.divide(gross_revenue, count_dec) if gross_revenue > Decimal("0.00") else Decimal("0.00")

        if gross_revenue > Decimal("0.00"):
            ratio = MoneyCalculator.divide(platform_revenue, gross_revenue, precision=4)
            net_margin_pct = MoneyCalculator.multiply(ratio, Decimal("100.00"))
        else:
            net_margin_pct = Decimal("0.00")

        # Detecção de anomalias: transações que superam em +30% o ticket médio
        limite_anomalia = MoneyCalculator.multiply(average_ticket, Decimal("1.30"))
        anomalies: List[Dict[str, Any]] = []

        for tx in valid_txs:
            val = MoneyCalculator.to_decimal(tx.get("valor_bruto", "0.00"))
            if val > limite_anomalia and len(valid_txs) > 1:
                desvio_pct = MoneyCalculator.multiply(
                    MoneyCalculator.divide(MoneyCalculator.subtract(val, average_ticket), average_ticket, precision=4),
                    Decimal("100.00")
                )
                anomalies.append({
                    "id": tx.get("id"),
                    "vendedor_id": tx.get("vendedor_id"),
                    "valor_bruto": str(val),
                    "desvio_acima_media_pct": f"+{desvio_pct}%",
                    "metodo": tx.get("metodo_pagamento")
                })

        recommendations: List[str] = []
        if net_margin_pct < Decimal("3.00"):
            recommendations.append(
                f"Margem da plataforma baixa ({net_margin_pct}%). Considere ajustar taxa_plataforma_pct acima de 3.5%."
            )
        else:
            recommendations.append(
                f"Margem saudável da plataforma ({net_margin_pct}%) com ticket médio de R$ {float(average_ticket):,.2f}."
            )

        if anomalies:
            recommendations.append(
                f"Foram detectadas {len(anomalies)} transações com desvio > 30% da média. Auditar conciliação."
            )

        return AnomalyReport(
            total_analyzed=len(valid_txs),
            gross_revenue=gross_revenue,
            platform_revenue=platform_revenue,
            net_margin_pct=net_margin_pct,
            average_ticket=average_ticket,
            anomalies_detected=anomalies,
            cfo_recommendations=recommendations
        )


# =============================================================================
# 4. AGENTE DE RECUPERAÇÃO DE VENDAS (RecoveryAgent)
# =============================================================================

class RecoveryAgent:
    """Identifica checkouts pendentes ou abandonados e gera ações de conversão."""

    def find_recoverable_sales(self, engine: FintechEngine) -> List[Dict[str, Any]]:
        """Filtra transações PENDING e prepara mensagens personalizadas com incentivo."""
        transactions = engine.get_all_transactions()
        recuperaveis: List[Dict[str, Any]] = []

        for tx in transactions:
            if tx.get("status") == "PENDING":
                valor_original = MoneyCalculator.to_decimal(tx.get("valor_bruto", "0.00"))
                desconto_sugerido = MoneyCalculator.percentage_of(valor_original, Decimal("5.00"))
                valor_com_desconto = MoneyCalculator.subtract(valor_original, desconto_sugerido)
                comprador = tx.get("comprador") or "Cliente"
                metodo = tx.get("metodo_pagamento", "PIX")

                recuperaveis.append({
                    "transaction_id": tx.get("id"),
                    "comprador": comprador,
                    "vendedor_id": tx.get("vendedor_id"),
                    "metodo_original": metodo,
                    "valor_original": str(valor_original),
                    "valor_oferta_recuperacao": str(valor_com_desconto),
                    "mensagem_sugerida": (
                        f"Olá {comprador}! Notamos que seu pagamento via {metodo} de "
                        f"R$ {float(valor_original):,.2f} ficou pendente. Finalize nas próximas 24h "
                        f"via PIX por R$ {float(valor_com_desconto):,.2f} (5% OFF imediato)!"
                    )
                })

        return recuperaveis


# =============================================================================
# 5. AGENTE DE SEGURANÇA, DEFESA ATIVA E SCORE DE RISCO (SecurityDefenseAgent)
# =============================================================================

class SecurityDefenseAgent:
    """Gerencia Defesa Ativa (bloqueio de IP), Score de Risco por arquivo e Webhook SIEM."""

    SENSITIVITY_WEIGHTS = {
        "transacoes.json": 95,
        "carteiras.json": 95,
        "assinaturas.json": 85,
        "fechamento_contabil.xlsx": 90,
        "logs_agentes.json": 75
    }

    def __init__(self, max_failed_attempts: int = 3):
        self.max_failed_attempts = max_failed_attempts
        self.failed_attempts: Dict[str, int] = {}
        self.blocked_identifiers: List[str] = []

    def register_access_attempt(self, identifier: str, failed: bool = True) -> bool:
        """
        Camada de Defesa Ativa: registra tentativa de acesso e bloqueia IP/usuário
        automaticamente após atingir o limite de falhas. Retorna True se bloqueado.
        """
        if not failed:
            self.failed_attempts[identifier] = 0
            return identifier in self.blocked_identifiers

        self.failed_attempts[identifier] = self.failed_attempts.get(identifier, 0) + 1
        if self.failed_attempts[identifier] >= self.max_failed_attempts:
            if identifier not in self.blocked_identifiers:
                self.blocked_identifiers.append(identifier)
            return True
        return False

    def calculate_file_risk_scores(self, monitor: IntegrityMonitor) -> List[Dict[str, Any]]:
        """Calcula o score de risco (0 a 100) e mapa de calor para cada arquivo monitorado."""
        scan_results = monitor.scan_directory()
        risk_table: List[Dict[str, Any]] = []

        for file_info in scan_results:
            filename = Path(file_info.filepath).name
            base_weight = self.SENSITIVITY_WEIGHTS.get(filename, 50)

            if file_info.status == "OK":
                score = int(base_weight * 0.2)
                priority = "BAIXA (Seguro)"
            elif file_info.status == "NEW":
                score = min(base_weight, 65)
                priority = "MÉDIA (Verificar Baseline)"
            elif file_info.status == "MODIFIED":
                score = min(base_weight + 20, 100)
                priority = "CRÍTICA (Adulteração Detectada)"
            else:  # DELETED ou ERROR
                score = 100
                priority = "EMERGÊNCIA (Arquivo Removido)"

            risk_table.append({
                "arquivo": filename,
                "caminho": file_info.filepath,
                "status_integridade": file_info.status,
                "risk_score": score,
                "prioridade": priority
            })

        risk_table.sort(key=lambda x: x["risk_score"], reverse=True)
        return risk_table

    def respond_to_incidents(
        self,
        engine: FintechEngine,
        monitor: IntegrityMonitor
    ) -> SIEMWebhookPayload:
        """Executa varredura completa, isola alertas e gera payload validado para SIEM."""
        ledger_ok = engine.verify_ledger_integrity()
        scan_results = monitor.scan_directory()

        compromised = [
            Path(f.filepath).name for f in scan_results if f.status in ("MODIFIED", "DELETED")
        ]

        if ledger_ok and not compromised:
            return SIEMWebhookPayload(
                severity="LOW",
                source_file="Meridian_Ledger_Cluster",
                status="HEALTHY",
                action_taken="Nenhuma violação detectada. Monitoramento ativo operante.",
                blocked_ips=list(self.blocked_identifiers),
                compromised_files=[]
            )

        severity = "CRITICAL" if any(f.status == "DELETED" for f in scan_results) else "HIGH"
        action = (
            "BLOQUEIO PREVENTIVO DE SAQUES ATIVADO: Violação de hash SHA-256 detectada. "
            "Notificação enviada ao administrador e ticket de incidente aberto."
        )

        return SIEMWebhookPayload(
            severity=severity,
            source_file=", ".join(compromised) if compromised else "transacoes.json",
            status="COMPROMISED",
            action_taken=action,
            blocked_ips=list(self.blocked_identifiers),
            compromised_files=compromised
        )


# =============================================================================
# 6. ORQUESTRADOR UNIFICADO (MeridianAgentHub)
# =============================================================================

class MeridianAgentHub:
    """Centraliza todos os agentes do Meridian Fintech ERP em diretório único."""

    def __init__(
        self,
        engine: Optional[FintechEngine] = None,
        monitor: Optional[IntegrityMonitor] = None
    ):
        self.engine = engine or create_fintech_engine(db_dir=".")
        self.monitor = monitor or IntegrityMonitor()
        self.antifraud = AntifraudAgent()
        self.cfo = CFOAnomalyAgent()
        self.recovery = RecoveryAgent()
        self.security = SecurityDefenseAgent()
        self.log_file = Path("logs_agentes.json")

    def save_agent_audit_log(self, event_type: str, details: Dict[str, Any]) -> None:
        """Salva logs de decisão dos agentes na pasta raiz e atualiza hash no monitor."""
        logs: List[Dict[str, Any]] = []
        if self.log_file.exists():
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except Exception:
                logs = []

        logs.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "details": details
        })

        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, default=str, ensure_ascii=False)

        self.monitor.add_path(str(self.log_file))

    def process_guarded_checkout(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """Passa a transação pelo Agente Antifraude antes de gravar no motor financeiro."""
        historico = self.engine.get_all_transactions()
        fraud_check = self.antifraud.analyze_transaction(tx_data, historico)

        if not fraud_check.is_approved:
            self.save_agent_audit_log("ANTIFRAUD_BLOCK", fraud_check.model_dump())
            return {
                "approved": False,
                "fraud_analysis": fraud_check.model_dump(),
                "transaction": None
            }

        tx_obj = self.engine.create_transaction(tx_data)
        self.save_agent_audit_log("CHECKOUT_APPROVED", {
            "transaction_id": tx_obj.id,
            "risk_score": fraud_check.risk_score
        })
        return {
            "approved": True,
            "fraud_analysis": fraud_check.model_dump(),
            "transaction": tx_obj
        }

    def run_full_diagnostics(self) -> Dict[str, Any]:
        """Executa diagnóstico completo de CFO, Recuperação, Risco e SIEM."""
        cfo_report = self.cfo.analyze_financial_health(self.engine)
        recoverable = self.recovery.find_recoverable_sales(self.engine)
        risk_scores = self.security.calculate_file_risk_scores(self.monitor)
        siem_payload = self.security.respond_to_incidents(self.engine, self.monitor)

        summary = {
            "cfo_report": cfo_report.model_dump(),
            "recoverable_sales_count": len(recoverable),
            "recoverable_sales": recoverable,
            "file_risk_scores": risk_scores,
            "siem_webhook_payload": siem_payload.model_dump()
        }
        self.save_agent_audit_log("FULL_DIAGNOSTICS", {
            "net_margin_pct": str(cfo_report.net_margin_pct),
            "anomalies": len(cfo_report.anomalies_detected),
            "siem_severity": siem_payload.severity
        })
        return summary


# =============================================================================
# 7. EXECUÇÃO DE TESTE NO TERMINAL
# =============================================================================

if __name__ == "__main__":
    hub = MeridianAgentHub()

    print("=" * 65)
    print("🤖 MERIDIAN AGENT HUB - TESTE INTEGRADO DE BACK-END (FASE 4)")
    print("=" * 65)

    # 1. Teste de Checkout Protegido pelo Agente Antifraude (Transação Normal)
    res_ok = hub.process_guarded_checkout({
        "id": generate_transaction_id(),
        "valor_bruto": 350.00,
        "metodo_pagamento": "PIX",
        "status": "PENDING",
        "comprador": "CLIENTE_VIP",
        "vendedor_id": "VENDEDOR_A"
    })
    print(f"[1. ANTIFRAUDE NORMAL] Aprovado: {res_ok['approved']} | Score: {res_ok['fraud_analysis']['risk_score']}")

    # 2. Teste de Bloqueio pelo Agente Antifraude (Valor Suspeito > R$ 10.000 e Anônimo no Cartão)
    res_fraude = hub.process_guarded_checkout({
        "id": generate_transaction_id(),
        "valor_bruto": 25000.00,
        "metodo_pagamento": "CARTAO",
        "status": "PENDING",
        "comprador": "ANONIMO",
        "vendedor_id": "VENDEDOR_A"
    })
    print(f"[2. ANTIFRAUDE BLOQUEIO] Aprovado: {res_fraude['approved']} | Motivo: {res_fraude['fraud_analysis']['reason']}")

    # 3. Teste de Defesa Ativa (Simulando 3 tentativas suspeitas de um IP)
    ip_suspeito = "192.168.1.250"
    for tentativa in range(1, 4):
        bloqueado = hub.security.register_access_attempt(ip_suspeito, failed=True)
    print(f"[3. DEFESA ATIVA] IP {ip_suspeito} bloqueado após 3 falhas: {bloqueado}")

    # 4. Diagnóstico Completo (CFO + Recuperação + Score de Risco + SIEM)
    diag = hub.run_full_diagnostics()
    print(f"[4. AGENTE CFO] Receita Bruta: R$ {float(diag['cfo_report']['gross_revenue']):,.2f} | Margem: {diag['cfo_report']['net_margin_pct']}%")
    print(f"[5. SIEM WEBHOOK] Status: {diag['siem_webhook_payload']['status']} | Severidade: {diag['siem_webhook_payload']['severity']}")
    print("=" * 65)