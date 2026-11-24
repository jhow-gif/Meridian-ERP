#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Meridian Fintech ERP - Suíte Completa de Testes Automatizados (21 Testes QA, AppSec & SOC)
Cobre: Decimal, Split, Estorno, SHA-256, Antifraude, Excel, Multi-Tenant RBAC, Saques Pix,
Links WhatsApp, API Key + Webhook, Extrato HTML, Multi-Split, LGPD, White-Label,
Split Tributário/NFS-e, ROI B2B, Supabase Cloud, Docker Kit, Bloqueio em 3 Tentativas + E-mail
exclusivo na 3ª falha + Desbloqueio SMS (6-8 dígitos), OWASP WAF, Cofre At-Rest e Pentest 8 Pilares.
"""

import json
import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from monitor_engine import IntegrityMonitor
from fintech_engine import (
    MoneyCalculator,
    FintechEngine,
    IntegrityError,
    generate_transaction_id
)
from excel_conciliador import export_accounting_report
from fintech_agents import MeridianAgentHub
from auth_engine import MeridianAuthManager, LGPDMasker, WhiteLabelConfig
from security_compliance import (
    DataVaultCipher,
    OWASPShield,
    AutomatedPentestScanner
)
from enterprise_modules import (
    TaxSplitNFSeEngine,
    B2BProposalROIEngine,
    SupabaseHybridSync,
    ProductionDeployGenerator
)
from ui_components import generate_executive_statement_html


class TestMeridianFintechERP(unittest.TestCase):
    """Testes integrados de ponta a ponta em diretório temporário 100% isolado."""

    def _isolate_monitor(self, monitor):
        """Garante que o IntegrityMonitor use um integrity_hashes.json exclusivo no diretório temporário."""
        temp_db = self.base_path / "integrity_hashes.json"
        for attr_name, attr_val in list(vars(monitor).items()):
            if isinstance(attr_val, Path) and attr_val.name == "integrity_hashes.json":
                setattr(monitor, attr_name, temp_db)
            elif isinstance(attr_val, str) and attr_val.endswith("integrity_hashes.json"):
                setattr(monitor, attr_name, str(temp_db))
            elif isinstance(attr_val, dict):
                cleaned = {
                    k: v for k, v in attr_val.items()
                    if str(self.base_path) in str(k)
                }
                if len(cleaned) != len(attr_val):
                    setattr(monitor, attr_name, cleaned)

    def setUp(self):
        self.orig_cwd = os.getcwd()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

        # LIFO: restaura cwd primeiro e limpa temp_dir depois (evita erro de lock no Windows)
        self.addCleanup(self.temp_dir.cleanup)
        os.chdir(self.base_path)
        self.addCleanup(os.chdir, self.orig_cwd)

        self.engine = FintechEngine(db_dir=str(self.base_path))
        if hasattr(self.engine, "db") and hasattr(self.engine.db, "monitor"):
            self.monitor = self.engine.db.monitor
        else:
            self.monitor = IntegrityMonitor()

        self._isolate_monitor(self.monitor)

        self.hub = MeridianAgentHub(engine=self.engine, monitor=self.monitor)
        self.hub.log_file = self.base_path / "logs_agentes.json"

        self.auth = MeridianAuthManager(
            engine=self.engine,
            monitor=self.monitor,
            base_dir=str(self.base_path)
        )
        self.tax_engine = TaxSplitNFSeEngine(
            engine=self.engine,
            monitor=self.monitor,
            base_dir=str(self.base_path)
        )
        self.supa_sync = SupabaseHybridSync(
            engine=self.engine,
            monitor=self.monitor,
            base_dir=str(self.base_path)
        )

    def test_01_precisao_decimal_e_split_exato(self):
        tx = self.engine.create_transaction({
            "id": generate_transaction_id(),
            "valor_bruto": "33.33",
            "metodo_pagamento": "PIX",
            "status": "PENDING",
            "comprador": "CLIENTE_TESTE",
            "vendedor_id": "VENDEDOR_1"
        })
        split = self.engine.wallet_manager.calculate_split(tx)
        soma = MoneyCalculator.add(MoneyCalculator.add(split.plataforma, split.vendedor), split.fornecedor)
        self.assertEqual(soma, Decimal("33.33"))

    def test_02_estorno_transacao(self):
        tx_id = generate_transaction_id()
        self.engine.create_transaction({
            "id": tx_id,
            "valor_bruto": "200.00",
            "metodo_pagamento": "CARTAO",
            "comprador": "CLIENTE_ESTORNO",
            "vendedor_id": "VENDEDOR_2"
        })
        self.assertTrue(bool(self.engine.refund_transaction(tx_id)))

    def test_03_bloqueio_adulteracao_sha256(self):
        self.engine.create_transaction({
            "id": generate_transaction_id(),
            "valor_bruto": "100.00",
            "metodo_pagamento": "PIX",
            "comprador": "CLIENTE_OK",
            "vendedor_id": "VENDEDOR_A"
        })
        arquivo_tx = self.base_path / "transacoes.json"
        with open(arquivo_tx, "r", encoding="utf-8") as f:
            dados = json.load(f)
        dados["transactions"][0]["valor_bruto"] = "999999.00"
        with open(arquivo_tx, "w", encoding="utf-8") as f:
            json.dump(dados, f)

        with self.assertRaises(IntegrityError):
            self.engine.create_transaction({
                "id": generate_transaction_id(),
                "valor_bruto": "50.00",
                "metodo_pagamento": "BOLETO",
                "comprador": "CLIENTE_2",
                "vendedor_id": "VENDEDOR_A"
            })

    def test_04_agente_antifraude_e_defesa_ativa(self):
        resultado = self.hub.process_guarded_checkout({
            "id": generate_transaction_id(),
            "valor_bruto": "25000.00",
            "metodo_pagamento": "CARTAO",
            "comprador": "ANONIMO",
            "vendedor_id": "VENDEDOR_A"
        })
        self.assertFalse(resultado["approved"])

    def test_05_exportacao_excel_contabil(self):
        self.engine.create_transaction({
            "id": generate_transaction_id(),
            "valor_bruto": "500.00",
            "metodo_pagamento": "PIX",
            "comprador": "CLIENTE_EXCEL",
            "vendedor_id": "VENDEDOR_EXCEL"
        })
        caminho_xlsx = export_accounting_report(
            output_file=str(self.base_path / "teste_fechamento.xlsx"),
            engine=self.engine
        )
        self.assertTrue(caminho_xlsx.exists())
        if caminho_xlsx.exists():
            caminho_xlsx.unlink()

    def test_06_autenticacao_e_isolamento_multitenant(self):
        self.engine.create_transaction({
            "id": generate_transaction_id(),
            "valor_bruto": "100.00",
            "metodo_pagamento": "PIX",
            "comprador": "CLI_A",
            "vendedor_id": "VENDEDOR_A"
        })
        sessao_a = self.auth.authenticate("vendedor_a", "lojista123")
        tx_visiveis_a = self.auth.get_tenant_transactions(sessao_a)
        self.assertEqual(len(tx_visiveis_a), 1)

    def test_07_saque_pix_com_antecipacao(self):
        self.engine.create_transaction({
            "id": generate_transaction_id(),
            "valor_bruto": "1000.00",
            "metodo_pagamento": "PIX",
            "comprador": "CLI_SAQUE",
            "vendedor_id": "VENDEDOR_A"
        })
        payout = self.auth.request_payout("VENDEDOR_A", "200.00", "pix@loja.com", antecipacao_imediata=True)
        self.assertEqual(payout.taxa_antecipacao, Decimal("5.00"))

    def test_08_link_pagamento_whatsapp_e_liquidacao_webhook(self):
        fatura = self.auth.create_payment_link("VENDEDOR_B", "Cliente", "11988887777", "Contrato", "1000.00")
        tx_liquidada = self.auth.settle_pending_transaction(fatura.transaction_id)
        self.assertEqual(tx_liquidada["status"], "PAID")

    def test_09_autenticacao_por_api_key(self):
        sessao_a = self.auth.authenticate("vendedor_a", "lojista123")
        owner = self.auth.get_user_by_api_key(sessao_a["api_key"])
        self.assertEqual(owner["vendedor_id"], "VENDEDOR_A")

    def test_10_geracao_extrato_executivo_html(self):
        sessao_a = self.auth.authenticate("vendedor_a", "lojista123")
        html_doc = generate_executive_statement_html(sessao_a, [], [], 1250.50)
        self.assertIn("EXTRATO EXECUTIVO DE REPASSE E DRE", html_doc)

    def test_11_multi_beneficiary_split_exato(self):
        res = self.auth.execute_multi_beneficiary_split(
            valor_bruto="100.00",
            metodo_pagamento="PIX",
            comprador="Cliente Contrato",
            descricao_contrato="Split Comercial",
            taxa_plataforma_pct="5.00",
            beneficiarios=[
                {"vendedor_id": "MATRIZ_HQ", "papel": "Empresa Matriz", "percentual": "50.00"},
                {"vendedor_id": "COMISSIONADO_01", "papel": "Vendedor", "percentual": "45.00"}
            ]
        )
        self.assertEqual(self.engine.get_vendor_balance("MATRIZ_HQ"), Decimal("50.00"))
        self.assertEqual(res["taxa_plataforma"], "5.00")

    def test_12_anonimizacao_lgpd_pii(self):
        sanitized = LGPDMasker.sanitize_transaction({"id": "1", "comprador": "Ana CPF 123.456.789-00"}, True)
        self.assertNotIn("123.456.789-00", sanitized["comprador"])

    def test_13_whitelabel_persistencia(self):
        self.auth.save_whitelabel_config(WhiteLabelConfig(brand_name="EMERALD PAY", primary_color="#059669"))
        loaded = self.auth.load_whitelabel_config()
        self.assertEqual(loaded.brand_name, "EMERALD PAY")
        self.assertEqual(loaded.primary_color, "#059669")

    def test_14_split_tributario_e_emissao_nfse_xml(self):
        sim = self.tax_engine.calculate_tax_savings_simulation("1000.00", "100000.00", "40.00", "10.00")
        self.assertEqual(sim["economia_mensal"], Decimal("6000.00"))

        self.engine.create_transaction({
            "id": generate_transaction_id(),
            "valor_bruto": "500.00",
            "metodo_pagamento": "PIX",
            "comprador": "Tomador NFSe",
            "vendedor_id": "VENDEDOR_A"
        })
        tx_dict = self.engine.get_all_transactions()[-1]
        notas = self.tax_engine.issue_nfse_for_transaction(tx_dict, aliquota_pct="6.00")
        self.assertGreaterEqual(len(notas), 1)
        xml_str = self.tax_engine.generate_nfse_xml(notas[0])
        self.assertIn("<BaseCalculoReduzidaSplit>", xml_str)

    def test_15_calculadora_roi_e_proposta_comercial_b2b(self):
        roi = B2BProposalROIEngine.calculate_b2b_roi("100000.00", "50.00", "10.00", 20, "50.00", "3000.00", "500.00")
        self.assertEqual(roi["economia_fiscal_mes"], Decimal("5000.00"))
        html_prop = B2BProposalROIEngine.generate_commercial_proposal_html("MERIDIAN", "Grupo Alpha", "B2B", roi)
        self.assertIn("Grupo Alpha", html_prop)
        self.assertIn("<svg", html_prop)

    def test_16_conector_hibrido_supabase_snapshot(self):
        res = self.supa_sync.sync_ledger_to_cloud()
        self.assertEqual(len(res["master_sha256"]), 64)
        self.assertIn("ENABLE ROW LEVEL SECURITY", self.supa_sync.get_postgres_ddl_sql())

    def test_17_gerador_kit_deploy_docker(self):
        criados = ProductionDeployGenerator.write_deploy_kit_to_disk(
            monitor=self.monitor,
            target_dir=str(self.base_path)
        )
        self.assertIn("Dockerfile", criados)
        self.assertTrue((self.base_path / "docker-compose.yml").exists())

    def test_18_bloqueio_estrito_3_tentativas_email_apenas_na_3a_e_sms_unlock(self):
        """Valida que o e-mail só é enviado na 3ª falha e que o código SMS (6-8 dígitos) desbloqueia."""
        res1 = self.auth.authenticate("vendedor_a", "senha_errada_1", security_agent=self.hub.security)
        self.assertIsNone(res1)
        self.assertEqual(self.auth.get_failed_attempts_count("vendedor_a"), 1)
        self.assertEqual(len(self.auth.email_dispatcher.load_outbox()), 0)

        res2 = self.auth.authenticate("vendedor_a", "senha_errada_2", security_agent=self.hub.security)
        self.assertIsNone(res2)
        self.assertEqual(self.auth.get_failed_attempts_count("vendedor_a"), 2)
        self.assertEqual(len(self.auth.email_dispatcher.load_outbox()), 0)

        with self.assertRaises(PermissionError):
            self.auth.authenticate("vendedor_a", "senha_errada_3", security_agent=self.hub.security)

        self.assertTrue(self.auth.is_user_locked("vendedor_a"))
        outbox = self.auth.email_dispatcher.load_outbox()
        self.assertEqual(len(outbox), 1)

        sms_code = self.auth.get_active_sms_unlock_code("vendedor_a")
        self.assertIsNotNone(sms_code)
        self.assertTrue(6 <= len(sms_code) <= 8)
        self.assertTrue(sms_code.isalnum())

        self.assertFalse(self.auth.verify_sms_and_unlock("vendedor_a", "000000", security_agent=self.hub.security))
        self.assertTrue(self.auth.is_user_locked("vendedor_a"))

        self.assertTrue(self.auth.verify_sms_and_unlock("vendedor_a", sms_code, security_agent=self.hub.security))
        self.assertFalse(self.auth.is_user_locked("vendedor_a"))

        sessao_ok = self.auth.authenticate("vendedor_a", "lojista123", security_agent=self.hub.security)
        self.assertIsNotNone(sessao_ok)

    def test_19_owasp_waf_bloqueia_sqli_e_xss_no_login(self):
        """Garante que ataques SQL Injection e XSS sejam barrados pelo OWASPShield."""
        with self.assertRaises(PermissionError):
            self.auth.authenticate("admin' OR '1'='1' --", "qualquer", security_agent=self.hub.security)

        ok_xss, _ = OWASPShield.inspect_input("<script>alert(1)</script>", "comprador")
        self.assertFalse(ok_xss)

    def test_20_criptografia_autenticada_em_repouso_vault(self):
        """Verifica se o DataVaultCipher cifra e autentica dados com HMAC-SHA256."""
        vault = DataVaultCipher(master_secret="chave_teste_secreta")
        cifrado = vault.encrypt_at_rest("DADO_CONFIDENCIAL_LGPD")
        self.assertNotIn("DADO_CONFIDENCIAL_LGPD", cifrado)
        self.assertEqual(vault.decrypt_at_rest(cifrado), "DADO_CONFIDENCIAL_LGPD")

    def test_21_scanner_pentest_automatizado_8_pilares(self):
        """Executa o scanner DAST/SAST completo e exige aprovação em todos os controles."""
        self.engine.create_transaction({
            "id": generate_transaction_id(),
            "valor_bruto": "100.00",
            "metodo_pagamento": "PIX",
            "comprador": "AUDITORIA_PENTEST",
            "vendedor_id": "VENDEDOR_A"
        })
        relatorio = AutomatedPentestScanner.run_security_audit_suite(self.auth, self.engine)
        self.assertEqual(len(relatorio), 8)
        falhas = [item for item in relatorio if item["Status"] != "PASSED"]
        self.assertEqual(len(falhas), 0, f"Pilares reprovados no pentest: {falhas}")


if __name__ == "__main__":
    unittest.main(verbosity=2)