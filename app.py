import streamlit as st
import pandas as pd
import datetime
import re
import glob
import os
import plotly.express as px
import plotly.graph_objects as go

# Configuración básica de la página
st.set_page_config(page_title="Sistema de Auditoría de Inventario", layout="wide")

# --- ESTILOS VISUALES CORPORATIVOS (AZUL & TARJETAS REDONDEADAS) ---
st.markdown("""
    <style>
    /* Estilizado del Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid rgba(13, 110, 253, 0.2) !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #f1f5f9 !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px !important;
    }
    [data-testid="stSidebar"] label {
        color: #94a3b8 !important;
        font-size: 0.9rem !important;
    }
    
    /* Selectbox del Sidebar */
    [data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #1e293b !important;
        border: 1px solid rgba(13, 110, 253, 0.3) !important;
        color: #f8fafc !important;
        border-radius: 6px !important;
    }
    
    /* Botones primarios */
    button[kind="primary"], button[kind="primaryFormSubmit"] {
        background-color: #0D6EFD !important;
        border-color: #0D6EFD !important;
        color: white !important;
    }
    button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {
        background-color: #0b5ed7 !important;
        border-color: #0a58ca !important;
    }
    
    [data-testid="stForm"] {
        background-color: rgba(13, 110, 253, 0.03);
        border: 1px solid rgba(13, 110, 253, 0.2);
        border-radius: 8px;
        padding: 1rem;
    }
    
    [data-testid="stFileUploadDropzone"] {
        border-color: rgba(13, 110, 253, 0.3);
        background-color: rgba(13, 110, 253, 0.02);
    }

    /* Tarjetas Contenedoras de Gráficos (Redondeadas & Translúcidas) */
    div[data-testid="stPlotlyChart"] {
        background-color: rgba(30, 41, 59, 0.4) !important;
        border: 1px solid rgba(13, 110, 253, 0.2) !important;
        border-radius: 12px !important;
        padding: 0.8rem !important;
    }

    /* Tarjeta Destacada Posición */
    .posicion-card {
        background-color: rgba(13, 110, 253, 0.06);
        border: 2px solid #0D6EFD;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    .posicion-card-sub {
        font-size: 0.85rem;
        color: #6c757d;
        font-weight: 600;
        text-transform: uppercase;
    }
    .posicion-card-title {
        font-size: 2.5rem;
        color: #0D6EFD;
        font-weight: 800;
    }

    /* TARJETAS KPI RESUMEN CONSOLIDADO */
    .dash-kpi-grey {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 8px;
        padding: 0.8rem;
        text-align: center;
        color: #e2e8f0;
    }
    .dash-kpi-blue {
        background-color: rgba(13, 110, 253, 0.05);
        border: 1px solid rgba(13, 110, 253, 0.25);
        border-radius: 8px;
        padding: 0.8rem;
        text-align: center;
        color: #e2e8f0;
    }
    
    /* ERI CONDICIONALES (Borde intenso + Fondo soft transparente) */
    .kpi-eri-green {
        background-color: rgba(16, 185, 129, 0.12) !important;
        border: 2px solid #10b981 !important;
        color: #10b981 !important;
        border-radius: 8px;
        padding: 0.8rem;
        text-align: center;
    }
    .kpi-eri-orange {
        background-color: rgba(245, 158, 11, 0.12) !important;
        border: 2px solid #f59e0b !important;
        color: #f59e0b !important;
        border-radius: 8px;
        padding: 0.8rem;
        text-align: center;
    }
    .kpi-eri-red {
        background-color: rgba(239, 68, 68, 0.12) !important;
        border: 2px solid #ef4444 !important;
        color: #ef4444 !important;
        border-radius: 8px;
        padding: 0.8rem;
        text-align: center;
    }

    .dash-kpi-label {
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 0.2rem;
    }
    .dash-kpi-val {
        font-size: 2.1rem;
        font-weight: 800;
        line-height: 1.1;
    }
    </style>
""", unsafe_allow_html=True)

# Función auxiliar para parsear componentes de la posición
def parse_posicion_completa(p):
    p_clean = re.sub(r'\s+', ' ', str(p).strip())
    m = re.match(r'^(\d+)([A-Za-z]+)\s*/\s*(\d+)\s*(\d+)?$', p_clean)
    if m:
        nivel = m.group(1)
        seccion = m.group(2).upper()
        modulo = m.group(3)
        pos_base = f"{nivel}{seccion} / {modulo}"
        return nivel, seccion, modulo, pos_base, p_clean
    return "Otros", "Otros", "Otros", p_clean, p_clean

# Carga de la base consolidada
@st.cache_data
def cargar_base_consolidada():
    archivos = glob.glob("*Base_de_Datos_Consolidada*.csv")
    if archivos:
        return pd.read_csv(archivos[0])
    try:
        return pd.read_csv("Base_de_Datos_Consolidada_Auditorías_de_Productos_V4.csv")
    except FileNotFoundError:
        return None

# ---------------------------------------------------------
# FUNCIÓN EMERGENTE: RUTA DE AUDITORÍA (SNAKE PATH)
# ---------------------------------------------------------
@st.dialog("Ruta Óptima de Auditoría", width="large")
def mostrar_ruta_auditoria(df, col_pos, col_dep):
    st.write("Sigue este orden para minimizar tus pasos en el depósito. El sistema alterna el recorrido por cada nivel.")
    
    df_ruta = df.copy()
    
    def obtener_nivel_seccion(pos):
        pos_str = str(pos).strip()
        match = re.match(r'^(\d+)([A-Za-z]+)', pos_str)
        if match:
            return int(match.group(1)), match.group(2).upper()
        return 999, 'ZZ' 
        
    df_ruta[['Nivel_Temp', 'Seccion_Temp']] = df_ruta[col_pos].apply(
        lambda x: pd.Series(obtener_nivel_seccion(x))
    )
    
    niveles = sorted(df_ruta['Nivel_Temp'].unique())
    df_ordenado = pd.DataFrame()
    
    for nivel in niveles:
        df_nivel = df_ruta[df_ruta['Nivel_Temp'] == nivel]
        
        if nivel == 999 or nivel % 2 != 0:
            df_nivel = df_nivel.sort_values(by=['Seccion_Temp'], ascending=True)
        else:
            df_nivel = df_nivel.sort_values(by=['Seccion_Temp'], ascending=False)
            
        df_ordenado = pd.concat([df_ordenado, df_nivel])
        
    columnas_mostrar = ['Cod Sku', 'Descripcion', col_pos, col_dep]
    if 'Stock auditado' in df_ordenado.columns:
        columnas_mostrar.append('Stock auditado')
        
    columnas_finales = [c for c in columnas_mostrar if c in df_ordenado.columns]
    
    st.dataframe(df_ordenado[columnas_finales], hide_index=True, use_container_width=True)
    if st.button("Cerrar Ruta", use_container_width=True):
        st.rerun()

# ---------------------------------------------------------
# 1. BARRA LATERAL: NAVEGACIÓN Y CARGA DE INVENTARIO
# ---------------------------------------------------------
logo_path = "LOGOAFTERMARKETLS_transparente.png"
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)
else:
    logos = glob.glob("*LOGO*.png") + glob.glob("*logo*.png")
    if logos:
        st.sidebar.image(logos[0], use_container_width=True)

st.sidebar.markdown("---")

st.sidebar.header("Menú Principal")
seccion_activa = st.sidebar.selectbox(
    "Selecciona una vista:",
    ["Resumen Consolidado", "Auditoría Live"]
)

st.sidebar.markdown("---")

if seccion_activa == "Auditoría Live":
    st.sidebar.header("Módulo de Auditoría")
    tipo_auditoria = st.sidebar.selectbox(
        "Selecciona el tipo de auditoría:",
        ["Productos", "Posiciones", "Clientes", "Proveedores"]
    )
    st.sidebar.markdown("---")
else:
    tipo_auditoria = "Dashboard"

st.sidebar.header("Inventario Diario")

col_codigo_inv = "Código"
col_stock_inv = "Saldo" 
col_posicion_inv = "Estanteria"
col_deposito_inv = "Deposito"

ID_GOOGLE_DRIVE = "TU_ID_DE_GOOGLE_DRIVE_AQUI"
df_inv = None

if ID_GOOGLE_DRIVE != "TU_ID_DE_GOOGLE_DRIVE_AQUI":
    try:
        url_drive = f'https://drive.google.com/uc?id={ID_GOOGLE_DRIVE}'
        df_inv_bruto = pd.read_excel(url_drive)
        df_inv = df_inv_bruto[~df_inv_bruto[col_deposito_inv].astype(str).str.contains('REV|EXT', case=False, na=False)]
        st.session_state['inventario_cargado'] = df_inv
        st.sidebar.success("Sincronizado con Google Drive")
    except Exception as e:
        st.sidebar.warning("Error al conectar con Drive. Utiliza la carga manual.")

archivo_inventario = st.sidebar.file_uploader(
    "Sube el archivo de Stock (Excel/CSV):", 
    type=["xlsx", "xls", "csv"],
    key="uploader_sidebar_global"
)

if archivo_inventario is not None:
    try:
        if archivo_inventario.name.endswith('.csv'):
            df_inv_bruto = pd.read_csv(archivo_inventario)
        else:
            df_inv_bruto = pd.read_excel(archivo_inventario)
        
        df_inv = df_inv_bruto[~df_inv_bruto[col_deposito_inv].astype(str).str.contains('REV|EXT', case=False, na=False)]
        st.session_state['inventario_cargado'] = df_inv
        st.sidebar.success("Inventario cargado correctamente")
    except Exception as e:
        st.sidebar.error(f"Error de lectura: {e}")
elif 'inventario_cargado' in st.session_state:
    df_inv = st.session_state['inventario_cargado']

archivos_auditoria = {
    "Productos": "Auditoría_Aleatoria_Productos.csv",
    "Posiciones": "Auditoría_Aleatoria_Posiciones.csv",
    "Clientes": "Auditoría_Aleatoria_Clientes.csv",
    "Proveedores": "Auditoría_Aleatoria_Proveedores.csv"
}

@st.cache_data 
def cargar_datos(ruta):
    return pd.read_csv(ruta)

if seccion_activa == "Auditoría Live":
    try:
        df_base = cargar_datos(archivos_auditoria[tipo_auditoria])
    except FileNotFoundError:
        st.error(f"No se encontró el archivo {archivos_auditoria[tipo_auditoria]}.")
        st.stop()

# ---------------------------------------------------------
# 2. PANTALLA PRINCIPAL: VISTAS Y MÓDULOS
# ---------------------------------------------------------
if 'muestra_actual' not in st.session_state:
    st.session_state['muestra_actual'] = pd.DataFrame()
if 'posicion_semanal' not in st.session_state:
    st.session_state['posicion_semanal'] = None

# =========================================================
# VISTA 1: RESUMEN CONSOLIDADO DE AUDITORÍAS
# =========================================================
if seccion_activa == "Resumen Consolidado":
    
    col_dash_tit, col_dash_btn = st.columns([3, 1])
    with col_dash_tit:
        st.title("Consolidado General de Auditorías")
    with col_dash_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Resetear Filtros", type="secondary", use_container_width=True):
            for k in ["chart_linea_interactivo", "chart_barras_interactivo"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.session_state["combo_semana_dash"] = "Todas"
            st.session_state["combo_obs_dash"] = "Todas"
            st.rerun()

    st.markdown("---")
    
    df_dash = cargar_base_consolidada()
    
    if df_dash is None:
        st.error("No se encontró la base consolidada de productos en la carpeta. Verifique el archivo CSV.")
    else:
        df_dash['Stock auditado'] = pd.to_numeric(df_dash['Stock auditado'], errors='coerce').fillna(0)
        df_dash['Stock Octosis'] = pd.to_numeric(df_dash['Stock Octosis'], errors='coerce').fillna(0)
        df_dash['desvio_neto'] = df_dash['Stock auditado'] - df_dash['Stock Octosis']
        df_dash['desvio_abs'] = df_dash['desvio_neto'].abs()
        
        filtro_click_semana = None
        if "chart_linea_interactivo" in st.session_state:
            evt_l = st.session_state["chart_linea_interactivo"]
            if evt_l and "selection" in evt_l and evt_l["selection"].get("points"):
                filtro_click_semana = evt_l["selection"]["points"][0].get("x")
                
        filtro_click_observacion = None
        if "chart_barras_interactivo" in st.session_state:
            evt_b = st.session_state["chart_barras_interactivo"]
            if evt_b and "selection" in evt_b and evt_b["selection"].get("points"):
                pts = evt_b["selection"]["points"][0]
                if "customdata" in pts and pts["customdata"]:
                    filtro_click_observacion = pts["customdata"][0]

        sem_sel = st.session_state.get("combo_semana_dash", "Todas")
        obs_sel = st.session_state.get("combo_obs_dash", "Todas")
        
        df_dash_filtered = df_dash.copy()
        filtro_aplicado_txt = []
        
        if filtro_click_semana:
            df_dash_filtered = df_dash_filtered[df_dash_filtered['Nombre del Archivo Origen'] == filtro_click_semana]
            filtro_aplicado_txt.append(f"Semana: **{filtro_click_semana}**")
        elif sem_sel != "Todas":
            df_dash_filtered = df_dash_filtered[df_dash_filtered['Nombre del Archivo Origen'] == sem_sel]
            filtro_aplicado_txt.append(f"Semana: **{sem_sel}**")
            
        if filtro_click_observacion:
            df_dash_filtered = df_dash_filtered[df_dash_filtered['Observaciones'] == filtro_click_observacion]
            filtro_aplicado_txt.append(f"Observación: **{filtro_click_observacion}**")
        elif obs_sel != "Todas":
            df_dash_filtered = df_dash_filtered[df_dash_filtered['Observaciones'] == obs_sel]
            filtro_aplicado_txt.append(f"Observación: **{obs_sel}**")

        total_auditorias = len(df_dash_filtered)
        ok_count = (df_dash_filtered['Resultado'] == 'OK').sum()
        eri_val = (ok_count / total_auditorias) * 100 if total_auditorias > 0 else 0
        desvio_neto_val = df_dash_filtered['desvio_neto'].sum()
        desvio_abs_val = df_dash_filtered['desvio_abs'].sum()
        
        if eri_val > 90:
            eri_class = "kpi-eri-green"
        elif eri_val >= 80:
            eri_class = "kpi-eri-orange"
        else:
            eri_class = "kpi-eri-red"
        
        with st.container():
            k1, k2, k3 = st.columns(3)
            
            with k1:
                st.markdown(f"""
                    <div class="{eri_class}">
                        <div class="dash-kpi-label">ERI</div>
                        <div class="dash-kpi-val">{eri_val:.1f}%</div>
                    </div>
                """, unsafe_allow_html=True)
                
            with k2:
                st.markdown(f"""
                    <div class="dash-kpi-blue">
                        <div class="dash-kpi-label">Desvío Neto</div>
                        <div class="dash-kpi-val">{int(desvio_neto_val):,}</div>
                    </div>
                """, unsafe_allow_html=True)
                
            with k3:
                st.markdown(f"""
                    <div class="dash-kpi-blue">
                        <div class="dash-kpi-label">Desvío Absoluto</div>
                        <div class="dash-kpi-val">{int(desvio_abs_val):,}</div>
                    </div>
                """, unsafe_allow_html=True)
                
            st.markdown("<br>", unsafe_allow_html=True)
            
            c_graf1, c_graf2 = st.columns(2)
            
            # --- GRÁFICO 1: EVOLUCIÓN ERI ---
            with c_graf1:
                df_dash['Semana_Num'] = df_dash['Nombre del Archivo Origen'].str.extract(r'(\d+)').astype(float)
                df_sem = df_dash.groupby(['Nombre del Archivo Origen', 'Semana_Num']).apply(
                    lambda g: pd.Series({
                        'Total': len(g),
                        'OK': (g['Resultado'] == 'OK').sum(),
                        'ERI': ((g['Resultado'] == 'OK').sum() / len(g)) * 100 if len(g) > 0 else 0
                    })
                ).reset_index().sort_values('Semana_Num')
                
                fig_line = go.Figure()
                
                fig_line.add_trace(go.Scatter(
                    x=df_sem['Nombre del Archivo Origen'],
                    y=df_sem['ERI'],
                    mode='lines+markers',
                    name='Calculo_ERI',
                    line=dict(color='#0D6EFD', width=3, shape='spline'),
                    marker=dict(size=8, color='#0D6EFD'),
                    fill='tozeroy',
                    fillcolor='rgba(13, 110, 253, 0.12)'
                ))
                
                fig_line.add_trace(go.Scatter(
                    x=df_sem['Nombre del Archivo Origen'],
                    y=[95] * len(df_sem),
                    mode='lines',
                    name='Objetivo (95%)',
                    line=dict(color='#dc3545', width=2, dash='dash')
                ))
                
                fig_line.update_layout(
                    title="",  # Elimina el "undefined"
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e2e8f0', size=11),
                    height=340, # Altura homologada
                    yaxis=dict(title="", range=[0, 105], ticksuffix="%", gridcolor='rgba(255,255,255,0.06)'),
                    xaxis=dict(gridcolor='rgba(255,255,255,0.06)', tickfont=dict(size=10, color='#cbd5e1')),
                    margin=dict(l=20, r=20, t=30, b=45), # Margen inferior ampliado (b=45) para leer bien las semanas
                    legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="center", x=0.5, font=dict(size=10, color='#94a3b8')) # Leyenda centrada para no robar ancho
                )
                
                st.plotly_chart(
                    fig_line, 
                    use_container_width=True, 
                    on_select="rerun", 
                    selection_mode="points",
                    key="chart_linea_interactivo"
                )
                
            # --- GRÁFICO 2: RESULTADO AUDITORÍAS ---
            with c_graf2:
                df_obs = df_dash[df_dash['Observaciones'] != 'Sin observaciones']['Observaciones'].value_counts().reset_index()
                df_obs.columns = ['Observacion', 'Cantidad']
                
                def formatear_etiqueta(texto):
                    if "Diferencias en posiciones" in texto:
                        return "Diferencias<br>cruzadas"
                    elif "posición errónea" in texto:
                        return "Posición<br>errónea"
                    words = texto.split()
                    if len(texto) > 14 and len(words) > 1:
                        mid = len(words) // 2
                        return "<br>".join([" ".join(words[:mid]), " ".join(words[mid:])])
                    return texto

                df_obs['Observacion_Formateada'] = df_obs['Observacion'].apply(formatear_etiqueta)
                max_cant = df_obs['Cantidad'].max() if not df_obs.empty else 10
                
                fig_bar = px.bar(
                    df_obs,
                    x='Observacion_Formateada',
                    y='Cantidad',
                    text='Cantidad',
                    custom_data=['Observacion']
                )
                fig_bar.update_traces(
                    marker_color='#9a1031',  # Nuevo color rojo intenso
                    textposition='outside',
                    textfont=dict(color='#f8fafc', size=11),
                    cliponaxis=False
                )
                fig_bar.update_layout(
                    title="", # Elimina el "undefined"
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e2e8f0', size=11),
                    height=340, # Altura homologada con el gráfico izquierdo
                    xaxis=dict(
                        title="", 
                        tickangle=0, 
                        gridcolor='rgba(255,255,255,0.06)', 
                        tickfont=dict(size=10, color='#cbd5e1')
                    ),
                    yaxis=dict(
                        title="", 
                        range=[0, max_cant * 1.25], 
                        gridcolor='rgba(255,255,255,0.06)'
                    ),
                    margin=dict(l=20, r=20, t=30, b=55) # Top margin idéntico (t=30) para igualar escalas
                )
                
                st.plotly_chart(
                    fig_bar, 
                    use_container_width=True, 
                    on_select="rerun", 
                    selection_mode="points",
                    key="chart_barras_interactivo"
                )

        st.markdown("---")
        
        st.markdown("### Detalle de Auditorías de Productos")
        
        semanas_list = ["Todas"] + sorted(df_dash['Nombre del Archivo Origen'].unique().tolist())
        
        col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
        with col_f1:
            st.selectbox("Filtrar por Semana:", semanas_list, key="combo_semana_dash")
        with col_f2:
            obs_list = ["Todas"] + sorted(df_dash['Observaciones'].unique().tolist())
            st.selectbox("Filtrar por Observación:", obs_list, key="combo_obs_dash")

        if filtro_aplicado_txt:
            st.info(f"Filtrando por: {', '.join(filtro_aplicado_txt)} (Total: **{len(df_dash_filtered)}** registros)")
            
        cols_dash = ['Nombre del Archivo Origen', 'Categoría', 'Código', 'Stock Octosis', 'Stock auditado', 'Diferencia', 'Resultado', 'Observaciones']
        cols_existentes = [c for c in cols_dash if c in df_dash_filtered.columns]
        
        df_mostrar_final = df_dash_filtered[cols_existentes].rename(columns={'Nombre del Archivo Origen': 'Semana'})
        
        st.dataframe(
            df_mostrar_final,
            use_container_width=True,
            hide_index=True
        )

# =========================================================
# VISTA 2: AUDITORÍA EN VIVO (MÓDULOS)
# =========================================================
elif seccion_activa == "Auditoría Live":
    
    st.title(f"Auditoría de {tipo_auditoria}")
    st.markdown("---")
    
    if tipo_auditoria == "Productos":
        
        if df_inv is None:
            st.info("Por favor, carga el archivo de inventario diario en la barra lateral para comenzar.")
        else:
            st.write("Filtros Aleatorios")
            
            with st.form("form_filtros_prod"):
                f_col1, f_col2, f_col3 = st.columns(3)
                
                with f_col1:
                    lista_rotacion = df_base["Clasificación Rotación "].dropna().unique().tolist()
                    rotacion_sel = st.selectbox("Tipo de Rotación:", ["Todos"] + lista_rotacion)
                with f_col2:
                    lista_valor = df_base["Clasificación Valor"].dropna().unique().tolist()
                    valor_sel = st.selectbox("Tipo de Valor:", ["Todos"] + lista_valor)
                with f_col3:
                    tamano_muestra = st.number_input("Cantidad:", min_value=1, value=5, step=1)
                
                submit_agregar = st.form_submit_button("Agregar a la Muestra", type="primary", use_container_width=True)
                
                if submit_agregar:
                    df_filtrado = df_base.copy()
                    
                    if rotacion_sel != "Todos":
                        df_filtrado = df_filtrado[df_filtrado["Clasificación Rotación "] == rotacion_sel]
                    if valor_sel != "Todos":
                        df_filtrado = df_filtrado[df_filtrado["Clasificación Valor"] == valor_sel]
                        
                    if not st.session_state['muestra_actual'].empty:
                        skus_ya_seleccionados = st.session_state['muestra_actual']['Cod Sku'].unique().tolist()
                        df_filtrado = df_filtrado[~df_filtrado['Cod Sku'].isin(skus_ya_seleccionados)]
                    
                    df_filtrado = df_filtrado[df_filtrado['Cod Sku'].isin(df_inv[col_codigo_inv])]
                        
                    if not df_filtrado.empty:
                        nueva_muestra_base = df_filtrado.sample(min(tamano_muestra, len(df_filtrado)))
                        
                        cruce_inmediato = pd.merge(
                            nueva_muestra_base, df_inv, how='left', left_on='Cod Sku', right_on=col_codigo_inv
                        )
                        
                        if st.session_state['muestra_actual'].empty:
                            st.session_state['muestra_actual'] = cruce_inmediato
                        else:
                            st.session_state['muestra_actual'] = pd.concat(
                                [st.session_state['muestra_actual'], cruce_inmediato], ignore_index=True
                            )
                    else:
                        st.info("No hay más productos que coincidan con los filtros seleccionados.")
            
            if not st.session_state['muestra_actual'].empty:
                if st.button("Limpiar Muestra", use_container_width=True):
                    st.session_state['muestra_actual'] = pd.DataFrame()
                    st.rerun()

        if not st.session_state['muestra_actual'].empty:
            st.markdown("---")
            
            col_tit, col_ruta = st.columns([3, 1])
            with col_tit:
                st.markdown("### Carga de Recuento Físico")
            with col_ruta:
                if st.button("Ver Ruta de Auditoría", type="secondary", use_container_width=True):
                    mostrar_ruta_auditoria(st.session_state['muestra_actual'], col_posicion_inv, col_deposito_inv)
            
            df_recuento = st.session_state['muestra_actual'].copy()
            
            if 'Stock auditado' not in df_recuento.columns:
                df_recuento['Stock auditado'] = None
            if 'Observaciones' not in df_recuento.columns:
                df_recuento['Observaciones'] = ""
                
            columnas_edicion = ['Cod Sku', 'Descripcion', col_posicion_inv, col_deposito_inv, col_stock_inv, 'Stock auditado', 'Observaciones']
            columnas_existentes = [col for col in columnas_edicion if col in df_recuento.columns]
            df_recuento = df_recuento[columnas_existentes]
            
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            metric_col1.metric("Posiciones a Auditar", len(df_recuento))
            placeholder_pendientes = metric_col2.empty()
            placeholder_diferencias = metric_col3.empty()
            
            df_editado = st.data_editor(
                df_recuento,
                column_config={
                    "Cod Sku": st.column_config.TextColumn("Código", disabled=True),
                    "Descripcion": st.column_config.TextColumn("Descripción", disabled=True),
                    col_posicion_inv: st.column_config.TextColumn("Posición", disabled=True),
                    col_deposito_inv: st.column_config.TextColumn("Depósito", disabled=True),
                    col_stock_inv: st.column_config.NumberColumn("Stock Teórico", disabled=True),
                    "Stock auditado": st.column_config.NumberColumn("Stock Físico", required=True),
                    "Observaciones": st.column_config.TextColumn("Observaciones")
                },
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                key="editor_auditoria_prod"
            )

            faltan_cargar = df_editado['Stock auditado'].isna().sum()
            placeholder_pendientes.metric("Cantidades Pendientes", faltan_cargar)
            
            if faltan_cargar > 0:
                st.info(f"Falta ingresar el recuento físico de {faltan_cargar} posiciones para habilitar el reporte.")
            
            if st.button("Generar Reporte Final", type="primary", disabled=(faltan_cargar > 0)):
                stock_teorico = pd.to_numeric(df_editado[col_stock_inv], errors='coerce').fillna(0)
                stock_fisico = pd.to_numeric(df_editado['Stock auditado'], errors='coerce').fillna(0)
                
                df_editado['Diferencia'] = stock_fisico - stock_teorico
                
                def evaluar_resultado(dif):
                    if dif == 0:
                        return "OK"
                    elif dif < 0:
                        return "FALTANTE"
                    else:
                        return "SOBRANTE"
                        
                df_editado['Resultado'] = df_editado['Diferencia'].apply(evaluar_resultado)
                
                total_dif = (df_editado['Diferencia'] != 0).sum()
                placeholder_diferencias.metric("Diferencias Detectadas", total_dif)
                
                categorias = df_editado['Cod Sku'].map(
                    df_base.set_index('Cod Sku')['Clasificación Valor']
                ).fillna("Sin Categoría")

                df_reporte_final = pd.DataFrame({
                    'Tipo de auditoria': tipo_auditoria,
                    'Categoría': categorias,
                    'Código': df_editado['Cod Sku'],
                    'Stock Sistema': stock_teorico,
                    'Stock auditado': stock_fisico,
                    'Diferencia': df_editado['Diferencia'],
                    'Resultado': df_editado['Resultado'],
                    'Observaciones': df_editado['Observaciones']
                })
                
                def resaltar_filas(row):
                    if row['Resultado'] == 'FALTANTE':
                        return ['background-color: #ffebee; color: #b71c1c'] * len(row)
                    elif row['Resultado'] == 'SOBRANTE':
                        return ['background-color: #fff8e1; color: #f57f17'] * len(row)
                    else:
                        return ['background-color: #e8f5e9; color: #1b5e20'] * len(row)

                df_estilizado = df_reporte_final.style.apply(resaltar_filas, axis=1)
                
                st.markdown("### Reporte Final de Auditoría")
                st.dataframe(df_estilizado, use_container_width=True, hide_index=True)
                
                csv = df_reporte_final.to_csv(index=False, sep=';', decimal=',')
                fecha_hoy = datetime.datetime.now().strftime("%d-%m")
                
                col_down1, col_down2 = st.columns([1, 4])
                with col_down1:
                    st.download_button(
                        label="Descargar Reporte (.csv)",
                        data=csv,
                        file_name=f"REG-AUD-PROD-{fecha_hoy}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

    elif tipo_auditoria == "Posiciones":
        
        if df_inv is None:
            st.info("Por favor, carga el archivo de inventario diario en la barra lateral para comenzar.")
        else:
            st.write("Filtros de Ubicación")
            
            df_parsed = df_base['POSICIONES'].apply(parse_posicion_completa)
            df_base['Nivel'] = [x[0] for x in df_parsed]
            df_base['Seccion'] = [x[1] for x in df_parsed]
            df_base['Modulo'] = [x[2] for x in df_parsed]
            df_base['Posicion_Base'] = [x[3] for x in df_parsed]
            
            niveles_disponibles = ['1', '2', '3']
            secciones_disponibles = sorted([s for s in df_base['Seccion'].unique() if s != "Otros"])
            
            with st.form("form_filtros_pos"):
                f1, f2 = st.columns(2)
                with f1:
                    nivel_sel = st.selectbox("Nivel:", ["Todos"] + niveles_disponibles)
                with f2:
                    seccion_sel = st.selectbox("Pasillo / Sección:", ["Todos"] + secciones_disponibles)
                    
                submit_pos = st.form_submit_button("Sustraer Posición Aleatoria", type="primary", use_container_width=True)
                
                if submit_pos:
                    df_pos_filtrado = df_base[df_base['Nivel'].isin(['1', '2', '3'])].copy()
                    
                    if nivel_sel != "Todos":
                        df_pos_filtrado = df_pos_filtrado[df_pos_filtrado['Nivel'] == nivel_sel]
                    if seccion_sel != "Todos":
                        df_pos_filtrado = df_pos_filtrado[df_pos_filtrado['Seccion'] == seccion_sel]
                        
                    df_inv_parsed = df_inv[col_posicion_inv].apply(parse_posicion_completa)
                    df_inv['Posicion_Base'] = [x[3] for x in df_inv_parsed]
                    df_inv['Estanteria_Clean'] = [x[4] for x in df_inv_parsed]
                    
                    pos_base_con_stock = df_inv['Posicion_Base'].unique()
                    df_pos_filtrado = df_pos_filtrado[df_pos_filtrado['Posicion_Base'].isin(pos_base_con_stock)]
                    
                    if not df_pos_filtrado.empty:
                        pos_base_elegida = df_pos_filtrado.sample(1)['Posicion_Base'].values[0].strip()
                        st.session_state['posicion_semanal'] = pos_base_elegida
                    else:
                        st.info("No hay posiciones con productos en el inventario para los filtros seleccionados.")

            if st.session_state['posicion_semanal'] is not None:
                if st.button("Limpiar Selección", use_container_width=True):
                    st.session_state['posicion_semanal'] = None
                    st.rerun()

            if st.session_state['posicion_semanal'] is not None:
                pos_actual = st.session_state['posicion_semanal']
                
                st.markdown(f"""
                    <div class="posicion-card">
                        <div class="posicion-card-sub">Posición Asignada para Auditar</div>
                        <div class="posicion-card-title">{pos_actual}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                df_inv_clean = df_inv.copy()
                if 'Posicion_Base' not in df_inv_clean.columns:
                    df_inv_parsed = df_inv_clean[col_posicion_inv].apply(parse_posicion_completa)
                    df_inv_clean['Posicion_Base'] = [x[3] for x in df_inv_parsed]
                    df_inv_clean['Estanteria_Clean'] = [x[4] for x in df_inv_parsed]
                
                productos_en_posicion = df_inv_clean[df_inv_clean['Posicion_Base'] == pos_actual].copy()
                
                if not productos_en_posicion.empty:
                    st.markdown("### Recuento Físico de Productos en la Posición")
                    
                    productos_en_posicion['Stock auditado'] = None
                    productos_en_posicion['Observaciones'] = ""
                    
                    cols_mostrar = ['Código', 'Descripcion', 'Estanteria_Clean', col_deposito_inv, col_stock_inv, 'Stock auditado', 'Observaciones']
                    cols_existentes = [c for c in cols_mostrar if c in productos_en_posicion.columns]
                    
                    df_editor_pos = st.data_editor(
                        productos_en_posicion[cols_existentes],
                        column_config={
                            "Código": st.column_config.TextColumn("Código", disabled=True),
                            "Descripcion": st.column_config.TextColumn("Descripción", disabled=True),
                            "Estanteria_Clean": st.column_config.TextColumn("Posición Específica", disabled=True),
                            col_deposito_inv: st.column_config.TextColumn("Depósito", disabled=True),
                            col_stock_inv: st.column_config.NumberColumn("Stock Teórico", disabled=True),
                            "Stock auditado": st.column_config.NumberColumn("Stock Físico", required=True),
                            "Observaciones": st.column_config.TextColumn("Observaciones")
                        },
                        use_container_width=True,
                        hide_index=True,
                        key="editor_posicion_semanal"
                    )
                    
                    faltan_pos = df_editor_pos['Stock auditado'].isna().sum()
                    
                    if st.button("Generar Reporte de Posición", type="primary", disabled=(faltan_pos > 0)):
                        st_teorico = pd.to_numeric(df_editor_pos[col_stock_inv], errors='coerce').fillna(0)
                        st_fisico = pd.to_numeric(df_editor_pos['Stock auditado'], errors='coerce').fillna(0)
                        
                        df_editor_pos['Diferencia'] = st_fisico - st_teorico
                        df_editor_pos['Resultado'] = df_editor_pos['Diferencia'].apply(
                            lambda d: "OK" if d == 0 else ("FALTANTE" if d < 0 else "SOBRANTE")
                        )
                        
                        df_rep_pos = pd.DataFrame({
                            'Tipo de auditoria': "POSICIONES",
                            'Posición Módulo': pos_actual,
                            'Posición Específica': df_editor_pos['Estanteria_Clean'],
                            'Código': df_editor_pos['Código'],
                            'Stock Sistema': st_teorico,
                            'Stock auditado': st_fisico,
                            'Diferencia': df_editor_pos['Diferencia'],
                            'Resultado': df_editor_pos['Resultado'],
                            'Observaciones': df_editor_pos['Observaciones']
                        })
                        
                        def resaltar_filas(row):
                            if row['Resultado'] == 'FALTANTE':
                                return ['background-color: #ffebee; color: #b71c1c'] * len(row)
                            elif row['Resultado'] == 'SOBRANTE':
                                return ['background-color: #fff8e1; color: #f57f17'] * len(row)
                            else:
                                return ['background-color: #e8f5e9; color: #1b5e20'] * len(row)

                        st.markdown("### Reporte de la Auditoría")
                        st.dataframe(df_rep_pos.style.apply(resaltar_filas, axis=1), use_container_width=True, hide_index=True)
                        
                        csv_pos = df_rep_pos.to_csv(index=False, sep=';', decimal=',')
                        fecha_hoy = datetime.datetime.now().strftime("%d-%m")
                        st.download_button(
                            label="Descargar Reporte de Posición (.csv)",
                            data=csv_pos,
                            file_name=f"REG-AUD-POS-{pos_actual.replace(' / ', '-').replace('/', '-')}-{fecha_hoy}.csv",
                            mime="text/csv"
                        )
                else:
                    st.info("No se registran productos en el inventario teórico para esta posición. Puedes auditarla visualmente o seleccionar otra ubicación.")

    elif tipo_auditoria in ["Clientes", "Proveedores"]:
        st.info("La lógica para este módulo se desarrollará próximamente.")
        st.dataframe(df_base.head())