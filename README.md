# Análise de resgates de capital

![python](https://img.shields.io/badge/python-3.10%2B-3776AB) ![pandas](https://img.shields.io/badge/pandas-ETL-150458) ![testes](https://img.shields.io/badge/testes-pytest-0A9EDC)

Pipeline em Python que **integra cinco bases de origem**, monta uma visão única dos resgates de capital social de uma cooperativa de crédito, **identifica padrões nos resgates feitos como exceção ao regulamento** e gera automaticamente uma **planilha gerencial** e uma **apresentação em PowerPoint**.

> **Dados 100% fictícios.** As bases são criadas pelo script `scripts/gerar_dados_ficticios.py`; nomes, matrículas, PAs, usuários e valores não correspondem a pessoas ou instituições reais.

## Contexto

Os resgates de capital seguem um regulamento interno: desligamento, falecimento, aposentadoria e resgate parcial anual são os motivos previstos. Qualquer outro motivo é **exceção** e precisa ser monitorado. O processo original era uma planilha com fórmulas e uma macro VBA para montar a apresentação. Ele foi migrado para Python para:

- juntar as bases de forma **reprodutível** e sem colar dados à mão;
- medir valor, PA e cooperado de cada resgate, e consolidar por **regional**, **superintendência** e **departamento** (descoberto pelo usuário que fez o lançamento);
- encontrar **concentrações de exceções** com critério estatístico, e não só no olho.

## Bases de entrada

| Base | Conteúdo | Particularidade tratada |
|---|---|---|
| `dcoop.csv` | PA → regional → superintendência | — |
| `associados.csv` | cadastro do cooperado | exportado em **UTF-16 com TAB** |
| `usuarios.csv` | login do sistema + setor/função (RH) | define o departamento do lançamento |
| `movimento_conta_201.csv` | lançamentos de capital por matrícula | mistura resgates e integralizações; valores em formato BR |
| `baixas_financeiro.csv` | baixas feitas pelo Financeiro | coluna **Motivos** preenchida à mão: fonte oficial do motivo |

## Pipeline

```
5 bases ──► etl.carregar_bases ──► etl.montar_base_resgates ──► analise ──► saidas
            (encoding, tipos)      (joins validados m:1,        (KPIs,     ├─ resgates_capital.xlsx (10 abas)
                                    enquadramento, motivo)       padrões)  └─ resgates_capital.pptx (5 slides)
```

- **Joins com `validate="m:1"`**: se uma base de cadastro vier com chave duplicada, o processo para em vez de duplicar valores em silêncio.
- **Checagens de qualidade** (aba própria): matrícula sem cadastro, PA sem regional, usuário sem RH, valor nulo, resgate sem baixa do Financeiro.
- **Enquadramento**: previsto no regulamento × exceção × sem baixa do Financeiro (motivo desconhecido).
- **Detecção de padrão**: um PA entra em alerta quando seu % de exceções supera **média + 1,5 desvio-padrão** entre os PAs com pelo menos 10 resgates. Também há análises por motivo, por departamento e por faixa de valor.

## Resultado com os dados de exemplo

```
640 resgates | R$ 1.129.027,30 | exceções: 13,9%
PAs em alerta: 15, 07
Resgate sem baixa do Financeiro (motivo desconhecido): 67
```

Os PAs 07 e 15 foram **propositalmente gerados** com mais exceções, e o método os encontrou. O teste automatizado garante isso.

Os arquivos gerados estão em [`docs/exemplo/`](docs/exemplo/): a planilha com 10 abas formatadas e a apresentação abaixo, criada 100% por código.

| Slide | Conteúdo |
|---|---|
| 1 | KPIs (quantidade, valor, ticket médio, % exceções) + evolução mensal por enquadramento |
| 2–4 | Valor por regional, top 10 PAs e valor por departamento |
| 5 | Padrão das exceções: motivos e % por PA, com corte estatístico |

## Como executar

```bash
pip install -r requirements.txt
python scripts/gerar_dados_ficticios.py            # cria data/bruto/
PYTHONPATH=src python -m resgates --entrada data/bruto --saida saida
pytest -q
```

## Estrutura

```
├── src/resgates/
│   ├── etl.py       # leitura das 5 bases, joins validados, enquadramento, qualidade
│   ├── analise.py   # agregações por dimensão, padrão de exceções, evolução mensal
│   ├── saidas.py    # Excel formatado + PowerPoint com gráficos (python-pptx, matplotlib)
│   └── cli.py
├── scripts/gerar_dados_ficticios.py
├── tests/test_processo.py
└── docs/exemplo/
```

## Stack

Python · pandas · openpyxl · python-pptx · matplotlib · pytest · GitHub Actions

---
Autor: **Gabriel Antônio Ribeiro**, Analista Financeiro · [LinkedIn](https://www.linkedin.com/in/gabriel-ant%C3%B4nio-ribeiro-017808210)
