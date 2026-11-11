
import pandas as pd

from utils.archivos import normalizar_columnas

from utils.normalizacion import (
    limpiar_sku,
    extraer_secuencia_lote,
    encontrar_columna
)


def consolidar_pedidos(df):

    df = normalizar_columnas(df)

    sku = encontrar_columna(
        df, "SKU", "ARTICULO"
    )

    cant = encontrar_columna(
        df, "SELECCION"
    )

    desc = encontrar_columna(
        df, "DESCRIPCION",
        requerida=False
    )

    lote = next(
        (
            c for c in df.columns
            if "LOTE" in c and "PROG" in c
        ),
        None
    )

    trabajo = pd.DataFrame({
        "SKU": df[sku].astype(str).str.strip(),

        "SKU_Clean": df[sku].map(limpiar_sku),

        "Descripcion": (
            df[desc].fillna("")
            if desc
            else df[sku].fillna("")
        ),

        "CANTIDAD SOLICITADA": pd.to_numeric(
            df[cant]
            .astype(str)
            .str.replace(",", ".", regex=False),
            errors="coerce"
        ).fillna(0),

        "SECUENCIA_LOTE": (
            df[lote].map(extraer_secuencia_lote)
            if lote
            else None
        )
    })

    trabajo = trabajo[
        trabajo["SKU_Clean"] != ""
    ]

    resumen = trabajo.groupby(
        "SKU_Clean",
        as_index=False
    ).agg({
        "SKU": "first",
        "Descripcion": "first",
        "CANTIDAD SOLICITADA": "sum",
        "SECUENCIA_LOTE": "min"
    })

    return resumen, lote is not None
