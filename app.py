import streamlit as st
import pandas as pd
import datetime
import re
import glob
import os
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Sistema de Auditoría de Inventario", layout="wide")

URL_GOOGLE_SHEETS = "https://docs.google.com/spreadsheets/d/1cxjiOrp-3ze99r-bPTU1OVEGGOMkRABwWzgkIHpC1Nw/edit"

st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid rgba(13, 110, 253, 0.2) !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #f1f5f9 !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
    }
    [data-testid="stSidebar"] label {
        color: #94a3b8 !important;
        font-size: 0.9rem !important;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #1e293b !important;
        border: 1px solid rgba(13, 110, 253, 0.3) !important;
        color: #f8fafc !important;
        border-radius: 6px !important;
    }
    button[kind="primary"], button[kind="primaryFormSubmit"] {
        background-color: #0D6EFD !important;
        border-color: #0D6EFD !important;
        color: white !important;
        padding: 0.8rem 1rem !important; 
        font-weight: 700 !important;
        font-size: 1.1rem !important;
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
    div[data-testid="stPlotlyChart"] {
        background-color: rgba(30, 41, 59, 0.4) !important;
        border: 1px solid rgba(13, 110, 253, 0.2) !important;
        border-radius: 12px !important;
        padding: 0.8rem !important;
    }
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
    .metric-card-soft {
        background-color: rgba(13, 110, 253, 0.05);
        border: 1px solid rgba(13, 110, 253, 0.25);
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        height: 98px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-card-soft-label {
        font-size: 0.8rem;
        color: #cbd5e1;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.2rem;
    }
    .metric-card-soft-val {
        font-size: 2rem;
        color: #ffffff;
        font-weight: 800;
        line-height: 1.1;
    }
    .dash-kpi-blue {
        background-color: rgba(13, 110, 253, 0.05);
        border: 1px solid rgba(13, 110, 253, 0.25);
        border-radius: 8px;
        padding: 0.8rem;
        text-align: center;
        color: #e2e8f0;
    }
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

@st.cache_data(ttl=10)
def cargar_base_consolidada():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=URL_GOOGLE_SHEETS, worksheet=0) 
        return df
    except Exception as e:
        st.error(f"Error de lectura en Google Sheets: {e}", icon=":material/error:")
        return None

def guardar_borrador_nube(df):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        conn.update(spreadsheet=URL_GOOGLE_SHEETS, worksheet="Borradores", data=df)
        return True
    except Exception as e:
        st.error(f"Error al guardar borrador en la nube: {e}", icon=":material/error:")
        return False

def cargar_borrador_nube():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # ttl=0 es la clave: le prohíbe a Streamlit usar la memoria caché para esta lectura
        df = conn.read(spreadsheet=URL_GOOGLE_SHEETS, worksheet="Borradores", ttl=0)
        return df.dropna(how='all')
    except:
        return pd.DataFrame()
        
def vaciar_borrador_nube():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_vacio = pd.DataFrame(columns=['Cod Sku', 'Descripcion'])
        conn.update(spreadsheet=URL_GOOGLE_SHEETS, worksheet="Borradores", data=df_vacio)
    except:
        pass

@st.dialog("Ruta Óptima de Auditoría", width="large")
def mostrar_ruta_auditoria(df, col_pos, col_dep, col_stock):
    df_ruta = df.copy()
    
    if 'Stock auditado' not in df_ruta.columns:
        df_ruta['Stock auditado'] = None
    if 'Observaciones' not in df_ruta.columns:
        df_ruta['Observaciones'] = ""
        
    def obtener_nivel_seccion(pos):
        pos_str = str(pos).strip()
        match = re.match(r'^(\d+)([A-Za-z]+)', pos_str)
        if match:
            return int(match.group(1)), match.group(2).upper()
        return 999, 'ZZ' 
        
    df_ruta[['Nivel_Temp', 'Seccion_Temp']] = df_ruta[col_pos].apply(lambda x: pd.Series(obtener_nivel_seccion(x)))
    niveles = sorted(df_ruta['Nivel_Temp'].unique())
    df_ordenado = pd.DataFrame()
    for nivel in niveles:
        df_nivel = df_ruta[df_ruta['Nivel_Temp'] == nivel]
        if nivel == 999 or nivel % 2 != 0:
            df_nivel = df_nivel.sort_values(by=['Seccion_Temp'], ascending=True)
        else:
            df_nivel = df_nivel.sort_values(by=['Seccion_Temp'], ascending=False)
        df_ordenado = pd.concat([df_ordenado, df_nivel])
        
    columnas_mostrar = ['Cod Sku', 'Descripcion', col_pos, col_dep, col_stock, 'Stock auditado', 'Observaciones']
    columnas_finales = [c for c in columnas_mostrar if c in df_ordenado.columns]
    
    with st.form("form_modal_ruta"):
        df_editado_ruta = st.data_editor(
            df_ordenado[columnas_finales],
            column_config={
                "Cod Sku": st.column_config.TextColumn("Código", disabled=True),
                "Descripcion": st.column_config.TextColumn("Descripción", disabled=True),
                col_pos: st.column_config.TextColumn("Posición", disabled=True),
                col_dep: st.column_config.TextColumn("Depósito", disabled=True),
                col_stock: st.column_config.NumberColumn("St. Teórico", disabled=True),
                "Stock auditado": st.column_config.NumberColumn("St. Físico", required=False),
                "Observaciones": st.column_config.TextColumn("Observaciones")
            },
            hide_index=True,
            use_container_width=True,
            height=400
        )
        
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            aplicar_local = st.form_submit_button("Aplicar Cambios", icon=":material/save:", type="secondary", use_container_width=True)
        with c2:
            guardar_nube = st.form_submit_button("Guardar en Nube", icon=":material/cloud_sync:", type="primary", use_container_width=True)
        with c3:
            cerrar = st.form_submit_button("Cerrar Ventana", icon=":material/close:", use_container_width=True)
            
    if aplicar_local or guardar_nube:
        df_main = st.session_state['muestra_actual'].copy()
        df_main.set_index('Cod Sku', inplace=True)
        df_edit_idx = df_editado_ruta.set_index('Cod Sku')
        df_main.update(df_edit_idx)
        st.session_state['muestra_actual'] = df_main.reset_index()
        
        if guardar_nube:
            if guardar_borrador_nube(st.session_state['muestra_actual']):
                st.success("Borrador actualizado exitosamente.", icon=":material/check_circle:")
        st.rerun()
        
    if cerrar:
        st.rerun()

@st.dialog("Confirmación e Impacto", width="large")
def confirmar_e_impactar_consolidado(df_preparado):
    semana_sugerida = "SEMANA 31"
    df_actual_cons = cargar_base_consolidada()
    if df_actual_cons is not None and 'Nombre del Archivo Origen' in df_actual_cons.columns:
        semanas_existentes = df_actual_cons['Nombre del Archivo Origen'].dropna().unique().tolist()
        if semanas_existentes:
            semana_sugerida = str(semanas_existentes[-1])

    semana_ingresada = st.text_input("Identificador Semanal:", value=semana_sugerida)
    df_validar = df_preparado.copy()
    
    df_confirmado = st.data_editor(
        df_validar,
        column_config={
            "Categoría": st.column_config.TextColumn("Categoría", disabled=True),
            "Código": st.column_config.TextColumn("Código SKU", disabled=True),
            "Stock Octosis": st.column_config.NumberColumn("Stock Sistema", disabled=True),
            "Stock auditado": st.column_config.NumberColumn("Stock Auditado", disabled=True),
            "Diferencia": st.column_config.NumberColumn("Diferencia", disabled=True),
            "Resultado": st.column_config.SelectboxColumn("Resultado Final", options=["OK", "KO", "FALTANTE", "SOBRANTE"], required=True),
            "Observaciones": st.column_config.TextColumn("Observaciones / Motivo")
        },
        use_container_width=True,
        hide_index=True,
        key="editor_confirmacion_modal"
    )
    
    c_modal1, c_modal2 = st.columns(2)
    with c_modal1:
        if st.button("Confirmar y Guardar", icon=":material/check_circle:", type="primary", use_container_width=True):
            df_confirmado["Nombre del Archivo Origen"] = semana_ingresada
            cols_base = ['Nombre del Archivo Origen', 'Categoría', 'Código', 'Stock Octosis', 'Stock auditado', 'Diferencia', 'Resultado', 'Observaciones']
            df_para_anexar = df_confirmado[[c for c in cols_base if c in df_confirmado.columns]].copy()
            
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_existente = conn.read(spreadsheet=URL_GOOGLE_SHEETS, worksheet=0)
                
                if len(df_existente.columns) > 0:
                    col_fecha = df_existente.columns[0]
                    df_para_anexar[col_fecha] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                
                if "Tipo de Auditoría" in df_existente.columns:
                    df_para_anexar["Tipo de Auditoría"] = tipo_auditoria.upper()
                
                df_final_actualizado = pd.concat([df_existente, df_para_anexar], ignore_index=True)
                conn.update(spreadsheet=URL_GOOGLE_SHEETS, worksheet=0, data=df_final_actualizado)
                
                st.cache_data.clear()
                st.session_state['muestra_actual'] = pd.DataFrame()
                st.session_state['posicion_semanal'] = None
                
                vaciar_borrador_nube()
                
                st.success("Datos impactados en Google Sheets.", icon=":material/check_circle:")
                st.rerun()
            except Exception as e:
                st.error(f"Error en Google Sheets: {e}", icon=":material/error:")
            
    with c_modal2:
        if st.button("Cancelar", icon=":material/cancel:", use_container_width=True):
            st.rerun()

logo_path = "LOGOAFTERMARKETLS_transparente.png"
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)
else:
    logos = glob.glob("*LOGO*.png") + glob.glob("*logo*.png")
    if logos:
        st.sidebar.image(logos[0], use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.header("Menú Principal")
seccion_activa = st.sidebar.selectbox("Selecciona una vista:", ["Resumen Consolidado", "Auditoría Live"])
st.sidebar.markdown("---")

if seccion_activa == "Auditoría Live":
    st.sidebar.header("Módulo de Auditoría")
    tipo_auditoria = st.sidebar.selectbox("Selecciona el tipo de auditoría:", ["Productos", "Posiciones", "Clientes", "Proveedores"])
    st.sidebar.markdown("---")
else:
    tipo_auditoria = "Dashboard"

st.sidebar.header("Inventario Diario")
col_codigo_inv = "Código"
col_stock_inv = "Saldo" 
col_posicion_inv = "Estanteria"
col_deposito_inv = "Deposito"

ID_GOOGLE_DRIVE = "1cxjiOrp-3ze99r-bPTU1OVEGGOMkRABwWzgkIHpC1Nw"
df_inv = None

if ID_GOOGLE_DRIVE != "1cxjiOrp-3ze99r-bPTU1OVEGGOMkRABwWzgkIHpC1Nw":
    try:
        url_drive = f'https://drive.google.com/uc?id={ID_GOOGLE_DRIVE}'
        df_inv_bruto = pd.read_excel(url_drive)
        df_inv = df_inv_bruto[~df_inv_bruto[col_deposito_inv].astype(str).str.contains('REV|EXT', case=False, na=False)]
        st.session_state['inventario_cargado'] = df_inv
        st.sidebar.success("Sincronizado con Google Drive", icon=":material/check_circle:")
    except Exception as e:
        st.sidebar.warning("Error al conectar con Drive. Utiliza la carga manual.", icon=":material/warning:")

archivo_inventario = st.sidebar.file_uploader("Sube el archivo de Stock (Excel/CSV):", type=["xlsx", "xls", "csv"], key="uploader_sidebar_global")

if archivo_inventario is not None:
    if 'nombre_archivo_cargado' not in st.session_state or st.session_state['nombre_archivo_cargado'] != archivo_inventario.name:
        try:
            if archivo_inventario.name.endswith('.csv'):
                df_inv_bruto = pd.read_csv(archivo_inventario)
            else:
                df_inv_bruto = pd.read_excel(archivo_inventario)
            
            df_inv = df_inv_bruto[~df_inv_bruto[col_deposito_inv].astype(str).str.contains('REV|EXT', case=False, na=False)]
            st.session_state['inventario_cargado'] = df_inv
            st.session_state['nombre_archivo_cargado'] = archivo_inventario.name
            st.sidebar.success("Inventario procesado con éxito.", icon=":material/check_circle:")
        except Exception as e:
            st.sidebar.error(f"Error de lectura: {e}", icon=":material/error:")
            df_inv = None
    else:
        df_inv = st.session_state['inventario_cargado']
elif 'inventario_cargado' in st.session_state:
    df_inv = st.session_state['inventario_cargado']
else:
    df_inv = None

archivos_auditoria = {
    "Productos": "Auditoría_Aleatoria_Productos.csv",
    "Posiciones": "Auditoría_Aleatoria_Posiciones.csv",
    "Clientes": "Auditoría_Aleatoria_Clientes.csv",
    "Proveedores": "Auditoría_Aleatoria_Proveedores.csv"
}

@st.cache_data 
def cargar_datos(ruta):
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.lower() == ruta.lower():
                try:
                    return pd.read_csv(os.path.join(root, file))
                except Exception:
                    continue
    return pd.read_csv(ruta)

if seccion_activa == "Auditoría Live":
    try:
        df_base = cargar_datos(archivos_auditoria[tipo_auditoria])
    except FileNotFoundError:
        st.error(f"No se encontró la base para {tipo_auditoria}.", icon=":material/error:")
        st.stop()

if 'muestra_actual' not in st.session_state:
    st.session_state['muestra_actual'] = pd.DataFrame()
if 'posicion_semanal' not in st.session_state:
    st.session_state['posicion_semanal'] = None

if seccion_activa == "Resumen Consolidado":
    col_dash_tit, col_dash_btn = st.columns([3, 1])
    with col_dash_tit:
        st.title("Consolidado General de Auditorías")
    with col_dash_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Resetear Filtros", type="secondary", use_container_width=True, icon=":material/filter_alt_off:"):
            for k in ["chart_linea_interactivo", "chart_barras_interactivo"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.session_state["combo_semana_dash"] = "Todas"
            st.session_state["combo_obs_dash"] = "Todas"
            st.rerun()

    st.markdown("---")
    df_dash = cargar_base_consolidada()
    
    if df_dash is None or df_dash.empty:
        st.warning("No se pudo cargar la base consolidada.", icon=":material/warning:")
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
        
        if filtro_click_semana:
            df_dash_filtered = df_dash_filtered[df_dash_filtered['Nombre del Archivo Origen'] == filtro_click_semana]
        elif sem_sel != "Todas":
            df_dash_filtered = df_dash_filtered[df_dash_filtered['Nombre del Archivo Origen'] == sem_sel]
            
        if filtro_click_observacion:
            df_dash_filtered = df_dash_filtered[df_dash_filtered['Observaciones'] == filtro_click_observacion]
        elif obs_sel != "Todas":
            df_dash_filtered = df_dash_filtered[df_dash_filtered['Observaciones'] == obs_sel]

        total_auditorias = len(df_dash_filtered)
        ok_count = (df_dash_filtered['Resultado'] == 'OK').sum()
        eri_val = (ok_count / total_auditorias) * 100 if total_auditorias > 0 else 0
        desvio_neto_val = df_dash_filtered['desvio_neto'].sum()
        desvio_abs_val = df_dash_filtered['desvio_abs'].sum()
        
        if eri_val > 90: eri_class = "kpi-eri-green"
        elif eri_val >= 80: eri_class = "kpi-eri-orange"
        else: eri_class = "kpi-eri-red"
        
        with st.container():
            k1, k2, k3 = st.columns(3)
            with k1: st.markdown(f"""<div class="{eri_class}"><div class="dash-kpi-label">ERI</div><div class="dash-kpi-val">{eri_val:.1f}%</div></div>""", unsafe_allow_html=True)
            with k2: st.markdown(f"""<div class="dash-kpi-blue"><div class="dash-kpi-label">Desvío Neto</div><div class="dash-kpi-val">{int(desvio_neto_val):,}</div></div>""", unsafe_allow_html=True)
            with k3: st.markdown(f"""<div class="dash-kpi-blue"><div class="dash-kpi-label">Desvío Absoluto</div><div class="dash-kpi-val">{int(desvio_abs_val):,}</div></div>""", unsafe_allow_html=True)
                
            st.markdown("<br>", unsafe_allow_html=True)
            c_graf1, c_graf2 = st.columns(2)
            
            with c_graf1:
                df_dash['Semana_Num'] = df_dash['Nombre del Archivo Origen'].astype(str).str.extract(r'(\d+)').astype(float)
                df_sem = df_dash.groupby(['Nombre del Archivo Origen', 'Semana_Num']).apply(
                    lambda g: pd.Series({'Total': len(g), 'OK': (g['Resultado'] == 'OK').sum(), 'ERI': ((g['Resultado'] == 'OK').sum() / len(g)) * 100 if len(g) > 0 else 0})
                ).reset_index().sort_values('Semana_Num')
                fig_line = go.Figure()
                fig_line.add_trace(go.Scatter(x=df_sem['Nombre del Archivo Origen'], y=df_sem['ERI'], mode='lines+markers', name='Calculo_ERI', line=dict(color='#0D6EFD', width=3, shape='spline'), marker=dict(size=8, color='#0D6EFD'), fill='tozeroy', fillcolor='rgba(13, 110, 253, 0.12)'))
                fig_line.add_trace(go.Scatter(x=df_sem['Nombre del Archivo Origen'], y=[95] * len(df_sem), mode='lines', name='Objetivo (95%)', line=dict(color='#dc3545', width=2, dash='dash')))
                fig_line.update_layout(title="", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0', size=11), height=340, yaxis=dict(title="", range=[0, 105], ticksuffix="%", gridcolor='rgba(255,255,255,0.06)'), xaxis=dict(gridcolor='rgba(255,255,255,0.06)', tickfont=dict(size=10, color='#cbd5e1')), margin=dict(l=20, r=20, t=30, b=45), legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="center", x=0.5, font=dict(size=10, color='#94a3b8')))
                st.plotly_chart(fig_line, use_container_width=True, on_select="rerun", selection_mode="points", key="chart_linea_interactivo")
                
            with c_graf2:
                df_obs = df_dash[df_dash['Observaciones'] != 'Sin observaciones']['Observaciones'].value_counts().reset_index()
                df_obs.columns = ['Observacion', 'Cantidad']
                def formatear_etiqueta(texto):
                    texto_str = str(texto)
                    if "Diferencias en posiciones" in texto_str: return "Diferencias<br>cruzadas"
                    elif "posición errónea" in texto_str: return "Posición<br>errónea"
                    words = texto_str.split()
                    if len(texto_str) > 14 and len(words) > 1:
                        mid = len(words) // 2
                        return "<br>".join([" ".join(words[:mid]), " ".join(words[mid:])])
                    return texto_str
                df_obs['Observacion_Formateada'] = df_obs['Observacion'].apply(formatear_etiqueta)
                max_cant = df_obs['Cantidad'].max() if not df_obs.empty else 10
                fig_bar = px.bar(df_obs, x='Observacion_Formateada', y='Cantidad', text='Cantidad', custom_data=['Observacion'])
                fig_bar.update_traces(marker_color='#9a1031', textposition='outside', textfont=dict(color='#f8fafc', size=11), cliponaxis=False)
                fig_bar.update_layout(title="", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0', size=11), height=340, xaxis=dict(title="", tickangle=0, gridcolor='rgba(255,255,255,0.06)', tickfont=dict(size=10, color='#cbd5e1')), yaxis=dict(title="", range=[0, max_cant * 1.25], gridcolor='rgba(255,255,255,0.06)'), margin=dict(l=20, r=20, t=30, b=55))
                st.plotly_chart(fig_bar, use_container_width=True, on_select="rerun", selection_mode="points", key="chart_barras_interactivo")

        st.markdown("---")
        st.markdown("### Detalle de Auditorías")
        if 'Nombre del Archivo Origen' in df_dash.columns:
            semanas_unicas = df_dash['Nombre del Archivo Origen'].dropna().unique()
            semanas_list = ["Todas"] + sorted([str(x) for x in semanas_unicas])
        else:
            semanas_list = ["Todas"]
            
        col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
        with col_f1: st.selectbox("Filtrar por Semana:", semanas_list, key="combo_semana_dash")
        with col_f2:
            if 'Observaciones' in df_dash.columns:
                obs_unicas = df_dash['Observaciones'].dropna().unique()
                obs_list = ["Todas"] + sorted([str(x) for x in obs_unicas])
            else:
                obs_list = ["Todas"]
            st.selectbox("Filtrar por Observación:", obs_list, key="combo_obs_dash")
            
        cols_dash = ['Nombre del Archivo Origen', 'Categoría', 'Código', 'Stock Octosis', 'Stock auditado', 'Diferencia', 'Resultado', 'Observaciones']
        cols_existentes = [c for c in cols_dash if c in df_dash_filtered.columns]
        df_mostrar_final = df_dash_filtered[cols_existentes].rename(columns={'Nombre del Archivo Origen': 'Semana'})
        st.dataframe(df_mostrar_final, use_container_width=True, hide_index=True)

elif seccion_activa == "Auditoría Live":
    st.title(f"Auditoría de {tipo_auditoria}")
    st.markdown("---")
    
    if tipo_auditoria == "Productos":
        if df_inv is None:
            st.info("Carga el archivo de inventario diario en la barra lateral para comenzar.", icon=":material/info:")
        else:
            # --- SISTEMA DE RECUPERACIÓN DESDE LA NUBE ---
            if st.session_state['muestra_actual'].empty:
                df_nube = cargar_borrador_nube()
                # Quitamos la restricción estricta de nombres de columnas para que el botón aparezca siempre que haya datos
                if not df_nube.empty:
                    st.warning("Se ha detectado un borrador de auditoría en la nube.", icon=":material/warning:")
                    c_n1, c_n2 = st.columns([1, 3])
                    with c_n1:
                        if st.button("Recuperar Borrador", type="primary", use_container_width=True, icon=":material/cloud_download:"):
                            cols_texto = ['Cod Sku', 'Descripcion', col_posicion_inv, col_deposito_inv, 'Observaciones']
                            for c in cols_texto:
                                if c in df_nube.columns:
                                    df_nube[c] = df_nube[c].astype(str).replace('nan', '')
                            if 'Stock auditado' in df_nube.columns:
                                df_nube['Stock auditado'] = pd.to_numeric(df_nube['Stock auditado'], errors='coerce')
                            if col_stock_inv in df_nube.columns:
                                df_nube[col_stock_inv] = pd.to_numeric(df_nube[col_stock_inv], errors='coerce')
                            st.session_state['muestra_actual'] = df_nube
                            st.rerun()
                    with c_n2:
                        if st.button("Descartar Borrador", type="secondary", icon=":material/delete:"):
                            vaciar_borrador_nube()
                            st.rerun()
                    st.markdown("---")

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
                
                submit_agregar = st.form_submit_button("Agregar a la Muestra", type="primary", use_container_width=True, icon=":material/add_circle:")
                
                if submit_agregar:
                    df_filtrado = df_base.copy()
                    if rotacion_sel != "Todos": df_filtrado = df_filtrado[df_filtrado["Clasificación Rotación "] == rotacion_sel]
                    if valor_sel != "Todos": df_filtrado = df_filtrado[df_filtrado["Clasificación Valor"] == valor_sel]
                        
                    if not st.session_state['muestra_actual'].empty:
                        skus_ya_seleccionados = st.session_state['muestra_actual']['Cod Sku'].unique().tolist()
                        df_filtrado = df_filtrado[~df_filtrado['Cod Sku'].isin(skus_ya_seleccionados)]
                    
                    df_filtrado = df_filtrado[df_filtrado['Cod Sku'].isin(df_inv[col_codigo_inv])]
                        
                    if not df_filtrado.empty:
                        nueva_muestra_base = df_filtrado.sample(min(tamano_muestra, len(df_filtrado)))
                        cruce_inmediato = pd.merge(nueva_muestra_base, df_inv, how='left', left_on='Cod Sku', right_on=col_codigo_inv)
                        
                        if st.session_state['muestra_actual'].empty:
                            st.session_state['muestra_actual'] = cruce_inmediato
                        else:
                            st.session_state['muestra_actual'] = pd.concat([st.session_state['muestra_actual'], cruce_inmediato], ignore_index=True)
                        
                        guardar_borrador_nube(st.session_state['muestra_actual'])
                    else:
                        st.warning("No hay más productos que coincidan con los filtros seleccionados.", icon=":material/warning:")
            
            if not st.session_state['muestra_actual'].empty:
                if st.button("Limpiar Muestra", use_container_width=True, icon=":material/delete:"):
                    st.session_state['muestra_actual'] = pd.DataFrame()
                    vaciar_borrador_nube()
                    st.rerun()

        if not st.session_state['muestra_actual'].empty:
            st.markdown("---")
            st.markdown("### Carga de Recuento Físico")
            
            df_recuento = st.session_state['muestra_actual'].copy()
            if 'Stock auditado' not in df_recuento.columns: df_recuento['Stock auditado'] = None
            if 'Observaciones' not in df_recuento.columns: df_recuento['Observaciones'] = ""
                
            columnas_edicion = ['Cod Sku', 'Descripcion', col_posicion_inv, col_deposito_inv, col_stock_inv, 'Stock auditado', 'Observaciones']
            columnas_existentes = [col for col in columnas_edicion if col in df_recuento.columns]
            df_recuento = df_recuento[columnas_existentes]
            
           # --- CÁLCULO DE MÉTRICAS (ESTÁTICAS) ---
            # Contamos cuántos códigos únicos tienen al menos una celda vacía
            pendientes_codigos = df_recuento[df_recuento['Stock auditado'].isna()]['Cod Sku'].nunique()
            pendientes_filas = df_recuento['Stock auditado'].isna().sum() # Control interno de filas
            
            st_teorico_temp = pd.to_numeric(df_recuento[col_stock_inv], errors='coerce').fillna(0)
            st_fisico_temp = pd.to_numeric(df_recuento['Stock auditado'], errors='coerce')
            dif_reales = ((st_fisico_temp.notna()) & (st_fisico_temp != st_teorico_temp)).sum()
            
            codigos_unicos = df_recuento['Cod Sku'].nunique()

            c_m1, c_m2, c_m3, c_m4, c_btn = st.columns([1, 1, 1, 1, 1.4])
            
            with c_m1: 
                st.markdown(f"""<div class="metric-card-soft"><div class="metric-card-soft-label">Posiciones</div><div class="metric-card-soft-val">{len(df_recuento)}</div></div>""", unsafe_allow_html=True)
            with c_m2: 
                st.markdown(f"""<div class="metric-card-soft"><div class="metric-card-soft-label">Códigos Únicos</div><div class="metric-card-soft-val">{codigos_unicos}</div></div>""", unsafe_allow_html=True)
            with c_m3: 
                st.markdown(f"""<div class="metric-card-soft"><div class="metric-card-soft-label">Pendientes</div><div class="metric-card-soft-val">{pendientes_codigos}</div></div>""", unsafe_allow_html=True)
            with c_m4: 
                st.markdown(f"""<div class="metric-card-soft"><div class="metric-card-soft-label">Diferencias</div><div class="metric-card-soft-val">{dif_reales}</div></div>""", unsafe_allow_html=True)
            
            with c_btn:
                if st.button("Mostrar Ruta y Cargar", type="primary", use_container_width=True, icon=":material/route:"):
                    mostrar_ruta_auditoria(st.session_state['muestra_actual'], col_posicion_inv, col_deposito_inv, col_stock_inv)
                    
            st.markdown("<br>", unsafe_allow_html=True)
            
            with st.form("form_editor_auditoria"):
                df_editado = st.data_editor(
                    df_recuento,
                    column_config={
                        "Cod Sku": st.column_config.TextColumn("Código", disabled=True),
                        "Descripcion": st.column_config.TextColumn("Descripción", disabled=True),
                        col_posicion_inv: st.column_config.TextColumn("Posición", disabled=True),
                        col_deposito_inv: st.column_config.TextColumn("Depósito", disabled=True),
                        col_stock_inv: st.column_config.NumberColumn("St. Teórico", disabled=True),
                        "Stock auditado": st.column_config.NumberColumn("St. Físico", required=False),
                        "Observaciones": st.column_config.TextColumn("Observaciones")
                    },
                    use_container_width=True,
                    hide_index=True,
                    num_rows="dynamic",
                    key="editor_auditoria_prod"
                )
                
                c_g1, c_g2 = st.columns([1, 1])
                with c_g1: btn_guardar_local = st.form_submit_button("Guardar Local", icon=":material/save:", type="secondary")
                with c_g2: btn_guardar_nube = st.form_submit_button("Guardar en Nube", icon=":material/cloud_sync:", type="primary")
                
            if btn_guardar_local or btn_guardar_nube:
                st.session_state['muestra_actual'] = df_editado
                if btn_guardar_nube:
                    if guardar_borrador_nube(df_editado):
                        st.success("Borrador guardado en Google Sheets.", icon=":material/check_circle:")
                st.rerun()
            
            if st.button("Generar Reporte Final", type="primary", icon=":material/assignment_turned_in:", disabled=(faltan_cargar > 0)):
                stock_teorico = pd.to_numeric(df_editado[col_stock_inv], errors='coerce').fillna(0)
                stock_fisico = pd.to_numeric(df_editado['Stock auditado'], errors='coerce').fillna(0)
                df_editado['Diferencia'] = stock_fisico - stock_teorico
                
                def evaluar_resultado(dif):
                    if dif == 0: return "OK"
                    elif dif < 0: return "FALTANTE"
                    else: return "SOBRANTE"
                        
                df_editado['Resultado'] = df_editado['Diferencia'].apply(evaluar_resultado)
                categorias = df_editado['Cod Sku'].map(df_base.set_index('Cod Sku')['Clasificación Valor']).fillna("Sin Categoría")

                df_preparado = pd.DataFrame({
                    'Categoría': categorias,
                    'Código': df_editado['Cod Sku'],
                    'Stock Octosis': stock_teorico,
                    'Stock auditado': stock_fisico,
                    'Diferencia': df_editado['Diferencia'],
                    'Resultado': df_editado['Resultado'],
                    'Observaciones': df_editado['Observaciones']
                })
                confirmar_e_impactar_consolidado(df_preparado)

    elif tipo_auditoria == "Posiciones":
        if df_inv is None:
            st.info("Carga el archivo de inventario diario en la barra lateral para comenzar.", icon=":material/info:")
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
                with f1: nivel_sel = st.selectbox("Nivel:", ["Todos"] + niveles_disponibles)
                with f2: seccion_sel = st.selectbox("Pasillo / Sección:", ["Todos"] + secciones_disponibles)
                    
                submit_pos = st.form_submit_button("Sustraer Posición Aleatoria", type="primary", use_container_width=True, icon=":material/my_location:")
                
                if submit_pos:
                    df_pos_filtrado = df_base[df_base['Nivel'].isin(['1', '2', '3'])].copy()
                    if nivel_sel != "Todos": df_pos_filtrado = df_pos_filtrado[df_pos_filtrado['Nivel'] == nivel_sel]
                    if seccion_sel != "Todos": df_pos_filtrado = df_pos_filtrado[df_pos_filtrado['Seccion'] == seccion_sel]
                        
                    df_inv_parsed = df_inv[col_posicion_inv].apply(parse_posicion_completa)
                    df_inv['Posicion_Base'] = [x[3] for x in df_inv_parsed]
                    df_inv['Estanteria_Clean'] = [x[4] for x in df_inv_parsed]
                    
                    pos_base_con_stock = df_inv['Posicion_Base'].unique()
                    df_pos_filtrado = df_pos_filtrado[df_pos_filtrado['Posicion_Base'].isin(pos_base_con_stock)]
                    
                    if not df_pos_filtrado.empty:
                        pos_base_elegida = df_pos_filtrado.sample(1)['Posicion_Base'].values[0].strip()
                        st.session_state['posicion_semanal'] = pos_base_elegida
                    else:
                        st.info("No hay posiciones con productos en el inventario para los filtros seleccionados.", icon=":material/info:")

            if st.session_state['posicion_semanal'] is not None:
                if st.button("Limpiar Selección", use_container_width=True, icon=":material/delete:"):
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
                    
                    with st.form("form_posiciones_audit"):
                        df_editor_pos = st.data_editor(
                            productos_en_posicion[cols_existentes],
                            column_config={
                                "Código": st.column_config.TextColumn("Código", disabled=True),
                                "Descripcion": st.column_config.TextColumn("Descripción", disabled=True),
                                "Estanteria_Clean": st.column_config.TextColumn("Posición Específica", disabled=True),
                                col_deposito_inv: st.column_config.TextColumn("Depósito", disabled=True),
                                col_stock_inv: st.column_config.NumberColumn("Stock Teórico", disabled=True),
                                "Stock auditado": st.column_config.NumberColumn("Stock Físico", required=False),
                                "Observaciones": st.column_config.TextColumn("Observaciones")
                            },
                            use_container_width=True,
                            hide_index=True,
                            key="editor_posicion_semanal"
                        )
                        btn_pos_guardar = st.form_submit_button("Actualizar Valores", icon=":material/save:", type="secondary")
                        
                    faltan_pos = df_editor_pos['Stock auditado'].isna().sum()
                    
                    if st.button("Generar Reporte de Posición", type="primary", icon=":material/assignment_turned_in:", disabled=(faltan_pos > 0)):
                        st_teorico = pd.to_numeric(df_editor_pos[col_stock_inv], errors='coerce').fillna(0)
                        st_fisico = pd.to_numeric(df_editor_pos['Stock auditado'], errors='coerce').fillna(0)
                        df_editor_pos['Diferencia'] = st_fisico - st_teorico
                        df_editor_pos['Resultado'] = df_editor_pos['Diferencia'].apply(
                            lambda d: "OK" if d == 0 else ("FALTANTE" if d < 0 else "SOBRANTE")
                        )
                        
                        df_rep_pos = pd.DataFrame({
                            'Categoría': "Posiciones",
                            'Código': df_editor_pos['Código'],
                            'Stock Octosis': st_teorico,
                            'Stock auditado': st_fisico,
                            'Diferencia': df_editor_pos['Diferencia'],
                            'Resultado': df_editor_pos['Resultado'],
                            'Observaciones': df_editor_pos['Observaciones']
                        })
                        confirmar_e_impactar_consolidado(df_rep_pos)
                else:
                    st.info("No se registran productos en el inventario teórico para esta posición.", icon=":material/info:")

    elif tipo_auditoria in ["Clientes", "Proveedores"]:
        st.info("Módulo en desarrollo.", icon=":material/construction:")
