# Datathon 2026 – Raio-X do Mercado de Trabalho e Vagas Industriais em SC

Pergunta central: quais regiões e setores industriais de Santa Catarina estão enfrentando apagão de mão de obra ou expansão acelerada, e como renda e escolaridade explicam esses gargalos?

## Como rodar

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python src/pipeline.py   # etapa 1: ingestão, validação e exclusões
.venv/bin/python src/escopo.py     # validação do escopo da pergunta
.venv/bin/python src/integracao.py # etapa 2: join CAGED x IBGE e saldo por 10 mil habitantes
.venv/bin/python src/indicadores.py # base do dashboard (indústria + regiões IBGE)
.venv/bin/streamlit run dashboard/app.py
```

O arquivo `data/brutos/Novo_Caged_MOV_Limpo.csv` (cerca de 400 MB) não está no repositório por causa do limite de tamanho do GitHub. Coloque-o em `data/brutos/` antes de rodar.

## Estrutura

- `src/ingestao.py`: carga dos arquivos e verificação de schema
- `src/tratamento.py`: tipagem, consistência, flags de qualidade e filtro MOV x EXC
- `src/erros.py`: erros e avisos do pipeline
- `src/pipeline.py`: executa a etapa 1 e grava em `data/processados/`
- `src/escopo.py`: números da validação do escopo
- `src/integracao.py`: join pela chave `municipio_codigo` e métrica de saldo por 10 mil habitantes (`data/processados/saldo_municipio.csv`)
- `src/indicadores.py`: indicadores de expansão e apagão e classificação região × setor
- `dashboard/app.py`: dashboard interativo (Streamlit)
- `data/brutos/regioes_ibge_sc.json` e `malha_municipios_sc.geojson`: regiões e mapa municipal (APIs do IBGE)
- `docs/escopo_pergunta_negocio.md`: análise do escopo, decisões pendentes e limites
