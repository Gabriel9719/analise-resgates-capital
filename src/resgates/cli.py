"""Executa o processo completo: python -m resgates --entrada data/bruto --saida saida"""
from __future__ import annotations

import argparse
from pathlib import Path

from .analise import evolucao_mensal, padrao_excecoes, por_dimensao
from .etl import carregar_bases, checar_qualidade, montar_base_resgates
from .saidas import exportar_excel, gerar_apresentacao


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="resgates")
    ap.add_argument("--entrada", type=Path, default=Path("data/bruto"))
    ap.add_argument("--saida", type=Path, default=Path("saida"))
    a = ap.parse_args(argv)

    res = montar_base_resgates(carregar_bases(a.entrada))
    qualidade = checar_qualidade(res)
    por_pa = por_dimensao(res, ["pa", "nome_pa", "regional", "superintendencia"])
    por_reg = por_dimensao(res, "regional")
    por_sup = por_dimensao(res, "superintendencia")
    por_dep = por_dimensao(res, "departamento")
    padrao = padrao_excecoes(res)
    mensal = evolucao_mensal(res)

    xlsx = exportar_excel({
        "Base resgates": res.drop(columns=["historico"]),
        "Por PA": por_pa, "Por regional": por_reg, "Por superintendência": por_sup,
        "Por departamento": por_dep, "Mensal": mensal,
        "Exceções - motivos": padrao["motivos"], "Exceções - PAs": padrao["pa"],
        "Exceções - faixa valor": padrao["faixa_valor"], "Qualidade dos dados": qualidade,
    }, a.saida / "resgates_capital.xlsx")
    pptx = gerar_apresentacao(res, por_pa, por_reg, por_dep, padrao, mensal, a.saida / "resgates_capital.pptx")

    print(f"{len(res)} resgates | R$ {res['valor'].sum():,.2f} | exceções: {(res['enquadramento'] == 'Exceção').mean():.1%}")
    print("PAs em alerta:", ", ".join(padrao["pa"].loc[padrao["pa"]["alerta"], "pa"]) or "nenhum")
    print(qualidade.to_string(index=False))
    print(f"Arquivos: {xlsx} | {pptx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
