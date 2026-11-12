"""
Validação manual da categorização (TAPI 6.1, mínimo de 50 publicações).

amostra  sorteia 50 posts categorizados (estratificado por plataforma e tipo de post) e gera
         data/validacao_manual.csv com as colunas da rubrica EM BRANCO. A anotação é cega,
         você classifica sem ver a resposta do modelo, para não ser influenciada.
avaliar  compara a sua anotação com a do modelo e gera data/validacao_resultado.md
         com concordância (%) e kappa de Cohen por campo.

Uso
    python validacao.py amostra
    (preencha data/validacao_manual.csv no Excel ou no Google Sheets)
    python validacao.py avaliar
"""
import sys
from pathlib import Path

import pandas as pd

from rubrica import CAMPOS_VALIDACAO

DATA = Path("data")
ARQ = DATA / "validacao_manual.csv"
N = 50
SEED = 42

OPCOES = {
    "formato_video": "talking_head | tutorial | bastidores | antes_depois | humor_esquete | depoimento | lista_dicas | trend | (vazio se imagem/carrossel)",
    "tipo_hook": "pergunta | promessa | dor | numero | polemica | curiosidade | nenhum",
    "tema_principal": "vendas | financas | marketing | atendimento | gestao | motivacao | ferramentas_maquininha | historia_de_empreendedor",
    "tem_rosto": "true | false",
    "texto_na_tela": "true | false",
    "tom": "informal | tecnico | inspiracional | humoristico",
    "tem_cta": "true | false",
    "tipo_cta": "comentar | salvar | link_na_bio | dm | seguir | compartilhar | nenhum",
}


def amostra():
    cat = pd.read_parquet(DATA / "categorias.parquet")
    n_estratos = cat.groupby(["plataforma", "tipo_post"]).ngroups
    por_estrato = max(1, N // n_estratos)
    amo = (cat.groupby(["plataforma", "tipo_post"], group_keys=False)
              .apply(lambda g: g.sample(min(len(g), por_estrato), random_state=SEED)))
    if len(amo) < N:
        resto = cat.drop(amo.index).sample(min(N - len(amo), len(cat) - len(amo)), random_state=SEED)
        amo = pd.concat([amo, resto])
    amo = amo.head(N).sample(frac=1, random_state=SEED)

    planilha = amo[["post_id", "plataforma", "tipo_post", "perfil", "url"]].copy()
    planilha["imagem_local"] = "data/midia/" + planilha["post_id"] + ".jpg"
    for c in CAMPOS_VALIDACAO:
        planilha[f"manual_{c}"] = ""
    planilha.to_csv(ARQ, index=False, encoding="utf-8-sig")

    print(f"{len(planilha)} posts sorteados -> {ARQ}")
    print("\nAbra cada URL, classifique e preencha as colunas manual_*. Valores aceitos")
    for c, o in OPCOES.items():
        print(f"  {c:<15} {o}")


def kappa(a, b):
    cats = sorted(set(a) | set(b))
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((list(a).count(c) / n) * (list(b).count(c) / n) for c in cats)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def normaliza(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    s = str(v).strip().lower()
    return {"verdadeiro": "true", "sim": "true", "1": "true", "1.0": "true",
            "falso": "false", "nao": "false", "não": "false", "0": "false", "0.0": "false",
            "none": "", "nan": ""}.get(s, s)


def avaliar():
    man = pd.read_csv(ARQ, encoding="utf-8-sig")
    cat = pd.read_parquet(DATA / "categorias.parquet")
    df = man.merge(cat, on="post_id", suffixes=("", "_modelo"))

    linhas = ["# Validação manual da categorização", "",
              f"Amostra de {len(df)} publicações do top 10%, sorteada por plataforma e tipo de post (seed {SEED}).",
              "Anotação manual feita às cegas, sem ver a resposta do modelo.", "",
              "| campo | n | concordância | kappa |", "|---|---|---|---|"]
    resumo = []
    for c in CAMPOS_VALIDACAO:
        m = df[f"manual_{c}"].map(normaliza)
        a = df[c].map(normaliza)
        preenchido = m != ""
        if c == "formato_video":
            preenchido = preenchido | df["tipo_post"].isin(["imagem", "carrossel"])
        m, a = m[preenchido], a[preenchido]
        conc = (m == a).mean() if len(m) else float("nan")
        k = kappa(list(m), list(a))
        resumo.append((c, len(m), conc, k))
        linhas.append(f"| {c} | {len(m)} | {conc:.0%} | {k:.2f} |")

    media = pd.DataFrame(resumo, columns=["c", "n", "conc", "k"])
    linhas += ["", f"Concordância média {media['conc'].mean():.0%}, kappa médio {media['k'].mean():.2f}.", "",
               "Leitura do kappa (Landis e Koch) abaixo de 0,40 fraco, 0,40 a 0,60 moderado, "
               "0,60 a 0,80 substancial, acima de 0,80 quase perfeito.", "",
               "## Divergências", ""]
    for c in CAMPOS_VALIDACAO:
        d = df[(df[f"manual_{c}"].map(normaliza) != df[c].map(normaliza)) & (df[f"manual_{c}"].map(normaliza) != "")]
        for _, r in d.iterrows():
            linhas.append(f"- {c} | {r['post_id']} | manual {normaliza(r[f'manual_{c}'])} | modelo {normaliza(r[c])}")

    (DATA / "validacao_resultado.md").write_text("\n".join(linhas), encoding="utf-8")
    print("\n".join(linhas[:6 + len(CAMPOS_VALIDACAO) + 2]))
    print("\nrelatório completo em data/validacao_resultado.md")


if __name__ == "__main__":
    {"amostra": amostra, "avaliar": avaliar}[sys.argv[1] if len(sys.argv) > 1 else "amostra"]()
