#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel Conciliador - Fase 3 do Meridian Fintech ERP
Módulo de conciliação financeira com importação/exportação em diretório único,
validação Pydantic v2, precisão Decimal e blindagem SHA-256.
"""

import pandas as pd
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from hashlib import sha256
from pydantic import BaseModel, Field, field_validator

from fintech_engine import (
    MoneyCalculator,
    create_fintech_engine,
    generate_transaction_id,
    Transaction
)
from monitor_engine import IntegrityMonitor


# =============================================================================
# 1. VALIDAÇÃO PYDANTIC V2 E PRECISÃO DECIMAL
# =============================================================================

class ExcelRowImport(BaseModel):
    """Schema Pydantic v2 para validar e normalizar linhas importadas de planilhas."""
    id: str = Field(default_factory=generate_transaction_id)
    valor_bruto: Decimal
    metodo_pagamento: str
    status: str = Field(default="PENDING")
    comprador: str = Field(default="COMPRADOR_PLANILHA")
    vendedor_id: str = Field(default="VENDEDOR_PADRAO")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @field_validator("valor_bruto", mode="before")
    @classmethod
    def validate_valor(cls, v: Any) -> Decimal:
        val = MoneyCalculator.to_decimal(str(v))
        if val <= Decimal("0.00"):
            raise ValueError(f"O valor_bruto deve ser maior que zero: {v}")
        return val

    @field_validator("metodo_pagamento", mode="before")
    @classmethod
    def validate_metodo(cls, v: Any) -> str:
        metodo = str(v).strip().upper()
        mapa = {"CARTÃO": "CARTAO", "CREDITO": "CARTAO", "CRÉDITO": "CARTAO"}
        metodo = mapa.get(metodo, metodo)
        if metodo not in ("PIX", "CARTAO", "BOLETO"):
            raise ValueError(f"metodo_pagamento inválido: {metodo}")
        return metodo

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> str:
        st_raw = str(v).strip().upper()
        mapa_status = {
            "PENDENTE": "PENDING",
            "APROVADA": "PAID",
            "APROVADO": "PAID",
            "PAGO": "PAID",
            "ESTORNADA": "REFUNDED",
            "CANCELADA": "REFUNDED",
            "REJEITADA": "BLOCKED_FRAUD",
            "FRAUDE": "BLOCKED_FRAUD"
        }
        st_norm = mapa_status.get(st_raw, st_raw)
        if st_norm not in ("PENDING", "PAID", "REFUNDED", "BLOCKED_FRAUD"):
            return "PENDING"
        return st_norm

    def to_engine_dict(self) -> Dict[str, Any]:
        """Converte a linha validada para o formato esperado por engine.create_transaction()."""
        return {
            "id": self.id,
            "valor_bruto": str(self.valor_bruto),
            "metodo_pagamento": self.metodo_pagamento,
            "status": self.status,
            "comprador": self.comprador,
            "vendedor_id": self.vendedor_id,
            "timestamp": self.timestamp
        }


# =============================================================================
# 2. IMPORTAÇÃO INTELIGENTE DE PLANILHAS
# =============================================================================

def import_transactions_from_excel(
    file_path: str,
    engine: Optional[Any] = None
) -> List[Transaction]:
    """Lê um ficheiro .xlsx ou .csv na pasta atual, valida via Pydantic e grava no motor."""
    path = Path(file_path).Name if hasattr(Path(file_path), "Name") else Path(Path(file_path).name)
    if not path.exists():
        raise FileNotFoundError(f"Ficheiro não encontrado na pasta atual: {path}")

    if engine is None:
        engine = create_fintech_engine(db_dir=".")

    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        df = pd.read_excel(path)
    elif suffix == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError(f"Formato não suportado ({suffix}). Use .xlsx ou .csv.")

    transacoes_registradas: List[Transaction] = []
    if df.empty:
        return transacoes_registradas

    for index, row in df.iterrows():
        try:
            raw_id = row.get("id")
            tx_id = str(raw_id) if pd.notna(raw_id) and str(raw_id).strip() else generate_transaction_id()

            excel_row = ExcelRowImport(
                id=tx_id,
                valor_bruto=row.get("valor_bruto", "0.00"),
                metodo_pagamento=row.get("metodo_pagamento", "PIX"),
                status=row.get("status", "PENDING"),
                comprador=str(row.get("comprador", "COMPRADOR_PLANILHA")),
                vendedor_id=str(row.get("vendedor_id", "VENDEDOR_A")),
                timestamp=str(row.get("timestamp", datetime.now(timezone.utc).isoformat()))
            )

            registered_tx = engine.create_transaction(excel_row.to_engine_dict())
            transacoes_registradas.append(registered_tx)
        except Exception as e:
            print(f"⚠️ Linha {index + 1} ignorada ({e})")
            continue

    return transacoes_registradas


# =============================================================================
# 3. EXPORTAÇÃO CONTÁBIL MULTI-ABAS (Sem criar subpastas)
# =============================================================================

def _calculate_dre_metrics(transactions: List[Dict[str, Any]]) -> Dict[str, Decimal]:
    """Calcula os totalizadores da DRE somando os splits reais com MoneyCalculator."""
    receita_bruta = Decimal("0.00")
    taxas_plataforma = Decimal("0.00")
    repasses_vendedores = Decimal("0.00")
    custo_fornecedores = Decimal("0.00")

    for tx in transactions:
        if tx.get("status") == "REFUNDED" or tx.get("status") == "BLOCKED_FRAUD":
            continue

        valor = MoneyCalculator.to_decimal(tx.get("valor_bruto", "0.00"))
        split = tx.get("split", {})

        taxa = MoneyCalculator.to_decimal(split.get("plataforma", "0.00"))
        vendedor = MoneyCalculator.to_decimal(split.get("vendedor", "0.00"))
        fornecedor = MoneyCalculator.to_decimal(split.get("fornecedor", "0.00"))

        receita_bruta = MoneyCalculator.add(receita_bruta, valor)
        taxas_plataforma = MoneyCalculator.add(taxas_plataforma, taxa)
        repasses_vendedores = MoneyCalculator.add(repasses_vendedores, vendedor)
        custo_fornecedores = MoneyCalculator.add(custo_fornecedores, fornecedor)

    return {
        "receita_bruta_total": receita_bruta,
        "total_taxas_plataforma": taxas_plataforma,
        "repasses_vendedores": repasses_vendedores,
        "custo_fornecedores": custo_fornecedores
    }


def _write_dre_tab(dre_data: Dict[str, Decimal], writer: pd.ExcelWriter) -> None:
    """Escreve a aba Resumo_DRE no ficheiro Excel."""
    dre_df = pd.DataFrame([
        {"Indicador Contábil": "Receita Bruta Total", "Valor (R$)": f"R$ {float(dre_data['receita_bruta_total']):,.2f}"},
        {"Indicador Contábil": "(-) Taxas Plataforma Meridian", "Valor (R$)": f"R$ {float(dre_data['total_taxas_plataforma']):,.2f}"},
        {"Indicador Contábil": "(=) Repasses Líquidos a Vendedores", "Valor (R$)": f"R$ {float(dre_data['repasses_vendedores']):,.2f}"},
        {"Indicador Contábil": "(-) Custo de Fornecedores", "Valor (R$)": f"R$ {float(dre_data['custo_fornecedores']):,.2f}"}
    ])
    dre_df.to_excel(writer, sheet_name="Resumo_DRE", index=False)


def _write_fluxo_tab(transactions: List[Dict[str, Any]], writer: pd.ExcelWriter) -> None:
    """Escreve a aba Fluxo_Transacoes com o histórico detalhado."""
    if not transactions:
        fluxo_df = pd.DataFrame(columns=[
            "ID", "Valor Bruto", "Taxa Plataforma", "Líquido Vendedor",
            "Fornecedor", "Método", "Status", "Comprador", "Vendedor", "Data/Hora"
        ])
    else:
        rows = []
        for tx in transactions:
            split = tx.get("split", {})
            val_bruto = MoneyCalculator.to_decimal(tx.get("valor_bruto", "0.00"))
            val_plat = MoneyCalculator.to_decimal(split.get("plataforma", "0.00"))
            val_vend = MoneyCalculator.to_decimal(split.get("vendedor", "0.00"))
            val_forn = MoneyCalculator.to_decimal(split.get("fornecedor", "0.00"))

            rows.append({
                "ID": tx.get("id", ""),
                "Valor Bruto": f"R$ {float(val_bruto):,.2f}",
                "Taxa Plataforma": f"R$ {float(val_plat):,.2f}",
                "Líquido Vendedor": f"R$ {float(val_vend):,.2f}",
                "Fornecedor": f"R$ {float(val_forn):,.2f}",
                "Método": tx.get("metodo_pagamento", ""),
                "Status": tx.get("status", ""),
                "Comprador": tx.get("comprador", ""),
                "Vendedor": tx.get("vendedor_id", ""),
                "Data/Hora": tx.get("timestamp", "")
            })
        fluxo_df = pd.DataFrame(rows)

    fluxo_df.to_excel(writer, sheet_name="Fluxo_Transacoes", index=False)


def _write_carteiras_tab(
    wallets: Dict[str, Decimal],
    subscriptions: List[Dict[str, Any]],
    writer: pd.ExcelWriter
) -> None:
    """Escreve saldos de carteiras e assinaturas MRR lado a lado na aba Carteiras_e_MRR."""
    carteira_rows = [
        {
            "Vendedor ID": vendedor,
            "Saldo Disponível": f"R$ {float(MoneyCalculator.to_decimal(saldo)):,.2f}"
        }
        for vendedor, saldo in wallets.items()
    ]
    carteira_df = pd.DataFrame(carteira_rows) if carteira_rows else pd.DataFrame(columns=["Vendedor ID", "Saldo Disponível"])

    sub_rows = [
        {
            "Subscription ID": sub.get("subscription_id", ""),
            "MRR Bruto": f"R$ {float(MoneyCalculator.to_decimal(sub.get('mrr_bruto', '0.00'))):,.2f}",
            "MRR Plataforma": f"R$ {float(MoneyCalculator.to_decimal(sub.get('mrr_plataforma', '0.00'))):,.2f}",
            "Status": sub.get("status", ""),
            "Próxima Cobrança": str(sub.get("next_billing_date", ""))
        }
        for sub in subscriptions
    ]
    assinatura_df = pd.DataFrame(sub_rows) if sub_rows else pd.DataFrame(
        columns=["Subscription ID", "MRR Bruto", "MRR Plataforma", "Status", "Próxima Cobrança"]
    )

    carteira_df.to_excel(writer, sheet_name="Carteiras_e_MRR", index=False, startcol=0)
    assinatura_df.to_excel(writer, sheet_name="Carteiras_e_MRR", index=False, startcol=3)


def register_file_hash(file_path: str, monitor: Optional[IntegrityMonitor] = None) -> str:
    """Calcula e regista o hash SHA-256 do ficheiro Excel no IntegrityMonitor."""
    target = Path(Path(file_path).name)
    if not target.exists():
        raise FileNotFoundError(f"Ficheiro não encontrado para assinatura SHA-256: {target}")

    if monitor is None:
        monitor = IntegrityMonitor()

    with open(target, "rb") as f:
        digest = sha256(f.read()).hexdigest()

    monitor.add_path(str(target))
    return digest


def export_accounting_report(
    output_file: str = "fechamento_contabil.xlsx",
    engine: Optional[Any] = None,
    include_dre: bool = True,
    include_fluxo: bool = True,
    include_carteiras: bool = True
) -> Path:
    """Gera o relatório contábil multi-abas na pasta raiz e assina com SHA-256."""
    if engine is None:
        engine = create_fintech_engine(db_dir=".")

    output_path = Path(Path(output_file).name)

    all_transactions = engine.get_all_transactions()
    wallets = engine.get_all_wallets()
    if not wallets and hasattr(engine, "db"):
        wallets = engine.db.load_wallets()
    subscriptions = engine.db.load_subscriptions() if hasattr(engine, "db") else []

    dre_data = _calculate_dre_metrics(all_transactions)

    with pd.ExcelWriter(output_path, engine="openpyxl", mode="w") as writer:
        if include_dre:
            _write_dre_tab(dre_data, writer)
        if include_fluxo:
            _write_fluxo_tab(all_transactions, writer)
        if include_carteiras:
            _write_carteiras_tab(wallets, subscriptions, writer)

    register_file_hash(str(output_path))
    return output_path


def generate_conciliation_report(
    input_file: Optional[str] = None,
    output_file: str = "fechamento_contabil.xlsx",
    engine: Optional[Any] = None,
    register_hash: bool = True
) -> Path:
    """Orquestra a importação opcional de planilha, exportação contábil e registo SHA-256."""
    if engine is None:
        engine = create_fintech_engine(db_dir=".")

    if input_file:
        import_transactions_from_excel(input_file, engine)

    output_path = export_accounting_report(output_file=output_file, engine=engine)

    if register_hash and output_path.exists():
        register_file_hash(str(output_path))

    return output_path


if __name__ == "__main__":
    caminho = generate_conciliation_report()
    print(f"Relatório gerado e blindado com sucesso em: {caminho.resolve()}")