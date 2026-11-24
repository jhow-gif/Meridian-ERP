# 🏛️ Meridian — Enterprise ERP, Fintech, Data Science & Multi-LLM Suite

<p align="center">
  <a href="https://meridian-fintech.streamlit.app/" target="_blank">
    <img src="https://img.shields.io/badge/LIVE%20DEMO-Acessar%20Meridian%20ERP-10B981?style=for-the-badge&logo=streamlit&logoColor=white" alt="Live Demo"/>
  </a>
  <a href="https://github.com/jhow-gif/Meridian-ERP/actions/workflows/ci.yml" target="_blank">
    <img src="https://github.com/jhow-gif/Meridian-ERP/actions/workflows/ci.yml/badge.svg" alt="CI Pipeline"/>
  </a>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12"/>
  <img src="https://img.shields.io/badge/License-All%20Rights%20Reserved-DC2626?style=for-the-badge" alt="Proprietary License"/>
</p>

> **Acesso à Demonstração Online:** [meridian-fintech.streamlit.app](https://meridian-fintech.streamlit.app/) *(ambiente de demonstração com dados simulados)*.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Design_System_SaaS-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Text--to--SQL_AppSec-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Multi-LLM](https://img.shields.io/badge/Multi--LLM-FinOps_%2B_Offline_Engine-10B981?style=for-the-badge)
![SecOps](https://img.shields.io/badge/SecOps-8--Pillar_Pentest_%26_FIM_SHA--256-8B5CF6?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-33_Passed_(100%25)-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)

O **Meridian** é uma plataforma corporativa **SaaS de ERP Autônomo, Operações Fintech, Ciência de Dados Preditiva, CRM Omnichannel e Governança SecOps/FinOps** construída em Python. O sistema centraliza a tomada de decisão executiva e a automação operacional de e-commerces combinando **Orquestração Multi-Agente com Function Calling** e um **Motor Determinístico 100% Offline (Zero-Downtime Fallback)** que garante operação contínua em milissegundos mesmo sem internet ou chaves de API.

---

## 🌟 Diferenciais de Engenharia (Arquitetura Staff / Enterprise)

1. **Arquitetura Híbrida Resiliente (Multi-LLM + Fallback Determinístico Offline):**
   - Roteamento inteligente entre **Google Gemini 2.5 Flash**, **OpenAI GPT-4o**, **Anthropic Claude 3.5 Sonnet**, **Groq (Llama 3.3 70B)**, **Ollama (Local)** e **Motor Determinístico Nativo em Python**.
   - Caso a API externa esteja indisponível ou o usuário ative o **Modo 100% Offline**, o sistema processa solicitações no chat localmente em `< 15 ms` a custo zero.
2. **Governança FinOps de IA em Tempo Real:**
   - Contabilização automática de tokens de entrada/saída, latência em milissegundos (`ms`), custo real em USD/BRL por requisição e economia acumulada frente a modelos de alto custo na tabela SQL `finops_llm_custos`.
3. **SecOps Avançado, Pentest Automatizado (8 Pilares) & Integridade FIM SHA-256:**
   - **Controle de Acesso Baseado em Cargos (RBAC):** Perfis corporativos (`C-Level / Diretoria`, `Analista de BI & Finanças`, `Operador de Suporte & Logística`) que bloqueiam dinamicamente relatórios sensíveis (DRE, Margem de Lucro e Antifraude/LGPD) tanto na interface quanto no chat.
   - **Scanner DAST/SAST Integrado:** Suíte automatizada de auditoria de segurança cobrindo 8 pilares críticos, incluindo proteção contra *SQL Injection* (`AppSec Guardrails`), anonimização LGPD e **Monitoramento de Integridade de Arquivos (FIM) & Ledger SHA-256** para detecção de adulteração de transações e relatórios.
4. **Ciência de Dados Preditiva (Curva ABC de Pareto, Z-Score & Forecast 30/60/90 Dias):**
   - Classificação automática de portfólio na **Curva ABC (80/15/5)**, detecção estatística de anomalias de vendas via **Z-Score** e projeção composta de faturamento para 30, 60 e 90 dias.
5. **Ingestão Dinâmica (*Bring Your Own Data* — BYOD) & Data Lake Parquet:**
   - Upload de planilhas customizadas (`.xlsx` ou `.csv`) diretamente na barra lateral para processar bases reais da empresa e exportar datasets colunares em **Apache Parquet (`.parquet`)**.
6. **Design System SaaS Multi-Tema & Onboarding Progressivo (Zero-Start):**
   - Interface executiva que inicia **100% zerada (`R$ 0,00`)** e popula gráficos, métricas e assinaturas criptográficas sob demanda conforme o usuário interage com os módulos, com 4 paletas corporativas selecionáveis ao vivo (*FinTech Midnight & Emerald*, *AI Cloud & Cyber Indigo*, *AWS Console & Operations Amber* e *Executive Light & Navy*) e reset instantâneo do painel.

---

## 🏛️ Módulos Corporativos Integrados

| Domínio Corporativo | Funcionalidades e Entregáveis Automatizados |
| :--- | :--- |
| **💰 Finanças, Fintech & Pricing (DRE)** | Cálculo de Receita Bruta, CMV, Impostos, Taxas de Gateway, Lucro Líquido (EBITDA), Margem (%), Precificação Dinâmica por IA e Ledger financeiro transacional. |
| **📦 Supply Chain & Compras** | Cálculo de *Burn Rate* diário, autonomia de estoque em dias, alerta de ruptura (`Estoque ≤ 5`) e emissão automática de Ordens de Compra (PO). |
| **🎯 CRM & Win-Back Omnichannel** | Filtro SQL de leads inativos, classificação de *Lead Scoring* (VIP/Warm), geração de links diretos da API do WhatsApp (*Click-to-Chat*), disparo via Gmail SMTP e payload Webhook JSON (n8n/Make/Z-API). |
| **🛡️ SecOps, Pentest, Antifraude & LGPD** | Motor de score de risco contra *Chargeback*, anonimização automática de CPF e IP (LGPD), *AppSec Guardrails* contra *SQL Injection*, Scanner Pentest de 8 pilares e assinatura forense SHA-256. |
| **🔍 Benchmarking & SEO** | Monitoramento competitivo de preços frente à concorrência e geração automatizada de títulos e *keywords long-tail* para Marketplaces. |
| **📄 Automação Office, BI & Cloud** | Exportação nativa em Excel estilizado (`.xlsx`), Power BI (`.csv`), Apache Parquet (`.parquet`), Word (`.docx`), PowerPoint (`.pptx`), Adobe PDF (`.pdf`), Google Workspace (`.ics`), Microsoft 365 (`.html`) e manifestos AWS/Azure/GCP. |

---

## 🖥️ Estrutura das 5 Abas Executivas na Interface

1. **💬 Chat Multi-LLM & RBAC:** Assistente conversacional com roteamento entre sub-agentes, governança RBAC, fallback offline instantâneo e telemetria FinOps.
2. **📊 Dashboard BI & Analytics:** KPIs executivos e gráficos comparativos de faturamento bruto, giro de estoque e margem líquida estimada.
3. **🧠 Ciência de Dados (Curva ABC, Forecast & FinOps):** Simulador de crescimento composto para 30/60/90 dias, matriz de Pareto 80/15/5, detector de anomalias Z-Score e painel de auditoria de custos de tokens LLM.
4. **🧮 Simulador Financeiro (What-If Analysis):** Modelagem de elasticidade de preços, descontos promocionais e alíquota tributária com impacto em tempo real no EBITDA.
5. **🗄️ SQL Explorer, SHA-256 & Telemetria SecOps:** Console Text-to-SQL protegido por guardrails, verificador de assinaturas criptográficas SHA-256 e trilha de auditoria SQLite (`telemetria_audit_log`).

---

## 🚀 Como Executar o Meridian Localmente

### 1. Clonar o Repositório e Instalar Dependências
```bash
git clone https://github.com/kaiquems17/meridian.git
cd meridian
python -m pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente (Opcional — Suporta Modo 100% Offline)
Crie um arquivo `.env` na raiz do projeto (caso não configure, o Meridian opera automaticamente no **Motor Determinístico Offline**):
```env
GEMINI_API_KEY="sua_chave_aqui"
GMAIL_USER="seu_email@gmail.com"
GMAIL_APP_PASSWORD="sua_senha_de_app_gmail"
```

### 3. Iniciar a Aplicação SaaS no Streamlit
```bash
python -m streamlit run app.py
```

### 4. Executar a Suíte Completa de Testes Automatizados (QA, Fintech & SecOps)
```bash
pytest -v
```

### 5. Executar via Container Docker
```bash
docker build -t meridian-erp .
docker run -p 8501:8501 meridian-erp
```

---

## 🧪 Cobertura de Testes Automatizados (`33 Passed — 100%`)

A esteira de integração contínua (`.github/workflows/ci.yml`) valida automaticamente **33 cenários críticos** distribuídos em `test_erp.py` e `test_meridian.py`, incluindo:
- **AppSec & Pentest Automatizado (8 Pilares):** Bloqueio de *SQL Injection* (`DROP`, `DELETE`, `UPDATE`), autenticação/RBAC, sanitização e verificação de integridade **FIM & Ledger SHA-256**.
- **Motor Financeiro & Fintech:** Auditoria matemática de DRE (Receita Bruta, CMV, Impostos, EBITDA), precificação dinâmica e transações.
- **Compliance LGPD & Antifraude:** Detecção de risco de *chargeback* e mascaramento obrigatório de dados sensíveis (CPF e IP).
- **Resiliência Offline & Ciência de Dados:** Execução determinística sem dependência de LLM externo, Curva ABC (Pareto), Z-Score e Forecast de 90 dias.

---

## 👨‍💻 Autor

**Kaique Moreira de Souza**  
Engenharia de Software • Inteligência Artificial • Ciência de Dados • Cibersegurança (SecOps)  
🌐 [github.com/kaiquems17](https://github.com/kaiquems17)
