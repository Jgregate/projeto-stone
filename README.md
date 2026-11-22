# Jade

**Agente que encontra o que faz as publicações para micro e pequenos empreendedores engajarem e transforma isso em criativos para a Stone, sempre ligados a posts reais.**

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-1C3C3C)
![Pydantic](https://img.shields.io/badge/Pydantic-contrato-E92063)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-FastMCP-555555)

Desenvolvido no **Case Stone** (Inteli Academy, Impulso Stone). A documentação completa, com base de dados, métrica, rubrica, arquitetura, contrato, decisões, resultados, testes e limitações, está em [`docs/documentacao.md`](docs/documentacao.md).

## Problema

A equipe de conteúdo da Stone fala com micro e pequenos empreendedores (MPEs) no Instagram e no YouTube, mas escolher gancho, tema e formato costuma depender de intuição ou de exemplos soltos. Comparar publicações pelo número de curtidas também engana, porque contas maiores sempre têm mais curtidas, e um perfil com audiência muito engajada pode parecer a regra quando é a exceção. Pedir ideias direto a um modelo de linguagem gera texto plausível, sem números verificáveis e sem dizer de onde a ideia saiu.

## Solução

Uma base de 4.841 publicações de 37 perfis e canais, coletada pelas APIs oficiais do Instagram e do YouTube, ranqueada pela taxa de engajamento normalizada ((curtidas + comentários) ÷ seguidores) e pelo lift sobre a mediana do próprio perfil. As 430 publicações do top 10% foram categorizadas por uma rubrica fixa validada com Pydantic e conferidas por amostragem manual. Sobre essa base, um agente em LangGraph analisa padrões, recomenda ações e escreve criativos (gancho, roteiro, legenda e chamada para ação). O modelo de linguagem só interpreta e redige. Contagens, percentuais e links vêm da base, e cada criativo aponta para as publicações que o inspiraram. O agente é uma função Python, um servidor MCP e um frontend de demonstração.

| Camada | Stack |
|---|---|
| Coleta | Instagram Graph API (Business Discovery), YouTube Data API v3, requests |
| Dados | pandas, pyarrow |
| Categorização | Groq (`qwen/qwen3.8-27b`), Ollama (`qwen3-vl:2b-instruct`), OpenCV, Pydantic |
| Agente | LangGraph, Groq (`openai/gpt-oss-120b`), Pydantic |
| Interfaces | função `executar()`, FastMCP, FastAPI com página em HTML, CSS e JavaScript |

## Estrutura de pastas

```
validar_perfis.py      validação e balanceamento dos perfis do Instagram
coleta_instagram.py    coleta oficial do Instagram (Business Discovery)
coleta_youtube.py      coleta oficial do YouTube Shorts
montar_base.py         base unificada, engajamento, lift, top 10%, chamada para ação e capas
rubrica.py             rubrica do TAPI em Pydantic e prompt da categorização
categorizar.py         categorização com imagem (Groq ou Ollama)
categorizar_texto.py   categorização híbrida final
validacao.py           amostra e concordância da validação manual
anotar.py              página local para a anotação cega
analisar_top.py        achados, recortes e perfis em destaque
agente.py              agente LangGraph, contrato e função executar()
servidor_mcp.py        servidor MCP (FastMCP)
demo.py                demonstração por script
gerar_playbook.py      playbook com cinco criativos
candidatos.csv, perfis.csv, perfis_validados.csv, canais_youtube.csv
frontend/              API e página da demonstração
data/                  base, categorias, achados, logs e saídas
modelos/               detector de rostos do OpenCV
docs/                  documentação, capturas, diagrama e figuras
```

## O que é cada pasta

**Raiz.** Ficam os scripts do pipeline, listados acima na ordem de uso, de `validar_perfis.py` a `analisar_top.py`. `agente.py` tem o grafo, os modelos `Entrada` e `Saida` e a função `executar()`, e `servidor_mcp.py`, `demo.py` e `gerar_playbook.py` usam essa função. Os CSVs da raiz são as listas de perfis e canais, com origem e segmento de cada um.

**`frontend/`** tem `app.py`, uma API FastAPI que chama `executar()` e acrescenta dados da base, e `static/`, com a página (abas Consultar o agente e Visão da base), os estilos e as fontes. **`data/`** guarda a base (`base.parquet`, `top10.csv`), as categorias (`categorias.parquet` e a rodada só com o modelo local em `categorias_vlm.parquet`), os achados (`achados.md`, `achados.json`), os logs de coleta, a validação manual, as saídas da demonstração e do playbook e o registro de cada execução do agente (`execucoes.jsonl`). As respostas brutas das APIs (`raw/`, `raw_youtube/`) e as capas (`midia/`) ficam fora do git. **`modelos/`** tem o detector Haar usado para identificar rosto na capa. **`docs/`** tem a documentação completa, as capturas de tela, o diagrama de arquitetura em Mermaid e as figuras de resultados.

## Como rodar a demo

É preciso Python 3.14 e um `.env` na raiz com `GROQ_API_KEY` e `GROQ_AGENT_MODEL` (as demais variáveis estão na [seção Como usar](docs/documentacao.md#2-como-usar) da documentação). A base já coletada está em `data/`, então a demo não chama as APIs de coleta.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r frontend\requirements.txt
```

Depois, na raiz do projeto, um único comando sobe a API e a página e abre o navegador em http://127.0.0.1:8000.

```powershell
.\.venv\Scripts\python.exe frontend\app.py
```

A página tem três pedidos prontos, um para cada modo (analisar, recomendar e criar criativo). Sem a chave do Groq, os achados e as publicações de referência continuam aparecendo, sem os textos do modelo.
