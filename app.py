
from pathlib import Path
import streamlit as st
import base64

from core.reabasto import procesar_reabasto
from reports.html_report import generar_html


BASE = Path(__file__).resolve().parent


st.set_page_config(
    page_title="Reabasto de Cajas",
    page_icon="📦",
    layout="wide"
)

st.markdown("""
<style>
[data-testid="stToolbar"] {
    visibility: hidden;
    height: 0%;
    position: fixed;
}
</style>
""", unsafe_allow_html=True)

def obtener_logo_base64(nombre):
    ruta = Path(__file__).resolve().parent / "static" / nombre

    if not ruta.exists():
        return None

    return base64.b64encode(ruta.read_bytes()).decode("ascii")


def aplicar_estilos_ccu():
    logo_ccu = obtener_logo_base64("ccu.png")
    logo_cuspide = obtener_logo_base64("cuspide.png")

    st.markdown("""
    <style>
        :root {
            --ccu-primary: #5AB031;
            --ccu-bg: #D9EAD7;
            --ccu-card: #E8F1EB;
            --ccu-dark: #264831;
            --ccu-border: #BFD8BB;
            --ccu-text: #1F2937;
        }

        .stApp {
            background-color: var(--ccu-bg);
            color: var(--ccu-text);
        }

        .block-container {
            max-width: 1350px !important;
            width: 100% !important;

            padding-left: 20px !important;
            padding-right: 20px !important;
            padding-top: 0 !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }

        [data-testid="stToolbar"] {
            z-index: 1000;
        }


        h1, h2, h3 {
            color: var(--ccu-dark) !important;
        }

        div[data-testid="stFileUploader"] {
            background-color: #FFFFFF;
            border: 1px solid var(--ccu-border);
            border-radius: 16px;
            padding: 15px;
        }

        div[data-testid="stFileUploader"] section {
            background: #FFFFFF;
            border-color: var(--ccu-border);
        }

        div[data-testid="stButton"] button[kind="primary"] {
            background: var(--ccu-primary);
            color: white;
            border: none;
            border-radius: 10px;
            font-weight: 700;
        }
        div[data-testid="stFileUploader"] button {
    background-color: #FFFFFF !important;
    color: #264831 !important;
    border: 1px solid var(--ccu-border) !important;
}

div[data-testid="stFileUploader"] button:hover {
    background-color: #F3F8F3 !important;
    color: #264831 !important;
    border-color: var(--ccu-primary) !important;
}

        div[data-testid="stButton"] button[kind="primary"]:hover {
            background: #478D26;
            color: white;
        }

        
/* Encabezado CCU de borde a borde */

/* Encabezado CCU de borde a borde */
.ccu-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;

    width: 100vw;
    max-width: none;

    position: relative;
    left: 50%;
    transform: translateX(-50%);

    /* Evitar que los logos queden fuera de pantalla */
    margin-top: 0 !important;
    margin-bottom: 25px;

    padding: 15px 25px;

    background: var(--ccu-bg);
    border: none;
    border-radius: 0;
    box-shadow: none;

    min-height: 100px;
    z-index: 1;
}


        .ccu-header h1 {
            font-size: clamp(24px, 3vw, 38px);
            font-weight: 800;
            margin: 0;
        }

        .ccu-header p {
            color: #64748B;
            margin: 6px 0 0;

        }

        .ccu-logo {
            max-height: 40px;
            max-width: 75px;
            object-fit: contain;
        }

        .ccu-logo-left {
            max-height: 105px;
        }
        .ccu-logo-right {
            padding-top: 20px;
            padding-right: 5px;
            max-height: 70px;
        }

        @media (max-width: 700px) {
            .ccu-header {
                flex-wrap: wrap;
                justify-content: center;
                text-align: center;
            }

            .ccu-header h1 {
                font-size: 25px;
            }

            .ccu-logo {
                max-height: 35px;
            }
        }
    </style>
    """, unsafe_allow_html=True)

    izquierda = (
        f'<img class="ccu-logo ccu-logo-left" '
        f'src="data:image/png;base64,{logo_ccu}" alt="CCU">'
        if logo_ccu else ""
    )

    derecha = (
        f'<img class="ccu-logo ccu-logo-right" '
        f'src="data:image/png;base64,{logo_cuspide}" '
        f'alt="Cúspide">'
        if logo_cuspide else ""
    )

    st.markdown(f"""
    <div class="ccu-header">
        {izquierda}
        {derecha}
    </div>
    """, unsafe_allow_html=True)


aplicar_estilos_ccu()

st.title("Sistema de Reabasto de Cajas")



col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Líneas de Pedido Sin Inventario")

    pedidos = st.file_uploader(
        "Archivo de pedidos",
        type=["csv", "xlsx", "xls"],
        key="pedidos"
    )

with col2:
    st.subheader("2. Inventario (Cuadratura o Vida Útil)")

    inventario = st.file_uploader(
        "Archivo de inventario",
        type=["csv", "xlsx", "xls"],
        key="inventario"
    )

st.divider()

if st.button(
    "🚀 Procesar Reabasto de Cajas",
    type="primary",
    use_container_width=True
):
    if pedidos is None or inventario is None:
        st.error("Sube ambos archivos antes de procesar.")

    else:
        try:
            resultado, tiene_lote, formato, faltantes = (
                procesar_reabasto(
                    pedidos,
                    inventario,
                    BASE / "data" / "Pos_SKU.csv"
                )
            )

            st.session_state["formato"] = formato
            st.session_state["faltantes"] = faltantes
            st.session_state["reporte"] = generar_html(resultado)
            st.session_state["cantidad"] = len(resultado)
            st.session_state["skus"] = resultado["SKU"].nunique()
            st.session_state["tiene_lote"] = tiene_lote

        except (ValueError, FileNotFoundError, KeyError) as exc:
            st.session_state.pop("reporte", None)
            st.error(f"Error de datos: {exc}")


if "reporte" in st.session_state:

    if not st.session_state["tiene_lote"]:
        st.warning(
            "No se encontró Lote de Programación; "
            "se mantiene el orden por ubicación."
        )

    st.success(
        f"Procesamiento exitoso: "
        f"{st.session_state['skus']} SKUs, "
        f"{st.session_state['cantidad']} filas."
    )

    if st.session_state["formato"] != "vida_util":
        st.warning("Advertencia: Cuadratura de stock no respeta FEFO, subir OPERACIONES DE VIDA UTIL.")


    altura_reporte = max(
    500,
    260 + st.session_state["cantidad"] * 48
    )

    st.components.v1.html(
        st.session_state["reporte"],
        height=altura_reporte,
        scrolling=False
    )

