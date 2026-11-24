import os
from ferramentas_ecommerce import (
    sincronizar_e_consultar_sql,
    gerar_dre_e_precificacao_dinamica,
    executar_auditoria_antifraude_e_lgpd,
    motor_deterministico_offline,
    executar_curva_abc_forecast_zscore,
    gerar_hash_sha256_arquivo,
)
from sistema_multiagente import verificar_permissao_rbac


def test_appsec_sql_injection_guardrail():
    resposta_ataque = sincronizar_e_consultar_sql("DROP TABLE produtos;")
    assert "BLOQUEIO DE SEGURANÇA" in resposta_ataque


def test_calculo_dre_financeiro():
    res = gerar_dre_e_precificacao_dinamica()
    assert "Lucro Líquido Mensal" in res
    assert os.path.exists("DRE_Financeiro_Precificacao.xlsx")


def test_antifraude_e_anonimizacao_lgpd():
    res = executar_auditoria_antifraude_e_lgpd()
    assert "Chargeback" in res
    assert os.path.exists("Relatorio_Antifraude_Conformidade_LGPD.xlsx")


def test_motor_offline_sem_ia():
    res = motor_deterministico_offline("Gere o DRE financeiro e audite fraudes LGPD")
    assert "Motor Determinístico Local" in res


def test_curva_abc_forecast_e_zscore():
    res = executar_curva_abc_forecast_zscore(8.0)
    assert "Classe A" in res
    assert os.path.exists("Curva_ABC_Forecast_ML.xlsx")


def test_integridade_criptografica_sha256():
    gerar_dre_e_precificacao_dinamica()
    assinatura = gerar_hash_sha256_arquivo("DRE_Financeiro_Precificacao.xlsx")
    assert len(assinatura) == 64


def test_governanca_rbac_bloqueio_operador():
    bloqueio = verificar_permissao_rbac("Gere o DRE financeiro com margem de lucro", "Operador de Suporte & Logística")
    assert "BLOQUEIO DE GOVERNANÇA RBAC" in bloqueio