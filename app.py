
from pathlib import Path
import streamlit as st

from core.reabasto import procesar_reabasto
from reports.html_report import generar_html


BASE = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Reabasto de Cajas",
    page_icon="📦",
    layout="wide"
)

st.title("📦 Sistema de Reabasto de Cajas")

st.markdown(
    "Procesa las **Líneas de Pedido Sin Inventario** "
    "y genera la **Orden de Reabasto Imprimible**."
)

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

