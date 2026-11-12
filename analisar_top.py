"""
Levantamento das características mais recorrentes entre as publicações de alto desempenho.

Gera os achados que alimentam o playbook e o agente.
    - frequência de cada categoria da rubrica no top 10%
    - notas médias (força do gancho e clareza)
    - recortes por tema x formato e por plataforma
    - perfis em destaque com tema e formato predominantes
    - exemplos reais (as 3 publicações de maior lift) para cada categoria frequente
    - confidence_flag quando a categoria se apoia em menos de 10 publicações

Saída
    data/achados.md     leitura humana, vai para o README e o playbook
    data/achados.json   mesma informação estruturada, consumida pelo agente

Uso
    python analisar_top.py
"""
import json
from pathlib import Path

import pandas as pd

from rubrica import CAMPOS_CATEGORICOS, CAMPOS_NOTA

DATA = Path("data")
MIN_CONFIANCA = 10


def exemplos(df, mask, n=3):
    ex = df[mask].sort_values("lift", ascending=False).head(n)
    return [{"post_id": r.post_id, "perfil": r.perfil, "url": r.url, "lift": round(float(r.lift), 2),
             "engajamento": round(float(r.engajamento), 5)} for r in ex.itertuples()]


def main():
    cat = pd.read_parquet(DATA / "categorias.parquet")
    n = len(cat)
    achados = {"n_posts_top": n, "criterio": "top 10% de lift por plataforma", "campos": {}, "notas": {},
               "recortes": {}, "perfis_destaque": []}
    md = ["# Achados do top 10%", "",
          f"Base de {n} publicações de alto desempenho categorizadas pela rubrica do TAPI.",
          f"Categorias com menos de {MIN_CONFIANCA} publicações recebem o aviso de baixa confiança (⚠).", ""]

    for campo in CAMPOS_CATEGORICOS:
        serie = cat[campo]
        if campo == "formato_video":
            serie = serie[cat["tipo_post"].isin(["reels", "short", "video"])]
        cont = serie.astype(str).value_counts()
        itens = []
        md += [f"## {campo}", "", "| valor | posts | % | exemplos |", "|---|---|---|---|"]
        for valor, qtd in cont.items():
            mask = (cat[campo].astype(str) == valor)
            ex = exemplos(cat, mask)
            baixa = qtd < MIN_CONFIANCA
            itens.append({"valor": valor, "posts": int(qtd), "pct": round(qtd / len(serie), 3),
                          "confidence_flag": baixa, "exemplos": ex})
            links = " ".join(f"[{e['perfil']}]({e['url']})" for e in ex)
            md.append(f"| {valor}{' ⚠' if baixa else ''} | {qtd} | {qtd / len(serie):.0%} | {links} |")
        achados["campos"][campo] = itens
        md.append("")

    md += ["## Notas médias", "", "| nota | média | mediana |", "|---|---|---|"]
    for c in CAMPOS_NOTA:
        achados["notas"][c] = {"media": round(cat[c].mean(), 2), "mediana": float(cat[c].median())}
        md.append(f"| {c} | {cat[c].mean():.1f} | {cat[c].median():.0f} |")
    md.append("")

    tf = pd.crosstab(cat["tema_principal"], cat["tipo_post"])
    achados["recortes"]["tema_x_tipo_post"] = tf.to_dict()
    md += ["## Tema x tipo de post", "", tf.to_markdown(), ""]

    vf = cat[cat["formato_video"].notna()]
    if not vf.empty:
        tv = pd.crosstab(vf["tema_principal"], vf["formato_video"])
        achados["recortes"]["tema_x_formato_video"] = tv.to_dict()
        md += ["## Tema x formato de vídeo", "", tv.to_markdown(), ""]

    tp = pd.crosstab(cat["tipo_hook"], cat["plataforma"])
    achados["recortes"]["tipo_hook_x_plataforma"] = tp.to_dict()
    md += ["## Tipo de gancho x plataforma", "", tp.to_markdown(), ""]

    seg = pd.crosstab(cat["segmento"], cat["tema_principal"])
    achados["recortes"]["segmento_x_tema"] = seg.to_dict()
    md += ["## Segmento do perfil x tema", "", seg.to_markdown(), ""]

    md += ["## Perfis em destaque", "",
           "| perfil | plataforma | faixa | posts no top | tema predominante | formato predominante | lift mediano |",
           "|---|---|---|---|---|---|---|"]
    for (perfil, plat), g in cat.groupby(["perfil", "plataforma"]):
        if len(g) < 3:
            continue
        fmt = g["formato_video"].dropna()
        item = {
            "perfil": perfil, "plataforma": plat, "faixa": g["faixa"].iloc[0], "posts_top": len(g),
            "tema_predominante": g["tema_principal"].mode().iloc[0],
            "tipo_post_predominante": g["tipo_post"].mode().iloc[0],
            "formato_predominante": fmt.mode().iloc[0] if not fmt.empty else None,
            "lift_mediano": round(float(g["lift"].median()), 2),
        }
        achados["perfis_destaque"].append(item)
    achados["perfis_destaque"].sort(key=lambda x: -x["posts_top"])
    for p in achados["perfis_destaque"][:15]:
        md.append(f"| {p['perfil']} | {p['plataforma']} | {p['faixa']} | {p['posts_top']} | "
                  f"{p['tema_predominante']} | {p['formato_predominante'] or p['tipo_post_predominante']} | {p['lift_mediano']} |")
    md.append("")

    elementos = cat["elementos_top5"].str.split("|").explode().str.strip().str.lower()
    top_el = elementos[elementos != ""].value_counts().head(20)
    achados["elementos_mais_citados"] = top_el.to_dict()
    md += ["## Elementos mais citados pelo modelo (elementos_top5)", "", top_el.rename("posts").to_markdown(), ""]

    md += ["## Leitura", "",
           "Estas são características recorrentes entre publicações de alto desempenho, ou seja, padrões observados.",
           "Elas não garantem resultado e não foram comparadas com o restante da base (extensão opcional do TAPI).", ""]

    (DATA / "achados.md").write_text("\n".join(md), encoding="utf-8")
    (DATA / "achados.json").write_text(json.dumps(achados, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"{n} publicações analisadas -> data/achados.md e data/achados.json")


if __name__ == "__main__":
    main()
