"""Taxa de engajamento normalizada, lift, top 10% e chamada para ação."""
import pandas as pd

from backend.analysis.montar_base import marcar_cta, ranquear
from backend.config import PROCESSED


def _base_sintetica():
    linhas = []
    for perfil, seguidores in [("a", 1000), ("b", 100000)]:
        for i in range(20):
            linhas.append({"plataforma": "instagram", "perfil": perfil, "post_id": f"{perfil}{i}", "faixa": "x",
                           "curtidas": 10 + i, "comentarios": 1, "seguidores": seguidores, "texto": ""})
    linhas.append({"plataforma": "instagram", "perfil": "a", "post_id": "oculto", "faixa": "x",
                   "curtidas": None, "comentarios": 1, "seguidores": 1000, "texto": ""})
    return pd.DataFrame(linhas)


def test_engajamento_normalizado_e_lift():
    df = ranquear(_base_sintetica())
    a0 = df[df.post_id == "a0"].iloc[0]
    assert a0.engajamento == (10 + 1) / 1000
    assert abs(a0.lift - a0.engajamento / a0.mediana_perfil) < 1e-12
    assert not df[df.post_id == "oculto"].iloc[0].metrica_valida


def test_top10_por_lift_nao_depende_do_tamanho_da_conta():
    df = ranquear(_base_sintetica())
    top = df[df.alto_perfil]
    assert set(top.perfil) == {"a", "b"}
    assert len(top) == 4


def test_cta_por_regra():
    df = marcar_cta(pd.DataFrame({"texto": ["Comenta aqui embaixo", "Link na bio!", "sem chamada"]}))
    assert df.tem_cta.tolist() == [True, True, False]
    assert df.tipos_cta.tolist()[:2] == ["comentar", "link_na_bio"]


def test_base_salva_tem_top10_coerente():
    base = pd.read_parquet(PROCESSED / "base.parquet", columns=["plataforma", "alto_desempenho", "pct_lift"])
    top = base[base.alto_desempenho]
    assert len(top) > 0 and (top.pct_lift >= 0.90).all()
