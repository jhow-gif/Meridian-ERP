#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Meridian Fintech ERP - Fase 1: Engine de Processamento Financeiro
Arquitetura: Módulo com precisão monetária Decimal, validação Pydantic v2,
motor de pagamentos e integração direta com monitor_engine.py (SHA-256).
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Optional, List, Dict, Any
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from monitor_engine import IntegrityMonitor as SystemIntegrityMonitor


# =============================================================================
# 1. PRECISÃO MONETÁRIA - Utilitário de Cálculo Financeiro Seguro
# =============================================================================

class MoneyCalculator:
    """Classe utilitária para operações monetárias com precisão bancária."""

    @staticmethod
    def to_decimal(value: float | str | Decimal, precision: int = 2) -> Decimal:
        """Converte valor para Decimal com arredondamento ROUND_HALF_UP."""
        quantizer = Decimal(f"0.{'0' * precision}") if precision > 0 else Decimal("1")
        if isinstance(value, Decimal):
            return value.quantize(quantizer, rounding=ROUND_HALF_UP)
        try:
            d = Decimal(str(value))
            return d.quantize(quantizer, rounding=ROUND_HALF_UP)
        except InvalidOperation:
            raise ValueError(f"Valor inválido para conversão monetária: {value}")

    @staticmethod
    def add(a: Decimal, b: Decimal) -> Decimal:
        return (a + b).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def subtract(a: Decimal, b: Decimal) -> Decimal:
        return (a - b).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def multiply(a: Decimal, b: Decimal) -> Decimal:
        return (a * b).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def divide(a: Decimal, b: Decimal, precision: int = 2) -> Decimal:
        if b == 0:
            raise ZeroDivisionError("Divisão por zero não permitida.")
        quantizer = Decimal(f"0.{'0' * precision}") if precision > 0 else Decimal("1")
        return (a / b).quantize(quantizer, rounding=ROUND_HALF_UP)

    @staticmethod
    def percentage_of(value: Decimal, pct: Decimal) -> Decimal:
        return (value * pct / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# =============================================================================
# 2. VALIDAÇÃO PYDANTIC V2 - Schemas de Domínio Financeiro
# =============================================================================

class Transaction(BaseModel):
    """Esquema para representação de transação financeira."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="UUID da transação")
    valor_bruto: Decimal = Field(..., gt=Decimal("0"), description="Valor total da transação em BRL")
    metodo_pagamento: str = Field(..., pattern=r"^(PIX|CARTAO|BOLETO)$", description="Método de pagamento")
    status: str = Field(default="PENDING", pattern=r"^(PENDING|PAID|REFUNDED|BLOCKED_FRAUD)$", description="Status da transação")
    comprador: Optional[str] = Field(None, description="Identificador do comprador")
    vendedor_id: str = Field(..., description="Identificador único do vendedor")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp UTC")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadados adicionais")

    @field_validator("valor_bruto", mode="before")
    @classmethod
    def validate_valor_bruto(cls, v):
        return MoneyCalculator.to_decimal(v)


class SplitRule(BaseModel):
    """Regras de divisão (split) de valores entre partes."""
    taxa_plataforma_pct: Decimal = Field(default=Decimal("5.00"), ge=Decimal("0"), le=Decimal("100"))
    comissao_vendedor_pct: Decimal = Field(default=Decimal("85.00"), ge=Decimal("0"), le=Decimal("100"))
    custo_fornecedor_pct: Decimal = Field(default=Decimal("10.00"), ge=Decimal("0"), le=Decimal("100"))

    @field_validator("taxa_plataforma_pct", "comissao_vendedor_pct", "custo_fornecedor_pct", mode="before")
    @classmethod
    def validate_percentages(cls, v):
        return MoneyCalculator.to_decimal(v)


class SplitResult(BaseModel):
    """Resultado do cálculo de divisão (split) entre partes."""
    transacao_id: str
    valor_total: Decimal
    plataforma: Decimal
    vendedor: Decimal
    fornecedor: Decimal = Field(default=Decimal("0.00"))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("valor_total", "plataforma", "vendedor", "fornecedor", mode="before")
    @classmethod
    def validate_splits(cls, v):
        return MoneyCalculator.to_decimal(v)


class SubscriptionMRR(BaseModel):
    """Representação de Receita Recorrente Mensal (MRR) de assinatura."""
    subscription_id: str
    cliente_id: str = Field(default="CLIENTE_PADRAO")
    vendedor_id: str = Field(default="VENDEDOR_A")
    mrr_bruto: Decimal
    mrr_plataforma: Decimal
    mrr_vendedor: Decimal
    status: str = Field(default="ACTIVE", pattern=r"^(ACTIVE|CANCELLED|EXPIRED)$")
    next_billing_date: Optional[datetime] = None

    @field_validator("mrr_bruto", "mrr_plataforma", "mrr_vendedor", mode="before")
    @classmethod
    def validate_mrr(cls, v):
        return MoneyCalculator.to_decimal(v)


# =============================================================================
# 3. MOTOR DE PAGAMENTOS E CARTEIRA - Processamento e Gestão Financeira
# =============================================================================

class PaymentProcessor:
    """Motor de processamento de pagamentos com múltiplos métodos."""

    STATUS_MAPPING = {
        "PIX": {"pending": "PENDING", "success": "PAID", "failed": "BLOCKED_FRAUD"},
        "CARTAO": {"pending": "PENDING", "success": "PAID", "failed": "BLOCKED_FRAUD", "refunded": "REFUNDED"},
        "BOLETO": {"pending": "PENDING", "success": "PAID", "failed": "BLOCKED_FRAUD"}
    }

    def __init__(self, split_rules: Optional[SplitRule] = None):
        self.split_rules = split_rules or SplitRule()

    def process_checkout(
        self,
        transaction_id: str,
        amount: Decimal,
        method: str,
        seller_id: str,
        buyer_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        simulate_fraud: bool = False
    ) -> Transaction:
        """Processa checkout e atualiza status da transação."""
        method_upper = method.upper()
        if method_upper not in self.STATUS_MAPPING:
            raise ValueError(f"Método inválido: {method}. Suportados: {', '.join(self.STATUS_MAPPING.keys())}")

        status_key = "failed" if simulate_fraud else "success"
        final_status = self.STATUS_MAPPING[method_upper][status_key]

        return Transaction(
            id=transaction_id,
            valor_bruto=amount,
            metodo_pagamento=method_upper,
            status=final_status,
            comprador=buyer_id,
            vendedor_id=seller_id,
            metadata=metadata or {}
        )


class WalletManager:
    """Gestão de carteiras digitais e cálculo de saldos líquidos."""

    def __init__(self, split_rules: Optional[SplitRule] = None, initial_wallets: Optional[Dict[str, Decimal]] = None):
        self.split_rules = split_rules or SplitRule()
        self.wallets: Dict[str, Decimal] = {
            k: MoneyCalculator.to_decimal(v) for k, v in (initial_wallets or {}).items()
        }

    def calculate_split(self, transaction: Transaction) -> SplitResult:
        """Calcula divisão automática do valor recebido entre Plataforma, Vendedor e Fornecedor."""
        valor_total = MoneyCalculator.to_decimal(transaction.valor_bruto)

        valor_plataforma = MoneyCalculator.percentage_of(valor_total, self.split_rules.taxa_plataforma_pct)
        valor_fornecedor = MoneyCalculator.percentage_of(valor_total, self.split_rules.custo_fornecedor_pct)
        valor_vendedor = MoneyCalculator.percentage_of(valor_total, self.split_rules.comissao_vendedor_pct)

        # Ajuste de centavos para garantir que soma == valor_total
        soma_splits = MoneyCalculator.add(MoneyCalculator.add(valor_plataforma, valor_vendedor), valor_fornecedor)
        ajuste = MoneyCalculator.subtract(valor_total, soma_splits)
        valor_vendedor_ajustado = MoneyCalculator.add(valor_vendedor, ajuste)

        return SplitResult(
            transacao_id=transaction.id,
            valor_total=valor_total,
            plataforma=valor_plataforma,
            vendedor=valor_vendedor_ajustado,
            fornecedor=valor_fornecedor
        )

    def update_wallet(self, seller_id: str, amount: Decimal, transaction_type: str = "CREDIT") -> Decimal:
        """Atualiza o saldo da carteira do vendedor."""
        atual = self.wallets.get(seller_id, Decimal("0.00"))
        if transaction_type == "CREDIT":
            self.wallets[seller_id] = MoneyCalculator.add(atual, amount)
        elif transaction_type == "DEBIT":
            self.wallets[seller_id] = MoneyCalculator.subtract(atual, amount)
        return self.wallets[seller_id]

    def get_wallet_balance(self, seller_id: str) -> Decimal:
        return self.wallets.get(seller_id, Decimal("0.00"))

    def get_all_balances(self) -> Dict[str, Decimal]:
        return dict(self.wallets)


# =============================================================================
# 4. BANCO JSON MODULAR E BLINDAGEM SHA-256 (Integrado ao monitor_engine.py)
# =============================================================================

class IntegrityError(Exception):
    """Exceção para violação de integridade do ledger financeiro."""
    pass


class FintechDatabase:
    """Banco JSON modular conectado ao IntegrityMonitor do projeto Meridian."""

    def __init__(self, base_dir: str = "data_fintech", system_monitor: Optional[SystemIntegrityMonitor] = None):
        self.data_dir = Path(base_dir).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.monitor = system_monitor or SystemIntegrityMonitor()
        self._setup_database_files()

    def _setup_database_files(self):
        """Inicializa ficheiros do banco de dados e regista hashes no monitor principal."""
        files_to_init = {
            "transacoes.json": {"transactions": []},
            "carteiras.json": {"wallets": {}},
            "assinaturas.json": {"subscriptions": []}
        }

        for filename, initial_data in files_to_init.items():
            file_path = self.data_dir / filename
            if not file_path.exists():
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(initial_data, f, indent=2, ensure_ascii=False)
                self.monitor.add_path(str(file_path))
            elif str(file_path) not in self.monitor.hash_database:
                self.monitor.add_path(str(file_path))

    def _verify_before_write(self, file_path: Path) -> None:
        """Verifica se o ficheiro sofreu adulteração externa antes de gravar novos dados."""
        if file_path.exists() and str(file_path) in self.monitor.hash_database:
            check = self.monitor.check_file_integrity(file_path)
            if check.status == "MODIFIED":
                raise IntegrityError(
                    f"ALERTA CRÍTICO: Ledger adulterado externamente em {file_path.name}! Operação bloqueada."
                )

    def _save_and_sign(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Verifica integridade prévia, grava o JSON e atualiza a assinatura SHA-256."""
        self._verify_before_write(file_path)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        # Atualiza o hash oficial no monitor_engine
        self.monitor.add_path(str(file_path))

    def save_transactions(self, transactions: List[Dict[str, Any]]) -> None:
        self._save_and_sign(self.data_dir / "transacoes.json", {"transactions": transactions})

    def save_wallets(self, wallets: Dict[str, Decimal]) -> None:
        serialized = {k: str(v) for k, v in wallets.items()}
        self._save_and_sign(self.data_dir / "carteiras.json", {"wallets": serialized})

    def save_subscriptions(self, subscriptions: List[Dict[str, Any]]) -> None:
        self._save_and_sign(self.data_dir / "assinaturas.json", {"subscriptions": subscriptions})

    def load_transactions(self) -> List[Dict[str, Any]]:
        file_path = self.data_dir / "transacoes.json"
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f).get("transactions", [])

    def load_wallets(self) -> Dict[str, Decimal]:
        file_path = self.data_dir / "carteiras.json"
        with open(file_path, "r", encoding="utf-8") as f:
            raw = json.load(f).get("wallets", {})
        return {k: MoneyCalculator.to_decimal(v) for k, v in raw.items()}

    def load_subscriptions(self) -> List[Dict[str, Any]]:
        file_path = self.data_dir / "assinaturas.json"
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f).get("subscriptions", [])


# =============================================================================
# 5. FINTECH ENGINE - Classe Principal de Integração
# =============================================================================

class FintechEngine:
    """Classe principal que integra pagamentos, split, carteiras e segurança SHA-256."""

    def __init__(
        self,
        db_dir: str = "data_fintech",
        split_rules: Optional[SplitRule] = None,
        system_monitor: Optional[SystemIntegrityMonitor] = None
    ):
        self.split_rules = split_rules or SplitRule()
        self.db = FintechDatabase(base_dir=db_dir, system_monitor=system_monitor)
        self.payment_processor = PaymentProcessor(split_rules=self.split_rules)
        self.wallet_manager = WalletManager(
            split_rules=self.split_rules,
            initial_wallets=self.db.load_wallets()
        )

    def create_transaction(self, transaction_data: Dict[str, Any]) -> Transaction:
        """Cria nova transação, calcula split e atualiza carteira se aprovada."""
        tx_input = Transaction.model_validate(transaction_data)

        processed_tx = self.payment_processor.process_checkout(
            transaction_id=tx_input.id,
            amount=tx_input.valor_bruto,
            method=tx_input.metodo_pagamento,
            seller_id=tx_input.vendedor_id,
            buyer_id=tx_input.comprador,
            metadata=tx_input.metadata
        )

        split_result = self.wallet_manager.calculate_split(processed_tx)

        if processed_tx.status == "PAID":
            self.wallet_manager.update_wallet(
                seller_id=processed_tx.vendedor_id,
                amount=split_result.vendedor,
                transaction_type="CREDIT"
            )

        transactions = self.db.load_transactions()
        transactions.append({
            "id": processed_tx.id,
            "valor_bruto": str(processed_tx.valor_bruto),
            "metodo_pagamento": processed_tx.metodo_pagamento,
            "status": processed_tx.status,
            "comprador": processed_tx.comprador,
            "vendedor_id": processed_tx.vendedor_id,
            "timestamp": processed_tx.timestamp.isoformat(),
            "split": {
                "plataforma": str(split_result.plataforma),
                "vendedor": str(split_result.vendedor),
                "fornecedor": str(split_result.fornecedor)
            }
        })
        self.db.save_transactions(transactions)
        self.db.save_wallets(self.wallet_manager.get_all_balances())

        return processed_tx

    def refund_transaction(self, transaction_id: str) -> bool:
        """Estorna uma transação paga e debita o saldo correspondente da carteira."""
        transactions = self.db.load_transactions()
        for tx in transactions:
            if tx["id"] == transaction_id and tx["status"] == "PAID":
                tx["status"] = "REFUNDED"
                valor_vendedor = MoneyCalculator.to_decimal(tx["split"]["vendedor"])
                self.wallet_manager.update_wallet(tx["vendedor_id"], valor_vendedor, "DEBIT")
                self.db.save_transactions(transactions)
                self.db.save_wallets(self.wallet_manager.get_all_balances())
                return True
        return False

    def get_vendor_balance(self, seller_id: str) -> Decimal:
        return self.wallet_manager.get_wallet_balance(seller_id)

    def process_subscription(self, subscription_data: Dict[str, Any]) -> SubscriptionMRR:
        """Processa nova assinatura recorrente (MRR)."""
        mrr_bruto = MoneyCalculator.to_decimal(subscription_data.get("mrr", 0))
        mrr_plataforma = MoneyCalculator.percentage_of(mrr_bruto, self.split_rules.taxa_plataforma_pct)
        mrr_vendedor = MoneyCalculator.subtract(mrr_bruto, mrr_plataforma)

        next_billing = subscription_data.get("next_billing_date")
        subscription = SubscriptionMRR(
            subscription_id=subscription_data.get("subscription_id", f"SUB_{uuid.uuid4().hex[:6].upper()}"),
            cliente_id=subscription_data.get("cliente_id", "CLIENTE_PADRAO"),
            vendedor_id=subscription_data.get("vendedor_id", "VENDEDOR_A"),
            mrr_bruto=mrr_bruto,
            mrr_plataforma=mrr_plataforma,
            mrr_vendedor=mrr_vendedor,
            status=subscription_data.get("status", "ACTIVE"),
            next_billing_date=datetime.fromisoformat(next_billing) if isinstance(next_billing, str) else next_billing
        )

        subscriptions = self.db.load_subscriptions()
        subscriptions.append({
            "subscription_id": subscription.subscription_id,
            "cliente_id": subscription.cliente_id,
            "vendedor_id": subscription.vendedor_id,
            "mrr_bruto": str(subscription.mrr_bruto),
            "mrr_plataforma": str(subscription.mrr_plataforma),
            "mrr_vendedor": str(subscription.mrr_vendedor),
            "status": subscription.status,
            "next_billing_date": subscription.next_billing_date.isoformat() if subscription.next_billing_date else None
        })
        self.db.save_subscriptions(subscriptions)
        return subscription

    def get_all_transactions(self) -> List[Dict[str, Any]]:
        return self.db.load_transactions()

    def get_all_wallets(self) -> Dict[str, Decimal]:
        return self.wallet_manager.get_all_balances()

    def get_all_subscriptions(self) -> List[Dict[str, Any]]:
        return self.db.load_subscriptions()

    def verify_ledger_integrity(self) -> bool:
        """Verifica a integridade de todos os ficheiros JSON financeiros através do monitor_engine."""
        results = self.db.monitor.scan_directory()
        return all(r.status == "OK" for r in results)


def create_fintech_engine(db_dir: str = "data_fintech") -> FintechEngine:
    return FintechEngine(db_dir=db_dir)


def generate_transaction_id() -> str:
    return str(uuid.uuid4())


if __name__ == "__main__":
    engine = create_fintech_engine()

    print("=" * 60)
    print("MERIDIAN FINTECH ERP - FASE 1: ENGINE DE PROCESSAMENTO")
    print("=" * 60)

    tx_pix = engine.create_transaction({
        "id": generate_transaction_id(),
        "valor_bruto": 100.00,
        "metodo_pagamento": "PIX",
        "comprador": "COMPRADOR_123",
        "vendedor_id": "VENDEDOR_A",
        "metadata": {"pix_copia": "00020126360014BR.GOV.BCB.PIX"}
    })
    print(f"[PIX] ID: {tx_pix.id[:8]}... | Status: {tx_pix.status} | Saldo VENDEDOR_A: R$ {engine.get_vendor_balance('VENDEDOR_A'):.2f}")

    tx_boleto = engine.create_transaction({
        "id": generate_transaction_id(),
        "valor_bruto": 250.50,
        "metodo_pagamento": "BOLETO",
        "comprador": "COMPRADOR_456",
        "vendedor_id": "VENDEDOR_B"
    })
    print(f"[BOLETO] ID: {tx_boleto.id[:8]}... | Status: {tx_boleto.status} | Saldo VENDEDOR_B: R$ {engine.get_vendor_balance('VENDEDOR_B'):.2f}")

    sub = engine.process_subscription({
        "subscription_id": "SUB_001",
        "vendedor_id": "VENDEDOR_A",
        "mrr": 99.90,
        "status": "ACTIVE",
        "next_billing_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    })
    print(f"[MRR] Assinatura: {sub.subscription_id} | Bruto: R$ {sub.mrr_bruto:.2f} | Líquido Vendedor: R$ {sub.mrr_vendedor:.2f}")
    print(f"[SEGURANÇA] Ledger íntegro no monitor_engine: {engine.verify_ledger_integrity()}")