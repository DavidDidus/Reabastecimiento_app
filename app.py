import streamlit as st
import pandas as pd
import io
import os
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

# Encabezado
st.title("📦 Sistema de Reabasto de Cajas")
st.markdown("""
Procesa la demanda de **Líneas de Pedido Sin Inventario** y genera la **Orden de Reabasto Imprimible** lista para entregar al operador de grúa.
""")

# Interfaz en 2 columnas
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Líneas de Pedido Sin Inventario")
    st.caption("Pega el texto copiado desde el sistema (con tabulaciones):")
    pedidos_text = st.text_area(
        "Pega aquí las líneas sin inventario:",
        height=240,
        placeholder="FECHA PROGRAMACION\tEstado de lote\tSKU\tDescripcion\tCANTIDAD SOLICITADA..."
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
    if not pedidos_text.strip():
        st.error("⚠️ Por favor pega el texto de las Líneas de Pedido Sin Inventario.")
    elif cuadratura_file is None:
        st.error("⚠️ Por favor sube el archivo de Cuadratura de Stock.")
    else:
        try:
            pos_map = cargar_pos_sku_fijo()

            # 1. Leer Pedidos
            df_pedidos = pd.read_csv(io.StringIO(pedidos_text), sep='\t')
            df_pedidos.columns = [str(c).strip() for c in df_pedidos.columns]
            
            if 'SKU' not in df_pedidos.columns or 'CANTIDAD SOLICITADA' not in df_pedidos.columns:
                st.error("❌ No se encontraron las columnas 'SKU' y 'CANTIDAD SOLICITADA' en el texto pegado.")
                st.stop()

            df_pedidos['SKU_Clean'] = df_pedidos['SKU'].apply(limpiar_sku)
            df_pedidos['CANTIDAD SOLICITADA'] = pd.to_numeric(df_pedidos['CANTIDAD SOLICITADA'], errors='coerce').fillna(0)

            df_resumen = df_pedidos.groupby(['SKU', 'SKU_Clean', 'Descripcion'], as_index=False)['CANTIDAD SOLICITADA'].sum()

            # 2. Leer Cuadratura
            if cuadratura_file.name.endswith('.csv'):
                try:
                    df_cuad = pd.read_csv(cuadratura_file)
                except Exception:
                    cuadratura_file.seek(0)
                    df_cuad = pd.read_csv(cuadratura_file, sep=';', encoding='utf-8', errors='ignore')
            else:
                df_cuad = pd.read_excel(cuadratura_file)

            df_cuad.columns = [str(c).strip().lower() for c in df_cuad.columns]
            
            col_art = 'articulo' if 'articulo' in df_cuad.columns else 'artículo'
            col_area = 'area' if 'area' in df_cuad.columns else 'área'
            col_ubi = 'ubicacion' if 'ubicacion' in df_cuad.columns else 'ubicación'

            df_cuad['SKU_Clean'] = df_cuad[col_art].apply(limpiar_sku)

            almac_map = df_cuad[df_cuad[col_area].isin(['ALMAC', 'ALMPIC'])].groupby('SKU_Clean')[col_ubi].first().to_dict()
            surt_cuad_map = df_cuad[df_cuad[col_area] == 'SURTID'].groupby('SKU_Clean')[col_ubi].first().to_dict()

            # 3. Cruce de Ubicaciones
            df_resumen['ALMACENAMIENTO'] = df_resumen['SKU_Clean'].map(almac_map).fillna("Sin Pall en almac")
            df_resumen['SURTIDO'] = (
                df_resumen['SKU_Clean']
                .map(pos_map)
                .fillna(df_resumen['SKU_Clean'].map(surt_cuad_map))
                .fillna("Sin Ubicación Surtido")
            )

            # Ordenar por ubicación de Almacenamiento para optimizar la ruta de la grúa
            df_resumen = df_resumen.sort_values(by=['ALMACENAMIENTO', 'SURTIDO']).reset_index(drop=True)

            df_final = df_resumen[['SKU', 'Descripcion', 'CANTIDAD SOLICITADA', 'ALMACENAMIENTO', 'SURTIDO']].copy()
            df_final.columns = ['SKU', 'Descripción del Producto', 'Cant. Solicitada', 'Ubicación Origen (ALMACÉN)', 'Ubicación Destino (SURTIDO)']

            st.success(f"🎉 **¡Procesamiento exitoso!** Se consolidaron **{len(df_final)} SKUs**.")

            # Pestaña para Vista previa en Pantalla y Vista de Impresión
            tab1, tab2 = st.tabs(["📊 Vista Previa Tabla", "🖨️ Hoja de Ruta para Grúa (Imprimible)"])

            with tab1:
                st.dataframe(df_final, use_container_width=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_final.to_excel(writer, sheet_name='RESUMEN', index=False)
                
                st.download_button(
                    label="📥 Descargar Excel para Registros",
                    data=output.getvalue(),
                    file_name="REABASTO_DE_CAJAS.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            with tab2:
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
                    .footer-sig {{
                        margin-top: 40px;
                        width: 100%;
                    }}
                    .signature-line {{
                        border-top: 1px solid #000;
                        width: 200px;
                        text-align: center;
                        padding-top: 5px;
                        font-size: 12px;
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

                # Renderizar HTML e incluir botón JavaScript de Impresión
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
                    height=750,
                    scrolling=True
                )

        except Exception as e:
            st.error(f"❌ Ocurrió un error al procesar los datos: {str(e)}")