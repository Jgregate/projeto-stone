"""
Validação manual da categorização (TAPI 6.1, mínimo de 50 publicações).

amostra  sorteia 50 posts do top 10% (estratificado por plataforma e tipo de post) e gera
         data/validacao_manual.csv com as colunas da rubrica EM BRANCO. A anotação é cega,
         você classifica sem ver a resposta do modelo, para não ser influenciada.
avaliar  compara a sua anotação com a do modelo e gera data/validacao_resultado.md
         com concordância (%) e kappa de Cohen por campo.

Uso
    python validacao.py amostra
    (preencha data/validacao_manual.xlsx no Excel, as colunas amarelas têm listas suspensas)
    python validacao.py avaliar
"""
import sys
from pathlib import Path

import pandas as pd

from rubrica import CAMPOS_VALIDACAO

DATA = Path("data")
ARQ = DATA / "validacao_manual.csv"
XLSX = DATA / "validacao_manual.xlsx"
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
    if XLSX.exists() and "--forcar" not in sys.argv:
        ja = ler_anotacao().filter(like="manual_").notna().to_numpy().sum()
        if ja:
            print(f"{XLSX} já tem {ja} células anotadas. Nada foi alterado.")
            print("Para sortear de novo e APAGAR a anotação, use  python validacao.py amostra --forcar")
            return
    # sorteia direto do top 10% da base, então a anotação manual pode começar
    # enquanto a categorização ainda está rodando
    base = pd.read_parquet(DATA / "base.parquet")
    cat = base[base["alto_desempenho"]]
    # se a categorização já existe, sorteia só entre os posts categorizados
    if (DATA / "categorias.parquet").exists():
        feitos = set(pd.read_parquet(DATA / "categorias.parquet", columns=["post_id"])["post_id"])
        cat = cat[cat["post_id"].isin(feitos)]
    n_estratos = cat.groupby(["plataforma", "tipo_post"]).ngroups
    por_estrato = max(1, N // n_estratos)
    idx = []
    for _, g in cat.groupby(["plataforma", "tipo_post"]):
        idx += list(g.sample(min(len(g), por_estrato), random_state=SEED).index)
    amo = cat.loc[idx]
    if len(amo) < N:
        resto = cat.drop(amo.index).sample(min(N - len(amo), len(cat) - len(amo)), random_state=SEED)
        amo = pd.concat([amo, resto])
    amo = amo.head(N).sample(frac=1, random_state=SEED)

    planilha = amo[["post_id", "plataforma", "tipo_post", "perfil", "url"]].copy()
    planilha["imagem_local"] = "data/midia/" + planilha["post_id"] + ".jpg"
    for c in CAMPOS_VALIDACAO:
        planilha[f"manual_{c}"] = ""
    planilha.to_csv(ARQ, index=False, encoding="utf-8-sig")
    gerar_xlsx(planilha)

    print(f"{len(planilha)} posts sorteados -> {XLSX} (e {ARQ})")
    print("\nAbra cada URL, classifique e preencha as colunas manual_*. Valores aceitos")
    for c, o in OPCOES.items():
        print(f"  {c:<15} {o}")


def gerar_xlsx(planilha):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    ws = wb.active
    ws.title = "validacao"
    ws.append(list(planilha.columns))
    for row in planilha.itertuples(index=False):
        ws.append(list(row))
    for cell in ws[1]:
        cell.font = Font(bold=True)
    amarelo = PatternFill("solid", fgColor="FFF2CC")
    n = len(planilha) + 1
    for j, col in enumerate(planilha.columns, 1):
        letra = ws.cell(1, j).column_letter
        ws.column_dimensions[letra].width = 22
        if col == "url":
            for i in range(2, n + 1):
                c = ws.cell(i, j)
                c.hyperlink = c.value
                c.font = Font(color="0563C1", underline="single")
        if col.startswith("manual_"):
            campo = col[len("manual_"):]
            valores = [v.strip() for v in OPCOES[campo].split("|") if "(" not in v]
            dv = DataValidation(type="list", formula1='"' + ",".join(valores) + '"', allow_blank=True)
            ws.add_data_validation(dv)
            dv.add(f"{letra}2:{letra}{n}")
            for i in range(2, n + 1):
                ws.cell(i, j).fill = amarelo
    ws.freeze_panes = "B2"
    wb.save(XLSX)


def ler_anotacao():
    if XLSX.exists():
        return pd.read_excel(XLSX, dtype=str)
    return pd.read_csv(ARQ, encoding="utf-8-sig", dtype=str)


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
    man = ler_anotacao()
    anotadas = man.filter(like="manual_").apply(lambda c: c.map(normaliza) != "").to_numpy().sum()
    if anotadas == 0:
        print(f"{XLSX if XLSX.exists() else ARQ} ainda não tem nenhuma anotação manual.")
        print("Preencha as colunas manual_* (amarelas no Excel), salve e rode de novo.")
        return
    cat = pd.read_parquet(DATA / "categorias.parquet")
    df = man.merge(cat, on="post_id", suffixes=("", "_modelo"))
    # completa plataforma e tipo_post a partir da categorização, se vierem vazios na planilha
    for col in ["plataforma", "tipo_post"]:
        if f"{col}_modelo" in df.columns:
            df[col] = df[col].where(df[col].notna() & (df[col].astype(str) != ""), df[f"{col}_modelo"])
    faltam = len(man) - len(df)
    if faltam:
        print(f"atenção: {faltam} posts da amostra ainda não foram categorizados e ficaram de fora")

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
