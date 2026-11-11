
import pandas as pd

from core.pedidos import consolidar_pedidos

from core.ubicaciones import (
    cargar_posiciones,
    mapas_cuadratura
)

from core.fefo import (
    detectar_formato,
    asignar_fefo
)

from utils.archivos import cargar_dataframe


COLUMNAS = [
    "Secuencia Camión",
    "SKU",
    "Descripción del Producto",
    "Cant. Solicitada",
    "Ubicación Origen (ALMACÉN)",
    "Ubicación Destino (SURTIDO)"
]


def procesar_reabasto(
    pedidos,
    inventario,
    ruta_posiciones
):

    resumen, tiene_lote = consolidar_pedidos(
        cargar_dataframe(pedidos)
    )

    posiciones = cargar_posiciones(
        ruta_posiciones
    )

    df_inv = cargar_dataframe(inventario)

    formato = detectar_formato(df_inv)

    almac, fallback, surt = mapas_cuadratura(df_inv)

    faltantes = []

    if formato == "vida_util":

        resumen, faltantes = asignar_fefo(
            resumen,
            df_inv,
            posiciones,
            surt
        )

    else:

        resumen["ALMACENAMIENTO"] = (
            resumen["SKU_Clean"]
            .map(almac)
            .fillna(
                resumen["SKU_Clean"].map(fallback)
            )
            .fillna("Sin Pall en almac")
        )

        resumen["SURTIDO"] = (
            resumen["SKU_Clean"]
            .map(posiciones)
            .fillna(
                resumen["SKU_Clean"].map(surt)
            )
            .fillna("Sin Ubicación Surtido")
        )

    if resumen.empty:
        return (
            pd.DataFrame(columns=COLUMNAS),
            tiene_lote,
            formato,
            faltantes
        )

    resumen["ORDEN"] = pd.to_numeric(
        resumen["SECUENCIA_LOTE"],
        errors="coerce"
    ).fillna(10**9)

    # Conservar el orden FEFO dentro de cada SKU.
    resumen = resumen.sort_values(
        ["ORDEN"],
        kind="stable"
    ).reset_index(drop=True)

    resumen["SECUENCIA_LOTE"] = (
        resumen["SECUENCIA_LOTE"].apply(
            lambda x: int(x)
            if pd.notna(x)
            else None
        )
    )

    final = resumen[[
        "SECUENCIA_LOTE",
        "SKU",
        "Descripcion",
        "CANTIDAD SOLICITADA",
        "ALMACENAMIENTO",
        "SURTIDO"
    ]].copy()

    final.columns = COLUMNAS

    return (
        final,
        tiene_lote,
        formato,
        faltantes
    )
