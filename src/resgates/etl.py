"""Leitura e integração das cinco bases do processo de resgates de capital."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

MOTIVOS_PREVISTOS = {
    "Desligamento do quadro social",
    "Falecimento do cooperado",
    "Aposentadoria",
    "Resgate parcial anual (até 10%)",
}


def _num_br(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False))


def carregar_bases(pasta: str | Path) -> dict[str, pd.DataFrame]:
    p = Path(pasta)
    bases = {
        "dcoop": pd.read_csv(p / "dcoop.csv", sep=";", dtype=str),
        # o cadastro de associados vem do sistema em UTF-16 separado por TAB
        "associados": pd.read_csv(p / "associados.csv", sep="\t", encoding="utf-16", dtype={"pa": str}),
        "usuarios": pd.read_csv(p / "usuarios.csv", sep=";"),
        "movimento": pd.read_csv(p / "movimento_conta_201.csv", sep=";"),
        "baixas": pd.read_csv(p / "baixas_financeiro.csv", sep=";"),
    }
    for nome in ("movimento", "baixas"):
        df = bases[nome]
        df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
        df["valor"] = _num_br(df["valor"])
    return bases


def montar_base_resgates(b: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Uma linha por resgate, enriquecida com cooperado, PA, regional, departamento e motivo."""
    mov = b["movimento"]
    res = mov[mov["historico"].str.contains("RESGATE", case=False)].copy()
    res["valor"] = res["valor"].abs()

    res = res.merge(b["associados"][["matricula", "nome", "pa", "tipo_pessoa"]], on="matricula", how="left", validate="m:1")
    res = res.merge(b["dcoop"], on="pa", how="left", validate="m:1")
    usu = b["usuarios"].rename(columns={"login": "usuario", "nome": "nome_usuario", "setor": "departamento"})
    res = res.merge(usu[["usuario", "nome_usuario", "departamento"]], on="usuario", how="left", validate="m:1")

    # A base do Financeiro é a fonte oficial do motivo; casa por matrícula + data + valor
    bx = b["baixas"].rename(columns={"Motivos": "motivo"})
    res = res.merge(bx[["matricula", "data", "valor", "motivo", "id_baixa"]], on=["matricula", "data", "valor"], how="left")
    res["enquadramento"] = res["motivo"].map(
        lambda m: "Sem baixa do Financeiro" if pd.isna(m) else "Previsto no regulamento" if m in MOTIVOS_PREVISTOS else "Exceção")
    res["motivo"] = res["motivo"].fillna("Sem baixa registrada pelo Financeiro")
    res["mes"] = res["data"].dt.to_period("M").astype(str)
    res["departamento"] = res["departamento"].fillna("Não identificado")
    return res.sort_values("data").reset_index(drop=True)


def checar_qualidade(res: pd.DataFrame) -> pd.DataFrame:
    """Checagens de integridade que devem ficar zeradas antes de publicar o relatório."""
    checks = {
        "Matrícula sem cadastro de associado": res["nome"].isna().sum(),
        "PA sem regional no dCoop": res["regional"].isna().sum(),
        "Usuário sem cadastro de RH": (res["departamento"] == "Não identificado").sum(),
        "Valor zerado ou nulo": (res["valor"].fillna(0) == 0).sum(),
        "Resgate sem baixa do Financeiro (motivo desconhecido)": (res["enquadramento"] == "Sem baixa do Financeiro").sum(),
    }
    return pd.DataFrame({"checagem": list(checks), "ocorrencias": [int(v) for v in checks.values()]})
