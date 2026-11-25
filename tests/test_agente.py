"""Agente LangGraph com a base real e o modelo de linguagem falso."""
import json

from backend.schemas.contrato import Entrada, Saida


def test_interpretar_detecta_segmento_e_formato(agente_offline):
    seg, f = agente_offline.interpretar_query(Entrada(mode="analisar", query="Reels para donos de restaurante no Instagram"))
    assert seg == "alimentacao" and f["tipo_post"] == "reels" and f["plataforma"] == "instagram"


def test_filtros_relaxam_quando_sobra_pouco(agente_offline):
    cat, _ = agente_offline.carregar()
    sub, aplicados, relaxados = agente_offline.filtrar(cat, "varejo", {"faixa": "micro", "plataforma": "youtube"})
    assert len(sub) >= agente_offline.MIN_SUBCONJUNTO or not any(aplicados.values())
    assert relaxados


def test_findings_vem_da_base(agente_offline):
    sub, _, _, achados = agente_offline.consultar_base("alimentacao", {})
    tipo = [a for a in achados if a.campo == "tipo_post"]
    assert tipo and tipo[0].posts == int((sub.tipo_post == tipo[0].valor).sum())


def test_referencias_sao_publicacoes_do_recorte(agente_offline):
    sub, _, _, _ = agente_offline.consultar_base("beleza", {})
    refs = agente_offline.buscar_referencias(sub, "salão de beleza", k=5)
    assert 0 < len(refs) <= 5 and {r.post_id for r in refs} <= set(sub.post_id)


def test_gerar_criativo_descarta_inspiracao_inventada(agente_offline):
    s = agente_offline.executar({"mode": "gerar_criativo", "query": "Reels para restaurantes", "segment": "alimentacao"})
    assert isinstance(s, Saida) and len(s.creatives) == 1
    ids = {p.post_id for p in s.reference_posts}
    assert s.creatives[0].inspirado_em and set(s.creatives[0].inspirado_em) <= ids


def test_cada_modo_executa_e_registra(agente_offline):
    for modo in ["analisar", "recomendar", "gerar_criativo"]:
        s = agente_offline.executar({"mode": modo, "query": "finanças para MEI"})
        assert s.findings and s.reference_posts and s.explanation
        assert isinstance(s.confidence_flag, bool)
    linhas = agente_offline.LOG.read_text(encoding="utf-8").splitlines()
    assert [json.loads(linha)["entrada"]["mode"] for linha in linhas] == ["analisar", "recomendar", "gerar_criativo"]


def test_falha_do_modelo_usa_explicacao_da_base(agente_offline, monkeypatch):
    def quebra(*a, **k):
        raise RuntimeError("sem rede")
    monkeypatch.setattr(agente_offline, "_llm", quebra)
    s = agente_offline.executar({"mode": "recomendar", "query": "gestão do MEI"})
    assert s.explanation.startswith("Entre ") and s.recomendacoes == []
