"""Gera as cinco bases FICTÍCIAS usadas no processo de resgates de capital.

Bases geradas (data/bruto/):
  dcoop.csv              PA -> regional -> superintendência
  associados.csv         cadastro de cooperados (exportado em UTF-16 com TAB, como no sistema de origem)
  usuarios.csv           logins do sistema + setor/função (cadastro de RH)
  movimento_conta_201.csv lançamentos de capital social por matrícula
  baixas_financeiro.csv  baixas realizadas pelo Financeiro, com o motivo preenchido manualmente
"""
from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

NOMES = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Fábio", "Gisele", "Hugo", "Isabela", "João", "Karen", "Lucas",
         "Marina", "Nelson", "Olívia", "Paulo", "Queila", "Rafael", "Sílvia", "Tiago", "Úrsula", "Vítor", "Wanda", "Yuri"]
SOBRENOMES = ["Almeida", "Barros", "Cardoso", "Duarte", "Esteves", "Freitas", "Gomes", "Henrique", "Igarashi",
              "Jardim", "Lopes", "Macedo", "Nogueira", "Oliveira", "Pacheco", "Queiroz", "Rocha", "Siqueira"]
REGIONAIS = {"Regional Norte": "Superintendência 1", "Regional Centro": "Superintendência 1",
             "Regional Sul": "Superintendência 2", "Regional Oeste": "Superintendência 2"}
SETORES = [("Financeiro", "Analista Financeiro"), ("Financeiro", "Assistente Financeiro"),
           ("Cadastro", "Analista de Cadastro"), ("Atendimento", "Gerente de Relacionamento"),
           ("Atendimento", "Assistente de Atendimento"), ("Controladoria", "Analista Contábil")]
# motivos previstos no regulamento fictício e motivos tratados como exceção
MOTIVOS_REGRA = ["Desligamento do quadro social", "Falecimento do cooperado", "Aposentadoria",
                 "Resgate parcial anual (até 10%)"]
MOTIVOS_EXCECAO = ["Necessidade financeira do cooperado", "Quitação de operação de crédito",
                   "Negociação comercial", "Sem motivo informado"]


def nome(rng):
    return f"{rng.choice(NOMES)} {rng.choice(SOBRENOMES)} {rng.choice(SOBRENOMES)}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", default="data/bruto")
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    out = Path(a.saida); out.mkdir(parents=True, exist_ok=True)

    # dCoop
    pas = []
    for i in range(1, 25):
        reg = list(REGIONAIS)[(i - 1) % 4]
        pas.append({"pa": f"{i:02d}", "nome_pa": f"PA {i:02d} - Cidade {chr(64 + i)}", "regional": reg,
                    "superintendencia": REGIONAIS[reg]})
    with (out / "dcoop.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pas[0].keys(), delimiter=";"); w.writeheader(); w.writerows(pas)

    # Associados (UTF-16 + TAB, como exportado pelo sistema de origem)
    assoc = []
    for m in range(100001, 101501):
        assoc.append({"matricula": m, "nome": nome(rng), "pa": rng.choice(pas)["pa"],
                      "tipo_pessoa": "PF" if rng.random() < 0.85 else "PJ",
                      "data_associacao": f"{date(2008, 1, 1) + timedelta(days=rng.randint(0, 6500)):%d/%m/%Y}"})
    with (out / "associados.csv").open("w", newline="", encoding="utf-16") as f:
        w = csv.DictWriter(f, fieldnames=assoc[0].keys(), delimiter="\t"); w.writeheader(); w.writerows(assoc)

    # Usuários do sistema
    usuarios = []
    for i in range(1, 31):
        setor, funcao = rng.choice(SETORES) if i > 6 else SETORES[i % 2]
        usuarios.append({"login": f"USR{i:03d}_COOP", "nome": nome(rng), "setor": setor, "funcao": funcao})
    with (out / "usuarios.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=usuarios[0].keys(), delimiter=";"); w.writeheader(); w.writerows(usuarios)

    # Movimento da conta 201 (capital social) e baixas do Financeiro
    mov, baixas = [], []
    pas_problema = {"07", "15"}                           # padrão plantado: exceções concentradas
    for n in range(1, 641):
        a_ = rng.choice(assoc)
        d = date(2026, 1, 2) + timedelta(days=rng.randint(0, 300))
        excecao = rng.random() < (0.45 if a_["pa"] in pas_problema else 0.12)
        motivo = rng.choice(MOTIVOS_EXCECAO if excecao else MOTIVOS_REGRA)
        valor = round(rng.lognormvariate(7.3, 0.9), 2)
        if motivo.startswith("Resgate parcial"):
            valor = round(valor * 0.3, 2)
        usuario = rng.choice(usuarios)
        mov.append({"data": f"{d:%d/%m/%Y}", "matricula": a_["matricula"], "historico": "RESGATE DE CAPITAL",
                    "valor": f"{-valor:.2f}".replace(".", ","), "usuario": usuario["login"]})
        if usuario["setor"] == "Financeiro" or rng.random() < 0.80:
            baixas.append({"id_baixa": n, "data": f"{d:%d/%m/%Y}", "matricula": a_["matricula"],
                           "valor": f"{valor:.2f}".replace(".", ","), "Motivos": motivo})
    for _ in range(150):                                    # integralizações (não são resgates)
        a_ = rng.choice(assoc)
        d = date(2026, 1, 2) + timedelta(days=rng.randint(0, 300))
        mov.append({"data": f"{d:%d/%m/%Y}", "matricula": a_["matricula"], "historico": "INTEGRALIZAÇÃO DE CAPITAL",
                    "valor": f"{rng.uniform(50, 500):.2f}".replace(".", ","), "usuario": rng.choice(usuarios)["login"]})
    with (out / "movimento_conta_201.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=mov[0].keys(), delimiter=";"); w.writeheader(); w.writerows(mov)
    with (out / "baixas_financeiro.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=baixas[0].keys(), delimiter=";"); w.writeheader(); w.writerows(baixas)
    print(f"Bases fictícias geradas em {out}: {len(assoc)} associados, {len(mov)} movimentos, {len(baixas)} baixas")


if __name__ == "__main__":
    main()
