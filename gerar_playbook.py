"""
Gera o playbook de conteúdo para a Stone a partir dos achados e do agente (TAPI seção 10).

Conteúdo
    1. como a base foi montada (números)
    2. características mais recorrentes no top 10%, com exemplos reais
    3. perfis em destaque
    4. formatos recomendados (gerados pelo agente no modo recomendar)
    5. cinco criativos prontos para produção, um por segmento, cada um com as publicações que o inspiraram
    6. limitações

Saída
    data/playbook.md   (e data/playbook_criativos.json com os criativos estruturados)

Uso
    python gerar_playbook.py
"""
import json
from pathlib import Path

from agente import carregar, executar

DATA = Path("data")

BRIEFS = [
    ("Alimentação", "alimentacao", "Reels para atrair donos de pequenos restaurantes, confeitarias e deliveries"),
    ("Beleza", "beleza", "Reels para donas de salão de beleza, manicures e esteticistas"),
    ("Varejo e moda", "varejo", "Conteúdo para lojistas de roupa e revendedoras que vendem pelo Instagram"),
    ("Finanças do MEI", "financas", "Carrossel ou Reels sobre precificação e caixa para o MEI"),
    ("Gestão e obrigações", "gestao", "Reels explicando de forma simples uma mudança de regra que afeta o MEI"),
]


def tabela_campo(achados, campo, n=4):
    itens = achados["campos"].get(campo, [])[:n]
    if not itens:
        return []
    linhas = ["| valor | % do top 10% | exemplos reais |", "|---|---|---|"]
    for it in itens:
        ex = " ".join(f"[@{e['perfil']}]({e['url']})" for e in it["exemplos"][:2])
        linhas.append(f"| {it['valor']}{' ⚠' if it['confidence_flag'] else ''} | {it['pct']:.0%} | {ex} |")
    return linhas


def main():
    achados = json.loads((DATA / "achados.json").read_text(encoding="utf-8"))
    cat, base = carregar()

    md = ["# Playbook de conteúdo para micro e pequenos empreendedores", "",
          "Stone · Impulso Stone · Inteli Academy", "",
          "Padrões observados nas publicações de maior engajamento voltadas a MPEs no Instagram e no YouTube Shorts. "
          "Os padrões descrevem o que aparece com frequência entre os posts de alto desempenho. Eles orientam a criação, "
          "mas não garantem resultado.", "",
          "## 1. A base", "",
          f"- {len(base)} publicações de {base['perfil'].nunique()} perfis e canais, de "
          f"{base['publicado_em'].min():%m/%Y} a {base['publicado_em'].max():%m/%Y}",
          "- Métrica (curtidas + comentários) ÷ seguidores",
          "- Alto desempenho é o top 10% de lift, ou seja, o engajamento do post dividido pela mediana do próprio perfil. "
          "Isso compara cada post com o desempenho normal da conta e isola o efeito do conteúdo",
          f"- {len(cat)} publicações de alto desempenho categorizadas pela rubrica do TAPI", ""]

    md += ["## 2. O que aparece no topo", ""]
    for titulo, campo in [("Tipo de gancho", "tipo_hook"), ("Tema", "tema_principal"), ("Formato de vídeo", "formato_video"),
                          ("Tom", "tom"), ("Chamada para ação", "tipo_cta")]:
        md += [f"### {titulo}", ""] + tabela_campo(achados, campo) + [""]

    md += ["## 3. Perfis em destaque", "", "| perfil | plataforma | posts no top | tema | formato |", "|---|---|---|---|---|"]
    for p in achados["perfis_destaque"][:10]:
        md.append(f"| @{p['perfil']} | {p['plataforma']} | {p['posts_top']} | {p['tema_predominante']} | "
                  f"{p['formato_predominante'] or p['tipo_post_predominante']} |")
    md.append("")

    print("gerando recomendações...")
    rec = executar({"mode": "recomendar", "query": "Quais formatos, ganchos e temas a Stone deve priorizar no Instagram "
                                                     "para engajar micro e pequenos empreendedores?"})
    md += ["## 4. Recomendações para a Stone", "", rec.explanation, ""] + [f"- {r}" for r in rec.recomendacoes] + [""]

    md += ["## 5. Criativos prontos para produção", ""]
    criativos = []
    for i, (nome, seg, pedido) in enumerate(BRIEFS, 1):
        print(f"gerando criativo {i}/5 ({nome})...")
        s = executar({"mode": "gerar_criativo", "query": pedido, "segment": seg, "n_criativos": 1})
        if not s.creatives:
            md += [f"### {i}. {nome}", "", "_não foi possível gerar este criativo nesta execução_", ""]
            continue
        c = s.creatives[0]
        refs = {p.post_id: p for p in s.reference_posts}
        criativos.append({"segmento": nome, **c.model_dump()})
        md += [f"### {i}. {nome} · {c.titulo}", "",
               f"**Formato** {c.formato}" + (" · ⚠ padrão apoiado em poucos posts" if s.confidence_flag else ""), "",
               f"**Gancho** {c.gancho}", "", "**Roteiro**", ""]
        md += [f"- {x.tempo} · {x.acao}" for x in c.roteiro]
        md += ["", f"**Legenda** {c.legenda}", "", f"**CTA** {c.cta}", "", f"**Por que** {c.justificativa}", "",
               "**Inspirado em**", ""]
        md += [f"- [@{refs[i_].perfil}]({refs[i_].url}) · {refs[i_].tipo_post} · lift {refs[i_].lift}"
               for i_ in c.inspirado_em if i_ in refs]
        md.append("")

    md += ["## 6. Limitações", "",
           "- Os padrões são de publicações de alto desempenho e não foram comparados com o restante da base.",
           "- Métricas públicas (curtidas e comentários) não medem conversão em leads.",
           "- A categorização é automática e foi validada por amostragem manual, com concordância variável por campo.",
           "- A rubrica do TAPI não tem categorias para notícias e propaganda institucional, que aparecem com frequência.", ""]

    (DATA / "playbook.md").write_text("\n".join(md), encoding="utf-8")
    (DATA / "playbook_criativos.json").write_text(json.dumps(criativos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nplaybook com {len(criativos)} criativos -> data/playbook.md")


if __name__ == "__main__":
    main()
