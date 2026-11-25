"""Configuração comum dos testes. Nenhum teste chama o modelo de linguagem nem as APIs de coleta."""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


@pytest.fixture
def agente_offline(monkeypatch, tmp_path):
    """Agente com o LLM falso e o registro das execuções numa pasta temporária."""
    import backend.api.main  # noqa: F401  (a API troca agente._llm ao ser importada; o teste troca de novo)
    from backend.graph import agente

    def llm_falso(sistema, usuario, max_tokens=2500):
        ids = [linha.split(" | ")[0][2:] for linha in usuario.split("PUBLICAÇÕES DE REFERÊNCIA\n")[1].splitlines()]
        if "criativos" in sistema:
            return {"criativos": [{
                "titulo": "Teste", "formato": "reels", "gancho": "Gancho de teste",
                "roteiro": [{"tempo": "0-5s", "acao": "abertura"}], "legenda": "legenda", "cta": "comente",
                "inspirado_em": [ids[0], "ig_inventado_000000"], "justificativa": "achados"}]}
        return {"explicacao": f"Análise baseada em {ids[0]}", "recomendacoes": ["recomendação 1"]}

    monkeypatch.setattr(agente, "_llm", llm_falso)
    monkeypatch.setattr(agente, "LOG", tmp_path / "execucoes.jsonl")
    return agente
