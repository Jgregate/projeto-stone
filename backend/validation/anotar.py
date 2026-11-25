"""
Ferramenta de anotação manual da validação (roda no seu computador, sem internet).

gerar    cria data/validacao/anotar.html com os 50 posts da amostra. Cada cartão mostra a imagem de capa,
         a legenda e as listas de opções da rubrica. A resposta do modelo NÃO aparece (anotação cega).
         O progresso fica salvo no próprio navegador. No fim, o botão "Exportar" baixa um CSV.
importar copia as respostas do CSV exportado para data/validacao/validacao_manual.xlsx.

Uso
    python -m backend.validation.anotar gerar
    (abra data/validacao/anotar.html no navegador, anote e clique em Exportar)
    python -m backend.validation.anotar importar "C:\\Users\\SEU_USUARIO\\Downloads\\validacao_anotada.csv"
    python -m backend.validation.validacao avaliar
"""
import json
import sys

import pandas as pd

from backend.config import PROCESSED, VALIDACAO
from backend.validation.validacao import OPCOES, XLSX, ler_anotacao

DATA = PROCESSED
SAIDA = VALIDACAO / "anotar.html"


def gerar():
    man = ler_anotacao()
    base = pd.read_parquet(DATA / "base.parquet")[["post_id", "plataforma", "tipo_post", "texto", "url"]]
    df = man.drop(columns=["plataforma", "tipo_post", "url"], errors="ignore").merge(base, on="post_id", how="left")

    opcoes = {c: [v.strip() for v in o.split("|") if "(" not in v] for c, o in OPCOES.items()}
    posts = []
    for r in df.itertuples():
        posts.append({
            "post_id": r.post_id, "perfil": r.perfil, "plataforma": r.plataforma, "tipo_post": r.tipo_post,
            "url": r.url, "img": f"../raw/midia/{r.post_id}.jpg", "texto": (r.texto if isinstance(r.texto, str) else "")[:1200],
        })

    pagina = PAGINA.replace("__POSTS__", json.dumps(posts, ensure_ascii=False)) \
                   .replace("__OPCOES__", json.dumps(opcoes, ensure_ascii=False))
    SAIDA.write_text(pagina, encoding="utf-8")
    print(f"{len(posts)} posts -> {SAIDA.resolve()}")
    print("abra esse arquivo no navegador (duplo clique)")


def importar(caminho):
    anot = pd.read_csv(caminho, dtype=str, encoding="utf-8-sig").fillna("")
    from openpyxl import load_workbook
    wb = load_workbook(XLSX)
    ws = wb.active
    cab = [c.value for c in ws[1]]
    linha_de = {ws.cell(i, 1).value: i for i in range(2, ws.max_row + 1)}
    n = 0
    for r in anot.itertuples(index=False):
        i = linha_de.get(r.post_id)
        if not i:
            continue
        for col in anot.columns:
            if col.startswith("manual_") and col in cab:
                ws.cell(i, cab.index(col) + 1).value = getattr(r, col) or None
        n += 1
    wb.save(XLSX)
    print(f"{n} posts importados para {XLSX}")


PAGINA = r"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Validação manual</title>
<style>
body{font-family:system-ui,Arial,sans-serif;margin:0;background:#f4f6f5;color:#1f2a24}
header{position:sticky;top:0;background:#003d1c;color:#fff;padding:12px 20px;display:flex;gap:16px;align-items:center;z-index:2}
header button{background:#00a868;color:#fff;border:0;padding:8px 16px;border-radius:6px;font-size:15px;cursor:pointer}
.card{display:grid;grid-template-columns:260px 1fr 330px;gap:18px;background:#fff;margin:14px 20px;padding:14px;border-radius:10px;border:1px solid #dce8e1}
.card.ok{border-left:6px solid #00a868}
.card img{width:260px;border-radius:6px;background:#ddd}
.txt{white-space:pre-wrap;font-size:14px;max-height:340px;overflow:auto}
.meta{font-size:13px;color:#55625b;margin-bottom:6px}
label{display:block;font-size:13px;margin:6px 0 2px;color:#55625b}
select{width:100%;padding:5px;font-size:14px}
.desab{opacity:.4}
</style></head><body>
<header><b>Validação manual · anotação cega</b><span id="prog"></span>
<button onclick="exportar()">Exportar CSV</button></header>
<div id="lista"></div>
<script>
const POSTS = __POSTS__;
const OP = __OPCOES__;
const CAMPOS = Object.keys(OP);
let dados = {};
try { dados = JSON.parse(localStorage.getItem("anotacao_stone") || "{}"); } catch (e) {}
function salvar(){ try { localStorage.setItem("anotacao_stone", JSON.stringify(dados)); } catch (e) {} }
function completo(p){
  const d = dados[p.post_id] || {};
  return CAMPOS.every(c => (c === "formato_video" && ["imagem","carrossel"].includes(p.tipo_post)) || d[c]);
}
function progresso(){
  const n = POSTS.filter(completo).length;
  document.getElementById("prog").textContent = n + " de " + POSTS.length + " completos";
  POSTS.forEach(p => document.getElementById("c_" + p.post_id).classList.toggle("ok", completo(p)));
}
function render(){
  const lista = document.getElementById("lista");
  POSTS.forEach((p, i) => {
    const d = dados[p.post_id] = dados[p.post_id] || {};
    const card = document.createElement("div"); card.className = "card"; card.id = "c_" + p.post_id;
    const img = document.createElement("div");
    img.innerHTML = `<img src="${p.img}" alt="capa"><div class="meta">${i+1}. @${p.perfil} · ${p.plataforma} · ${p.tipo_post}</div><a href="${p.url}" target="_blank">abrir post original</a>`;
    const txt = document.createElement("div"); txt.className = "txt"; txt.textContent = p.texto || "(sem legenda)";
    const form = document.createElement("div");
    CAMPOS.forEach(c => {
      const semVideo = c === "formato_video" && ["imagem","carrossel"].includes(p.tipo_post);
      const lab = document.createElement("label"); lab.textContent = c + (semVideo ? " (não se aplica)" : "");
      const sel = document.createElement("select"); sel.disabled = semVideo; if (semVideo) sel.className = "desab";
      sel.innerHTML = `<option value=""></option>` + OP[c].map(v => `<option ${d[c]===v?"selected":""}>${v}</option>`).join("");
      sel.onchange = () => {
        d[c] = sel.value;
        if (c === "tem_cta" && sel.value === "false") { d.tipo_cta = "nenhum"; form.querySelector('[data-c="tipo_cta"]').value = "nenhum"; }
        salvar(); progresso();
      };
      sel.dataset.c = c;
      form.append(lab, sel);
    });
    card.append(img, txt, form); lista.append(card);
  });
  progresso();
}
function exportar(){
  const cab = ["post_id"].concat(CAMPOS.map(c => "manual_" + c));
  const linhas = [cab.join(",")].concat(POSTS.map(p => {
    const d = dados[p.post_id] || {};
    return [p.post_id].concat(CAMPOS.map(c => d[c] || "")).join(",");
  }));
  const blob = new Blob(["\ufeff" + linhas.join("\n")], {type: "text/csv"});
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "validacao_anotada.csv"; a.click();
}
render();
</script></body></html>"""


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "gerar"
    if cmd == "gerar":
        gerar()
    elif cmd == "importar":
        importar(sys.argv[2])
