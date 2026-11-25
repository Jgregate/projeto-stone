"""API do frontend com o modelo falso."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def cliente(agente_offline):
    import backend.api.main as api
    return TestClient(api.app), api


def test_pagina_e_arquivos_estaticos(cliente):
    cli, _ = cliente
    assert cli.get("/").status_code == 200
    assert cli.get("/static/estilo.css").status_code == 200
    assert cli.get("/static/fontes/figtree-latin-wght-normal.woff2").status_code == 200


def test_visao_da_base(cliente):
    cli, _ = cliente
    r = cli.get("/api/base").json()
    assert r["numeros"]["publicacoes"] > 0 and r["ranking"] and r["perfis_destaque"]


def test_consulta_devolve_contrato_e_rastreabilidade(cliente):
    cli, _ = cliente
    r = cli.post("/api/consultar", json={"mode": "gerar_criativo", "query": "Reels para restaurantes",
                                         "segment": "alimentacao"})
    assert r.status_code == 200
    corpo = r.json()
    s = corpo["saida"]
    for campo in ["findings", "reference_posts", "creatives", "confidence_flag", "explanation"]:
        assert campo in s
    assert set(corpo["detalhes"]) == {p["post_id"] for p in s["reference_posts"]}
    assert corpo["exemplos_achados"]


def test_erros_de_pedido(cliente):
    cli, _ = cliente
    assert cli.post("/api/consultar", json={"mode": "analisar", "query": "  "}).status_code == 400
    assert cli.post("/api/consultar", json={"mode": "analisar", "query": "criptomoedas blockchain"}).status_code == 404
    assert cli.post("/api/consultar", json={"mode": "outro", "query": "x"}).status_code == 422


def test_limite_do_modelo_vira_429(cliente, monkeypatch):
    cli, api = cliente
    from backend.graph import agente
    monkeypatch.setenv("SIMULAR_LIMITE", "1")
    monkeypatch.setattr(agente, "_llm", api._llm_demo)
    r = cli.post("/api/consultar", json={"mode": "gerar_criativo", "query": "Reels para restaurantes"})
    assert r.status_code == 429 and r.json()["erro"] == "limite" and r.json()["saida"]["findings"]
