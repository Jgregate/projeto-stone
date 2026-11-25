"""
Servidor MCP do agente de conteúdo (FastMCP).

Expõe o agente como ferramenta para qualquer cliente MCP (Claude Desktop, Cursor, etc.).

Rodar (na raiz do repositório)
    python -m backend.mcp_server

Configurar no Claude Desktop (claude_desktop_config.json)
    {
      "mcpServers": {
        "stone-conteudo": {
          "command": "C:\\\\caminho\\\\projeto-stone\\\\.venv\\\\Scripts\\\\python.exe",
          "args": ["-m", "backend.mcp_server"],
          "cwd": "C:\\\\caminho\\\\projeto-stone"
        }
      }
    }
"""
from typing import Optional

from fastmcp import FastMCP

from backend.graph.agente import executar

mcp = FastMCP("stone-conteudo")


@mcp.tool()
def conteudo_mpe(mode: str, query: str, segment: Optional[str] = None, plataforma: Optional[str] = None,
                 tipo_post: Optional[str] = None, faixa: Optional[str] = None, n_criativos: int = 1) -> dict:
    """Analisa publicações de alto desempenho voltadas a micro e pequenos empreendedores e gera recomendações
    ou criativos para a Stone, sempre com as publicações reais de referência.

    mode        analisar | recomendar | gerar_criativo
    query       pergunta ou pedido em linguagem natural
    segment     alimentacao | beleza | varejo | financas | gestao | marketing (opcional)
    plataforma  instagram | youtube (opcional)
    tipo_post   reels | carrossel | imagem | short (opcional)
    faixa       micro | medio | grande, tamanho do perfil (opcional)
    n_criativos de 1 a 5, só no modo gerar_criativo
    """
    saida = executar({"mode": mode, "query": query, "segment": segment, "n_criativos": n_criativos,
                      "filters": {"plataforma": plataforma, "tipo_post": tipo_post, "faixa": faixa}})
    return saida.model_dump()


@mcp.tool()
def resumo_da_base() -> dict:
    """Números gerais da base (volume, período, perfis e critério de alto desempenho)."""
    from backend.graph.agente import carregar
    cat, base = carregar()
    return {
        "publicacoes_na_base": int(len(base)),
        "publicacoes_top10_categorizadas": int(len(cat)),
        "perfis": int(base["perfil"].nunique()),
        "periodo": [str(base["publicado_em"].min().date()), str(base["publicado_em"].max().date())],
        "criterio": "top 10% de lift (engajamento do post / mediana do próprio perfil), por plataforma",
        "metrica": "(curtidas + comentários) / seguidores",
    }


if __name__ == "__main__":
    mcp.run()
