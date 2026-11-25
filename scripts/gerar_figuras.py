"""
Gera as figuras de resultados da documentação em docs/resultados/figuras.

Lê outputs/analise/achados.json, data/processed/base.parquet e os números de outputs/validacao/validacao_resultado.md.

Uso (na raiz do repositório)
    python scripts/gerar_figuras.py
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from backend.config import OUT_ANALISE, PROCESSED  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "docs" / "resultados" / "figuras"
OUT.mkdir(parents=True, exist_ok=True)
A = json.loads((OUT_ANALISE / "achados.json").read_text(encoding="utf-8"))

VERDE, AZUL, TRILHO, TINTA, TINTA2, GRADE = "#008f00", "#2a78d6", "#e3ebe6", "#1b221f", "#424a53", "#e1e0d9"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRADE,
                     "axes.labelcolor": TINTA2, "xtick.color": TINTA2, "ytick.color": TINTA, "figure.dpi": 150})

ROT = {"curiosidade": "Curiosidade", "promessa": "Promessa", "pergunta": "Pergunta", "nenhum": "Nenhum", "dor": "Dor",
       "polemica": "Polêmica", "numero": "Número", "financas": "Finanças", "marketing": "Marketing", "gestao": "Gestão",
       "motivacao": "Motivação", "ferramentas_maquininha": "Ferramentas e maquininha",
       "historia_de_empreendedor": "História de empreendedor", "vendas": "Vendas", "atendimento": "Atendimento",
       "depoimento": "Depoimento", "tutorial": "Tutorial", "humor_esquete": "Humor ou esquete",
       "talking_head": "Pessoa falando para a câmera", "bastidores": "Bastidores", "lista_dicas": "Lista de dicas",
       "antes_depois": "Antes e depois", "informal": "Informal", "inspiracional": "Inspiracional", "tecnico": "Técnico",
       "humoristico": "Humorístico", "link_na_bio": "Link na bio", "comentar": "Comentar", "seguir": "Seguir",
       "compartilhar": "Compartilhar", "salvar": "Salvar", "dm": "Mensagem direta",
       "reels": "Reels", "short": "Short", "carrossel": "Carrossel", "imagem": "Imagem"}


def barras(ax, campo, titulo):
    itens = A["campos"][campo]
    nomes = [ROT.get(i["valor"], i["valor"]) for i in itens][::-1]
    pcts = [i["pct"] * 100 for i in itens][::-1]
    posts = [i["posts"] for i in itens][::-1]
    fraco = [i["confidence_flag"] for i in itens][::-1]
    y = range(len(itens))
    ax.barh(y, [100] * len(itens), color=TRILHO, height=0.55)
    ax.barh(y, pcts, color=[VERDE if not f else "white" for f in fraco], edgecolor=[VERDE] * len(itens),
            hatch=["" if not f else "////" for f in fraco], height=0.55, linewidth=0.8)
    for yi, p, n in zip(y, pcts, posts):
        ax.text(101, yi, f"{p:.0f}%  ({n})", va="center", fontsize=8.5, color=TINTA)
    ax.set_yticks(list(y), nomes)
    ax.set_xlim(0, 125)
    ax.set_xticks([])
    for s in ["top", "right", "bottom"]:
        ax.spines[s].set_visible(False)
    ax.set_title(titulo, loc="left", fontsize=11, fontweight="bold", color=TINTA)


fig, axs = plt.subplots(2, 2, figsize=(12, 7.5))
barras(axs[0, 0], "tipo_hook", "Tipo de gancho")
barras(axs[0, 1], "tema_principal", "Tema principal")
barras(axs[1, 0], "formato_video", "Formato de vídeo (só Reels e Shorts)")
barras(axs[1, 1], "tipo_cta", "Chamada para ação")
fig.suptitle("Características mais recorrentes no top 10% (425 publicações categorizadas)", x=0.01, ha="left",
             fontsize=13, fontweight="bold", color=TINTA)
fig.text(0.01, 0.005, "Barra listrada indica menos de 10 publicações (baixa confiança). Fonte outputs/analise/achados.json.",
         fontsize=8.5, color=TINTA2)
fig.tight_layout(rect=(0, 0.02, 1, 0.96))
fig.savefig(OUT / "frequencias_top10.png")

# tipo de post, base x top
b = pd.read_parquet(PROCESSED / "base.parquet")
val = b[b["metrica_valida"]]
top = b[b["alto_desempenho"]]
pb = val["tipo_post"].value_counts(normalize=True) * 100
pt = top["tipo_post"].value_counts(normalize=True) * 100
ordem = ["reels", "short", "carrossel", "imagem"]
fig, ax = plt.subplots(figsize=(8, 4))
x = range(len(ordem))
w = 0.36
ax.bar([i - w / 2 - 0.01 for i in x], [pb[o] for o in ordem], w, color=AZUL, label="Base com métrica válida")
ax.bar([i + w / 2 + 0.01 for i in x], [pt[o] for o in ordem], w, color=VERDE, label="Top 10%")
for i, o in enumerate(ordem):
    ax.text(i - w / 2, pb[o] + 1, f"{pb[o]:.1f}%".replace(".", ","), ha="center", fontsize=8.5, color=TINTA)
    ax.text(i + w / 2, pt[o] + 1, f"{pt[o]:.1f}%".replace(".", ","), ha="center", fontsize=8.5, color=TINTA)
    ax.text(i, -11, f"razão {pt[o] / pb[o]:.2f}".replace(".", ","), ha="center", fontsize=8.5, color=TINTA2)
ax.set_xticks(list(x), [ROT[o] for o in ordem])
ax.tick_params(axis="x", pad=4, length=0)
ax.set_ylim(0, 65)
ax.yaxis.grid(True, color=GRADE, linewidth=0.8)
ax.set_axisbelow(True)
for s in ["top", "right", "left"]:
    ax.spines[s].set_visible(False)
ax.set_ylabel("% das publicações")
ax.legend(frameon=False, loc="upper right")
ax.set_title("Tipo de publicação na base e no top 10%", loc="left", fontsize=12, fontweight="bold", color=TINTA)
fig.text(0.01, 0.01, f"Fonte data/processed/base.parquet ({len(val):,} publicações com métrica válida, {len(top)} no top 10%).".replace(",", "."), fontsize=8.5, color=TINTA2)
fig.tight_layout(rect=(0, 0.05, 1, 1))
fig.savefig(OUT / "tipo_post_base_vs_top.png")

# validação manual, campos comparáveis (valores de outputs/validacao/validacao_resultado.md)
campos = [("tem_rosto", 0.82, 0.60), ("texto_na_tela", 0.65, 0.22), ("tem_cta", 0.57, 0.07)]
fig, ax = plt.subplots(figsize=(8, 3))
y = range(len(campos))
ax.barh(y, [100] * 3, color=TRILHO, height=0.5)
ax.barh(y, [c[1] * 100 for c in campos], color=VERDE, height=0.5)
for yi, c in zip(y, campos):
    ax.text(101, yi, f"{c[1]:.0%} de concordância, kappa {c[2]:.2f}".replace(".", ","), va="center", fontsize=9, color=TINTA)
ax.set_yticks(list(y), ["Rosto na capa", "Texto na tela", "Tem chamada para ação"])
ax.invert_yaxis()
ax.set_xlim(0, 160)
ax.set_xticks([])
for s in ["top", "right", "bottom"]:
    ax.spines[s].set_visible(False)
ax.set_title("Validação manual, campos comparáveis (49 publicações)", loc="left", fontsize=12, fontweight="bold", color=TINTA)
fig.text(0.01, 0.02, "Fonte outputs/validacao/validacao_resultado.md.", fontsize=8.5, color=TINTA2)
fig.tight_layout(rect=(0, 0.05, 1, 1))
fig.savefig(OUT / "validacao_manual.png")
print("ok", sorted(p.name for p in OUT.iterdir()))
