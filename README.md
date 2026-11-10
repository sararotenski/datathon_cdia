# Datathon 2026 – Raio-X do Mercado de Trabalho e Vagas Industriais em SC

Pergunta central: quais regiões e setores industriais de Santa Catarina estão enfrentando apagão de mão de obra ou expansão acelerada, e como renda e escolaridade explicam esses gargalos?

## Como rodar

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python src/pipeline.py   # etapa 1: ingestão, validação e exclusões
.venv/bin/python src/escopo.py     # validação do escopo da pergunta
```

O arquivo `data/brutos/Novo_Caged_MOV_Limpo.csv` (cerca de 400 MB) não está no repositório por causa do limite de tamanho do GitHub. Coloque-o em `data/brutos/` antes de rodar.

## Estrutura

- `src/ingestao.py`: carga dos arquivos e verificação de schema
- `src/tratamento.py`: tipagem, consistência, flags de qualidade e filtro MOV x EXC
- `src/erros.py`: erros e avisos do pipeline
- `src/pipeline.py`: executa a etapa 1 e grava em `data/processados/`
- `src/escopo.py`: números da validação do escopo
- `docs/escopo_pergunta_negocio.md`: análise do escopo, decisões pendentes e limites
