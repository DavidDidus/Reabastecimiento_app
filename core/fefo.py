
"""Asignación FEFO por SKU/LPN, sin cambiar las columnas de la hoja."""

import pandas as pd

from utils.archivos import normalizar_columnas
from utils.normalizacion import limpiar_sku
from core.ubicaciones import FALLBACK


AREAS_ORIGEN = {"ALMAC", "ALMPIC"}


def detectar_formato(df):

    cols = set(normalizar_columnas(df).columns)

    vida = {
        "ARTICULO",
        "AREA",
        "UBICACION",
        "CANTIDAD",
        "LPN",
        "FECHA DE CADUCIDAD",
        "ESTADO DE INVENTARIO"
    }

    cuad = {
        "ARTICULO",
        "AREA",
        "UBICACION"
    }

    if vida <= cols and "VIDA UTIL" in cols:
        return "vida_util"

    if cuad <= cols:
        return "cuadratura"

    raise ValueError(
        "Archivo de inventario no reconocido: "
        "faltan columnas de artículo, área o ubicación."
    )


def preparar_lpn(df):

    d = normalizar_columnas(df)

    d["SKU_Clean"] = d["ARTICULO"].map(limpiar_sku)

    d["AREA_NORM"] = (
        d["AREA"].fillna("").str.strip().str.upper()
    )

    d["UBICACION"] = (
        d["UBICACION"].fillna("").str.strip()
    )

    d["UBI_NORM"] = (
        d["UBICACION"]
        .str.upper()
        .str.replace(r"[^A-Z0-9]", "", regex=True)
    )

    d["ESTADO"] = (
        d["ESTADO DE INVENTARIO"]
        .fillna("")
        .str.strip()
        .str.upper()
    )

    d["CANTIDAD_NUM"] = pd.to_numeric(
        d["CANTIDAD"].str.replace(
            ",", ".", regex=False
        ),
        errors="coerce"
    ).fillna(0)

    d["CADUCIDAD"] = pd.to_datetime(
        d["FECHA DE CADUCIDAD"],
        dayfirst=True,
        errors="coerce"
    )

    d["LPN"] = d["LPN"].fillna("").str.strip()

    # Solo inventario elegible para reabasto.
    d = d[
        (d["SKU_Clean"] != "")
        & (d["UBICACION"] != "")
        & (d["LPN"] != "")
        & (d["ESTADO"] == "D")
        & (d["CANTIDAD_NUM"] > 0)
        & d["CADUCIDAD"].notna()
        & (
            d["CADUCIDAD"].dt.normalize()
            >= pd.Timestamp.today().normalize()
        )
        & (
            d["AREA_NORM"].isin(AREAS_ORIGEN)
            | d["UBI_NORM"].isin(FALLBACK)
        )
    ].copy()

    d["PRIORIDAD"] = (
        ~d["AREA_NORM"].isin(AREAS_ORIGEN)
    ).astype(int)

    # Consolidar registros de un mismo LPN.
    return d.groupby(
        ["SKU_Clean", "UBICACION", "LPN"],
        as_index=False
    ).agg(
        CANTIDAD_NUM=("CANTIDAD_NUM", "sum"),
        CADUCIDAD=("CADUCIDAD", "min"),
        PRIORIDAD=("PRIORIDAD", "min")
    )


def asignar_fefo(resumen, df_vida, posiciones, surtido):

    candidatos = preparar_lpn(df_vida)

    grupos = {
        sku: g.sort_values([
            "CADUCIDAD",
            "PRIORIDAD",
            "UBICACION",
            "LPN"
        ])
        for sku, g in candidatos.groupby("SKU_Clean")
    }

    filas = []
    faltantes = []

    for _, pedido in resumen.iterrows():

        sku = pedido["SKU_Clean"]

        destino = (
            posiciones.get(sku)
            or surtido.get(sku)
            or "Sin Ubicación Surtido"
        )

        restante = float(
            pedido["CANTIDAD SOLICITADA"]
        )

        solicitado = restante

        for _, pallet in grupos.get(
            sku, pd.DataFrame()
        ).iterrows():

            if restante <= 0:
                break

            asignado = min(
                restante,
                float(pallet["CANTIDAD_NUM"])
            )

            fila = pedido.to_dict()

            fila.update({
                "ALMACENAMIENTO": pallet["UBICACION"],
                "SURTIDO": destino,
                "CANTIDAD SOLICITADA": asignado
            })

            filas.append(fila)

            restante -= asignado

        if restante > 0:

            # Nunca asignar cajas sin stock a un origen ficticio.
            fila = pedido.to_dict()

            fila.update({
                "ALMACENAMIENTO": "Sin pallet en Almacen",
                "SURTIDO": destino,
                "CANTIDAD SOLICITADA": restante
            })

            filas.append(fila)

            faltantes.append({
                "SKU": pedido["SKU"],
                "Solicitado": solicitado,
                "Sin asignar": restante
            })

    return pd.DataFrame(filas), faltantes
