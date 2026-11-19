"""
ETL ENFR 2005-2009-2013-2018  (adaptado del notebook de Colab).
Lee data/raw/*.txt  ->  escribe CSVs limpios en data/clean/
La lógica de armonización/limpieza es la misma del notebook; solo cambió la E/S.
"""
import os, re, sys, json, glob, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", 60, "display.width", 200)

ANIOS = [2005, 2009, 2013, 2018]
ENTRADA = os.environ.get("ENFR_ENTRADA", "data/raw")
SALIDA  = os.environ.get("ENFR_SALIDA", "data/clean")
os.makedirs(ENTRADA, exist_ok=True); os.makedirs(SALIDA, exist_ok=True)

NO_MEDIDO_COMO_NEGATIVO = True
RANGOS = dict(edad=(18, 110), peso_kg=(30, 250), talla_cm=(120, 220), imc=(12, 70), fv_promedio_diario=(0, 20))

# ---- Archivos de entrada ----------------------------------------------------
ARCHIVOS = {}
for p in sorted(glob.glob(os.path.join(ENTRADA, "*.txt"))):
    anios_en_nombre = re.findall(r"(?<!\d)(20\d{2})(?!\d)", os.path.basename(p))
    if anios_en_nombre and int(anios_en_nombre[-1]) in ANIOS:
        ARCHIVOS[int(anios_en_nombre[-1])] = p
faltan = [a for a in ANIOS if a not in ARCHIVOS]
assert not faltan, f"Faltan archivos para los años: {faltan}. Encontrados: {ARCHIVOS}"
for a, p in sorted(ARCHIVOS.items()):
    print(a, "->", os.path.basename(p), f"({os.path.getsize(p)/1e6:.1f} MB)")



def leer_enfr(path):
    df = pd.read_csv(path, sep="|", dtype=str, encoding="utf-8-sig", keep_default_na=False,
                     quotechar='"', low_memory=False)
    df.columns = [c.strip().strip('"').lower() for c in df.columns]
    return df

def tipar(df):
    """Strings -> numérico compacto. Vacío/espacios -> NaN, coma decimal -> punto. Devuelve (df_tipado, columnas_no_numericas)."""
    out, no_num = {}, []
    for c in df.columns:
        s = df[c].astype("string").str.strip().replace("", pd.NA)
        n = pd.to_numeric(s.str.replace(",", ".", regex=False), errors="coerce")   # algunas columnas vienen con coma decimal
        if n.notna().sum() < s.notna().sum():            # hay valores no numéricos: se deja como texto
            out[c] = s; no_num.append(c); continue
        if (n.dropna() % 1 == 0).all():
            mx, mn = (n.max(), n.min()) if n.notna().any() else (0, 0)
            out[c] = n.astype("Int16" if -32000 < mn and mx < 32000 else "Int32")
        else:
            out[c] = n.astype("float32")
    return pd.DataFrame(out), no_num

RAW = {}
for anio, path in sorted(ARCHIVOS.items()):
    df, no_num = tipar(leer_enfr(path))
    RAW[anio] = df
    print(f"{anio}: {df.shape[0]:>6,} filas x {df.shape[1]:>3} cols | no numéricas: {no_num or '-'}")


filas = []
for a, df in RAW.items():
    idc = df.columns[0]
    filas.append(dict(anio=a, filas=len(df), columnas=df.shape[1], col_id=idc,
                      ids_duplicados=int(df[idc].duplicated().sum()),
                      filas_duplicadas=int(df.duplicated().sum()),
                      pct_nulos_total=round(float(df.isna().mean().mean()) * 100, 1)))
auditoria = pd.DataFrame(filas).set_index("anio")
display(auditoria) if "display" in globals() else print(auditoria)

comunes = set.intersection(*[set(df.columns) for df in RAW.values()])
print(f"\nColumnas con el mismo nombre en los {len(RAW)} años: {len(comunes)} de ~{int(np.mean([d.shape[1] for d in RAW.values()]))}"
      " -> los nombres cambian entre ediciones, por eso se armoniza explícitamente (sección 5).")

SPEC = {
 2005: dict(id="identifi", peso="ponderacion", provincia="prov", region="region", sexo="chch04", edad="chch05",
            instr="nivinstr", cob="cs", cob_tipo="multi", act="c_act", quintil="itf_uc_quintiles", hogar="cant_componentes",
            salud="cisg01", tabaco="consumo_tabaco_100", af=None, reg="c_reg", epi="c_epi", fv=None, cumple_fv=None,
            ha_med="ciha01", ha_dx="ciha03", col_med="cico01", col_dx="cico03", dia="cidi01",
            peso_kg="cipc05", talla_cm="cipc06"),
 2009: dict(id="identifi", peso="ponderacion", provincia="prvnc", region="region", sexo="bhch04", edad="bhch05",
            instr="nivinstr", cob="cob_salud", cob_tipo="multi", act="c_act", quintil="itf_uc_quintiles", hogar="cant_componentes",
            salud="bisg01", tabaco="con_ta", af="niv_af", reg="c_reg", epi=None, fv="promedio_fv_diario", cumple_fv="fruyver",
            ha_med="biha01", ha_dx="biha03", col_med="bico01", col_dx="bico03", dia="bidi01",
            peso_kg="bipc05", talla_cm="bipc06"),
 2013: dict(id="id", peso="ponderacion", provincia="cod_provincia", region="region", sexo="bhch04", edad="bhch05",
            instr="nivel_instruccion", cob="cobertura_salud", cob_tipo="bin", act="condicion_actividad", quintil="itf_uc_quintiles",
            hogar="cant_componentes", salud="bisg01", tabaco="consumo_tabaco_100", af="nivel_actividad_fisica",
            reg="c_reg", epi="c_epi", fv="promedio_fv_diario", cumple_fv="fruyver",
            ha_med="biha01", ha_dx="biha03", col_med="bico01", col_dx="bico03", dia="bidi01",
            peso_kg="bipc05", talla_cm="bipc06"),
 2018: dict(id="id", peso="wf1p", provincia="cod_provincia", region="region", sexo="bhch03", edad="bhch04",
            instr="nivel_instruccion", cob="cobertura_salud", cob_tipo="bin", act="condicion_actividad", quintil="quintil_uc",
            hogar="cant_componentes", salud="bisg01", tabaco="consumo_tabaco_100", af="nivel_actividad_fisica",
            reg="consumo_regular_riesgo", epi="consumo_episodico_excesivo", fv="promedio_fv_diario", cumple_fv="consumo_fv",
            ha_med="biha01", ha_dx="biha03", col_med="bico01", col_dx="bico03", dia="bidi01",
            peso_kg="bipc04", talla_cm="bipc05"),
}
# Variables oficiales de INDEC contra las que se valida la regla propia (sección 8)
OFICIALES = {2009: dict(hta="prv_ha", col="prv_col", dia="prv_dia"),
             2013: dict(hta="prevalencia_hipertension", col="prevalencia_colesterol", dia="prevalencia_diabetes"),
             2018: dict(hta="prevalencia_hipertension", col="prevalencia_colesterol", dia="prevalencia_diabetes")}
NSNC_PESO_TALLA = (999, 9999)     # códigos de "no sabe" en peso/talla autorreportados (2005-2013)

def g(df, col):
    """Columna como float64; si la variable no existe en esa edición -> NaN."""
    if col is None or col not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype="float64")
    return df[col].astype("float64")

def binaria(s, si=1, no=2):
    """si->1, no->0, cualquier otro código (9/99 = NS/NC, vacío) -> NaN."""
    return pd.Series(np.select([s == si, s == no], [1.0, 0.0], default=np.nan), index=s.index)

def armonizar(df, anio):
    s, o = SPEC[anio], pd.DataFrame(index=df.index)
    o["anio"] = anio
    o["id_original"] = df[s["id"]].astype("Int64").astype(str)
    o["id_unico"] = str(anio) + "_" + o["id_original"]
    o["peso_muestral"] = g(df, s["peso"])
    o["provincia"] = g(df, s["provincia"])
    o["region"] = g(df, s["region"])
    # --- sociodemográficas
    sexo = g(df, s["sexo"]);                  o["mujer"] = binaria(sexo, si=2, no=1)
    o["edad"] = g(df, s["edad"])
    instr = g(df, s["instr"]);                o["nivel_instruccion"] = instr.where(instr.between(1, 7))      # 8 = otro/especial -> NaN
    cob = g(df, s["cob"])
    if s["cob_tipo"] == "multi": o["tiene_cobertura"] = pd.Series(np.select([cob == 8, cob.between(1, 7)], [0.0, 1.0], default=np.nan), index=df.index)
    else:                        o["tiene_cobertura"] = binaria(cob, si=1, no=2)
    act = g(df, s["act"]);                    o["condicion_actividad"] = act.where(act.isin([1, 2, 3]))      # 1 ocupado, 2 desocupado, 3 inactivo
    q = g(df, s["quintil"]);                  o["quintil_ingreso"] = q.where(q.between(1, 5))
    o["cant_componentes"] = g(df, s["hogar"])
    # --- percepción y hábitos
    sal = g(df, s["salud"]);                  o["salud_autopercibida"] = sal.where(sal.between(1, 5))        # 1 excelente ... 5 mala
    tab = g(df, s["tabaco"]);                 o["tabaco"] = tab.where(tab.isin([1, 2, 3]))                   # 1 actual, 2 ex, 3 nunca
    af = g(df, s["af"]);                      o["actividad_fisica"] = af.where(af.isin([1, 2, 3]))           # ordinal INDEC (ver diccionario)
    o["alcohol_regular_riesgo"] = binaria(g(df, s["reg"]))
    o["alcohol_episodico"] = binaria(g(df, s["epi"]))
    o["fv_promedio_diario"] = g(df, s["fv"])
    o["cumple_5_fyv"] = binaria(g(df, s["cumple_fv"]))
    # --- medidas autorreportadas
    pk, tc = g(df, s["peso_kg"]), g(df, s["talla_cm"])
    o["peso_kg"] = pk.mask(pk.isin(NSNC_PESO_TALLA));  o["talla_cm"] = tc.mask(tc.isin(NSNC_PESO_TALLA))
    # --- condiciones de salud (autorreportadas)
    o["hta_medida"] = binaria(g(df, s["ha_med"]))
    dx = g(df, s["ha_dx"])
    o["hta"] = pd.Series(np.select([o["hta_medida"].eq(1) & dx.isin([1, 2]), o["hta_medida"].eq(1) & dx.eq(3)], [1.0, 0.0], default=np.nan), index=df.index)
    o["colesterol_medido"] = binaria(g(df, s["col_med"]))
    cdx = g(df, s["col_dx"])
    o["colesterol_alto"] = pd.Series(np.select([o["colesterol_medido"].eq(1) & cdx.eq(1), o["colesterol_medido"].eq(1) & cdx.eq(2)], [1.0, 0.0], default=np.nan), index=df.index)
    o["diabetes"] = binaria(g(df, s["dia"]))
    return o

H = pd.concat([armonizar(RAW[a], a) for a in sorted(RAW)], ignore_index=True)
print("Dataset armonizado (sin limpiar):", H.shape)

LOG = []
def log(paso, anio, n, detalle=""): LOG.append(dict(paso=paso, anio=anio, afectados=int(n), detalle=detalle))

# 1) duplicados por id
dup = H.duplicated("id_unico", keep="first")
for a, n in H[dup].groupby("anio").size().items(): log("duplicados_id", a, n, "se elimina")
H = H[~dup].copy()

# 2) filas sin variables críticas (necesarias para cualquier modelo/ponderación)
for col in ["edad", "mujer", "peso_muestral"]:
    m = H[col].isna()
    for a, n in H[m].groupby("anio").size().items(): log(f"sin_{col}", a, n, "se elimina la fila")
    H = H[~m]
m = H["peso_muestral"] <= 0
for a, n in H[m].groupby("anio").size().items(): log("peso_muestral<=0", a, n, "se elimina la fila")
H = H[~m].copy()

# 3) valores fuera de rango -> NaN
for col, (lo, hi) in RANGOS.items():
    if col == "imc": continue            # se controla después de calcularlo
    fuera = H[col].notna() & ~H[col].between(lo, hi)
    for a, n in H[fuera].groupby("anio").size().items(): log(f"fuera_de_rango_{col}", a, n, f"fuera de [{lo}, {hi}] -> NaN")
    H.loc[fuera, col] = np.nan

# 4) IMC (peso / talla^2). 2018 trae su propio IMC: coincide con este cálculo (dif. máx ~0.005)
H["imc"] = H["peso_kg"] / (H["talla_cm"] / 100) ** 2
lo, hi = RANGOS["imc"]
fuera = H["imc"].notna() & ~H["imc"].between(lo, hi)
for a, n in H[fuera].groupby("anio").size().items(): log("fuera_de_rango_imc", a, n, f"fuera de [{lo}, {hi}] -> NaN")
H.loc[fuera, "imc"] = np.nan

LOG_LIMPIEZA = pd.DataFrame(LOG)
print(f"Filas tras limpieza: {len(H):,}")
display(LOG_LIMPIEZA) if "display" in globals() else print(LOG_LIMPIEZA)

H["obesidad"] = np.where(H["imc"].isna(), np.nan, (H["imc"] >= 30).astype(float))
H["sobrepeso"] = np.where(H["imc"].isna(), np.nan, (H["imc"] >= 25).astype(float))      # incluye obesidad
H["salud_regular_mala"] = np.where(H["salud_autopercibida"].isna(), np.nan, (H["salud_autopercibida"] >= 4).astype(float))

COND = ["hta", "diabetes", "colesterol_alto", "obesidad"]
cond = H[COND].fillna(0) if NO_MEDIDO_COMO_NEGATIVO else H[COND]
algun_pos = (cond == 1).any(axis=1)
todos_conocidos = cond.notna().all(axis=1)
H["n_condiciones"] = np.where(todos_conocidos, cond.sum(axis=1), np.nan)
H["riesgo_cardiometabolico"] = np.where(algun_pos, 1.0, np.where(todos_conocidos, 0.0, np.nan))

TARGETS = ["hta", "diabetes", "colesterol_alto", "obesidad", "n_condiciones", "riesgo_cardiometabolico", "salud_regular_mala"]
resumen = H.groupby("anio")[TARGETS].mean().round(3).T
resumen.columns = [f"prev_{c}" for c in resumen.columns]
resumen["pct_nulos"] = (H[TARGETS].isna().mean() * 100).round(1)
print("Prevalencia SIN ponderar por año (n_condiciones = promedio) y % de nulos:")
display(resumen) if "display" in globals() else print(resumen)

filas = []
Hi = H.set_index(["anio", "id_original"])
for a, of in OFICIALES.items():
    raw = RAW[a]; ids = raw[SPEC[a]["id"]].astype("Int64").astype(str)
    for nombre, var_propia in [("hta", "hta"), ("col", "colesterol_alto"), ("dia", "diabetes")]:
        oficial = pd.Series(binaria(raw[of[nombre]].astype("float64")).values, index=ids.values)
        propia = Hi.loc[a][var_propia]
        j = pd.concat([oficial.rename("of"), propia.rename("propia")], axis=1, join="inner")
        j = j[j["of"].notna() | j["propia"].notna()]
        filas.append(dict(anio=a, variable=var_propia, comparados=len(j), coinciden_pct=round(100 * (j["of"].fillna(-1) == j["propia"].fillna(-1)).mean(), 2)))
VALIDACION = pd.DataFrame(filas)
display(VALIDACION) if "display" in globals() else print(VALIDACION)
assert (VALIDACION["coinciden_pct"] > 98).all(), "La regla propia no replica la variable oficial: revisar SPEC"

# peso relativo dentro de cada año (media 1) -> permite combinar años sin que un año domine por tener más población expandida
H["peso_rel"] = H["peso_muestral"] / H.groupby("anio")["peso_muestral"].transform("mean")
H["grupo_etario"] = pd.cut(H["edad"], [17, 24, 34, 49, 64, 200], labels=[1, 2, 3, 4, 5]).astype("float")   # 1:18-24 2:25-34 3:35-49 4:50-64 5:65+

ENTEROS = ["anio", "provincia", "region", "mujer", "edad", "nivel_instruccion", "tiene_cobertura", "condicion_actividad",
           "quintil_ingreso", "cant_componentes", "salud_autopercibida", "tabaco", "actividad_fisica", "alcohol_regular_riesgo",
           "alcohol_episodico", "cumple_5_fyv", "hta_medida", "hta", "colesterol_medido", "colesterol_alto", "diabetes",
           "obesidad", "sobrepeso", "salud_regular_mala", "n_condiciones", "riesgo_cardiometabolico", "grupo_etario"]
for c in ENTEROS: H[c] = H[c].round().astype("Int16" if c in ("anio", "provincia", "edad", "cant_componentes") else "Int8")
for c in ["peso_muestral", "peso_rel", "peso_kg", "talla_cm", "imc", "fv_promedio_diario"]: H[c] = H[c].astype("float32")
H = H[["id_unico", "anio", "peso_muestral", "peso_rel"] + [c for c in H.columns if c not in ("id_unico", "id_original", "anio", "peso_muestral", "peso_rel")] + ["id_original"]]
H = H.reset_index(drop=True)

DICC = [
 ("id_unico", "id", "Identificador único: año_idoriginal"),
 ("id_original", "id", "Identificador en el archivo original"),
 ("anio", "meta", "Edición de la ENFR"),
 ("peso_muestral", "peso", "Factor de expansión (2018: wf1p). No comparable en escala entre años"),
 ("peso_rel", "peso", "peso_muestral / media del año. Usar como sample_weight al combinar años"),
 ("provincia", "feature cat", "Código INDEC de provincia"),
 ("region", "feature cat", "Región (1 GBA, 2 Pampeana, 3 NOA, 4 NEA, 5 Cuyo, 6 Patagonia; verificar con diccionario INDEC)"),
 ("mujer", "feature bin", "1 mujer, 0 varón"),
 ("edad", "feature num", "Años (18-110)"),
 ("grupo_etario", "feature ord", "1: 18-24, 2: 25-34, 3: 35-49, 4: 50-64, 5: 65+"),
 ("nivel_instruccion", "feature ord", "1..7 (INDEC); el código 8 se pasa a NaN"),
 ("tiene_cobertura", "feature bin", "1 tiene cobertura de salud (obra social/prepaga/etc.), 0 no"),
 ("condicion_actividad", "feature cat", "1 ocupado, 2 desocupado, 3 inactivo"),
 ("quintil_ingreso", "feature ord", "Quintil de ingreso per cápita del hogar (1 más bajo)"),
 ("cant_componentes", "feature num", "Cantidad de integrantes del hogar"),
 ("salud_autopercibida", "feature ord", "1 excelente, 2 muy buena, 3 buena, 4 regular, 5 mala"),
 ("tabaco", "feature cat", "1 fumador actual, 2 ex fumador, 3 nunca"),
 ("actividad_fisica", "feature ord", "Nivel de actividad física INDEC (1-3). NaN en 2005. Verificar sentido del orden con el diccionario INDEC"),
 ("alcohol_regular_riesgo", "feature bin", "Consumo regular de riesgo (1 sí)"),
 ("alcohol_episodico", "feature bin", "Consumo episódico excesivo (1 sí). NaN en 2009"),
 ("fv_promedio_diario", "feature num", "Porciones diarias de frutas y verduras. NaN en 2005. Puede haber diferencias de cálculo entre ediciones"),
 ("cumple_5_fyv", "feature bin", "Consume 5+ porciones de frutas y verduras por día. NaN en 2005"),
 ("peso_kg", "feature num", "Peso autorreportado (kg)"),
 ("talla_cm", "feature num", "Talla autorreportada (cm)"),
 ("imc", "feature num", "peso / talla^2 con medidas autorreportadas"),
 ("hta_medida", "aux", "Se midió la presión alguna vez. Auxiliar (leakage para hta / compuestos)"),
 ("colesterol_medido", "aux", "Se midió el colesterol alguna vez. Auxiliar (leakage para colesterol_alto / compuestos)"),
 ("hta", "target / feature", "Hipertensión diagnosticada (NaN si nunca se midió la presión)"),
 ("colesterol_alto", "target / feature", "Colesterol alto diagnosticado (NaN si nunca se midió)"),
 ("diabetes", "target / feature", "Diabetes o glucemia elevada diagnosticada"),
 ("obesidad", "target / feature", "IMC >= 30"),
 ("sobrepeso", "feature bin", "IMC >= 25 (incluye obesidad)"),
 ("salud_regular_mala", "target", "Autopercibe salud regular o mala"),
 ("n_condiciones", "target", "Nº de condiciones entre hta, diabetes, colesterol_alto, obesidad (0-4)"),
 ("riesgo_cardiometabolico", "target", "1 si tiene al menos una de las 4 condiciones; ver NO_MEDIDO_COMO_NEGATIVO"),
]
orden = [d[0] for d in DICC]
assert set(orden) == set(H.columns), f"Columnas sin documentar: {set(H.columns) ^ set(orden)}"
disp = H.groupby("anio").apply(lambda x: (x.notna().mean() * 100).round(0)).T
disp.loc["anio"] = 100.0
diccionario = pd.DataFrame(DICC, columns=["variable", "rol", "descripcion"]).set_index("variable").join(disp.add_prefix("pct_no_nulo_")).loc[orden]

qa_nulos = (H.groupby("anio").apply(lambda x: (x.isna().mean() * 100).round(1))).T
ruta_ds = os.path.join(SALIDA, "enfr_armonizado.csv")
H.to_csv(ruta_ds, index=False)
diccionario.to_csv(os.path.join(SALIDA, "diccionario_variables.csv"))
qa_nulos.to_csv(os.path.join(SALIDA, "qa_nulos_por_anio.csv"))
LOG_LIMPIEZA.to_csv(os.path.join(SALIDA, "qa_log_limpieza.csv"), index=False)
VALIDACION.to_csv(os.path.join(SALIDA, "qa_validacion_oficial.csv"), index=False)
auditoria.to_csv(os.path.join(SALIDA, "qa_auditoria_cruda.csv"))
resumen.to_csv(os.path.join(SALIDA, "qa_prevalencias_sin_ponderar.csv"))
print("Guardado:", ruta_ds, f"| {H.shape[0]:,} filas x {H.shape[1]} columnas | {H.memory_usage(deep=True).sum()/1e6:.1f} MB en memoria")
print("\n% de datos disponibles por variable y año:")
display(diccionario.drop(columns="descripcion")) if "display" in globals() else print(diccionario.drop(columns="descripcion"))