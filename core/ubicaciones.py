
from pathlib import Path

from utils.archivos import (
    cargar_dataframe,
    normalizar_columnas
)

from utils.normalizacion import (
    limpiar_sku,
    encontrar_columna
)


FALLBACK = {
    "REBA01",
    "MIX01",
    *(f"STREC{i:02d}" for i in range(1, 6))
}


def cargar_posiciones(ruta):

    if not Path(ruta).exists():
        raise FileNotFoundError(
            f"No existe el maestro de posiciones: {ruta}"
        )

    df = normalizar_columnas(
        cargar_dataframe(ruta)
    )

    sku = encontrar_columna(
        df, "ARTICULO", "SKU"
    )

    ubi = encontrar_columna(
        df, "UBICAC"
    )

    df["SKU_Clean"] = df[sku].map(limpiar_sku)

    df = df.dropna(subset=[ubi])

    df = df[
        (df["SKU_Clean"] != "")
        & (df[ubi].astype(str).str.strip() != "")
    ]

    return (
        df.drop_duplicates("SKU_Clean")
        .set_index("SKU_Clean")[ubi]
        .to_dict()
    )


def mapas_cuadratura(df):

    df = normalizar_columnas(df)

    art = encontrar_columna(
        df, "ARTICULO", "SKU"
    )

    area = encontrar_columna(
        df, "AREA"
    )

    ubi = encontrar_columna(
        df, "UBICAC"
    )

    df["SKU_Clean"] = df[art].map(limpiar_sku)

    df["AREA_NORM"] = (
        df[area]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["UBI_NORM"] = (
        df[ubi]
        .fillna("")
        .astype(str)
        .str.upper()
        .str.replace(
            r"[^A-Z0-9]",
            "",
            regex=True
        )
    )

    df = df[
        (df["SKU_Clean"] != "")
        & df[ubi].notna()
        & (df[ubi].astype(str).str.strip() != "")
    ]

    def mapa(filtro):
        return (
            df.loc[filtro]
            .drop_duplicates("SKU_Clean")
            .set_index("SKU_Clean")[ubi]
            .to_dict()
        )

    return (
        mapa(
            df["AREA_NORM"].isin([
                "ALMAC",
                "ALMPIC"
            ])
        ),

        mapa(
            df["UBI_NORM"].isin(FALLBACK)
        ),

        mapa(
            df["AREA_NORM"] == "SURTID"
        )
    )
