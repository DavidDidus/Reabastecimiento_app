
from datetime import datetime
from html import escape
import json

import pandas as pd


def generar_html(df):

    filas = []

    for i, (_, r) in enumerate(df.iterrows(), 1):

        def cel(columna):
            valor = r[columna]
            return escape(str(valor)) if pd.notna(valor) else "-"

        filas.append(f"""
            <tr>
                <td class="numero">{i}</td>
                <td class="sku">{cel('SKU')}</td>
                <td>{cel('Descripción del Producto')}</td>
                <td class="origen">
                    {cel('Ubicación Origen (ALMACÉN)')}
                </td>
                <td class="destino">
                    {cel('Ubicación Destino (SURTIDO)')}
                </td>
                <td class="centrado">
                    {cel('Secuencia Camión')}
                </td>
                <td class="cantidad">
                    {cel('Cant. Solicitada')}
                </td>
                <td class="check"></td>
            </tr>
        """)

    fecha = datetime.now().strftime("%d/%m/%Y %H:%M hrs")

    total_skus = df["SKU"].nunique()
    total_filas = len(df)

    return f"""
    <!DOCTYPE html>
    <html lang="es">

    <head>
        <meta charset="utf-8">

        <script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.6/Sortable.min.js"></script>

        <style>
            * {{
                box-sizing: border-box;
            }}

            body {{
                font-family: Arial, sans-serif;
                color: #0f172a;
                margin: 0;
                padding: 12px;
                background: #ffffff;
            }}

            .report-card {{
                padding: 16px;
                border: 2px solid #1e293b;
                border-radius: 8px;
            }}

            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
            }}

            h2 {{
                margin: 0;
                font-size: 22px;
                text-transform: uppercase;
            }}

            .fecha {{
                font-size: 12px;
            }}

            .resumen {{
                font-size: 13px;
                color: #475569;
                margin-bottom: 12px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
            }}

            th {{
                background: #1e293b;
                color: white;
                border: 1px solid #1e293b;
                padding: 5px 4px;
                font-size: 12px;
                text-transform: uppercase;
            }}

            td {{
                border: 1px solid #94a3b8;
                padding: 4px 5px;
                font-size: 13px;
                line-height: 1.15;
            }}

            tbody tr {{
                cursor: grab;
                background: white;
            }}

            tbody tr:hover {{
                background: #eff6ff;
            }}

            tbody tr:active {{
                cursor: grabbing;
            }}

            .sortable-ghost {{
                opacity: 0.35;
                background: #bfdbfe !important;
            }}

            .sortable-chosen {{
                background: #dbeafe !important;
            }}

            .numero,
            .centrado,
            .cantidad,
            .check {{
                text-align: center;
            }}

            .sku {{
                font-family: monospace;
                font-weight: bold;
            }}

            .origen {{
                color: #1e3a8a;
                font-weight: bold;
                text-align: center;
            }}

            .destino {{
                color: #065f46;
                font-weight: bold;
                text-align: center;
            }}

            .cantidad {{
                font-size: 16px;
                font-weight: bold;
            }}

            .check {{
                width: 80px;
            }}

            .controls {{
                display: flex;
                justify-content: center;
                gap: 12px;
                margin-top: 16px;
                flex-wrap: wrap;
            }}

            button {{
                border: none;
                border-radius: 6px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: bold;
                cursor: pointer;
            }}

            .print-btn {{
                background: #2563eb;
                color: white;
            }}

            .reset-btn {{
                background: #e2e8f0;
                color: #0f172a;
            }}

            .ayuda {{
                font-size: 12px;
                color: #64748b;
                text-align: center;
                margin-top: 10px;
            }}

            @media print {{
                @page {{
                    size: landscape;
                    margin: 10mm;
                }}

                body {{
                    padding: 0;
                }}

                .report-card {{
                    border: none;
                    padding: 0;
                }}

                .controls,
                .ayuda {{
                    display: none !important;
                }}

                tbody tr {{
                    cursor: default;
                    break-inside: avoid;
                    page-break-inside: avoid;
                }}

                tbody tr:hover {{
                    background: white;
                }}

                thead {{
                    display: table-header-group;
                }}

                th {{
                    print-color-adjust: exact;
                    -webkit-print-color-adjust: exact;
                }}
            }}
        </style>
    </head>

    <body>

        <div class="report-card">

            <div class="header">
                <h2>Reabasto / Hoja de Ruta</h2>

                <div class="fecha">
                    <strong>Fecha Emisión:</strong> {fecha}
                </div>
            </div>

            <div class="resumen">
                <strong>Total SKUs a Mover:</strong> {total_skus}
                &nbsp; | &nbsp;
                <strong>Total Filas:</strong> {total_filas}
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

                <tbody id="tabla-reabasto">
                    {''.join(filas)}
                </tbody>
            </table>

        </div>

        <div class="controls">

            <button
                class="print-btn"
                onclick="window.print()"
            >
                🖨️ Imprimir Hoja de Ruta
            </button>

            <button
                class="reset-btn"
                onclick="restablecerOrden()"
            >
                ↺ Restablecer Orden
            </button>

        </div>

        <div class="ayuda">
            Arrastra cualquier fila para cambiar su posición.
            La numeración se actualizará automáticamente.
        </div>

        <script>

            const tabla = document.getElementById(
                "tabla-reabasto"
            );

            // Guardar el orden inicial de las filas.
            const filasOriginales = Array.from(
                tabla.querySelectorAll("tr")
            );

            function actualizarNumeracion() {{

                const filas = tabla.querySelectorAll("tr");

                filas.forEach((fila, indice) => {{

                    const celdaNumero = fila.querySelector(
                        ".numero"
                    );

                    if (celdaNumero) {{
                        celdaNumero.textContent = indice + 1;
                    }}

                }});

            }}

            function restablecerOrden() {{

                filasOriginales.forEach(fila => {{
                    tabla.appendChild(fila);
                }});

                actualizarNumeracion();

            }}

            if (typeof Sortable !== "undefined") {{

                new Sortable(tabla, {{

                    animation: 180,

                    ghostClass: "sortable-ghost",

                    chosenClass: "sortable-chosen",

                    onEnd: function() {{
                        actualizarNumeracion();
                    }}

                }});

            }} else {{

                document.querySelector(".ayuda").textContent =
                    "No se pudo cargar la función de arrastre. " +
                    "Verifica la conexión a Internet.";

            }}

        </script>

    </body>
    </html>
    """
