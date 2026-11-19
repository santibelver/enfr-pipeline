"""Dashboard Streamlit – ENFR 2005-2018. Lee las tablas de data/eda y los reportes QA de data/clean."""
import os
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="ENFR 2005-2018", page_icon="📊", layout="wide")
EDA, CLEAN = "data/eda", "data/clean"

INDICADORES = {
    "hta": "Hipertensión diagnosticada",
    "diabetes": "Diabetes / glucemia elevada",
    "colesterol_alto": "Colesterol alto diagnosticado",
    "obesidad": "Obesidad (IMC ≥ 30)",
    "sobrepeso": "Sobrepeso u obesidad (IMC ≥ 25)",
    "riesgo_cardiometabolico": "Riesgo cardiometabólico (≥ 1 condición)",
    "salud_regular_mala": "Salud autopercibida regular/mala",
    "tabaco_actual": "Fumador actual",
    "alcohol_regular_riesgo": "Consumo regular de alcohol de riesgo",
    "alcohol_episodico": "Consumo episódico excesivo de alcohol",
    "cumple_5_fyv": "Consume 5+ porciones de frutas y verduras",
}
NOTA_HTA = {"hta", "colesterol_alto"}
GRUPOS = {1: "18-24", 2: "25-34", 3: "35-49", 4: "50-64", 5: "65+"}
SEXO = {0: "Varón", 1: "Mujer"}
COBERTURA = {0: "Sin cobertura", 1: "Con cobertura"}
INSTR = {1: "1 (menor)", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7 (mayor)"}
# Nombres según códigos INDEC estándar: VERIFICAR contra el diccionario de cada edición (se muestra el código al lado).
PROV = {2: "CABA", 6: "Buenos Aires", 10: "Catamarca", 14: "Córdoba", 18: "Corrientes", 22: "Chaco", 26: "Chubut",
        30: "Entre Ríos", 34: "Formosa", 38: "Jujuy", 42: "La Pampa", 46: "La Rioja", 50: "Mendoza", 54: "Misiones",
        58: "Neuquén", 62: "Río Negro", 66: "Salta", 70: "San Juan", 74: "San Luis", 78: "Santa Cruz", 82: "Santa Fe",
        86: "Santiago del Estero", 90: "Tucumán", 94: "Tierra del Fuego"}


@st.cache_data
def leer(carpeta, nombre, **kw):
    p = os.path.join(carpeta, nombre)
    return pd.read_csv(p, **kw) if os.path.exists(p) else None


if leer(EDA, "prevalencia_por_anio.csv") is None:
    st.error("Todavía no hay datos: corré el pipeline (n8n → GitHub Actions) para generar data/eda y data/clean.")
    st.stop()

anual = leer(EDA, "prevalencia_por_anio.csv")
kpis = leer(EDA, "kpis_por_anio.csv")
anios_disp = sorted(anual["anio"].unique())

# ------------------------------------------------------------------ sidebar
st.sidebar.title("Filtros")
anios = st.sidebar.multiselect("Ediciones", anios_disp, default=anios_disp)
ind = st.sidebar.selectbox("Indicador", list(INDICADORES), format_func=INDICADORES.get)
if not anios:
    st.warning("Elegí al menos una edición.")
    st.stop()
st.sidebar.caption("Prevalencias ponderadas con el factor de expansión relativo (peso_rel). Son autorreportes, no mediciones clínicas.")
if ind in NOTA_HTA:
    st.sidebar.info("Se calcula solo sobre quienes se midieron alguna vez (presión / colesterol).")


def pct(x): return None if pd.isna(x) else round(100 * x, 1)


def dimension(nombre, col, mapa=None):
    d = leer(EDA, nombre)
    d = d[d["anio"].isin(anios)].dropna(subset=[col, ind]).copy()
    d[col] = d[col].astype(int)
    d["grupo"] = d[col].map(mapa) if mapa else d[col].astype(str)
    d["grupo"] = d["grupo"].fillna(d[col].astype(str))
    d["prev"] = (100 * d[ind]).round(1)
    d["Edición"] = d["anio"].astype(str)
    return d


def barras(d, orden=None, titulo=""):
    fig = px.bar(d, x="grupo", y="prev", color="Edición", barmode="group", text="prev",
                 labels={"grupo": "", "prev": "% de la población"}, title=titulo,
                 category_orders={"grupo": orden} if orden else None)
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_layout(yaxis_range=[0, max(5, d["prev"].max() * 1.2)], legend_title="")
    return fig


st.title("Encuesta Nacional de Factores de Riesgo (ENFR)")
st.caption("Argentina · ediciones 2005, 2009, 2013 y 2018 · datos armonizados por el pipeline ETL")

tabs = st.tabs(["Resumen", "Perfil sociodemográfico", "Territorio", "IMC y hábitos", "Correlaciones", "Calidad de datos"])

# ------------------------------------------------------------------ Resumen
with tabs[0]:
    a = anual[anual["anio"].isin(anios)].sort_values("anio")
    k = kpis[kpis["anio"].isin(anios)]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Encuestados (ediciones elegidas)", f"{int(k['encuestados'].sum()):,}".replace(",", "."))
    ult, pri = a.iloc[-1], a.iloc[0]
    c2.metric(f"{INDICADORES[ind]} · {int(ult['anio'])}", f"{pct(ult[ind])} %")
    if len(a) > 1:
        c3.metric(f"Variación vs {int(pri['anio'])}", f"{pct(ult[ind]) - pct(pri[ind]):+.1f} pp")
    c4.metric("Edad media (última edición)", f"{k.sort_values('anio').iloc[-1]['edad_media']:.1f} años")

    fig = px.line(a.assign(prev=(100 * a[ind]).round(1), Edición=a["anio"].astype(str)), x="anio", y="prev", markers=True,
                  text="prev", labels={"anio": "Edición", "prev": "% de la población"}, title=f"Evolución: {INDICADORES[ind]}")
    fig.update_traces(textposition="top center")
    fig.update_xaxes(tickvals=list(a["anio"]))
    fig.update_layout(yaxis_rangemode="tozero")
    st.plotly_chart(fig, use_container_width=True)

    todos = a.set_index("anio")[[c for c in INDICADORES if c in a.columns]].mul(100).round(1).rename(columns=INDICADORES).T
    st.subheader("Todos los indicadores (%)")
    st.dataframe(todos, use_container_width=True)

# ------------------------------------------------------------------ Perfil
with tabs[1]:
    dim = st.radio("Desagregar por", ["Sexo", "Grupo etario", "Quintil de ingreso", "Nivel de instrucción", "Cobertura de salud"], horizontal=True)
    cfg = {"Sexo": ("prevalencia_por_sexo.csv", "mujer", SEXO, None),
           "Grupo etario": ("prevalencia_por_grupo_etario.csv", "grupo_etario", GRUPOS, list(GRUPOS.values())),
           "Quintil de ingreso": ("prevalencia_por_quintil.csv", "quintil_ingreso", {i: f"Q{i}" for i in range(1, 6)}, [f"Q{i}" for i in range(1, 6)]),
           "Nivel de instrucción": ("prevalencia_por_instruccion.csv", "nivel_instruccion", INSTR, list(INSTR.values())),
           "Cobertura de salud": ("prevalencia_por_cobertura.csv", "tiene_cobertura", COBERTURA, None)}[dim]
    d = dimension(cfg[0], cfg[1], cfg[2])
    st.plotly_chart(barras(d, cfg[3], f"{INDICADORES[ind]} por {dim.lower()}"), use_container_width=True)
    if dim == "Quintil de ingreso":
        st.caption("Q1 = hogares de menores ingresos per cápita, Q5 = mayores.")
    if dim == "Nivel de instrucción":
        st.caption("Escala ordinal INDEC 1-7: confirmar la equivalencia exacta con el diccionario oficial.")

# ------------------------------------------------------------------ Territorio
with tabs[2]:
    anio_t = st.selectbox("Edición", sorted(anios, reverse=True))
    p = leer(EDA, "prevalencia_por_provincia.csv")
    p = p[(p["anio"] == anio_t)].dropna(subset=[ind, "provincia"]).copy()
    p["provincia"] = p["provincia"].astype(int)
    p["Provincia"] = p["provincia"].map(lambda c: f"{PROV.get(c, 'Código')} ({c})")
    p["prev"] = (100 * p[ind]).round(1)
    p = p.sort_values("prev")
    fig = px.bar(p, x="prev", y="Provincia", orientation="h", text="prev", labels={"prev": "% de la población", "Provincia": ""},
                 title=f"{INDICADORES[ind]} por provincia · {anio_t}", height=max(450, 24 * len(p)))
    fig.update_traces(texttemplate="%{text:.1f}")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Los nombres se asignan según los códigos INDEC estándar y el código se muestra entre paréntesis; "
               "verificar contra el diccionario de cada edición. Con muestras provinciales chicas, las diferencias pequeñas no son concluyentes.")
    r = dimension("prevalencia_por_region.csv", "region", {i: f"Región {i}" for i in range(1, 9)})
    st.plotly_chart(barras(r, None, f"{INDICADORES[ind]} por región (código INDEC)"), use_container_width=True)

# ------------------------------------------------------------------ IMC y hábitos
with tabs[3]:
    h = leer(EDA, "imc_histograma.csv")
    h = h[h["anio"].isin(anios)].assign(Edición=lambda x: x["anio"].astype(str), pct=lambda x: 100 * x["proporcion"])
    fig = px.line(h, x="imc_desde", y="pct", color="Edición", labels={"imc_desde": "IMC (intervalos de 2)", "pct": "% de la población"},
                  title="Distribución del IMC (autorreportado)")
    fig.add_vline(x=25, line_dash="dot"); fig.add_vline(x=30, line_dash="dot")
    st.plotly_chart(fig, use_container_width=True)
    hab = [c for c in ["tabaco_actual", "alcohol_regular_riesgo", "alcohol_episodico", "cumple_5_fyv"] if c in anual.columns]
    t = anual[anual["anio"].isin(anios)].melt(id_vars="anio", value_vars=hab, var_name="indicador", value_name="v").dropna()
    t["Indicador"] = t["indicador"].map(INDICADORES); t["pct"] = (100 * t["v"]).round(1)
    fig = px.line(t, x="anio", y="pct", color="Indicador", markers=True, labels={"anio": "Edición", "pct": "% de la población"},
                  title="Hábitos a lo largo del tiempo")
    fig.update_xaxes(tickvals=list(sorted(t["anio"].unique())))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Algunas preguntas no existen o cambiaron entre ediciones (alcohol episódico no está en 2009; frutas y verduras no está en 2005): "
               "los huecos son esperables.")

# ------------------------------------------------------------------ Correlaciones
with tabs[4]:
    c = leer(EDA, "correlaciones.csv", index_col=0)
    fig = px.imshow(c, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1, aspect="auto", height=650,
                    title="Correlación de Pearson (exploratoria, sin ponderar)")
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ Calidad
with tabs[5]:
    st.subheader("% de valores nulos por variable y edición")
    q = leer(CLEAN, "qa_nulos_por_anio.csv", index_col=0)
    if q is not None:
        st.dataframe(q.style.background_gradient(cmap="Reds", axis=None, vmin=0, vmax=100), use_container_width=True, height=600)
    st.subheader("Registro de limpieza")
    lg = leer(CLEAN, "qa_log_limpieza.csv")
    if lg is not None: st.dataframe(lg, use_container_width=True)
    st.subheader("Validación contra variables oficiales de INDEC")
    v = leer(CLEAN, "qa_validacion_oficial.csv")
    if v is not None: st.dataframe(v, use_container_width=True)
    dic = leer(CLEAN, "diccionario_variables.csv")
    if dic is not None:
        with st.expander("Diccionario de variables"):
            st.dataframe(dic, use_container_width=True)
