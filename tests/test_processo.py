import subprocess
import sys
from pathlib import Path

import pytest

from resgates.analise import padrao_excecoes, por_dimensao
from resgates.etl import carregar_bases, checar_qualidade, montar_base_resgates

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("bruto")
    subprocess.run([sys.executable, str(RAIZ / "scripts/gerar_dados_ficticios.py"), "--saida", str(pasta)], check=True)
    return montar_base_resgates(carregar_bases(pasta))


def test_somente_resgates_e_valores_positivos(base):
    assert (base["valor"] > 0).all()
    assert base["historico"].str.contains("RESGATE").all()


def test_joins_nao_duplicam_linhas(base):
    assert base["id_baixa"].dropna().is_unique


def test_integridade_das_bases(base):
    q = checar_qualidade(base).set_index("checagem")["ocorrencias"]
    assert q["Matrícula sem cadastro de associado"] == 0
    assert q["PA sem regional no dCoop"] == 0


def test_totais_por_dimensao_fecham(base):
    for dim in ("regional", "superintendencia", "departamento", "pa"):
        assert por_dimensao(base, dim)["valor_total"].sum() == pytest.approx(base["valor"].sum(), abs=0.05)


def test_detecta_pas_com_excecao_concentrada(base):
    alerta = set(padrao_excecoes(base)["pa"].query("alerta")["pa"])
    assert {"07", "15"} <= alerta   # padrão plantado no gerador de dados
