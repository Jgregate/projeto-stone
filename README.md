# Conteúdo de alto engajamento para micro e pequenos empreendedores

Projeto da liga de IA do Inteli Academy para a Stone (Impulso Stone). Mapeia as publicações de maior engajamento voltadas a micro e pequenos empreendedores (MPEs) no Instagram e no YouTube Shorts, categoriza suas características e transforma os padrões em recomendações e criativos para a Stone, sempre apoiados em publicações reais.

**Pergunta norteadora.** Quais características de conteúdo, formato e perfil de criador estão presentes nas publicações de maior engajamento voltadas a MPEs, e como transformar esse conhecimento em criativos para a Stone?

## Resultados em números

| etapa | resultado |
|---|---|
| Perfis do Instagram | 31 aprovados de 62 candidatos |
| Canais do YouTube | 14 de 20 encontrados |
| Publicações na base | 4.841 (3.866 do Instagram e 975 Shorts) |
| Publicações com métrica válida | 4.314 |
| Período | 22/11/2024 a 09/11/2026 |
| Publicações de alto desempenho | 430 (top 10% de lift por plataforma) |
| Publicações categorizadas | 425 |
| Validação manual | 49 publicações, anotação cega |

## Arquitetura

```
coleta_instagram.py  ─┐
coleta_youtube.py    ─┼─> montar_base.py ─> categorizar*.py ─> analisar_top.py ─> agente.py ─┬─> servidor_mcp.py
validar_perfis.py    ─┘   (ranking, top 10%,  (rubrica JSON,     (achados e        (LangGraph)  ├─> demo.py
                           mídias, CTA)        Pydantic)         perfis)                      └─> gerar_playbook.py
```

O agente segue o fluxo interpretar, consultar a base, buscar referências e, conforme o modo, redigir recomendações ou criar criativos. O modelo de linguagem só orquestra e redige. Todos os números, exemplos e links vêm da base, e cada criativo aponta para as publicações que o inspiraram. Referências que não existem na base são descartadas.

**Contrato da ferramenta (Pydantic)**
- Entrada `mode` (analisar, recomendar ou gerar_criativo), `query`, `segment` e `filters`
- Saída `findings`, `reference_posts`, `creatives`, `recomendacoes`, `confidence_flag` e `explanation`
- Cada execução fica registrada em `data/execucoes.jsonl`

## Instalação e execução

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # preencha as chaves
```

| passo | comando |
|---|---|
| Validar perfis | `python validar_perfis.py --entrada candidatos.csv` |
| Coletar Instagram | `python coleta_instagram.py --perfis perfis.csv --max-posts 300 --janela-dias 730` |
| Coletar YouTube | `python coleta_youtube.py --canais canais_youtube.csv --max-videos 150` |
| Montar base e ranking | `python montar_base.py` |
| Categorizar (híbrido) | `python categorizar_texto.py` |
| Gerar achados | `python analisar_top.py` |
| Validação manual | `python validacao.py amostra`, anotar, `python validacao.py avaliar` |
| Demonstração | `python demo.py` |
| Playbook | `python gerar_playbook.py` |
| Servidor MCP | `python servidor_mcp.py` |
| Agente como função | `from agente import executar` |

## Dados

**Origem e licença.** Dados públicos de perfis profissionais, coletados por rotas oficiais. O Instagram foi coletado pelo endpoint Business Discovery da Instagram Graph API (Meta), com app em modo de desenvolvimento e token de usuário. O YouTube foi coletado pela YouTube Data API v3, lendo a playlist de uploads de cada canal (1 unidade de cota por página, em vez da busca, que custa 100). Nenhum scraping foi usado. As imagens baixadas para a categorização são de terceiros e não fazem parte do repositório.

**Seleção de perfis.** Os candidatos vieram de quatro fontes, o ecossistema Stone (Impulso Stone, Stone e parceiros do relatório do case), a curadoria do setor (Sebrae, Jornal Contábil, PEGN, Contabilizei), os concorrentes citados na aula (InfinitePay, PagBank, Mercado Pago, Cora, Conta Azul) e criadores MPE encontrados por busca no Instagram por segmento. O `validar_perfis.py` aprova só contas profissionais ativas nos últimos 12 meses e limita as contas grandes a 15, para reduzir o viés de sobrevivência. Contas não oficiais e um banco generalista foram excluídos manualmente, com o motivo registrado em `perfis_validados.csv`.

**Critérios.** Só entram publicações com pelo menos 14 dias (métricas estabilizadas) e até 24 meses. O perfil precisa estar ativo nos últimos 12 meses, e a janela de posts foi ampliada para 24 meses para garantir volume em contas que publicam pouco. Shorts são vídeos de até 180 segundos.

## Metodologia

**Métrica.** Taxa de engajamento igual a (curtidas + comentários) ÷ seguidores, como define o TAPI.

**Alto desempenho.** A primeira versão usou o top 10% dentro de cada faixa de tamanho de conta, e um único perfil (@nathfinancas) ficou com 32% do topo, porque a audiência dele engaja muito mais que a das outras contas grandes. A versão final usa o **lift**, que é o engajamento do post dividido pela mediana do próprio perfil. O top 10% passa a ser os posts que mais superam o desempenho normal da própria conta, o que isola o efeito do conteúdo. A maior participação de um perfil caiu para 16,7%. Só entram perfis com pelo menos 10 posts válidos.

**Indicador de lead.** Presença e tipo de chamada para ação, detectados por regras na legenda (`montar_base.py`) e pela rubrica.

**Categorização.** A rubrica fixa do TAPI (seção 6.2) está em `rubrica.py`, com respostas em JSON validadas por Pydantic.
1. A primeira tentativa usou o Groq (Qwen 3.8 27B com imagem), mas o plano gratuito comporta uns 50 posts por dia, porque cada imagem conta 2.048 tokens.
2. A segunda usou um modelo local de visão (Qwen3-VL 2B no Ollama). Ela entrou em colapso de respostas, com 100% dos vídeos como talking head, 100% dos perfis como empreendedor real, 97% com CTA e notas médias de 9,9. Essa rodada está guardada em `categorias_vlm.parquet` para comparação.
3. A versão final é **híbrida por fonte**. Os campos de texto vêm do Qwen 3.8 27B (Groq) lendo só a legenda, em lotes de 10. O rosto vem do detector Haar do OpenCV, que é determinístico. O texto na tela vem do modelo de visão local. O ritmo de cortes fica nulo, porque não é observável pela capa (Nível 1 do TAPI).

**Validação.** 50 publicações sorteadas com estratificação por plataforma e tipo de post (49 entraram, uma ficou sem categorização), anotadas às cegas.

| campo | concordância | kappa |
|---|---|---|
| tem_rosto | 82% | 0,60 (substancial) |
| texto_na_tela | 65% | 0,22 (fraco) |
| tem_cta | 57% | 0,07 (fraco) |

Os campos tipo_hook, tema_principal, tom e tipo_cta foram anotados com categorias livres, e não com os valores da rubrica, então não foram comparados. Essas anotações mostram uma lacuna da rubrica, porque "notícias" (reforma tributária, limite do MEI) e "propaganda" de produto aparecem com frequência no topo e não têm categoria própria. Na leitura das divergências de CTA, a anotação humana considerou pedidos como "baixe o app" e "inscreva-se", que a rubrica não cobre bem. O formato de vídeo não foi avaliado, porque a anotação deixou o campo em branco.

## Principais achados

Os números abaixo descrevem o top 10% e são padrões observados, sem garantia de resultado. O detalhe completo está em `data/achados.md`.

- **Gancho.** Curiosidade é o mais comum (32%), seguido de promessa (18%) e pergunta (16%). Dor aparece em 9%.
- **Tema.** Finanças lidera (27%), seguido de marketing, gestão, motivação e ferramentas de pagamento (15% a 16% cada).
- **Formato de vídeo.** Depoimento (12%), tutorial (11%) e humor ou esquete (10%) superam o talking head (8%).
- **Tom.** Informal (43%) e inspiracional (26%).
- **CTA.** 58% do topo não tem chamada para ação explícita. Quando há, o link na bio domina (21%).
- **Tipo de post.** Reels aparecem um pouco mais no topo do que na base (razão 1,1), e imagem estática bem menos (0,6).

## Limitações

- Padrões do top 10% sem comparação com o restante da base (extensão opcional do TAPI).
- Métricas públicas não medem conversão em leads. 11% das publicações ficaram sem métrica por curtidas ocultas.
- Só contas profissionais são acessíveis pela API oficial. A faixa micro ficou com 7 perfis no Instagram, abaixo da meta de 12, e o YouTube micro tem só 17 posts.
- O Business Discovery não fornece salvamentos nem compartilhamentos.
- O formato de vídeo é inferido da legenda e da capa, sem assistir ao vídeo.
- Validação parcial, com 3 campos comparáveis e concordância fraca em texto na tela e CTA.
- Modelos e limites gratuitos podem mudar. Os IDs usados ficam registrados em cada arquivo de saída.

## Possibilidades de evolução

- Comparar as características do top 10% com o restante da base para separar o que é sucesso do que é só comum no nicho.
- Ampliar a rubrica com categorias de notícia e propaganda, e de CTA de aplicativo ou inscrição.
- Nível 2 do TAPI, com frames e transcrição dos vídeos (faster-whisper ou Whisper no Groq).
- RAG sobre as publicações de alto desempenho e análise de intenção nos comentários.
- Usar os Insights do Instagram da Stone para medir conversão real.

## Estrutura

```
coleta_instagram.py   coleta oficial do Instagram (Business Discovery)
coleta_youtube.py     coleta oficial do YouTube Shorts
validar_perfis.py     validação e balanceamento dos perfis
montar_base.py        base unificada, lift, top 10%, CTA por regra e mídias
rubrica.py            rubrica do TAPI em Pydantic
categorizar.py        categorização multimodal (Groq ou Ollama)
categorizar_texto.py  categorização híbrida final
validacao.py          amostra e concordância da validação manual
analisar_top.py       achados, recortes e perfis em destaque
agente.py             agente LangGraph e função integrável
servidor_mcp.py       servidor MCP (FastMCP)
demo.py               demonstração executável
gerar_playbook.py     playbook com 5 criativos
```
