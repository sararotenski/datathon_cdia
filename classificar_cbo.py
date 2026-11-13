import pandas as pd

REGRAS = {
    # Gestão
    "1": "Gestão e Direção",
    # Ciências, engenharia, técnicos
    "20": "Educação e Pesquisa",
    "21": "Engenharia, TI e Técnicos Industriais",
    "22": "Saúde",
    "23": "Educação e Pesquisa",
    "24": "Direito, Comunicação, Cultura e Esporte",
    "25": "Administrativo e Financeiro",
    "251": "Educação e Pesquisa",
    "2531": "Direito, Comunicação, Cultura e Esporte",
    "2534": "Direito, Comunicação, Cultura e Esporte",
    "224": "Direito, Comunicação, Cultura e Esporte",
    "27": "Alimentação, Hospedagem e Serviços Pessoais",
    "26": "Direito, Comunicação, Cultura e Esporte",
    "30": "Engenharia, TI e Técnicos Industriais",
    "31": "Engenharia, TI e Técnicos Industriais",
    "32": "Saúde",
    "321": "Agropecuária, Pesca e Extração",
    "323": "Agropecuária, Pesca e Extração",
    "33": "Educação e Pesquisa",
    "341": "Logística e Transporte",
    "342": "Logística e Transporte",
    "35": "Administrativo e Financeiro",
    "352": "Comércio e Atendimento",
    "354": "Comércio e Atendimento",
    "3516": "Engenharia, TI e Técnicos Industriais",
    "37": "Direito, Comunicação, Cultura e Esporte",
    "39": "Engenharia, TI e Técnicos Industriais",
    "395": "Educação e Pesquisa",
    # Administrativo
    "4": "Administrativo e Financeiro",
    "414": "Logística e Transporte",
    "421": "Comércio e Atendimento",
    "422": "Comércio e Atendimento",
    # Serviços e comércio
    "5": "Alimentação, Hospedagem e Serviços Pessoais",
    "514": "Limpeza, Segurança e Conservação",
    "515": "Saúde",
    "517": "Limpeza, Segurança e Conservação",
    "52": "Comércio e Atendimento",
    # Agro
    "6": "Agropecuária, Pesca e Extração",
    # Indústria e construção
    "71": "Construção Civil e Mineração",
    "72": "Metalmecânica e Eletroeletrônica",
    "73": "Metalmecânica e Eletroeletrônica",
    "74": "Metalmecânica e Eletroeletrônica",
    "75": "Química, Plástico e Minerais",
    "76": "Têxtil, Confecção e Calçados",
    "77": "Madeira, Papel e Mobiliário",
    "78": "Embalagem e Operação Industrial Geral",
    "781": "Metalmecânica e Eletroeletrônica",
    "782": "Logística e Transporte",
    "783": "Logística e Transporte",
    "79": "Têxtil, Confecção e Calçados",
    "81": "Química, Plástico e Minerais",
    "82": "Química, Plástico e Minerais",
    "821": "Metalmecânica e Eletroeletrônica",
    "822": "Metalmecânica e Eletroeletrônica",
    "83": "Madeira, Papel e Mobiliário",
    "84": "Alimentos e Bebidas (Indústria)",
    "86": "Embalagem e Operação Industrial Geral",
    # Manutenção
    "91": "Manutenção e Reparação",
    "95": "Manutenção e Reparação",
    "99": "Manutenção e Reparação",
    "999": "Forças Armadas e Não Identificado",
    # Forças Armadas
    "0": "Forças Armadas e Não Identificado",
}

EXCECOES = {
    "422105": "Comércio e Atendimento",
    "514325": "Manutenção e Reparação",
    "312320": "Construção Civil e Mineração",
    "251605": "Saúde",
    "318805": "Madeira, Papel e Mobiliário",
    "252725": "Logística e Transporte",
    "322715": "Saúde",
    "253120": "Administrativo e Financeiro",
    "910130": "Gestão e Direção",
    "768325": "Têxtil, Confecção e Calçados",
    "810305": "Química, Plástico e Minerais",
    "311705": "Química, Plástico e Minerais",
    "812105": "Química, Plástico e Minerais",
    "391230": "Logística e Transporte",
    "316310": "Construção Civil e Mineração",
}
def classificar(cod):
    if cod in EXCECOES:
        return EXCECOES[cod]

    for tam in range(len(cod), 0, -1):
        if cod[:tam] in REGRAS:
            return REGRAS[cod[:tam]]
    return "Forças Armadas e Não Identificado"

d = pd.read_csv("cbos_unicos.csv", dtype=str)
d["codigo"] = d["codigo"].str.zfill(6)
d["macrofamilia"] = d["codigo"].apply(classificar)
d["grande_grupo"] = d["codigo"].str[0]
d["descricao"] = d["descricao"].fillna("(sem descrição no dicionário)")

d[["codigo", "descricao", "macrofamilia", "grande_grupo"]].to_csv(
    "cbo_macrofamilia.csv", index=False, encoding="utf-8")

d["n_movimentacoes"] = d["n_movimentacoes"].astype(int)
resumo = (d.groupby("macrofamilia")
            .agg(cbos=("codigo", "count"), movimentacoes=("n_movimentacoes", "sum"))
            .sort_values("movimentacoes", ascending=False))
resumo["%_mov"] = (resumo["movimentacoes"] / resumo["movimentacoes"].sum() * 100).round(1)
print(resumo.to_string())
print("\nTotal CBOs:", len(d))
