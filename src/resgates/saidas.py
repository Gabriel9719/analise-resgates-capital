"""Saídas: planilha Excel formatada e apresentação PowerPoint gerada automaticamente."""
from __future__ import annotations

import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

AUTOR = "Gabriel Antônio Ribeiro"
AZUL, VERDE, CINZA = "#003641", "#00AE9D", "#7F8C8D"


# ---------------------------------------------------------------- Excel
def exportar_excel(abas: dict[str, pd.DataFrame], caminho: str | Path) -> Path:
    caminho = Path(caminho); caminho.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(caminho, engine="openpyxl") as xw:
        for nome, df in abas.items():
            df.to_excel(xw, sheet_name=nome[:31], index=False)
            ws = xw.sheets[nome[:31]]
            for c in ws[1]:
                c.font = Font(bold=True, color="FFFFFF")
                c.fill = PatternFill("solid", fgColor=AZUL[1:])
            for i, col in enumerate(df.columns, start=1):
                letra = get_column_letter(i)
                ws.column_dimensions[letra].width = min(max(len(str(col)), *(len(str(v)) for v in df[col].head(100))) + 2, 45) if len(df) else 14
                fmt = ("#,##0.00" if col.startswith(("valor", "ticket")) or col in ("Exceção", "Previsto no regulamento", "Sem baixa do Financeiro")
                       else "0.0%" if col.startswith(("pct", "participacao")) else "DD/MM/YYYY" if col == "data" else None)
                if fmt:
                    for c in ws[letra][1:]:
                        c.number_format = fmt
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
        xw.book.properties.creator = AUTOR
        xw.book.properties.lastModifiedBy = AUTOR
    return caminho


# ---------------------------------------------------------------- Gráficos
def _png(fig) -> io.BytesIO:
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=160, bbox_inches="tight"); plt.close(fig); buf.seek(0)
    return buf


def _barras(df, x, y, titulo, cor=AZUL, fmt="R$ {:,.0f}"):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(df[x].astype(str)[::-1], df[y][::-1], color=cor)
    ax.set_title(titulo, loc="left", fontsize=12, color=AZUL, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    for i, v in enumerate(df[y][::-1]):
        ax.text(v, i, " " + fmt.format(v).replace(",", "."), va="center", fontsize=8, color=CINZA)
    ax.tick_params(labelsize=8)
    return _png(fig)


def _linhas(mensal):
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for col, cor in (("Previsto no regulamento", AZUL), ("Exceção", VERDE), ("Sem baixa do Financeiro", CINZA)):
        if col in mensal:
            ax.plot(mensal["mes"], mensal[col], marker="o", color=cor, label=col)
    ax.set_title("Valor resgatado por mês", loc="left", fontsize=12, color=AZUL, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False); ax.legend(frameon=False, fontsize=8); ax.tick_params(labelsize=8)
    return _png(fig)


# ---------------------------------------------------------------- PowerPoint
def _titulo(slide, texto, sub=None):
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9), Inches(0.8)).text_frame
    tb.text = texto
    p = tb.paragraphs[0]; p.font.size = Pt(24); p.font.bold = True; p.font.color.rgb = RGBColor.from_string(AZUL[1:])
    if sub:
        q = tb.add_paragraph(); q.text = sub; q.font.size = Pt(12); q.font.color.rgb = RGBColor.from_string(CINZA[1:])


def _kpis(slide, itens):
    for i, (rot, val) in enumerate(itens):
        box = slide.shapes.add_textbox(Inches(0.5 + i * 2.3), Inches(1.6), Inches(2.1), Inches(1.2)).text_frame
        box.text = val
        box.paragraphs[0].font.size = Pt(22); box.paragraphs[0].font.bold = True
        box.paragraphs[0].font.color.rgb = RGBColor.from_string(VERDE[1:])
        r = box.add_paragraph(); r.text = rot; r.font.size = Pt(11)


def brl(v: float) -> str:
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_apresentacao(res, por_pa, por_reg, por_dep, padrao, mensal, caminho) -> Path:
    prs = Presentation(); prs.slide_width, prs.slide_height = Inches(10), Inches(5.625)
    prs.core_properties.author = AUTOR; prs.core_properties.last_modified_by = AUTOR
    prs.core_properties.title = "Resgates de capital - relatório gerencial"
    branco = prs.slide_layouts[6]

    s = prs.slides.add_slide(branco)
    _titulo(s, "Resgates de capital", f"Período: {res['data'].min():%d/%m/%Y} a {res['data'].max():%d/%m/%Y} · dados fictícios")
    exc = res[res["enquadramento"] == "Exceção"]
    _kpis(s, [("resgates", f"{len(res):,}".replace(",", ".")), ("valor resgatado", brl(res["valor"].sum())),
              ("ticket médio", brl(res["valor"].mean())), ("% exceções", f"{len(exc) / len(res):.1%}".replace(".", ","))])
    s.shapes.add_picture(_linhas(mensal), Inches(1.2), Inches(2.9), height=Inches(2.6))

    for titulo, df, x in (("Valor por regional", por_reg, "regional"),
                          ("Top 10 PAs por valor resgatado", por_pa.head(10), "nome_pa"),
                          ("Valor por departamento que realizou o lançamento", por_dep, "departamento")):
        s = prs.slides.add_slide(branco); _titulo(s, titulo)
        s.shapes.add_picture(_barras(df, x, "valor_total", ""), Inches(0.8), Inches(1.2), height=Inches(4.1))

    s = prs.slides.add_slide(branco)
    alerta = padrao["pa"][padrao["pa"]["alerta"]]
    _titulo(s, "Padrão das exceções", f"{len(alerta)} PA(s) acima do corte de {padrao['corte_pct'].iloc[0, 0]:.1%}".replace(".", ","))
    s.shapes.add_picture(_barras(padrao["motivos"], "motivo", "qtd", "Exceções por motivo", cor=VERDE, fmt="{:,.0f}"),
                         Inches(0.3), Inches(1.3), width=Inches(4.8))
    s.shapes.add_picture(_barras(padrao["pa"].head(8), "nome_pa", "pct_excecao", "% de exceções por PA", cor=VERDE, fmt="{:.0%}"),
                         Inches(5.1), Inches(1.3), width=Inches(4.7))

    caminho = Path(caminho); caminho.parent.mkdir(parents=True, exist_ok=True)
    prs.save(caminho)
    return caminho
