"""
Demonstração executável do agente (TAPI seção 10): análise, referências, criativo e justificativa.

Roda três pedidos, um de cada modo, mostra no terminal e salva tudo em data/demo.md.

Uso
    python demo.py
"""
from pathlib import Path

from agente import executar

PEDIDOS = [
    {"mode": "analisar", "query": "Quais formatos e ganchos mais aparecem nas publicações de alto desempenho de pequenos negócios de alimentação?"},
    {"mode": "recomendar", "query": "Como a Stone pode aumentar o engajamento de salões de beleza no Instagram?"},
    {"mode": "gerar_criativo", "query": "Preciso de um Reels para atrair donos de pequenos restaurantes", "n_criativos": 1},
]


def em_markdown(s):
    md = [f"## {s.mode} · {s.query}", "",
          f"Publicações analisadas {s.n_posts_analisados} · filtros {s.filtros_aplicados}"
          + (" · ⚠ baixa confiança" if s.confidence_flag else ""), "", "### Explicação", "", s.explanation, ""]
    if s.recomendacoes:
        md += ["### Recomendações", ""] + [f"- {r}" for r in s.recomendacoes] + [""]
    for c in s.creatives:
        md += [f"### Criativo · {c.titulo}", "", f"**Formato** {c.formato}", "", f"**Gancho** {c.gancho}", "",
               "**Roteiro**", ""] + [f"- {x.tempo} · {x.acao}" for x in c.roteiro] + \
              ["", f"**Legenda** {c.legenda}", "", f"**CTA** {c.cta}", "", f"**Inspirado em** {', '.join(c.inspirado_em)}",
               "", f"**Justificativa** {c.justificativa}", ""]
    md += ["### Principais achados", "", "| campo | valor | posts | % | confiança |", "|---|---|---|---|---|"]
    vistos = set()
    for a in s.findings:
        if a.campo in vistos:
            continue
        vistos.add(a.campo)
        md.append(f"| {a.campo} | {a.valor} | {a.posts} | {a.pct:.0%} | {'⚠ baixa' if a.confidence_flag else 'ok'} |")
    md += ["", "### Publicações de referência", "", "| post | perfil | tipo | lift | link |", "|---|---|---|---|---|"]
    md += [f"| {p.post_id} | @{p.perfil} | {p.tipo_post} | {p.lift} | {p.url} |" for p in s.reference_posts]
    return "\n".join(md + [""])


def main():
    partes = ["# Demonstração do agente", ""]
    for p in PEDIDOS:
        print(f"\n>>> {p['mode']}: {p['query']}")
        s = executar(p)
        texto = em_markdown(s)
        print(texto)
        partes.append(texto)
    Path("data/demo.md").write_text("\n".join(partes), encoding="utf-8")
    print("\nsalvo em data/demo.md")


if __name__ == "__main__":
    main()
