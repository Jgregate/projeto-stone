"""Servidor MCP em memória, sem rede."""
import asyncio

from fastmcp import Client


def test_servidor_lista_e_responde(agente_offline):
    from backend.mcp_server.servidor import mcp

    async def rodar():
        async with Client(mcp) as c:
            nomes = {t.name for t in await c.list_tools()}
            resumo = await c.call_tool("resumo_da_base", {})
            consulta = await c.call_tool("conteudo_mpe", {"mode": "analisar", "query": "finanças para MEI"})
            return nomes, resumo, consulta

    nomes, resumo, consulta = asyncio.run(rodar())
    assert {"conteudo_mpe", "resumo_da_base"} <= nomes
    assert resumo.data["publicacoes_na_base"] > 0
    assert consulta.data["findings"] and consulta.data["reference_posts"]
