import pandas as pd

col = "cbo2002ocupação"

cbo = pd.read_csv("dados/Novo_Caged_MOV_Limpo.csv", sep=";", usecols=[col], dtype=str)

cbos = (cbo[col].value_counts()
        .rename_axis("codigo").reset_index(name="n_movimentacoes"))
cbos["codigo"] = cbos["codigo"].str.strip().str.zfill(6)

desc = pd.read_excel("dados/Dicionario_de_dados.xlsx",
                     sheet_name="cbo2002ocupação", dtype=str)
desc.columns = ["codigo", "descricao"]
desc["codigo"] = desc["codigo"].str.strip().str.zfill(6)

cbos = cbos.merge(desc, on="codigo", how="left")
cbos.to_csv("cbos_unicos.csv", index=False)

print(len(cbos), "CBOs únicas")
print(cbos["descricao"].isna().sum(), "sem descrição")
print(cbos.head(10))
