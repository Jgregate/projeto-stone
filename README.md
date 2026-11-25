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
| Testes | pytest |

## Estrutura de pastas

```
backend/
  ingestion/         validação de perfis e coleta (Instagram e YouTube)
  analysis/          base, engajamento, lift, top 10% e achados
  categorization/    categorização pela rubrica
  validation/        validação manual da categorização
  schemas/           contratos Pydantic (ferramenta e rubrica)
  prompts/           prompts da rubrica, da categorização e do agente
  graph/             agente LangGraph e ferramentas
  mcp_server/        servidor MCP
  api/               API do frontend
frontend/            página da demonstração
data/                perfis, dados processados, validação e modelos de apoio
outputs/             coleta, análise, validação, demo, playbook e execuções
docs/                documentação, capturas, diagrama e figuras
notebooks/           análises exploratórias (vazia por enquanto)
scripts/             demo, playbook, figuras e capturas
tests/               testes automatizados
_to_delete/          arquivos sem uso, para revisão antes de apagar
```

## O que é cada pasta

**`backend/`** é o núcleo em Python. `ingestion/` valida os perfis candidatos e coleta as publicações pela Instagram Graph API (Business Discovery) e pela YouTube Data API v3, com cache das respostas e espera em caso de limite; `analysis/` monta a base unificada, calcula a taxa de engajamento normalizada, o lift e o top 10% e levanta as características recorrentes; `categorization/` aplica a rubrica com o Groq, o modelo local e o OpenCV; `validation/` sorteia a amostra, gera a página de anotação cega e calcula a concordância; `schemas/` define em Pydantic o contrato da ferramenta e a rubrica; `prompts/` guarda os prompts da rubrica, da categorização e do agente; `graph/` tem o agente LangGraph e as ferramentas `consultar_base`, `buscar_referencias` e `gerar_criativos`; `mcp_server/` expõe o agente por MCP; e `api/` serve a página e a API do frontend. Na raiz de `backend/` ficam `config.py`, com todos os caminhos de dados e saídas, e `run.py`, o CLI do agente.

**`frontend/`** é a página da demonstração (abas Consultar o agente e Visão da base), em HTML, CSS e JavaScript sem build, com as fontes. **`data/`** guarda as listas de perfis e canais (`perfis/`), a base e as categorias (`processed/`), a anotação manual (`validacao/`) e o detector de rostos (`modelos/`). As respostas brutas das APIs e as capas das publicações ficam em `raw/`, fora do git. **`outputs/`** guarda os registros da coleta, os achados e o relatório da base, o resultado da validação, as saídas da demo e do playbook e o registro de cada execução do agente (`execucoes/execucoes.jsonl`). **`docs/`** tem a documentação completa, as capturas de tela, o diagrama de arquitetura e as figuras de resultados. **`scripts/`** roda a demo por script, gera o playbook e refaz as figuras e as capturas da documentação. **`tests/`** tem 30 testes offline, com a base real e um modelo de linguagem falso. **`_to_delete/`** reúne arquivos que não são usados (fontes antigas do frontend e o antigo `frontend/requirements.txt`) para conferência antes de apagar.

## Como rodar a demo

É preciso Python 3.14. A base já coletada está em `data/`, então a demo não chama as APIs de coleta. Na raiz do projeto, instale as dependências e crie o `.env`.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # preencha GROQ_API_KEY
```

Depois, um único comando sobe a API e a página e abre o navegador em http://127.0.0.1:8000.

```powershell
python -m backend.api
```

A página tem três pedidos prontos, um para cada modo (analisar, recomendar e criar criativo). Sem a chave do Groq, os achados e as publicações de referência continuam aparecendo, sem os textos do modelo. O servidor MCP sobe com `python -m backend.mcp_server`, a função Python é `from backend.graph.agente import executar` e os testes rodam com `python -m pytest`. Os demais comandos estão na seção [Como usar](docs/documentacao.md#2-como-usar) da documentação.

Licença [PREENCHER].
