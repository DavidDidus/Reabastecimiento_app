
import re
import unicodedata
import pandas as pd


def normalizar_columna(valor):
    texto = unicodedata.normalize(
        "NFKD",
        str(valor).strip()
    )

    return "".join(
        c for c in texto
        if not unicodedata.combining(c)
    ).upper()


def limpiar_sku(sku):
    if pd.isna(sku):
        return ""

    val = str(sku).strip()

    if re.fullmatch(r"[0-9]+(?:\.0+)?", val):
        return (
            str(int(float(val)))
            if "." in val
            else (val.lstrip("0") or "0")
        )

    return val.upper()


def extraer_secuencia_lote(lote):
    if pd.isna(lote):
        return None

    val = str(lote).strip()

    if not val:
        return None

    tramo = val.split("-")[-1].strip()

    match = re.search(r"(\d+)$", tramo)

    if match:
        return int(match.group(1))

    bloques = re.findall(r"\d+", val)

    return int(bloques[-1]) if bloques else None


def encontrar_columna(df, *terminos, requerida=True):
    for termino in terminos:
        for col in df.columns:
            if termino in col:
                return col

    if requerida:
        raise ValueError(
            "Falta columna con alguno de: "
            f"{', '.join(terminos)}. "
            f"Disponibles: {list(df.columns)}"
        )

    return None
