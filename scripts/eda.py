"""
EDA sobre data/clean/enfr_armonizado.csv  ->  tablas agregadas en data/eda/*.csv
(las prevalencias son PONDERADAS con peso_rel, como corresponde a un diseño muestral complejo).
"""
import os
import numpy as np
import pandas as pd

ENTRADA = os.environ.get("ENFR_SALIDA", "data/clean")
SALIDA = os.environ.get("ENFR_EDA", "data/eda")
os.makedirs(SALIDA, exist_ok=True)

df = pd.read_csv(os.path.join(ENTRADA, "enfr_armonizado.csv"), low_memory=False)
print("Dataset:", df.shape)

TARGETS = ["hta", "diabetes", "colesterol_alto", "obesidad", "sobrepeso", "riesgo_cardiometabolico", "salud_regular_mala"]
HABITOS = ["tabaco_actual", "alcohol_regular_riesgo", "alcohol_episodico", "cumple_5_fyv"]

# variables derivadas para el dashboard
df["tabaco_actual"] = np.where(df["tabaco"].isna(), np.nan, (df["tabaco"] == 1).astype(float))


def wmean(d, col):
    m = d[col].notna()
    return np.average(d.loc[m, col], weights=d.loc[m, "peso_rel"]) if m.any() else np.nan


def prevalencias(por, vars_):
    """Fila por (anio, grupo) y columna por variable: media ponderada + n válido."""
    filas = []
    for keys, d in df.groupby(["anio"] + por):
        keys = keys if isinstance(keys, tuple) else (keys,)
        fila = dict(zip(["anio"] + por, keys))
        fila["n"] = len(d)
        for v in vars_:
            fila[v] = wmean(d, v)
            fila[f"n_{v}"] = int(d[v].notna().sum())
        filas.append(fila)
    return pd.DataFrame(filas)


vars_all = TARGETS + HABITOS
prevalencias([], vars_all).round(4).to_csv(f"{SALIDA}/prevalencia_por_anio.csv", index=False)
prevalencias(["mujer"], vars_all).round(4).to_csv(f"{SALIDA}/prevalencia_por_sexo.csv", index=False)
prevalencias(["grupo_etario"], vars_all).round(4).to_csv(f"{SALIDA}/prevalencia_por_grupo_etario.csv", index=False)
prevalencias(["quintil_ingreso"], vars_all).round(4).to_csv(f"{SALIDA}/prevalencia_por_quintil.csv", index=False)
prevalencias(["nivel_instruccion"], vars_all).round(4).to_csv(f"{SALIDA}/prevalencia_por_instruccion.csv", index=False)
prevalencias(["tiene_cobertura"], vars_all).round(4).to_csv(f"{SALIDA}/prevalencia_por_cobertura.csv", index=False)
prevalencias(["region"], vars_all).round(4).to_csv(f"{SALIDA}/prevalencia_por_region.csv", index=False)
prevalencias(["provincia"], vars_all).round(4).to_csv(f"{SALIDA}/prevalencia_por_provincia.csv", index=False)

# distribución de IMC (histograma ponderado por año)
bins = np.arange(12, 62, 2)
filas = []
for a, d in df.groupby("anio"):
    d = d[d["imc"].notna()]
    h, edges = np.histogram(d["imc"], bins=bins, weights=d["peso_rel"])
    for hi, lo in zip(h / h.sum(), edges[:-1]):
        filas.append(dict(anio=a, imc_desde=lo, proporcion=round(float(hi), 5)))
pd.DataFrame(filas).to_csv(f"{SALIDA}/imc_histograma.csv", index=False)

# resumen de variables numéricas por año
num = ["edad", "imc", "peso_kg", "talla_cm", "fv_promedio_diario", "cant_componentes"]
df.groupby("anio")[num].describe().round(2).T.to_csv(f"{SALIDA}/describe_numericas.csv")

# correlaciones (Pearson sobre binarias/ordinales/numéricas; sin ponderar, solo exploratorio)
corr_vars = ["edad", "mujer", "imc", "quintil_ingreso", "nivel_instruccion", "tiene_cobertura", "tabaco_actual",
             "alcohol_regular_riesgo", "cumple_5_fyv", "salud_autopercibida", "hta", "diabetes", "colesterol_alto", "obesidad"]
df[corr_vars].corr().round(3).to_csv(f"{SALIDA}/correlaciones.csv")

# KPIs globales
kpis = df.groupby("anio").agg(encuestados=("id_unico", "count"), edad_media=("edad", "mean")).round(1)
kpis["poblacion_expandida"] = df.groupby("anio")["peso_muestral"].sum().round(0)
kpis.to_csv(f"{SALIDA}/kpis_por_anio.csv")

print("EDA listo ->", sorted(os.listdir(SALIDA)))
