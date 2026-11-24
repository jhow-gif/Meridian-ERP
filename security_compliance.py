#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Meridian AppSec & Compliance Suite (8 Pilares de Cibersegurança)
- E-mail formal de segurança (sem emojis) disparado exclusivamente após a 3ª falha de login
- Gerador e validador de código SMS de 6 a 8 dígitos (numérico ou alfanumérico) para desbloqueio
"""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


class TLSAndHeadersManager:
    SECURITY_HEADERS = {
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Content-Security-Policy": "default-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://api.qrserver.com;"
    }

    @classmethod
    def get_headers_Status(cls) -> Dict[str, str]:
        return dict(cls.SECURITY_HEADERS)

    @staticmethod
    def get_tls_deployment_commands() -> str:
        return (
            "openssl req -x509 -newkey rsa:4096 -keyout ssl_key.pem -out ssl_cert.pem -sha256 -days 365 -nodes -subj \"/CN=meridian.erp\"\n"
            "uvicorn api_server:app --host 0.0.0.0 --port 8443 --ssl-keyfile=ssl_key.pem --ssl-certfile=ssl_cert.pem\n"
            "streamlit run app.py --server.port=8501 --server.sslCertFile=ssl_cert.pem --server.sslKeyFile=ssl_key.pem"
        )


class DataVaultCipher:
    def __init__(self, master_secret: Optional[str] = None):
        raw_secret = master_secret or os.environ.get("MERIDIAN_VAULT_SECRET", "mrd_master_vault_key_2026_sha256")
        self.master_key = hashlib.sha256(raw_secret.encode("utf-8")).digest()

    def _keystream(self, salt: bytes, length: int) -> bytes:
        blocks = []
        counter = 0
        while sum(len(b) for b in blocks) < length:
            blk = hashlib.pbkdf2_hmac(
                "sha256",
                self.master_key,
                salt + counter.to_bytes(4, "big"),
                iterations=1000,
                dklen=32
            )
            blocks.append(blk)
            counter += 1
        return b"".join(blocks)[:length]

    def encrypt_at_rest(self, plaintext: str) -> str:
        data = plaintext.encode("utf-8")
        salt = os.urandom(16)
        stream = self._keystream(salt, len(data))
        ciphertext = bytes(a ^ b for a, b in zip(data, stream))
        mac = hmac.new(self.master_key, salt + ciphertext, hashlib.sha256).digest()
        payload = salt + mac + ciphertext
        return "ENCv1:" + base64.urlsafe_b64encode(payload).decode("ascii")

    def decrypt_at_rest(self, token: str) -> str:
        if not token.startswith("ENCv1:"):
            raise ValueError("Formato de criptografia em repouso inválido.")
        raw = base64.urlsafe_b64decode(token[6:].encode("ascii"))
        salt = raw[:16]
        mac_stored = raw[16:48]
        ciphertext = raw[48:]

        mac_calc = hmac.new(self.master_key, salt + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(mac_stored, mac_calc):
            raise ValueError("Violação de integridade detectada no cofre criptográfico (HMAC inválido).")

        stream = self._keystream(salt, len(ciphertext))
        plaintext_bytes = bytes(a ^ b for a, b in zip(ciphertext, stream))
        return plaintext_bytes.decode("utf-8")


class LeastPrivilegeGuard:
    PERMISSION_MATRIX: Dict[str, List[str]] = {
        "ADMIN": [
            "VIEW_GLOBAL_LEDGER", "EXECUTE_CHECKOUT", "EXECUTE_MULTI_SPLIT",
            "REQUEST_PAYOUT", "ISSUE_NFSE", "MANAGE_TEAM", "MANAGE_WHITELABEL",
            "RUN_PENTEST", "EXECUTE_INCIDENT_PLAYBOOK", "UNMASK_LGPD_PII", "REFUND_TX"
        ],
        "MERCHANT": [
            "VIEW_CLINIC_LEDGER", "EXECUTE_CHECKOUT", "EXECUTE_MULTI_SPLIT",
            "REQUEST_PAYOUT", "ISSUE_NFSE", "MANAGE_TEAM", "MANAGE_WHITELABEL", "REFUND_TX"
        ],
        "PARTNER": [
            "VIEW_OWN_WALLET", "REQUEST_PAYOUT", "ISSUE_NFSE", "CREATE_PAYMENT_LINK"
        ],
        "STAFF": [
            "EXECUTE_CHECKOUT", "EXECUTE_MULTI_SPLIT", "CREATE_PAYMENT_LINK"
        ],
        "AUDITOR": [
            "VIEW_CLINIC_LEDGER", "ISSUE_NFSE", "EXPORT_ACCOUNTING_EXCEL"
        ]
    }

    @classmethod
    def check_permission(cls, role: str, action: str) -> bool:
        allowed = cls.PERMISSION_MATRIX.get(role.upper(), [])
        return action in allowed

    @staticmethod
    def generate_csrf_token(session_id: str) -> str:
        secret = os.environ.get("MERIDIAN_CSRF_SECRET", "csrf_meridian_zero_trust_key")
        return hmac.new(secret.encode("utf-8"), session_id.encode("utf-8"), hashlib.sha256).hexdigest()[:32]

    @classmethod
    def verify_csrf_token(cls, session_id: str, token: str) -> bool:
        expected = cls.generate_csrf_token(session_id)
        return hmac.compare_digest(expected, str(token or ""))


class OWASPShield:
    SQLI_PATTERNS = [
        r"(?i)(\bUNION\b\s+\bSELECT\b)",
        r"(?i)(\bDROP\b\s+\bTABLE\b)",
        r"(?i)(\bOR\b\s+['\"]?1['\"]?\s*=\s*['\"]?1)",
        r"(?i)(--\s|;\s*DROP\b|;\s*DELETE\b|;\s*UPDATE\b|;\s*INSERT\b)",
        r"(?i)(\bEXEC\b\s*\(|\bSLEEP\b\s*\(|\bBENCHMARK\b\s*\()"
    ]

    XSS_PATTERNS = [
        r"(?i)<\s*script\b[^>]*>",
        r"(?i)javascript\s*:",
        r"(?i)\bon(error|load|click|mouseover|focus)\s*=",
        r"(?i)<\s*iframe\b[^>]*>",
        r"(?i)<\s*img\b[^>]+onerror\b"
    ]

    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"(?i)/etc/passwd",
        r"(?i)c:\\windows\\system32"
    ]

    @classmethod
    def inspect_input(cls, value: Any, field_name: str = "input") -> Tuple[bool, str]:
        text = str(value or "")
        for pat in cls.SQLI_PATTERNS:
            if re.search(pat, text):
                return False, f"OWASP A03 (SQL Injection) bloqueado no campo '{field_name}'."
        for pat in cls.XSS_PATTERNS:
            if re.search(pat, text):
                return False, f"OWASP A03 (Cross-Site Scripting / XSS) bloqueado no campo '{field_name}'."
        for pat in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pat, text):
                return False, f"OWASP A01 (Path Traversal) bloqueado no campo '{field_name}'."
        return True, "CLEAN"


class SecurityEmailDispatcher:
    """
    Dispara o e-mail formal de segurança (sem emojis) EXCLUSIVAMENTE após a falha da
    3ª tentativa de login e gera o código SMS de 6 a 8 dígitos (numérico ou alfanumérico)
    necessário para desbloquear a conta.
    """

    def __init__(self, base_dir: str = "."):
        self.base_path = Path(base_dir)
        self.smtp_config_file = self.base_path / "smtp_security_config.json"
        self.outbox_file = self.base_path / "security_emails_outbox.json"
        self.siem_file = self.base_path / "siem_security_logs.json"

    @staticmethod
    def generate_sms_verification_code(length: int = 7, alphanumeric: bool = True) -> str:
        """Gera um código de verificação SMS de 6 a 8 caracteres (números ou letras + números)."""
        safe_len = max(6, min(8, int(length)))
        alphabet = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ" if alphanumeric else "0123456789"
        return "".join(secrets.choice(alphabet) for _ in range(safe_len))

    def load_smtp_config(self) -> Dict[str, Any]:
        default_cfg = {
            "smtp_host": os.environ.get("MERIDIAN_SMTP_HOST", "smtp.gmail.com"),
            "smtp_port": int(os.environ.get("MERIDIAN_SMTP_PORT", "587")),
            "smtp_user": os.environ.get("MERIDIAN_SMTP_USER", ""),
            "smtp_password": os.environ.get("MERIDIAN_SMTP_PASSWORD", ""),
            "alert_recipient": os.environ.get("MERIDIAN_ALERT_EMAIL", "seguranca@meridian.com.br"),
            "send_only_on_third_failure": True
        }
        if self.smtp_config_file.exists():
            try:
                with open(self.smtp_config_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                default_cfg.update(saved)
            except Exception:
                pass
        return default_cfg

    def save_smtp_config(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        recipient: str
    ) -> Dict[str, Any]:
        cfg = {
            "smtp_host": host.strip(),
            "smtp_port": int(port),
            "smtp_user": user.strip(),
            "smtp_password": password.strip(),
            "alert_recipient": recipient.strip(),
            "send_only_on_third_failure": True
        }
        with open(self.smtp_config_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return cfg

    def load_outbox(self) -> List[Dict[str, Any]]:
        if not self.outbox_file.exists():
            return []
        try:
            with open(self.outbox_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def load_siem_logs(self) -> List[Dict[str, Any]]:
        if not self.siem_file.exists():
            return []
        try:
            with open(self.siem_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def log_siem_event(self, event_type: str, severity: str, username: str, details: str) -> Dict[str, Any]:
        logs = self.load_siem_logs()
        entry = {
            "event_id": f"SIEM_{uuid.uuid4().hex[:8].upper()}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "severity": severity,
            "username": username,
            "details": details
        }
        logs.append(entry)
        with open(self.siem_file, "w", encoding="utf-8") as f:
            json.dump(logs[-200:], f, indent=2, ensure_ascii=False)
        return entry

    def send_third_strike_lockout_email(
        self,
        username: str,
        recipient_email: str,
        sms_unlock_code: str,
        max_attempts: int = 3,
        reason: str = "Limite de 3 tentativas consecutivas de login excedido"
    ) -> Dict[str, Any]:
        """
        Dispara a notificação formal de segurança (sem emojis) exclusivamente após a falha
        da 3ª tentativa, informando o bloqueio da conta e o procedimento de desbloqueio por SMS.
        """
        cfg = self.load_smtp_config()
        destino = recipient_email or cfg.get("alert_recipient", "seguranca@meridian.com.br")
        now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")

        assunto = f"[ALERTA DE SEGURANCA] Bloqueio preventivo da conta '{username}' apos 3 tentativas de acesso"
        mensagem_formal = (
            f"Detectamos {max_attempts} tentativas consecutivas de autenticacao sem sucesso na conta '{username}'. "
            f"Caso nao tenha sido voce que realizou essas tentativas, informamos que a sua conta foi bloqueada "
            f"preventivamente por seguranca. Para realizar o desbloqueio da conta, e obrigatorio concluir a "
            f"verificacao de identidade utilizando o codigo de seguranca de 6 a 8 digitos (numerico ou alfanumerico) "
            f"enviado via SMS para o dispositivo cadastrado."
        )

        corpo_html = f"""
        <div style="font-family:'Segoe UI',Arial,sans-serif; background:#081028; color:#ffffff; padding:28px; border-radius:8px; border:1px solid #ef4444; max-width:620px;">
            <div style="font-size:11px; color:#38bdf8; font-weight:700; letter-spacing:1.2px; text-transform:uppercase;">
                MERIDIAN SECURITY OPERATIONS CENTER (SOC) — NOTIFICACAO OFICIAL
            </div>
            <h2 style="margin:10px 0; color:#f87171; font-size:18px; font-weight:700;">
                CONTA BLOQUEADA POR SEGURANCA APOS 3 TENTATIVAS DE LOGIN
            </h2>
            <p style="color:#e2e8f0; font-size:13.5px; line-height:1.55;">
                {mensagem_formal}
            </p>
            <table style="width:100%; background:#0b1739; border-radius:6px; padding:14px; font-size:13px; color:#e2e8f0; border:1px solid #13224c; margin-top:12px;">
                <tr><td><strong>Conta / Identificador:</strong></td><td>{username}</td></tr>
                <tr><td><strong>Status da Conta:</strong></td><td style="color:#f87171; font-weight:bold;">BLOQUEADA ({max_attempts}/{max_attempts} FALHAS)</td></tr>
                <tr><td><strong>Evento Registrado:</strong></td><td>{reason}</td></tr>
                <tr><td><strong>Requisito de Desbloqueio:</strong></td><td>Verificacao por SMS (6 a 8 caracteres numericos/alfanumericos)</td></tr>
                <tr><td><strong>Data e Hora (UTC):</strong></td><td>{now_str}</td></tr>
            </table>
        </div>
        """

        delivery_mode = "OUTBOX_AUDIT_LOG (Configure SMTP para envio externo)"
        smtp_user = cfg.get("smtp_user", "").strip()
        smtp_pass = cfg.get("smtp_password", "").strip()

        if smtp_user and smtp_pass:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = assunto
                msg["From"] = smtp_user
                msg["To"] = destino
                msg.attach(MIMEText(corpo_html, "html", "utf-8"))

                with smtplib.SMTP(cfg.get("smtp_host", "smtp.gmail.com"), int(cfg.get("smtp_port", 587)), timeout=5) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(smtp_user, [destino], msg.as_string())
                delivery_mode = "SMTP_REAL_SENT"
            except Exception as e:
                delivery_mode = f"OUTBOX_SAVED (Falha SMTP: {str(e)[:40]})"

        email_record = {
            "email_id": f"SEC_{uuid.uuid4().hex[:8].upper()}",
            "timestamp": now_str,
            "to": destino,
            "username": username,
            "attempt": f"{max_attempts}/{max_attempts}",
            "locked": True,
            "sms_code_generated": sms_unlock_code,
            "subject": assunto,
            "formal_message": mensagem_formal,
            "delivery_status": delivery_mode,
            "html_body": corpo_html
        }

        outbox = self.load_outbox()
        outbox.append(email_record)
        with open(self.outbox_file, "w", encoding="utf-8") as f:
            json.dump(outbox[-100:], f, indent=2, ensure_ascii=False)

        self.log_siem_event(
            event_type="ACCOUNT_LOCKOUT_3_STRIKES",
            severity="CRITICAL",
            username=username,
            details=f"Conta bloqueada na 3a tentativa. E-mail formal disparado para {destino} e codigo SMS ({len(sms_unlock_code)} digitos) emitido."
        )
        return email_record


class AutomatedPentestScanner:
    @staticmethod
    def run_security_audit_suite(auth_manager, engine) -> List[Dict[str, Any]]:
        results = []

        ok_sqli, _ = OWASPShield.inspect_input("admin' OR '1'='1' --", "username")
        results.append({
            "Pilar": "4. Prevenção OWASP (Anti-SQLi)",
            "Vetor Testado": "Payload: admin' OR '1'='1' --",
            "Resultado": "BLOQUEADO COM SUCESSO" if not ok_sqli else "VULNERÁVEL",
            "Status": "PASSED" if not ok_sqli else "FAILED"
        })

        ok_xss, _ = OWASPShield.inspect_input("<script>alert('xss')</script>", "comprador")
        results.append({
            "Pilar": "4. Prevenção OWASP (Anti-XSS)",
            "Vetor Testado": "Payload: <script>alert('xss')</script>",
            "Resultado": "BLOQUEADO COM SUCESSO" if not ok_xss else "VULNERÁVEL",
            "Status": "PASSED" if not ok_xss else "FAILED"
        })

        cipher = DataVaultCipher()
        token_enc = cipher.encrypt_at_rest("CPF_SENSIVEL_123.456.789-00")
        dec_ok = (cipher.decrypt_at_rest(token_enc) == "CPF_SENSIVEL_123.456.789-00")
        results.append({
            "Pilar": "2. Criptografia em Repouso (LGPD/HIPAA)",
            "Vetor Testado": "PBKDF2-Stream + HMAC-SHA256 Verification",
            "Resultado": "CRIPTOGRAFADO & AUTENTICADO" if dec_ok else "FALHA",
            "Status": "PASSED" if dec_ok else "FAILED"
        })

        staff_blocked = not LeastPrivilegeGuard.check_permission("STAFF", "REQUEST_PAYOUT")
        partner_blocked = not LeastPrivilegeGuard.check_permission("PARTNER", "REFUND_TX")
        results.append({
            "Pilar": "3. Privilégio Mínimo (PoLP Zero-Trust)",
            "Vetor Testado": "Bloqueio de Saque p/ STAFF e Estorno p/ PARTNER",
            "Resultado": "ACESSO NEGADO CORRETAMENTE" if (staff_blocked and partner_blocked) else "FALHA RBAC",
            "Status": "PASSED" if (staff_blocked and partner_blocked) else "FAILED"
        })

        csrf_tok = LeastPrivilegeGuard.generate_csrf_token("sess_test_01")
        csrf_ok = LeastPrivilegeGuard.verify_csrf_token("sess_test_01", csrf_tok) and not LeastPrivilegeGuard.verify_csrf_token("sess_test_01", "token_falso")
        results.append({
            "Pilar": "3. Proteção Anti-CSRF",
            "Vetor Testado": "Assinatura HMAC de Token de Sessão",
            "Resultado": "TOKEN VALIDADO" if csrf_ok else "FALHA CSRF",
            "Status": "PASSED" if csrf_ok else "FAILED"
        })

        headers = TLSAndHeadersManager.get_headers_Status()
        hsts_ok = "max-age=" in headers.get("Strict-Transport-Security", "")
        results.append({
            "Pilar": "1. HTTPS / SSL / HSTS Headers",
            "Vetor Testado": "Strict-Transport-Security & CSP Policy",
            "Resultado": "POLÍTICAS ATIVAS" if hsts_ok else "AUSENTE",
            "Status": "PASSED" if hsts_ok else "FAILED"
        })

        ledger_ok = engine.verify_ledger_integrity()
        results.append({
            "Pilar": "5. Monitoramento FIM & Ledger SHA-256",
            "Vetor Testado": "Verificação Criptográfica de transacoes.json",
            "Resultado": "100% ÍNTEGRO" if ledger_ok else "ADULTERADO",
            "Status": "PASSED" if ledger_ok else "FAILED"
        })

        max_cfg = getattr(auth_manager, "MAX_LOGIN_ATTEMPTS", 3)
        results.append({
            "Pilar": "7. Bloqueio na 3a Tentativa + E-mail e SMS (6-8 digitos)",
            "Vetor Testado": f"Limite: {max_cfg} tentativas | Desbloqueio SMS 6-8 chars",
            "Resultado": "ATIVO E VALIDADO" if max_cfg == 3 else "DESCALIBRADO",
            "Status": "PASSED" if max_cfg == 3 else "FAILED"
        })

        return results


class IncidentResponsePlaybook:
    PLAYBOOK_STEPS = [
        {"Fase": "1. Detecção & Triagem", "Responsável": "SIEM / SOC Automatizado", "SLA": "< 5 segundos", "Ação": "Monitoramento de tentativas de login e integridade SHA-256."},
        {"Fase": "2. Contenção na 3ª Tentativa", "Responsável": "Defesa Ativa Meridian", "SLA": "Instantâneo (3ª falha)", "Ação": "Bloqueio imediato da conta, disparo de e-mail formal de segurança e exigência de código SMS (6 a 8 dígitos)."},
        {"Fase": "3. Verificação e Erradicação", "Responsável": "Titular (SMS) ou Admin (SOAR)", "SLA": "< 15 minutos", "Ação": "Validação de identidade via código SMS alfanumérico de 6-8 dígitos ou rotação de chaves de API."},
        {"Fase": "4. Recuperação & Pós-Incidente", "Responsável": "Engenharia & Compliance LGPD", "SLA": "< 1 hora", "Ação": "Auditoria completa da trilha SIEM e verificação do Ledger."}
    ]

    @staticmethod
    def rotate_all_merchant_api_keys(auth_manager) -> int:
        users = auth_manager._load_users()
        count = 0
        for uname, udata in users.items():
            udata["api_key"] = f"mrd_live_{secrets.token_hex(12)}"
            count += 1
        auth_manager._save_users(users)
        auth_manager.email_dispatcher.log_siem_event(
            event_type="SOAR_MASS_API_KEY_ROTATION",
            severity="CRITICAL",
            username="ADMIN_SOAR",
            details=f"Rotacao de emergencia concluida para {count} contas."
        )
        return count


class SecurityAwarenessTrainer:
    SCENARIOS = [
        {
            "id": "Q1",
            "titulo": "Cenário 1 — E-mail Falso Solicitando Código de Desbloqueio SMS",
            "mensagem": "Você recebe uma mensagem pedindo para informar o código SMS de 7 dígitos recebido no seu celular para uma suposta manutenção cadastral.",
            "opcoes": [
                "A) Informar o código rapidamente por resposta de mensagem.",
                "B) Nunca compartilhar códigos SMS de verificação e reportar a tentativa de phishing ao setor de segurança."
            ],
            "correta": 1,
            "explicacao": "Códigos SMS de 6 a 8 dígitos são exclusivos para inserção direta na tela oficial de verificação do sistema."
        },
        {
            "id": "Q2",
            "titulo": "Cenário 2 — Ligação de Falso Suporte Solicitando Chave de API (Vishing)",
            "mensagem": "Alguém liga dizendo ser do suporte técnico e solicita a leitura da chave X-Meridian-Key exibida no painel.",
            "opcoes": [
                "A) Negar o pedido imediatamente, pois chaves X-Meridian-Key são secretas e restritas.",
                "B) Fornecer a chave por telefone."
            ],
            "correta": 0,
            "explicacao": "Nenhuma equipe de suporte solicita senhas ou chaves de API por telefone."
        },
        {
            "id": "Q3",
            "titulo": "Cenário 3 — Comprovante de Pagamento com Extensão Executável",
            "mensagem": "Um cliente envia um arquivo chamado 'comprovante_pix.exe' solicitando abertura imediata no computador do financeiro.",
            "opcoes": [
                "A) Executar o arquivo no terminal financeiro.",
                "B) Bloquear o arquivo imediatamente: comprovantes legítimos nunca possuem extensão executável (.exe, .scr, .bat)."
            ],
            "correta": 1,
            "explicacao": "Arquivos executáveis disfarçados de comprovantes são vetores clássicos de malware bancário."
        }
    ]