"""Indicadores dos resgates: volume por dimensão e padrão das exceções."""
from __future__ import annotations

import pandas as pd

FAIXAS = [0, 500, 1_000, 5_000, 20_000, float("inf")]
ROTULOS = ["até 500", "500 a 1 mil", "1 mil a 5 mil", "5 mil a 20 mil", "acima de 20 mil"]


def por_dimensao(res: pd.DataFrame, dim: str | list[str]) -> pd.DataFrame:
    g = res.groupby(dim).agg(
        qtd=("valor", "size"),
        valor_total=("valor", "sum"),
        ticket_medio=("valor", "mean"),
        qtd_excecao=("enquadramento", lambda s: (s == "Exceção").sum()),
    ).reset_index()
    g["pct_excecao"] = (g["qtd_excecao"] / g["qtd"]).round(4)
    g["participacao_valor"] = (g["valor_total"] / g["valor_total"].sum()).round(4)
    return g.sort_values("valor_total", ascending=False).round(2)


def padrao_excecoes(res: pd.DataFrame, limite_desvios: float = 1.5) -> dict[str, pd.DataFrame]:
    """Procura concentração de exceções.

    Um PA é sinalizado quando seu % de exceções supera a média + `limite_desvios` desvios-padrão
    entre os PAs, considerando apenas PAs com pelo menos 10 resgates (evita falso alarme).
    """
    exc = res[res["enquadramento"] == "Exceção"]
    pa = por_dimensao(res, ["pa", "nome_pa", "regional"])
    base = pa[pa["qtd"] >= 10]
    corte = base["pct_excecao"].mean() + limite_desvios * base["pct_excecao"].std()
    pa["alerta"] = (pa["qtd"] >= 10) & (pa["pct_excecao"] > corte)

    faixa = res.assign(faixa=pd.cut(res["valor"], FAIXAS, labels=ROTULOS))
    por_faixa = (faixa.groupby("faixa", observed=False)["enquadramento"]
                      .agg(qtd="size", qtd_excecao=lambda s: (s == "Exceção").sum()).reset_index())
    por_faixa["pct_excecao"] = (por_faixa["qtd_excecao"] / por_faixa["qtd"].where(por_faixa["qtd"] > 0)).round(4)

    return {
        "motivos": exc.groupby("motivo").agg(qtd=("valor", "size"), valor=("valor", "sum")).reset_index()
                      .sort_values("qtd", ascending=False).round(2),
        "pa": pa.sort_values("pct_excecao", ascending=False),
        "departamento": por_dimensao(res, "departamento").sort_values("pct_excecao", ascending=False),
        "faixa_valor": por_faixa,
        "corte_pct": pd.DataFrame({"corte_pct_excecao": [round(corte, 4)]}),
    }


def evolucao_mensal(res: pd.DataFrame) -> pd.DataFrame:
    m = res.pivot_table(index="mes", columns="enquadramento", values="valor", aggfunc="sum", fill_value=0).reset_index()
    m.columns.name = None
    return m.round(2)
