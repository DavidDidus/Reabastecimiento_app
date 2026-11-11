
from pathlib import Path
from io import BytesIO

import pandas as pd

from utils.normalizacion import normalizar_columna


def cargar_dataframe(archivo, nombre=None):

    if isinstance(archivo, (str, Path)):
        nombre = nombre or str(archivo)
        contenido = Path(archivo).read_bytes()

    else:
        nombre = nombre or getattr(
            archivo,
            "name",
            "archivo.csv"
        )

        contenido = (
            archivo.getvalue()
            if hasattr(archivo, "getvalue")
            else archivo.read()
        )

    if str(nombre).lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(
            BytesIO(contenido),
            dtype=str
        )

    errores = []

    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        for sep in (";", ",", "\t"):
            try:
                df = pd.read_csv(
                    BytesIO(contenido),
                    sep=sep,
                    encoding=encoding,
                    dtype=str
                )

                if len(df.columns) > 1:
                    return df

            except (
                UnicodeError,
                pd.errors.ParserError
            ) as exc:
                errores.append(str(exc))

    raise ValueError(
        f"No se pudo interpretar el CSV {nombre}. "
        "Verifica separador y codificación."
    )


def normalizar_columnas(df):
    df = df.copy()

    df.columns = [
        normalizar_columna(c)
        for c in df.columns
    ]

    return df
