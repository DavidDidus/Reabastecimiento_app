
from datetime import datetime
from html import escape

import pandas as pd


def generar_html(df):

    filas = []

    for i, (_, r) in enumerate(df.iterrows(), 1):

        def cel(c):
            v = r[c]
            return escape(str(v)) if pd.notna(v) else "-"

        filas.append(
            f"""
            <tr>
                <td>{i}</td>
                <td>{cel('SKU')}</td>
                <td>{cel('Descripción del Producto')}</td>
                <td>{cel('Ubicación Origen (ALMACÉN)')}</td>
                <td>{cel('Ubicación Destino (SURTIDO)')}</td>
                <td>{cel('Secuencia Camión')}</td>
                <td>{cel('Cant. Solicitada')}</td>
                <td></td>
            </tr>
            """
        )

    fecha = datetime.now().strftime(
        "%d/%m/%Y %H:%M hrs"
    )

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="utf-8">

        <style>
            body {{
                font-family: Arial, sans-serif;
                color: #0f172a;
            }}

            .card {{
                padding: 16px;
                border: 2px solid #1e293b;
                border-radius: 8px;
            }}

            h2 {{
                margin: 0 0 10px;
            }}

            table {{
                border-collapse: collapse;
                width: 100%;
                margin-top: 12px;
            }}

            th {{
                background: #1e293b;
                color: white;
            }}

            th, td {{
                border: 1px solid #94a3b8;
                padding: 7px;
                font-size: 12px;
            }}

            td:nth-child(4) {{
                color: #1e3a8a;
                font-weight: bold;
            }}

            td:nth-child(5) {{
                color: #065f46;
                font-weight: bold;
            }}

            .controls {{
                text-align: center;
                margin: 15px;
            }}

            button {{
                background: #2563eb;
                color: white;
                border: 0;
                padding: 12px 24px;
                border-radius: 6px;
                cursor: pointer;
            }}

            @media print {{
                .controls {{
                    display: none;
                }}

                .card {{
                    border: 0;
                    padding: 0;
                }}

                @page {{
                    size: landscape;
                    margin: 10mm;
                }}
            }}
        </style>
    </head>

    <body>

        <div class="card">

            <h2>Reabasto / Hoja de Ruta</h2>

            <div>
                Fecha Emisión: {fecha}
                | Total SKUs a mover: {df["SKU"].nunique()}
                | Filas: {len(df)}
            </div>

            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>SKU</th>
                        <th>Descripción Producto</th>
                        <th>Origen (Almacén)</th>
                        <th>Destino (Surtido)</th>
                        <th>Secuencia</th>
                        <th>Cajas</th>
                        <th>Check ✓</th>
                    </tr>
                </thead>

                <tbody>
                    {''.join(filas)}
                </tbody>
            </table>

        </div>

        <div class="controls">
            <button onclick="window.print()">
                🖨️ Imprimir Hoja de Ruta
            </button>
        </div>

    </body>
    </html>
    """
