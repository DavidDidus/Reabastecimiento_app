import streamlit as st
import pandas as pd
import io
import os
import re
from datetime import datetime

# Configuración de página
st.set_page_config(
    page_title="Reabasto de Cajas",
    page_icon="📦",
    layout="wide"
)

def limpiar_sku(sku):
    """
    Normaliza los SKUs quitando espacios y ceros iniciales
    para evitar fallos por formato (ej: '000836' vs '836').
    """
    val = str(sku).strip()
    if val.replace('0', '').isdigit():
        return val.lstrip('0')
    return val

def extraer_secuencia_lote(lote_programacion):
    """
    Extrae la secuencia final desde el lote con formato fecha-planilla-secuencia.
    Si no puede extraerla, devuelve None.
    """
    val = str(lote_programacion).strip()
    if not val or val.lower() == 'nan':
        return None

    # Caso esperado: 20260901-ABC-15 -> 15
    partes = val.split('-')
    ultimo_tramo = partes[-1].strip()

    match_final = re.search(r'(\d+)$', ultimo_tramo)
    if match_final:
        return int(match_final.group(1))

    # Respaldo: tomar el último bloque numérico presente en todo el texto.
    bloques_numericos = re.findall(r'\d+', val)
    if bloques_numericos:
        return int(bloques_numericos[-1])

    return None

@st.cache_data
def cargar_pos_sku_fijo():
    """
    Carga el archivo maestro Pos_SKU.csv desde la carpeta del proyecto.
    """
    pos_file = "Pos_SKU.csv"
    if not os.path.exists(pos_file):
        st.error(f"⚠️ No se encontró el archivo base '{pos_file}' en el proyecto.")
        return {}
    
    try:
        df_pos = pd.read_csv(pos_file, sep=';')
    except Exception:
        df_pos = pd.read_csv(pos_file, sep=',')

    df_pos.columns = [str(c).strip().upper() for c in df_pos.columns]
    col_sku_pos = [c for c in df_pos.columns if 'ARTICULO' in c or 'SKU' in c][0]
    col_ubi_pos = [c for c in df_pos.columns if 'UBICAC' in c][0]

    df_pos['SKU_Clean'] = df_pos[col_sku_pos].apply(limpiar_sku)
    return df_pos.set_index('SKU_Clean')[col_ubi_pos].to_dict()

def cargar_dataframe(uploaded_file):
    """
    Función auxilar para leer archivos CSV (con coma o punto y coma) o Excel (.xlsx/.xls)
    """
    if uploaded_file.name.endswith('.csv'):
        try:
            df = pd.read_csv(uploaded_file)
        except Exception:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8', errors='ignore')
    else:
        df = pd.read_excel(uploaded_file)
    return df

# Encabezado
st.title("📦 Sistema de Reabasto de Cajas")
st.markdown("""
Procesa la demanda de **Líneas de Pedido Sin Inventario** y genera la **Orden de Reabasto Imprimible** lista para entregar al operador de grúa.
""")

# Interfaz en 2 columnas
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Líneas de Pedido Sin Inventario")
    st.caption("Subir archivo CSV / Excel descargado:")
    pedidos_file = st.file_uploader(
        "Sube Líneas de Pedido Sin Inventario:",
        type=["csv", "xlsx", "xls"],
        key="pedidos"
    )

with col2:
    st.subheader("2. Cuadratura de Stock")
    st.caption("Subir archivo CSV / Excel descargado:")
    cuadratura_file = st.file_uploader(
        "Sube Cuadratura de Stock:",
        type=["csv", "xlsx", "xls"],
        key="cuad"
    )

st.divider()

if st.button("🚀 Procesar Reabasto de Cajas", type="primary", use_container_width=True):
    if pedidos_file is None:
        st.error("⚠️ Por favor sube el archivo de Líneas de Pedido Sin Inventario.")
    elif cuadratura_file is None:
        st.error("⚠️ Por favor sube el archivo de Cuadratura de Stock.")
    else:
        try:
            pos_map = cargar_pos_sku_fijo()

            # 1. Leer Pedidos
            df_pedidos = cargar_dataframe(pedidos_file)
            
            # Normalizar nombres de columnas a mayúsculas y sin espacios laterales
            df_pedidos.columns = [str(c).strip().upper() for c in df_pedidos.columns]

            # Mapeo flexible de columnas
            col_sku = [c for c in df_pedidos.columns if 'SKU' in c or 'ARTICULO' in c]
            col_cant = [c for c in df_pedidos.columns if 'SELECCION' in c]
            col_desc = [c for c in df_pedidos.columns if 'DESCRIPCION' in c or 'DESCRIPCIÓN' in c]
            col_lote_prog = [c for c in df_pedidos.columns if 'LOTE' in c and ('PROGRAM' in c or 'PROG' in c)]

            if not col_sku or not col_cant:
                st.error("❌ No se encontraron las columnas necesarias ('SKU' y 'CANTIDAD PEDIDA / SOLICITADA') en el archivo de pedidos.")
                st.stop()

            sku_col_name = col_sku[0]
            cant_col_name = col_cant[0]
            desc_col_name = col_desc[0] if col_desc else sku_col_name
            lote_col_name = col_lote_prog[0] if col_lote_prog else None

            df_pedidos['SKU_Clean'] = df_pedidos[sku_col_name].apply(limpiar_sku)
            df_pedidos['CANTIDAD_SOLICITADA'] = pd.to_numeric(df_pedidos[cant_col_name], errors='coerce').fillna(0)
            df_pedidos['SECUENCIA_LOTE'] = (
                df_pedidos[lote_col_name].apply(extraer_secuencia_lote)
                if lote_col_name else None
            )

            # Consolidar por SKU
            if lote_col_name:
                df_resumen = df_pedidos.groupby(
                    [sku_col_name, 'SKU_Clean', desc_col_name],
                    as_index=False
                ).agg({
                    'CANTIDAD_SOLICITADA': 'sum',
                    'SECUENCIA_LOTE': 'min'
                })
            else:
                st.warning("⚠️ No se encontró la columna de Lote de Programación. Se mantiene el orden tradicional.")
                df_resumen = df_pedidos.groupby(
                    [sku_col_name, 'SKU_Clean', desc_col_name],
                    as_index=False
                )['CANTIDAD_SOLICITADA'].sum()
                df_resumen['SECUENCIA_LOTE'] = None

            # Renombrar columnas internas para estandarización
            df_resumen.rename(columns={
                sku_col_name: 'SKU',
                desc_col_name: 'Descripcion',
                'CANTIDAD_SOLICITADA': 'CANTIDAD SOLICITADA'
            }, inplace=True)

            # 2. Leer Cuadratura
            df_cuad = cargar_dataframe(cuadratura_file)
            df_cuad.columns = [str(c).strip().lower() for c in df_cuad.columns]
            
            col_art = 'articulo' if 'articulo' in df_cuad.columns else 'artículo'
            col_area = 'area' if 'area' in df_cuad.columns else 'área'
            col_ubi = 'ubicacion' if 'ubicacion' in df_cuad.columns else 'ubicación'

            df_cuad['SKU_Clean'] = df_cuad[col_art].apply(limpiar_sku)
            df_cuad['UBI_NORM'] = (
                df_cuad[col_ubi]
                .astype(str)
                .str.upper()
                .str.replace(r'[^A-Z0-9]', '', regex=True)
            )

            almac_map = df_cuad[df_cuad[col_area].isin(['ALMAC', 'ALMPIC'])].groupby('SKU_Clean')[col_ubi].first().to_dict()
            ubicaciones_fallback_norm = {
                'REBA01',
                'MIX01',
                'STREC01',
                'STREC02',
                'STREC03',
                'STREC04',
                'STREC05'
            }
            almac_fallback_map = (
                df_cuad[df_cuad['UBI_NORM'].isin(ubicaciones_fallback_norm)]
                .groupby('SKU_Clean')[col_ubi]
                .first()
                .to_dict()
            )
            surt_cuad_map = df_cuad[df_cuad[col_area] == 'SURTID'].groupby('SKU_Clean')[col_ubi].first().to_dict()

            # 3. Cruce de Ubicaciones
            df_resumen['ALMACENAMIENTO'] = (
                df_resumen['SKU_Clean']
                .map(almac_map)
                .fillna(df_resumen['SKU_Clean'].map(almac_fallback_map))
                .fillna("Sin Pall en almac")
            )
            df_resumen['SURTIDO'] = (
                df_resumen['SKU_Clean']
                .map(pos_map)
                .fillna(df_resumen['SKU_Clean'].map(surt_cuad_map))
                .fillna("Sin Ubicación Surtido")
            )

            # Orden principal por secuencia de lote; ubicación queda como desempate.
            df_resumen['SECUENCIA_LOTE_ORDEN'] = pd.to_numeric(df_resumen['SECUENCIA_LOTE'], errors='coerce')
            df_resumen['SECUENCIA_LOTE_ORDEN'] = df_resumen['SECUENCIA_LOTE_ORDEN'].fillna(10**9)
            df_resumen = df_resumen.sort_values(
                by=['SECUENCIA_LOTE_ORDEN', 'ALMACENAMIENTO', 'SURTIDO']
            ).reset_index(drop=True)

            df_resumen['SECUENCIA_CAMION'] = df_resumen['SECUENCIA_LOTE'].apply(
                lambda x: int(x) if pd.notna(x) else None
            )

            df_final = df_resumen[['SECUENCIA_CAMION', 'SKU', 'Descripcion', 'CANTIDAD SOLICITADA', 'ALMACENAMIENTO', 'SURTIDO']].copy()
            df_final.columns = ['Secuencia Camión', 'SKU', 'Descripción del Producto', 'Cant. Solicitada', 'Ubicación Origen (ALMACÉN)', 'Ubicación Destino (SURTIDO)']

            st.success(f"🎉 **¡Procesamiento exitoso!** Se consolidaron **{len(df_final)} SKUs**.")

            fecha_hora = datetime.now().strftime("%d/%m/%Y %H:%M hrs")
            
            # Generar HTML de las filas para la grúa
            filas_html = ""
            for idx, r in df_final.iterrows():
                filas_html += f"""
                <tr>
                    <td style="text-align: center;">{idx + 1}</td>
                    <td style="font-weight: bold; font-family: monospace; font-size: 14px;">{r['SKU']}</td>
                    <td>{r['Descripción del Producto']}</td>
                    <td style="text-align: center; font-weight: bold; color: #1E3A8A; font-size: 15px;">{r['Ubicación Origen (ALMACÉN)']}</td>
                    <td style="text-align: center; font-weight: bold; color: #065F46; font-size: 15px;">{r['Ubicación Destino (SURTIDO)']}</td>
                        <td style="text-align: center; font-weight: bold;">{r['Secuencia Camión'] if pd.notna(r['Secuencia Camión']) else '-'}</td>
                    <td style="text-align: center; font-weight: bold; font-size: 16px;">{r['Cant. Solicitada']}</td>
                    <td style="width: 80px;"></td>
                </tr>
                """

            # Plantilla HTML con estilos CSS aptos para impresoras
            html_report = f"""
            <style>
                @media print {{
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; }}
                    .no-print {{ display: none !important; }}
                    .print-container {{ width: 100%; margin: 0; padding: 0; }}
                }}
                .report-card {{
                    border: 2px solid #1E293B;
                    border-radius: 8px;
                    padding: 20px;
                    background-color: #FFFFFF;
                    color: #0F172A;
                    font-family: Arial, sans-serif;
                }}
                .header-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 15px;
                }}
                .header-table td {{
                    padding: 4px;
                }}
                .title {{
                    font-size: 22px;
                    font-weight: bold;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    color: #0F172A;
                }}
                .data-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 15px;
                }}
                .data-table th {{
                    background-color: #1E293B;
                    color: white;
                    border: 1px solid #1E293B;
                    padding: 8px 6px;
                    font-size: 13px;
                    text-transform: uppercase;
                }}
                .data-table td {{
                    border: 1px solid #94A3B8;
                    padding: 8px 6px;
                    font-size: 13px;
                }}
            </style>

            <div class="report-card">
                <table class="header-table">
                    <tr>
                        <td class="title">Reabasto / Hoja de Ruta</td>
                        <td style="text-align: right; font-size: 12px;"><strong>Fecha Emisión:</strong> {fecha_hora}</td>
                    </tr>
                    <tr>
                        <td colspan="2" style="font-size: 13px; color: #475569;">
                            <strong>Total SKUs a Mover:</strong> {len(df_final)}
                        </td>
                    </tr>
                </table>

                <table class="data-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>SKU</th>
                            <th>Descripción Producto</th>
                            <th>Origen (Almacén)</th>
                            <th>Destino (Surtido)</th>
                            <th>Secuencia</th>
                            <th>Cajas</th>
                            <th>Check (✓)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filas_html}
                    </tbody>
                </table>
            </div>
            """

            # Renderizar directo el HTML con el botón de Impresión
            st.components.v1.html(
                f"""
                {html_report}
                <div style="margin-top: 15px; text-align: center;" class="no-print">
                    <button onclick="window.print()" style="
                        background-color: #2563EB; 
                        color: white; 
                        font-weight: bold; 
                        padding: 12px 24px; 
                        font-size: 16px; 
                        border: none; 
                        border-radius: 6px; 
                        cursor: pointer;
                    ">
                        🖨️ Imprimir Hoja de Ruta
                    </button>
                </div>
                """,
                height=800,
                scrolling=True
            )

        except Exception as e:
            st.error(f"❌ Ocurrió un error al procesar los datos: {str(e)}")