"""Contrato da ferramenta, rubrica e prompts."""
import pytest
from pydantic import ValidationError

from backend.schemas.contrato import Criativo, Entrada, Saida
from backend.schemas.rubrica import CAMPOS_CATEGORICOS, CAMPOS_VALIDACAO, Lote, Rubrica


def test_entrada_valida_e_padroes():
    e = Entrada.model_validate({"mode": "analisar", "query": "ganchos de alimentação"})
    assert e.n_criativos == 1 and e.segment is None and e.filters.plataforma is None


@pytest.mark.parametrize("dados", [
    {"mode": "resumir", "query": "x"},
    {"mode": "gerar_criativo", "query": "x", "n_criativos": 6},
    {"mode": "analisar", "query": "x", "filters": {"plataforma": "tiktok"}},
])
def test_entrada_invalida(dados):
    with pytest.raises(ValidationError):
        Entrada.model_validate(dados)


def test_saida_tem_os_campos_do_contrato():
    campos = set(Saida.model_fields)
    assert {"findings", "reference_posts", "creatives", "confidence_flag", "explanation"} <= campos


def test_criativo_exige_inspiracao():
    with pytest.raises(ValidationError):
        Criativo.model_validate({"titulo": "t", "formato": "reels", "gancho": "g", "roteiro": [],
                                 "legenda": "l", "cta": "c", "justificativa": "j"})


def test_rubrica_aceita_so_valores_fechados():
    base = {"formato_video": None, "hook_primeiros_3s": "Você sabia", "tipo_hook": "pergunta", "forca_hook_0a10": 7,
            "tema_principal": "financas", "tem_rosto": True, "criador_e_empreendedor_real": False,
            "prova_social": False, "texto_na_tela": True, "tom": "informal", "usa_linguagem_regional": False,
            "clareza_mensagem_0a10": 8, "tem_cta": False, "tipo_cta": "nenhum",
            "oferta_ou_beneficio_explicito": False, "elementos_top5": ["a"]}
    assert Rubrica.model_validate(base).tema_principal == "financas"
    with pytest.raises(ValidationError):
        Rubrica.model_validate({**base, "tema_principal": "noticias"})
    with pytest.raises(ValidationError):
        Rubrica.model_validate({**base, "forca_hook_0a10": 11})


def test_lote_da_categorizacao_texto():
    item = {"id": "ig_1", "hook_primeiros_3s": "x", "tipo_hook": "dor", "forca_hook_0a10": 5,
            "tema_principal": "vendas", "criador_e_empreendedor_real": False, "prova_social": False, "tom": "tecnico",
            "usa_linguagem_regional": False, "clareza_mensagem_0a10": 5, "tem_cta": False, "tipo_cta": "nenhum",
            "oferta_ou_beneficio_explicito": False, "elementos_top5": []}
    assert Lote.model_validate({"resultados": [item]}).resultados[0].id == "ig_1"


def test_campos_de_validacao_estao_na_rubrica():
    assert set(CAMPOS_VALIDACAO) - {"tem_rosto", "texto_na_tela"} <= set(CAMPOS_CATEGORICOS)


def test_prompts_referenciam_a_rubrica():
    from backend.prompts.agente import SISTEMA_CRIATIVOS, TOM_STONE, sistema_redigir
    from backend.prompts.categorizacao_texto import PROMPT
    from backend.prompts.rubrica import PROMPT_SISTEMA
    assert "Impulso Stone" in TOM_STONE and TOM_STONE in SISTEMA_CRIATIVOS
    assert "inspirado_em" in SISTEMA_CRIATIVOS
    assert "análise objetiva" in sistema_redigir("analisar")
    assert "recomendações práticas" in sistema_redigir("recomendar")
    for campo in ["tipo_hook", "tema_principal", "tipo_cta"]:
        assert campo in PROMPT and campo in PROMPT_SISTEMA
