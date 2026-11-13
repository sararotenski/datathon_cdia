
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# Caminhos
BASE = Path(__file__).resolve().parents[1]
ENTRADA = BASE / "data" / "processados" / "analises_etapa2"
SAIDA = BASE / "data" / "processados" / "graficos_etapa2"
SAIDA.mkdir(parents=True, exist_ok=True)

# Aparência
plt.rcParams["figure.figsize"] = (11, 6)
plt.rcParams["axes.titleweight"] = "bold"
plt.rcParams["font.size"] = 10

# Carregar tabelas
escolaridade = pd.read_csv(ENTRADA / "escolaridade_geral.csv")
escolaridade_polo = pd.read_csv(ENTRADA / "escolaridade_por_polo.csv")
salario_polo = pd.read_csv(ENTRADA / "salario_por_polo.csv")
salario_escolaridade = pd.read_csv(ENTRADA / "salario_por_escolaridade.csv")
evolucao = pd.read_csv(ENTRADA / "evolucao_salarial_mensal.csv")

# 1. Escolaridade geral: admitidos x desligados
ax = escolaridade.set_index("recorte")[
    [
        "pct_medio_ou_mais_admitidos",
        "pct_medio_ou_mais_desligados",
        "pct_superior_admitidos",
        "pct_superior_desligados",
    ]
].T.plot(kind="bar")

ax.set_title("Escolaridade dos admitidos e desligados")
ax.set_ylabel("Percentual (%)")
ax.set_xlabel("")
ax.set_xticklabels(
    ["Médio ou mais - admitidos", "Médio ou mais - desligados",
     "Superior - admitidos", "Superior - desligados"],
    rotation=15, ha="right"
)
ax.legend().remove()
plt.tight_layout()
plt.savefig(SAIDA / "01_escolaridade_geral.png", dpi=180)
plt.close()

# 2. Escolaridade por polo industrial
ax = escolaridade_polo.set_index("polo")[
    [
        "pct_medio_ou_mais_admitidos",
        "pct_medio_ou_mais_desligados",
    ]
].plot(kind="bar")

ax.set_title("Trabalhadores com ensino médio ou mais por polo")
ax.set_ylabel("Percentual (%)")
ax.set_xlabel("Polo industrial")
ax.legend(["Admitidos", "Desligados"])
plt.xticks(rotation=25, ha="right")
plt.tight_layout()
plt.savefig(SAIDA / "02_escolaridade_por_polo.png", dpi=180)
plt.close()

# 3. Salário mediano por polo
ax = salario_polo.set_index("polo")[
    ["mediana_admitidos", "mediana_desligados"]
].plot(kind="bar")

ax.set_title("Salário mediano por polo industrial")
ax.set_ylabel("Salário mediano (R$)")
ax.set_xlabel("Polo industrial")
ax.legend(["Admitidos", "Desligados"])
plt.xticks(rotation=25, ha="right")
plt.tight_layout()
plt.savefig(SAIDA / "03_salario_por_polo.png", dpi=180)
plt.close()

# 4. Salário mediano por escolaridade
nomes_escolaridade = {
    1: "Analfabeto",
    2: "Até 5ª incompleto",
    3: "5ª fundamental",
    4: "6ª a 9ª fundamental",
    5: "Fundamental completo",
    6: "Médio incompleto",
    7: "Médio completo",
    8: "Superior incompleto",
    9: "Superior completo",
    10: "Mestrado",
    11: "Doutorado",
    80: "Pós-graduação",
}

salario_escolaridade["grau_instrucao"] = pd.to_numeric(
    salario_escolaridade["grau_instrucao"]
)
salario_escolaridade = salario_escolaridade.sort_values(
    "grau_instrucao"
)
salario_escolaridade["escolaridade"] = (
    salario_escolaridade["grau_instrucao"].map(nomes_escolaridade)
)

ax = salario_escolaridade.set_index("escolaridade")[
    ["mediana_admitidos", "mediana_desligados"]
].plot(kind="bar")

ax.set_title("Salário mediano por nível de escolaridade")
ax.set_ylabel("Salário mediano (R$)")
ax.set_xlabel("Escolaridade")
ax.legend(["Admitidos", "Desligados"])
plt.xticks(rotation=35, ha="right")
plt.tight_layout()
plt.savefig(SAIDA / "04_salario_por_escolaridade.png", dpi=180)
plt.close()

# 5. Evolução salarial mensal
evolucao["competencia_mov"] = evolucao["competencia_mov"].astype(str)
evolucao["data"] = pd.to_datetime(
    evolucao["competencia_mov"], format="%Y%m"
)
evolucao["mes"] = evolucao["data"].dt.strftime("%m/%Y")

pivot = evolucao.pivot(
    index="data",
    columns="movimento",
    values="salario_mediano"
).sort_index()

ax = pivot.plot(marker="o")
ax.set_title("Evolução mensal do salário mediano")
ax.set_ylabel("Salário mediano (R$)")
ax.set_xlabel("Competência")
ax.legend(["Admissões", "Desligamentos"])
ax.set_xticks(pivot.index)
ax.set_xticklabels(
    [data.strftime("%m/%Y") for data in pivot.index],
    rotation=35, ha="right"
)
plt.tight_layout()
plt.savefig(SAIDA / "05_evolucao_salarial_mensal.png", dpi=180)
plt.close()

print("\nCinco gráficos gerados com sucesso!")
print(f"Pasta de saída: {SAIDA}")

for arquivo in sorted(SAIDA.glob("*.png")):
    print(" -", arquivo.name)
