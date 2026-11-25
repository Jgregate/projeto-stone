"""Prompt da categorização híbrida (campos de texto), usado por backend/categorization/categorizar_texto.py."""

PROMPT = """Você analisa publicações de redes sociais voltadas a micro e pequenos empreendedores (MPEs) no Brasil.
Você recebe uma lista de publicações, cada uma com id, plataforma, tipo_post, perfil e texto (legenda, ou título e descrição).
Classifique CADA publicação só com base no texto. Responda SOMENTE com JSON no formato {"resultados": [ ... ]},
um objeto por publicação, na mesma ordem, com exatamente estas chaves.

id  o mesmo id recebido
formato_video  só para reels, video ou short, e só se o texto permitir inferir; senão null
  talking_head | tutorial | bastidores | antes_depois | humor_esquete | depoimento | lista_dicas | trend
hook_primeiros_3s  a primeira frase do texto, até 15 palavras
tipo_hook  pergunta | promessa | dor | numero | polemica | curiosidade | nenhum
forca_hook_0a10  quanto a primeira frase prende um MPE
tema_principal  vendas | financas | marketing | atendimento | gestao | motivacao | ferramentas_maquininha | historia_de_empreendedor
criador_e_empreendedor_real  true só se quem fala é uma pessoa contando a própria experiência de negócio; perfis de marca, banco ou instituição são false
prova_social  true só se há números de resultado, depoimento, cliente ou validação de terceiros explícitos
tom  informal | tecnico | inspiracional | humoristico
usa_linguagem_regional  gírias ou expressões regionais marcadas
clareza_mensagem_0a10
tem_cta  true só se o texto pede explicitamente uma ação (comentar, salvar, clicar no link, mandar mensagem, seguir, compartilhar)
tipo_cta  comentar | salvar | link_na_bio | dm | seguir | compartilhar | nenhum (nenhum quando tem_cta for false)
oferta_ou_beneficio_explicito  promete benefício concreto ou faz oferta (desconto, ferramenta, ganho)
elementos_top5  até 5 elementos curtos do texto que explicam o potencial de engajamento

Regras de calibração
- Use a escala de 0 a 10 inteira. 5 é um gancho ou mensagem comum, 8 é bom, 10 é raro e excepcional.
- Na dúvida entre true e false, responda false.
- Não invente nada que não esteja no texto."""
