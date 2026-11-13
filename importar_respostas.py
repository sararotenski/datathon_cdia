"""
Lê as respostas dos modelos de IA e compara as classificações com as regras definidas no projeto.

Uso:
    python3 importar_respostas.py --versao v1

Entrada:
    llm/<versao>/respostas/lote_XX.txt
    (uma linha por CBO, no formato codigo;macrofamilia)

Saídas:
    llm/<versao>/comparacao.csv
    (reúne todas as CBOs respondidas e suas respectivas classificações)

    llm/<versao>/divergencias.csv
    (reúne as CBOs em que as classificações dos modelos de IA
    diferem da classificação gerada pelas regras, ordenadas
    pela quantidade de movimentações)
"""
import argparse
import glob
import os
import re
import unicodedata
import pandas as pd


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--versao", default="v1")
    a = ap.parse_args()
    pasta = os.path.join("llm", a.versao)

    regra = pd.read_csv("cbo_macrofamilia.csv", dtype=str)
    regra["codigo"] = regra["codigo"].str.zfill(6)
    validas = {norm(c): c for c in regra["macrofamilia"].unique()}

    cbos = pd.read_csv("cbos_unicos.csv", dtype=str)
    cbos["codigo"] = cbos["codigo"].str.zfill(6)
    cbos["n_mov"] = cbos["n_movimentacoes"].astype(int)

    linhas, ignoradas = [], 0
    arquivos = sorted(glob.glob(os.path.join(pasta, "respostas", "*.txt")))
    if not arquivos:
        print(f"Nenhuma resposta em {pasta}/respostas/. Cola as respostas do LLM lá.")
        return

    for arq in arquivos:
        for linha in open(arq, encoding="utf-8"):
            m = re.match(r"^\W*(\d{6})\s*[;|,\t]\s*(.+?)\s*$", linha)
            if not m:
                if linha.strip():
                    ignoradas += 1
                continue
            cod, cat = m.group(1), m.group(2).strip(" *`\"'")
            linhas.append((cod, validas.get(norm(cat), "CATEGORIA INVÁLIDA: " + cat)))

    llm = pd.DataFrame(linhas, columns=["codigo", "llm"]).drop_duplicates("codigo", keep="last")
    df = (llm.merge(regra[["codigo", "descricao", "macrofamilia"]].rename(columns={"macrofamilia": "regra"}), on="codigo", how="left")
             .merge(cbos[["codigo", "n_mov"]], on="codigo", how="left"))
    df["concorda"] = df["llm"] == df["regra"]
    df = df.sort_values("n_mov", ascending=False)
    df.to_csv(os.path.join(pasta, "comparacao.csv"), index=False, encoding="utf-8")
    div = df[~df["concorda"]]
    div.to_csv(os.path.join(pasta, "divergencias.csv"), index=False, encoding="utf-8")

    n = len(df)
    print(f"CBOs respondidas: {n}  (linhas ignoradas/mal formatadas: {ignoradas})")
    print(f"Concordância por CBO:           {df['concorda'].mean()*100:.1f}%")
    print(f"Concordância por movimentações: {df.loc[df['concorda'],'n_mov'].sum()/df['n_mov'].sum()*100:.1f}%")
    invalidas = df["llm"].str.startswith("CATEGORIA INVÁLIDA").sum()
    if invalidas:
        print(f"ATENÇÃO: {invalidas} respostas com categoria que não existe na lista (veja em divergencias.csv)")
    print(f"\nDivergências: {len(div)}. As 15 mais pesadas:")
    print(div.head(15)[["codigo", "descricao", "regra", "llm", "n_mov"]].to_string(index=False))
    print(f"\nArquivos salvos em {pasta}/")


if __name__ == "__main__":
    main()
