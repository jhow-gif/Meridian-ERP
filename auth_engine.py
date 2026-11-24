#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Meridian Auth, Multi-Tenant, RBAC Corporativo Padronizado, Multi-Split, LGPD & White-Label
Cargos Padronizados:
- ADMIN (Proprietário / Admin Master)
- MERCHANT (Diretor / Gerente de Unidade)
- AUDITOR (Supervisor / Auditoria Financeira)
- PARTNER (Especialista / Vendedor Comissionado — visão exclusiva do próprio saldo)
- STAFF (Atendente / Operador de Caixa — cria cobranças sem ver saldos)
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field

from fintech_engine import MoneyCalculator, FintechEngine, generate_transaction_id
from monitor_engine import IntegrityMonitor
from security_compliance import OWASPShield, SecurityEmailDispatcher


class MerchantUser(BaseModel):
    username: str
    nome_exibicao: str
    role: str = Field(..., pattern=r"^(ADMIN|MERCHANT|PARTNER|STAFF|AUDITOR)$")
    cargo: str = "Admin / Proprietario"
    clinica_id: str = "ALL"
    vendedor_id: str
    comissao_padrao_pct: Decimal = Decimal("0.00")
    chave_pix: str
    email_alerta: str = "seguranca@meridian.com.br"
    telefone_sms: str = "+55 (11) 9****-8899"
    api_key: str
    password_hash: str
    salt: str
    ativo: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PayoutRequest(BaseModel):
    payout_id: str = Field(default_factory=lambda: f"PAY_{uuid.uuid4().hex[:8].upper()}")
    vendedor_id: str
    valor_solicitado: Decimal
    taxa_antecipacao: Decimal
    valor_liquido_pix: Decimal
    chave_pix_destino: str
    modalidade: str = Field(..., pattern=r"^(NORMAL_D1|ANTECIPACAO_IMEDIATA)$")
    status: str = Field(default="PAID", pattern=r"^(PENDING|PAID|REJECTED)$")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PaymentLinkInvoice(BaseModel):
    link_id: str = Field(default_factory=lambda: f"LNK_{uuid.uuid4().hex[:8].upper()}")
    transaction_id: str
    vendedor_id: str
    cliente_nome: str
    cliente_whatsapp: str
    descricao: str
    valor: Decimal
    metodo_preferencial: str = Field(default="PIX", pattern=r"^(PIX|CARTAO|BOLETO)$")
    vencimento: str
    url_checkout: str
    pix_copia_e_cola: str
    status: str = Field(default="PENDING", pattern=r"^(PENDING|PAID|EXPIRED)$")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MultiSplitItem(BaseModel):
    vendedor_id: str
    papel: str
    percentual: Decimal


class WhiteLabelConfig(BaseModel):
    brand_name: str = "MERIDIAN"
    brand_subtitle: str = "Fintech ERP • Multi-Tenant SaaS & AppSec FIM"
    badge_text: str = "ENTERPRISE FINTECH SUITE • SHA-256"
    logo_emoji: str = "M"
    primary_color: str = "#0284c7"
    secondary_color: str = "#2563eb"
    accent_color: str = "#38bdf8"
    lgpd_masking_default: bool = True


class LGPDMasker:
    @staticmethod
    def mask_cpf_or_doc(text: str) -> str:
        digits = "".join(ch for ch in str(text) if ch.isdigit())
        if len(digits) == 11:
            return f"***.{digits[3:6]}.{digits[6:9]}-**"
        if len(digits) == 14:
            return f"**.{digits[2:5]}.{digits[5:8]}/0001-**"
        return text

    @staticmethod
    def mask_name(name: str) -> str:
        raw = str(name or "ANONIMO").strip()
        if raw.upper() in ("ANONIMO", "CLIENTE", "N/A"):
            return raw
        raw = re.sub(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", "***.***.***-**", raw)
        parts = raw.split()
        masked_parts = []
        for idx, p in enumerate(parts):
            if idx == 0 and len(p) > 2:
                masked_parts.append(p[:2] + "*" * (len(p) - 2))
            elif len(p) > 2:
                masked_parts.append(p[0] + "*" * (len(p) - 2) + p[-1])
            else:
                masked_parts.append(p)
        return " ".join(masked_parts)

    @staticmethod
    def mask_phone(phone: str) -> str:
        digits = "".join(ch for ch in str(phone) if ch.isdigit())
        if len(digits) >= 10:
            return f"({digits[:2]}) 9****-{digits[-4:]}"
        return "****-****"

    @staticmethod
    def mask_pix_key(pix_key: str) -> str:
        raw = str(pix_key or "").strip()
        if "@" in raw:
            user_part, domain = raw.split("@", 1)
            prefix = user_part[:2] if len(user_part) >= 2 else user_part
            return f"{prefix}***@{domain}"
        return LGPDMasker.mask_cpf_or_doc(raw)

    @staticmethod
    def pii_audit_hash(value: str) -> str:
        return hashlib.sha256(str(value).strip().lower().encode("utf-8")).hexdigest()[:16]

    @classmethod
    def sanitize_transaction(cls, tx: Dict[str, Any], mask_active: bool = True) -> Dict[str, Any]:
        tx_copy = dict(tx)
        comprador_orig = str(tx_copy.get("comprador", "ANONIMO"))
        tx_copy["pii_token_lgpd"] = f"lgpd_{cls.pii_audit_hash(comprador_orig)}"
        if mask_active:
            tx_copy["comprador"] = cls.mask_name(comprador_orig)
        return tx_copy


class MeridianAuthManager:
    MAX_LOGIN_ATTEMPTS: int = 3

    PRESET_THEMES = {
        "Cyber Blue (Azul Royal & Ciano)": {
            "brand_name": "MERIDIAN",
            "brand_subtitle": "Fintech ERP • Gestao Corporativa, Split & AppSec",
            "badge_text": "ENTERPRISE FINTECH SUITE • SHA-256",
            "logo_emoji": "M",
            "primary_color": "#0284c7",
            "secondary_color": "#2563eb",
            "accent_color": "#38bdf8",
            "lgpd_masking_default": True
        },
        "Emerald Corporate (Verde Esmeralda Executivo)": {
            "brand_name": "MERIDIAN CORP",
            "brand_subtitle": "Gestao de Equipes, Split Comercial & Auditoria LGPD",
            "badge_text": "CORPORATE FINTECH ERP • LGPD COMPLIANT",
            "logo_emoji": "E",
            "primary_color": "#059669",
            "secondary_color": "#047857",
            "accent_color": "#34d399",
            "lgpd_masking_default": True
        },
        "Royal Indigo (Roxo / Indigo SaaS)": {
            "brand_name": "NEXUS ENTERPRISE",
            "brand_subtitle": "Motor de Split Multi-Beneficiarios & BPO Financeiro",
            "badge_text": "MULTI-SPLIT ENGINE • REAL-TIME PAYOUTS",
            "logo_emoji": "N",
            "primary_color": "#6366f1",
            "secondary_color": "#4338ca",
            "accent_color": "#a855f7",
            "lgpd_masking_default": True
        },
        "Amber Gold (Dourado / Private Banking)": {
            "brand_name": "ALPHABANK ERP",
            "brand_subtitle": "Conciliacao Contabil Automatizada, DRE & Custodia SHA-256",
            "badge_text": "PRIVATE FINANCIAL SUITE • DECIMAL PRECISION",
            "logo_emoji": "A",
            "primary_color": "#d97706",
            "secondary_color": "#b45309",
            "accent_color": "#fbbf24",
            "lgpd_masking_default": True
        },
        "Crimson Ruby (Vermelho Corporativo)": {
            "brand_name": "VANGUARD PAY",
            "brand_subtitle": "Plataforma Multi-Tenant de Faturamento e Comissoes",
            "badge_text": "HIGH SECURITY FINTECH • SHA-256",
            "logo_emoji": "V",
            "primary_color": "#e11d48",
            "secondary_color": "#be123c",
            "accent_color": "#fb7185",
            "lgpd_masking_default": True
        },
        "Titanium Slate (Grafite Minimalista)": {
            "brand_name": "TITANIUM ERP",
            "brand_subtitle": "Controle de Caixa, Comissoes e Governanca Corporativa",
            "badge_text": "ENTERPRISE CORE • ZERO-TRUST",
            "logo_emoji": "T",
            "primary_color": "#475569",
            "secondary_color": "#334155",
            "accent_color": "#94a3b8",
            "lgpd_masking_default": True
        }
    }

    def __init__(
        self,
        engine: FintechEngine,
        monitor: Optional[IntegrityMonitor] = None,
        base_dir: str = "."
    ):
        self.engine = engine
        self.monitor = monitor or IntegrityMonitor()
        base = Path(base_dir)
        self.users_file = base / "lojistas_auth.json"
        self.payouts_file = base / "saques_pix.json"
        self.links_file = base / "links_pagamento.json"
        self.whitelabel_file = base / "whitelabel_config.json"
        self.lockouts_file = base / "security_lockouts.json"
        self.email_dispatcher = SecurityEmailDispatcher(base_dir=str(base))
        self.last_auth_event: Dict[str, Any] = {}
        self._ensure_default_users()

    @staticmethod
    def _hash_password(password: str, salt_hex: Optional[str] = None) -> tuple[str, str]:
        salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
        pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
        return pw_hash.hex(), salt.hex()

    def _verify_password(self, password: str, stored_hash: str, salt_hex: str) -> bool:
        calculated_hash, _ = self._hash_password(password, salt_hex)
        return hmac.compare_digest(calculated_hash, stored_hash)

    def _ensure_default_users(self) -> None:
        users = self._load_users() if self.users_file.exists() else {}
        changed = False

        def _upsert_default_corporate(uname: str, pw: str, **kwargs):
            nonlocal changed
            if uname not in users:
                pw_h, s_h = self._hash_password(pw)
                users[uname] = MerchantUser(
                    username=uname,
                    api_key=f"mrd_live_{secrets.token_hex(12)}",
                    password_hash=pw_h,
                    salt=s_h,
                    **kwargs
                ).model_dump(mode="json")
                changed = True
            else:
                for k in ("nome_exibicao", "cargo", "role", "clinica_id", "vendedor_id"):
                    if k in kwargs and users[uname].get(k) != kwargs[k]:
                        users[uname][k] = str(kwargs[k]) if isinstance(kwargs[k], Decimal) else kwargs[k]
                        changed = True
                for k, v in kwargs.items():
                    if k not in users[uname]:
                        users[uname][k] = str(v) if isinstance(v, Decimal) else v
                        changed = True

        _upsert_default_corporate(
            "admin", "admin123",
            nome_exibicao="Diretoria / Proprietario (Master Admin)",
            role="ADMIN",
            cargo="Admin / Proprietario",
            clinica_id="ALL",
            vendedor_id="ALL",
            comissao_padrao_pct=Decimal("5.00"),
            chave_pix="tesouraria@meridian.com.br",
            email_alerta="seguranca@meridian.com.br",
            telefone_sms="+55 (11) 9****-0001"
        )
        _upsert_default_corporate(
            "vendedor_a", "lojista123",
            nome_exibicao="Unidade Alpha Tech (Filial A)",
            role="MERCHANT",
            cargo="Gerente de Unidade",
            clinica_id="VENDEDOR_A",
            vendedor_id="VENDEDOR_A",
            comissao_padrao_pct=Decimal("75.00"),
            chave_pix="financeiro@alphatech.com.br",
            email_alerta="financeiro@alphatech.com.br",
            telefone_sms="+55 (11) 9****-1020"
        )
        _upsert_default_corporate(
            "vendedor_b", "lojista123",
            nome_exibicao="Grupo Prime Enterprise (Matriz)",
            role="MERCHANT",
            cargo="Supervisor / Diretor de Unidade",
            clinica_id="VENDEDOR_B",
            vendedor_id="VENDEDOR_B",
            comissao_padrao_pct=Decimal("50.00"),
            chave_pix="repasse@grupoprime.com.br",
            email_alerta="diretoria@grupoprime.com.br",
            telefone_sms="+55 (11) 9****-3040"
        )
        _upsert_default_corporate(
            "dr_cirurgiao", "parceiro123",
            nome_exibicao="Marcos Oliveira (Vendedor / Comissionado)",
            role="PARTNER",
            cargo="Comissionado / Executivo de Contas",
            clinica_id="VENDEDOR_B",
            vendedor_id="DR_CIRURGIAO",
            comissao_padrao_pct=Decimal("35.00"),
            chave_pix="marcos.comercial@empresa.com.br",
            email_alerta="marcos.comercial@empresa.com.br",
            telefone_sms="+55 (11) 9****-5566"
        )
        _upsert_default_corporate(
            "lab_analises", "parceiro123",
            nome_exibicao="Carlos Mendes (Supervisor Operacional)",
            role="AUDITOR",
            cargo="Supervisor / Auditoria",
            clinica_id="VENDEDOR_B",
            vendedor_id="LAB_ANALISES",
            comissao_padrao_pct=Decimal("10.00"),
            chave_pix="supervisor@empresa.com.br",
            email_alerta="supervisor@empresa.com.br",
            telefone_sms="+55 (11) 9****-7788"
        )
        _upsert_default_corporate(
            "recepcao_prime", "equipe123",
            nome_exibicao="Juliana Costa (Atendente / Operacional)",
            role="STAFF",
            cargo="Atendente / Caixa",
            clinica_id="VENDEDOR_B",
            vendedor_id="VENDEDOR_B",
            comissao_padrao_pct=Decimal("0.00"),
            chave_pix="nao_habilitado_para_saque",
            email_alerta="diretoria@grupoprime.com.br",
            telefone_sms="+55 (11) 9****-9900"
        )

        if changed or not self.users_file.exists():
            self._save_users(users)

        if not self.payouts_file.exists():
            self._save_payouts([])

        if not self.links_file.exists():
            self._save_payment_links([])

        if not self.whitelabel_file.exists():
            self.save_whitelabel_config(WhiteLabelConfig())

        if not self.lockouts_file.exists():
            self._save_lockouts({"failed_attempts": {}, "blocked_users": [], "sms_unlock_codes": {}})

    def _load_lockouts(self) -> Dict[str, Any]:
        if not self.lockouts_file.exists():
            return {"failed_attempts": {}, "blocked_users": [], "sms_unlock_codes": {}}
        try:
            with open(self.lockouts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                "failed_attempts": data.get("failed_attempts", {}),
                "blocked_users": data.get("blocked_users", []),
                "sms_unlock_codes": data.get("sms_unlock_codes", {})
            }
        except Exception:
            return {"failed_attempts": {}, "blocked_users": [], "sms_unlock_codes": {}}

    def _save_lockouts(self, data: Dict[str, Any]) -> None:
        with open(self.lockouts_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.monitor.add_path(str(self.lockouts_file))

    def get_failed_attempts_count(self, username: str) -> int:
        uname = str(username or "").strip().lower()
        data = self._load_lockouts()
        return int(data["failed_attempts"].get(uname, 0))

    def is_user_locked(self, username: str) -> bool:
        uname = str(username or "").strip().lower()
        data = self._load_lockouts()
        return uname in data["blocked_users"] or int(data["failed_attempts"].get(uname, 0)) >= self.MAX_LOGIN_ATTEMPTS

    def get_active_sms_unlock_code(self, username: str) -> Optional[str]:
        uname = str(username or "").strip().lower()
        data = self._load_lockouts()
        return data.get("sms_unlock_codes", {}).get(uname)

    def reissue_sms_unlock_code(self, username: str, length: int = 7, alphanumeric: bool = True) -> str:
        uname = str(username or "").strip().lower()
        data = self._load_lockouts()
        new_code = self.email_dispatcher.generate_sms_verification_code(length=length, alphanumeric=alphanumeric)
        data.setdefault("sms_unlock_codes", {})[uname] = new_code
        self._save_lockouts(data)
        return new_code

    def verify_sms_and_unlock(self, username: str, code_input: str, security_agent: Optional[Any] = None) -> bool:
        uname = str(username or "").strip().lower()
        clean_code = str(code_input or "").strip().upper()

        if not (6 <= len(clean_code) <= 8) or not clean_code.isalnum():
            return False

        data = self._load_lockouts()
        expected_code = str(data.get("sms_unlock_codes", {}).get(uname, "")).strip().upper()
        if not expected_code:
            return False

        if hmac.compare_digest(clean_code, expected_code):
            self.unlock_user_account(uname, security_agent=security_agent)
            return True
        return False

    def unlock_user_account(self, username: str, security_agent: Optional[Any] = None) -> None:
        uname = str(username or "").strip().lower()
        data = self._load_lockouts()
        data["failed_attempts"][uname] = 0
        if uname in data["blocked_users"]:
            data["blocked_users"].remove(uname)
        if uname in data.get("sms_unlock_codes", {}):
            del data["sms_unlock_codes"][uname]
        self._save_lockouts(data)

        if security_agent:
            if hasattr(security_agent, "failed_attempts"):
                security_agent.failed_attempts[uname] = 0
            if hasattr(security_agent, "blocked_identifiers") and uname in security_agent.blocked_identifiers:
                security_agent.blocked_identifiers.remove(uname)

        self.email_dispatcher.log_siem_event(
            event_type="ACCOUNT_UNLOCKED_VERIFIED",
            severity="INFO",
            username=uname,
            details=f"Conta '{uname}' desbloqueada apos verificacao de seguranca."
        )

    def _record_failed_attempt(
        self,
        uname: str,
        recipient_email: str,
        security_agent: Optional[Any] = None,
        reason: str = "Credenciais invalidas informadas no Portal de Login"
    ) -> Dict[str, Any]:
        lock_data = self._load_lockouts()
        atual = int(lock_data["failed_attempts"].get(uname, 0)) + 1
        lock_data["failed_attempts"][uname] = atual

        locked_now = atual >= self.MAX_LOGIN_ATTEMPTS
        email_sent = None
        sms_code = None

        if locked_now:
            if uname not in lock_data["blocked_users"]:
                lock_data["blocked_users"].append(uname)
            sms_code = lock_data.get("sms_unlock_codes", {}).get(uname)
            if not sms_code:
                sms_code = self.email_dispatcher.generate_sms_verification_code(length=7, alphanumeric=True)
                lock_data.setdefault("sms_unlock_codes", {})[uname] = sms_code

        self._save_lockouts(lock_data)

        if security_agent:
            security_agent.register_access_attempt(uname, failed=True)

        if locked_now:
            email_sent = self.email_dispatcher.send_third_strike_lockout_email(
                username=uname,
                recipient_email=recipient_email,
                sms_unlock_code=sms_code,
                max_attempts=self.MAX_LOGIN_ATTEMPTS,
                reason=reason
            )
        else:
            self.email_dispatcher.log_siem_event(
                event_type="LOGIN_ATTEMPT_FAILED",
                severity="WARNING",
                username=uname,
                details=f"Tentativa falha {atual}/{self.MAX_LOGIN_ATTEMPTS} registrada (e-mail sera disparado na 3a falha)."
            )

        self.last_auth_event = {
            "success": False,
            "username": uname,
            "attempts": atual,
            "max_attempts": self.MAX_LOGIN_ATTEMPTS,
            "remaining": max(0, self.MAX_LOGIN_ATTEMPTS - atual),
            "locked": locked_now,
            "sms_unlock_code": sms_code,
            "email_dispatched": email_sent,
            "reason": reason
        }
        return self.last_auth_event

    def authenticate(self, username: str, password: str, security_agent: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        ok_u, msg_u = OWASPShield.inspect_input(username, "username")
        ok_p, msg_p = OWASPShield.inspect_input(password, "password")
        uname = str(username or "").strip().lower()

        if not ok_u or not ok_p:
            motivo_owasp = msg_u if not ok_u else msg_p
            raise PermissionError(f"Bloqueio de seguranca OWASP WAF: {motivo_owasp}")

        users = self._load_users()
        user_data = users.get(uname)
        email_destino = (
            user_data.get("email_alerta") or user_data.get("chave_pix")
            if user_data and "@" in str(user_data.get("chave_pix", ""))
            else "seguranca@meridian.com.br"
        )

        if self.is_user_locked(uname):
            sms_code = self.get_active_sms_unlock_code(uname) or self.reissue_sms_unlock_code(uname, 7, True)
            self.last_auth_event = {
                "success": False,
                "username": uname,
                "attempts": self.MAX_LOGIN_ATTEMPTS,
                "max_attempts": self.MAX_LOGIN_ATTEMPTS,
                "remaining": 0,
                "locked": True,
                "sms_unlock_code": sms_code,
                "email_dispatched": None
            }
            raise PermissionError(
                f"ALERTA DE SEGURANCA: A conta '{uname}' encontra-se bloqueada apos {self.MAX_LOGIN_ATTEMPTS} tentativas "
                f"sem sucesso. Se nao foi voce, sua conta esta protegida e bloqueada por seguranca. Para realizar o "
                f"desbloqueio, informe abaixo o codigo de verificacao SMS de 6 a 8 digitos (numerico ou alfanumerico)."
            )

        if not user_data or not user_data.get("ativo", True):
            ev = self._record_failed_attempt(
                uname=uname,
                recipient_email=email_destino,
                security_agent=security_agent,
                reason="Tentativa de acesso em conta nao localizada ou inativa"
            )
            if ev["locked"]:
                raise PermissionError(
                    f"ALERTA DE SEGURANCA: Limite de {self.MAX_LOGIN_ATTEMPTS} tentativas excedido para '{uname}'. "
                    f"Uma notificacao de seguranca foi enviada para {ev['email_dispatched']['to']}. Se nao foi voce, "
                    f"a conta foi bloqueada preventivamente por seguranca. Utilize o codigo SMS de 6 a 8 digitos para desbloquear."
                )
            return None

        if self._verify_password(password, user_data["password_hash"], user_data["salt"]):
            lock_data = self._load_lockouts()
            lock_data["failed_attempts"][uname] = 0
            if uname in lock_data.get("sms_unlock_codes", {}):
                del lock_data["sms_unlock_codes"][uname]
            self._save_lockouts(lock_data)
            if security_agent:
                security_agent.register_access_attempt(uname, failed=False)
            self.last_auth_event = {"success": True, "username": uname, "attempts": 0}
            return user_data

        ev = self._record_failed_attempt(
            uname=uname,
            recipient_email=email_destino,
            security_agent=security_agent,
            reason="Falha de autenticacao por senha incorreta"
        )
        if ev["locked"]:
            raise PermissionError(
                f"ALERTA DE SEGURANCA: Falha na 3a tentativa de login. Uma notificacao oficial de bloqueio foi enviada "
                f"por e-mail para {ev['email_dispatched']['to']}. Se nao foi voce, sua conta esta bloqueada por seguranca. "
                f"Para realizar o desbloqueio, conclua a verificacao abaixo com o codigo SMS de 6 a 8 digitos."
            )
        return None

    def _load_users(self) -> Dict[str, Dict[str, Any]]:
        try:
            with open(self.users_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_users(self, users: Dict[str, Dict[str, Any]]) -> None:
        with open(self.users_file, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, default=str, ensure_ascii=False)
        self.monitor.add_path(str(self.users_file))

    def load_payouts(self, vendedor_id: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            with open(self.payouts_file, "r", encoding="utf-8") as f:
                payouts = json.load(f)
        except Exception:
            payouts = []

        if vendedor_id and vendedor_id != "ALL":
            return [p for p in payouts if p.get("vendedor_id") == vendedor_id]
        return payouts

    def _save_payouts(self, payouts: List[Dict[str, Any]]) -> None:
        with open(self.payouts_file, "w", encoding="utf-8") as f:
            json.dump(payouts, f, indent=2, default=str, ensure_ascii=False)
        self.monitor.add_path(str(self.payouts_file))

    def load_payment_links(self, vendedor_id: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            with open(self.links_file, "r", encoding="utf-8") as f:
                links = json.load(f)
        except Exception:
            links = []

        if vendedor_id and vendedor_id != "ALL":
            return [lnk for lnk in links if lnk.get("vendedor_id") == vendedor_id]
        return links

    def _save_payment_links(self, links: List[Dict[str, Any]]) -> None:
        with open(self.links_file, "w", encoding="utf-8") as f:
            json.dump(links, f, indent=2, default=str, ensure_ascii=False)
        self.monitor.add_path(str(self.links_file))

    def load_whitelabel_config(self) -> WhiteLabelConfig:
        try:
            with open(self.whitelabel_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return WhiteLabelConfig(**data)
        except Exception:
            return WhiteLabelConfig()

    def save_whitelabel_config(self, config: WhiteLabelConfig) -> WhiteLabelConfig:
        with open(self.whitelabel_file, "w", encoding="utf-8") as f:
            json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)
        self.monitor.add_path(str(self.whitelabel_file))
        return config

    def register_merchant(
        self,
        username: str,
        password: str,
        nome_exibicao: str,
        vendedor_id: str,
        chave_pix: str,
        role: str = "MERCHANT",
        cargo: str = "Admin / Gerente",
        clinica_id: Optional[str] = None,
        comissao_padrao_pct: Any = "0.00",
        email_alerta: Optional[str] = None
    ) -> Dict[str, Any]:
        for campo, val in [("username", username), ("nome_exibicao", nome_exibicao), ("chave_pix", chave_pix)]:
            ok, motivo = OWASPShield.inspect_input(val, campo)
            if not ok:
                raise ValueError(motivo)

        uname = username.strip().lower()
        users = self._load_users()
        if uname in users:
            raise ValueError(f"O login '{uname}' ja esta em uso.")

        vid_clean = vendedor_id.strip().upper()
        clinica_clean = (clinica_id or vid_clean).strip().upper()
        pw_hash, salt = self._hash_password(password)
        alert_mail = email_alerta or (chave_pix.strip() if "@" in chave_pix else "seguranca@meridian.com.br")

        novo = MerchantUser(
            username=uname,
            nome_exibicao=nome_exibicao.strip(),
            role=role,
            cargo=cargo.strip(),
            clinica_id=clinica_clean,
            vendedor_id=vid_clean,
            comissao_padrao_pct=MoneyCalculator.to_decimal(comissao_padrao_pct),
            chave_pix=chave_pix.strip(),
            email_alerta=alert_mail,
            api_key=f"mrd_live_{secrets.token_hex(12)}",
            password_hash=pw_hash,
            salt=salt
        ).model_dump(mode="json")

        users[uname] = novo
        self._save_users(users)

        if role in ("MERCHANT", "PARTNER") and vid_clean != "ALL":
            wallets = self.engine.get_all_wallets()
            if vid_clean not in wallets:
                self.engine.wallet_manager.wallets[vid_clean] = Decimal("0.00")
                self.engine.db.save_wallets(self.engine.wallet_manager.wallets)

        return novo

    def get_clinic_team_members(self, user_session: Dict[str, Any]) -> List[Dict[str, Any]]:
        users = self._load_users()
        is_admin = (user_session.get("role") == "ADMIN" or user_session.get("vendedor_id") == "ALL")
        my_unit = user_session.get("clinica_id") or user_session.get("vendedor_id")

        team = []
        for u in users.values():
            if is_admin or u.get("clinica_id") == my_unit or u.get("vendedor_id") == my_unit:
                team.append(u)
        return team

    def get_tenant_transactions(self, user_session: Dict[str, Any]) -> List[Dict[str, Any]]:
        all_tx = self.engine.get_all_transactions()
        role = user_session.get("role", "MERCHANT")
        vid = user_session.get("vendedor_id", "ALL")
        clinica_id = user_session.get("clinica_id", vid)

        if role == "ADMIN" or vid == "ALL":
            return all_tx

        filtered = []
        for tx in all_tx:
            tx_vid = tx.get("vendedor_id")
            multi_recs = tx.get("metadata", {}).get("multi_split_breakdown", [])

            if role == "PARTNER":
                matching_slice = next((r for r in multi_recs if r.get("vendedor_id") == vid), None)
                if matching_slice:
                    tx_copy = dict(tx)
                    sp_copy = dict(tx.get("split", {}))
                    sp_copy["vendedor"] = str(matching_slice.get("valor_liquido", "0.00"))
                    tx_copy["split"] = sp_copy
                    tx_copy["vendedor_id"] = f"{vid} ({matching_slice.get('percentual', '0')}%)"
                    filtered.append(tx_copy)
                elif tx_vid == vid:
                    filtered.append(dict(tx))
            else:
                if tx_vid in (vid, clinica_id) or any(r.get("vendedor_id") in (vid, clinica_id) for r in multi_recs):
                    filtered.append(dict(tx))

        return filtered

    def get_tenant_wallets(self, user_session: Dict[str, Any]) -> Dict[str, Decimal]:
        role = user_session.get("role", "MERCHANT")
        if role == "STAFF":
            return {}

        all_wallets = self.engine.get_all_wallets()
        if not all_wallets and hasattr(self.engine, "db"):
            all_wallets = self.engine.db.load_wallets()

        vid = user_session.get("vendedor_id", "ALL")
        if role == "ADMIN" or vid == "ALL":
            return all_wallets

        if role == "PARTNER":
            return {vid: all_wallets.get(vid, Decimal("0.00"))}

        my_team = self.get_clinic_team_members(user_session)
        allowed_vids = {vid}
        for member in my_team:
            m_vid = member.get("vendedor_id")
            if m_vid and m_vid != "ALL":
                allowed_vids.add(m_vid)

        return {k: all_wallets.get(k, Decimal("0.00")) for k in sorted(allowed_vids)}

    def request_payout(
        self,
        vendedor_id: str,
        valor: Any,
        chave_pix: str,
        antecipacao_imediata: bool = False
    ) -> PayoutRequest:
        ok_pix, motivo = OWASPShield.inspect_input(chave_pix, "chave_pix")
        if not ok_pix:
            raise ValueError(motivo)

        val_dec = MoneyCalculator.to_decimal(valor)
        if val_dec <= Decimal("0.00"):
            raise ValueError("O valor do saque deve ser maior que zero.")

        wallets = self.engine.get_all_wallets()
        if not wallets and hasattr(self.engine, "db"):
            wallets = self.engine.db.load_wallets()

        saldo_atual = MoneyCalculator.to_decimal(wallets.get(vendedor_id, Decimal("0.00")))
        if val_dec > saldo_atual:
            raise ValueError(f"Saldo insuficiente na carteira de {vendedor_id} (Disponivel: R$ {float(saldo_atual):,.2f}).")

        if antecipacao_imediata:
            taxa_ant = MoneyCalculator.percentage_of(val_dec, Decimal("2.50"))
            modalidade = "ANTECIPACAO_IMEDIATA"
        else:
            taxa_ant = Decimal("0.00")
            modalidade = "NORMAL_D1"

        liquido_pix = MoneyCalculator.subtract(val_dec, taxa_ant)

        novo_saldo = MoneyCalculator.subtract(saldo_atual, val_dec)
        self.engine.wallet_manager.wallets[vendedor_id] = novo_saldo
        self.engine.db.save_wallets(self.engine.wallet_manager.wallets)

        payout = PayoutRequest(
            vendedor_id=vendedor_id,
            valor_solicitado=val_dec,
            taxa_antecipacao=taxa_ant,
            valor_liquido_pix=liquido_pix,
            chave_pix_destino=chave_pix,
            modalidade=modalidade,
            status="PAID"
        )

        historico = self.load_payouts()
        historico.append(payout.model_dump())
        self._save_payouts(historico)
        return payout

    def create_payment_link(
        self,
        vendedor_id: str,
        cliente_nome: str,
        cliente_whatsapp: str,
        descricao: str,
        valor: Any,
        metodo_preferencial: str = "PIX",
        vencimento: str = "24 horas"
    ) -> PaymentLinkInvoice:
        for c_name, c_val in [("cliente_nome", cliente_nome), ("descricao", descricao)]:
            ok, motivo = OWASPShield.inspect_input(c_val, c_name)
            if not ok:
                raise ValueError(motivo)

        val_dec = MoneyCalculator.to_decimal(valor)
        if val_dec <= Decimal("0.00"):
            raise ValueError("O valor da cobranca deve ser maior que zero.")

        tx_id = generate_transaction_id()
        link_id = f"LNK_{uuid.uuid4().hex[:8].upper()}"

        plat_val = MoneyCalculator.percentage_of(val_dec, self.engine.split_rules.taxa_plataforma_pct)
        vend_val = MoneyCalculator.percentage_of(val_dec, self.engine.split_rules.comissao_vendedor_pct)
        forn_val = MoneyCalculator.subtract(val_dec, MoneyCalculator.add(plat_val, vend_val))

        all_tx = self.engine.get_all_transactions()
        all_tx.append({
            "id": tx_id,
            "valor_bruto": str(val_dec),
            "metodo_pagamento": metodo_preferencial.upper(),
            "status": "PENDING",
            "comprador": cliente_nome.strip() or "CLIENTE_LINK",
            "vendedor_id": vendedor_id.strip(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "split": {
                "plataforma": str(plat_val),
                "vendedor": str(vend_val),
                "fornecedor": str(forn_val)
            },
            "metadata": {
                "origem": "payment_link_whatsapp",
                "link_id": link_id,
                "descricao": descricao.strip(),
                "whatsapp": cliente_whatsapp.strip(),
                "pii_hash_lgpd": LGPDMasker.pii_audit_hash(cliente_nome)
            }
        })
        self.engine.db.save_transactions(all_tx)

        pix_emv = (
            f"00020126580014BR.GOV.BCB.PIX0136{tx_id}"
            f"5204000053039865406{float(val_dec):.2f}5802BR5915MERIDIAN_FINTECH6009SAO_PAULO"
        )
        url_checkout = f"https://pay.meridian.erp/checkout/{link_id}"

        invoice = PaymentLinkInvoice(
            link_id=link_id,
            transaction_id=tx_id,
            vendedor_id=vendedor_id.strip(),
            cliente_nome=cliente_nome.strip() or "Cliente",
            cliente_whatsapp=cliente_whatsapp.strip() or "5511999999999",
            descricao=descricao.strip() or "Pedido / Contrato Comercial",
            valor=val_dec,
            metodo_preferencial=metodo_preferencial.upper(),
            vencimento=vencimento,
            url_checkout=url_checkout,
            pix_copia_e_cola=pix_emv,
            status="PENDING"
        )

        links = self.load_payment_links()
        links.append(invoice.model_dump())
        self._save_payment_links(links)
        return invoice

    def get_user_by_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        key_clean = api_key.strip()
        users = self._load_users()
        for udata in users.values():
            if hmac.compare_digest(str(udata.get("api_key", "")), key_clean):
                return udata
        return None

    def settle_pending_transaction(self, transaction_id: str) -> Dict[str, Any]:
        all_tx = self.engine.get_all_transactions()
        target_tx = None

        for tx in all_tx:
            if tx.get("id") == transaction_id:
                target_tx = tx
                break

        if not target_tx:
            raise ValueError(f"Transacao '{transaction_id}' nao localizada no Ledger.")

        if target_tx.get("status") == "PAID":
            return target_tx

        if target_tx.get("status") != "PENDING":
            raise ValueError(f"Status '{target_tx.get('status')}' nao permite liquidacao via Webhook.")

        valor_bruto = MoneyCalculator.to_decimal(target_tx.get("valor_bruto", "0.00"))
        split_data = target_tx.get("split", {})
        if not split_data or "vendedor" not in split_data:
            plat_val = MoneyCalculator.percentage_of(valor_bruto, self.engine.split_rules.taxa_plataforma_pct)
            vend_val = MoneyCalculator.percentage_of(valor_bruto, self.engine.split_rules.comissao_vendedor_pct)
            forn_val = MoneyCalculator.subtract(valor_bruto, MoneyCalculator.add(plat_val, vend_val))
            split_data = {
                "plataforma": str(plat_val),
                "vendedor": str(vend_val),
                "fornecedor": str(forn_val)
            }
            target_tx["split"] = split_data

        target_tx["status"] = "PAID"
        target_tx["paid_at"] = datetime.now(timezone.utc).isoformat()
        self.engine.db.save_transactions(all_tx)

        vid = target_tx.get("vendedor_id", "VENDEDOR_A")
        repasse_vendedor = MoneyCalculator.to_decimal(split_data["vendedor"])
        wallets = self.engine.get_all_wallets()
        if not wallets and hasattr(self.engine, "db"):
            wallets = self.engine.db.load_wallets()

        saldo_atual = MoneyCalculator.to_decimal(wallets.get(vid, Decimal("0.00")))
        novo_saldo = MoneyCalculator.add(saldo_atual, repasse_vendedor)
        self.engine.wallet_manager.wallets[vid] = novo_saldo
        self.engine.db.save_wallets(self.engine.wallet_manager.wallets)

        links = self.load_payment_links()
        alterou_link = False
        for lnk in links:
            if lnk.get("transaction_id") == transaction_id:
                lnk["status"] = "PAID"
                alterou_link = True
        if alterou_link:
            self._save_payment_links(links)

        return target_tx

    def execute_multi_beneficiary_split(
        self,
        valor_bruto: Any,
        metodo_pagamento: str,
        comprador: str,
        descricao_contrato: str,
        taxa_plataforma_pct: Any,
        beneficiarios: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        for c_name, c_val in [("comprador", comprador), ("descricao_contrato", descricao_contrato)]:
            ok, motivo = OWASPShield.inspect_input(c_val, c_name)
            if not ok:
                raise ValueError(motivo)

        val_dec = MoneyCalculator.to_decimal(valor_bruto)
        if val_dec <= Decimal("0.00"):
            raise ValueError("O valor bruto deve ser maior que zero.")

        taxa_plat_dec = MoneyCalculator.to_decimal(taxa_plataforma_pct)
        soma_benef_pct = sum(
            (MoneyCalculator.to_decimal(b.get("percentual", "0.00")) for b in beneficiarios),
            Decimal("0.00")
        )
        soma_total_pct = MoneyCalculator.add(taxa_plat_dec, soma_benef_pct)

        if soma_total_pct != Decimal("100.00"):
            raise ValueError(
                f"A soma da Taxa da Plataforma ({taxa_plat_dec}%) + Beneficiarios ({soma_benef_pct}%) "
                f"deve ser exatamente 100.00% (Atual: {soma_total_pct}%)."
            )

        if not beneficiarios:
            raise ValueError("Informe ao menos 1 beneficiario para o Multi-Split.")

        plat_valor = MoneyCalculator.percentage_of(val_dec, taxa_plat_dec)
        distribuido_benef = Decimal("0.00")
        breakdown = []

        for b in beneficiarios:
            vid = str(b.get("vendedor_id", "PARCEIRO")).strip().upper()
            papel = str(b.get("papel", "Comissionado")).strip()
            pct = MoneyCalculator.to_decimal(b.get("percentual", "0.00"))
            fatia_val = MoneyCalculator.percentage_of(val_dec, pct)
            distribuido_benef = MoneyCalculator.add(distribuido_benef, fatia_val)
            breakdown.append({
                "vendedor_id": vid,
                "papel": papel,
                "percentual": str(pct),
                "valor_liquido": fatia_val
            })

        soma_valores = MoneyCalculator.add(plat_valor, distribuido_benef)
        diferenca_centavos = MoneyCalculator.subtract(val_dec, soma_valores)
        if diferenca_centavos != Decimal("0.00"):
            breakdown[0]["valor_liquido"] = MoneyCalculator.add(
                breakdown[0]["valor_liquido"],
                diferenca_centavos
            )
            distribuido_benef = MoneyCalculator.add(distribuido_benef, diferenca_centavos)

        wallets = self.engine.get_all_wallets()
        if not wallets and hasattr(self.engine, "db"):
            wallets = self.engine.db.load_wallets()

        for item in breakdown:
            vid = item["vendedor_id"]
            val_credito = item["valor_liquido"]
            saldo_ant = MoneyCalculator.to_decimal(wallets.get(vid, Decimal("0.00")))
            novo_saldo = MoneyCalculator.add(saldo_ant, val_credito)
            wallets[vid] = novo_saldo
            self.engine.wallet_manager.wallets[vid] = novo_saldo
            item["valor_liquido"] = str(val_credito)

        self.engine.db.save_wallets(self.engine.wallet_manager.wallets)

        tx_id = generate_transaction_id()
        vendedor_principal = breakdown[0]["vendedor_id"]

        tx_record = {
            "id": tx_id,
            "valor_bruto": str(val_dec),
            "metodo_pagamento": metodo_pagamento.upper(),
            "status": "PAID",
            "comprador": comprador.strip() or "CLIENTE_MULTISPLIT",
            "vendedor_id": vendedor_principal,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "split": {
                "plataforma": str(plat_valor),
                "vendedor": str(distribuido_benef),
                "fornecedor": "0.00"
            },
            "metadata": {
                "origem": "multi_beneficiary_split",
                "contrato": descricao_contrato,
                "pii_hash_lgpd": LGPDMasker.pii_audit_hash(comprador),
                "multi_split_breakdown": breakdown
            }
        }

        all_tx = self.engine.get_all_transactions()
        all_tx.append(tx_record)
        self.engine.db.save_transactions(all_tx)

        return {
            "transaction_id": tx_id,
            "valor_bruto": str(val_dec),
            "taxa_plataforma": str(plat_valor),
            "total_beneficiarios": str(distribuido_benef),
            "beneficiarios": breakdown,
            "contrato": descricao_contrato
        }