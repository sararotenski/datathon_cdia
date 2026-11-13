"""
Gera os lotes de texto que você cola no chat do LLM (Claude, ChatGPT, Gemini...).

Uso (no terminal, dentro da pasta do projeto):
    python3 exportar_lotes.py --modo amostra --versao v1   (prompt v1)
    python3 exportar_lotes.py --modo amostra --versao v2   (prompt v2, com definições)
    python3 exportar_lotes.py --modo principais --versao v1
    python3 exportar_lotes.py --modo completo --versao v1

Modos:
    amostra     100 CBOs (60 mais frequentes + 40 aleatórias) -> pra TESTAR o prompt
    principais  seleciona CBOs com movimentações acumuladas próximas de 95%
    completo    todas as 2.201 CBOs

--versao escolhe o prompt (v1, v2...) e também o nome da pasta de saída.
Quer testar outro prompt? Cria o PROMPT_V3 no código, adiciona em PROMPTS e roda com --versao v3.
"""
import argparse
import os
import unicodedata
import pandas as pd

PROMPT_V1 = """Você é especialista em mercado de trabalho brasileiro e na CBO 2002 (Classificação Brasileira de Ocupações).

Vou te passar uma lista de ocupações (código CBO e descrição). Classifique CADA ocupação em exatamente UMA das macrofamílias abaixo.

MACROFAMÍLIAS (use o nome exatamente como está escrito):
{CATEGORIAS}

REGRAS:
1. Use somente os nomes da lista acima. Não invente categorias.
2. Decida pela atividade real da ocupação. O código CBO ajuda (o 1º dígito indica o grande grupo), mas não é regra absoluta.
3. Ocupações da indústria vão para a macrofamília do setor industrial correspondente. Ocupações de comércio e serviços vão para as macrofamílias de serviços.
4. Se estiver em dúvida, escolha a mais provável. Nenhuma ocupação pode ficar sem classificação.
5. Responda SOMENTE com uma linha por ocupação, no formato codigo;macrofamilia, sem cabeçalho, sem explicação e sem nenhum texto antes ou depois.

EXEMPLOS DE RESPOSTA:
{EXEMPLOS}

OCUPAÇÕES PARA CLASSIFICAR (codigo | descricao):
{LISTA}
"""

# ---------------------------------------------------------------------
# V2: mesmas regras, mas cada categoria vem com uma DEFINIÇÃO curta
# (o que entra nela). Corrige erros do v1 como "Carpinteiro de Obras"
# indo pra Madeira e "Operador de Máquinas Fixas" indo pra TI.
# ---------------------------------------------------------------------
DESCRICOES = {
    "Administrativo e Financeiro": "trabalho de escritório, contabilidade, finanças, RH, secretariado, bancos",
    "Agropecuária, Pesca e Extração": "agricultura, pecuária, pesca, silvicultura, extrativismo vegetal",
    "Alimentação, Hospedagem e Serviços Pessoais": "cozinha, bares e restaurantes, hotelaria, beleza, cuidadores, serviços domésticos",
    "Alimentos e Bebidas (Indústria)": "abate e frigoríficos, laticínios, panificação industrial, bebidas, processamento de alimentos",
    "Comércio e Atendimento": "vendas, caixa, repositores, atendimento ao público",
    "Construção Civil e Mineração": "trabalho em obras (pedreiro, servente, carpinteiro de obras, pintor de obras, eletricista de instalações, operador de escavadeira), mineração e petróleo",
    "Direito, Comunicação, Cultura e Esporte": "advogados, jornalistas, publicidade, artes, esporte, lazer",
    "Educação e Pesquisa": "professores, instrutores, pesquisadores, apoio à pesquisa",
    "Embalagem e Operação Industrial Geral": "alimentador de linha de produção, embalador, operador de máquinas fixas, caldeiras, utilidades industriais (vapor, energia)",
    "Engenharia, TI e Técnicos Industriais": "engenheiros, tecnologia da informação, técnicos industriais de nível médio, qualidade, segurança do trabalho",
    "Forças Armadas e Não Identificado": "militares e ocupações não identificadas",
    "Gestão e Direção": "gerentes, diretores e dirigentes",
    "Limpeza, Segurança e Conservação": "limpeza, vigilância, portaria, zeladoria, conservação de edifícios",
    "Logística e Transporte": "motoristas, ajudantes, almoxarifes, estoque, entregas, transporte",
    "Madeira, Papel e Mobiliário": "marcenaria e móveis (fábrica e projeto), serrarias, celulose e papel",
    "Manutenção e Reparação": "mecânicos e eletricistas de manutenção, reparação de veículos e máquinas",
    "Metalmecânica e Eletroeletrônica": "soldagem, usinagem, montagem metálica, fundição, montagem de eletroeletrônicos",
    "Química, Plástico e Minerais": "plástico, borracha, química, cerâmica, vidro, minerais não metálicos",
    "Saúde": "médicos, enfermagem, técnicos de saúde, odontologia, farmácia",
    "Têxtil, Confecção e Calçados": "tecelagem, costura, confecção, calçados, couro",
}

PROMPT_V2 = """Você é especialista em mercado de trabalho brasileiro e na CBO 2002 (Classificação Brasileira de Ocupações).

Vou te passar uma lista de ocupações (código CBO e descrição). Classifique CADA ocupação em exatamente UMA das macrofamílias abaixo.

MACROFAMÍLIAS (nome, seguido de o que entra nela):
{CATEGORIAS_DESC}

REGRAS:
1. Use somente os nomes da lista acima, escritos exatamente como estão. Não invente categorias e NÃO copie a definição, só o nome.
2. Decida pela atividade real da ocupação, olhando as definições. O código CBO ajuda (o 1º dígito indica o grande grupo), mas não é regra absoluta.
3. Ocupações da indústria vão para a macrofamília do setor industrial correspondente. Ocupações de comércio e serviços vão para as macrofamílias de serviços. Trabalho feito em obras vai para Construção Civil, mesmo que o ofício também exista em fábricas (ex.: carpinteiro de obras).
4. Se estiver em dúvida, escolha a mais provável. Nenhuma ocupação pode ficar sem classificação.
5. Responda SOMENTE com uma linha por ocupação, no formato codigo;macrofamilia, sem cabeçalho, sem explicação e sem nenhum texto antes ou depois.

EXEMPLOS DE RESPOSTA:
{EXEMPLOS}

OCUPAÇÕES PARA CLASSIFICAR (codigo | descricao):
{LISTA}
"""

PROMPTS = {"v1": PROMPT_V1, "v2": PROMPT_V2}
# Pra criar uma v3: copia o PROMPT_V2, muda o que quiser e adiciona em PROMPTS.

# Exemplos mostrados ao LLM. Ficam FORA dos lotes (senão o teste seria "colado").
EXEMPLOS = [
    ("741105", "Metalmecânica e Eletroeletrônica"),
    ("761405", "Têxtil, Confecção e Calçados"),
    ("421120", "Comércio e Atendimento"),
    ("782715", "Logística e Transporte"),
    ("223905", "Saúde"),
    ("212315", "Engenharia, TI e Técnicos Industriais"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modo", choices=["amostra", "principais", "completo"], default="amostra")
    ap.add_argument("--versao", default="v2", help="v1, v2... (também é o nome da pasta)")
    ap.add_argument("--tam", type=int, default=50, help="CBOs por lote (padrão 50)")
    a = ap.parse_args()

    cbos = pd.read_csv("cbos_unicos.csv", dtype=str)
    cbos["codigo"] = cbos["codigo"].str.zfill(6)
    cbos["n"] = cbos["n_movimentacoes"].astype(int)
    cbos["descricao"] = cbos["descricao"].fillna("(sem descrição no dicionário)")
    cbos = cbos[~cbos["codigo"].isin([c for c, _ in EXEMPLOS])]
    cbos = cbos.sort_values("n", ascending=False).reset_index(drop=True)

    if a.modo == "amostra":
        top = cbos.head(60)
        resto = cbos.iloc[60:].sample(40, random_state=42)
        sel = pd.concat([top, resto])
    elif a.modo == "principais":
        cum = cbos["n"].cumsum() / cbos["n"].sum()
        sel = cbos[cum <= 0.95]
    else:
        sel = cbos

    regra = pd.read_csv("cbo_macrofamilia.csv", dtype=str)
    categorias = sorted(regra["macrofamilia"].unique())
    cat_txt = "\n".join(f"- {c}" for c in categorias)
    ex_txt = "\n".join(f"{c};{m}" for c, m in EXEMPLOS)

    pasta = os.path.join("llm", a.versao)
    os.makedirs(os.path.join(pasta, "lotes"), exist_ok=True)
    os.makedirs(os.path.join(pasta, "respostas"), exist_ok=True)
    sel[["codigo"]].to_csv(os.path.join(pasta, f"enviadas_{a.modo}.csv"), index=False)

    if a.versao not in PROMPTS:
        raise SystemExit(f"Versão '{a.versao}' não existe. Opções: {', '.join(PROMPTS)}")
    prompt = PROMPTS[a.versao]
    desc_txt = "\n".join(f"- {c}: {DESCRICOES.get(c, '')}" for c in categorias)

    n_lotes = (len(sel) + a.tam - 1) // a.tam
    for i in range(n_lotes):
        parte = sel.iloc[i * a.tam:(i + 1) * a.tam]
        lista = "\n".join(f"{r.codigo} | {r.descricao}" for r in parte.itertuples())
        texto = (prompt.replace("{CATEGORIAS_DESC}", desc_txt)
                       .replace("{CATEGORIAS}", cat_txt)
                       .replace("{EXEMPLOS}", ex_txt)
                       .replace("{LISTA}", lista))
        with open(os.path.join(pasta, "lotes", f"lote_{i+1:02d}.txt"), "w", encoding="utf-8") as f:
            f.write(texto)

    print(f"{len(sel)} CBOs em {n_lotes} lotes -> {pasta}/lotes/")
    print(f"Cole cada lote no chat e salve a resposta em {pasta}/respostas/lote_XX.txt")


if __name__ == "__main__":
    main()
