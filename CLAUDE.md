# CLAUDE.md — Inventario Pymes (Licorería y Abarrotes Botellas)

## Proyecto

Sistema web de administración de inventario con alertas para Licorería y Abarrotes Botellas.
Locales: Osorno, Temuco y Valdivia.

- Código: NOV-001
- Patrocinador / cliente: Licorería y Abarrotes Botellas
- Product Owner: Anastasia Anyelina Fuentes Cuevas
- Scrum Master: José Luis Oporto Calisto
- Equipo de desarrollo: Antonella Pezzopane, Benjamín Ceballos, Felipe Melo
- Inicio: 06-11-2026. Término estimado: 11-12-2026 (defensa 11-12).
- Contexto: trabajo de la 3ra Evaluación (metodología Scrum, asignatura de INACAP).

## Stack

- Python + Flask
- MySQL
- Exportación a Excel con tildes y `ñ` (UTF-8 / BOM según corresponda)

## Alcance

Incluido:
- Registro, edición y baja de productos (con confirmación) por local.
- Entradas y salidas con fecha. Salidas mayores al stock se rechazan. Stock nunca negativo.
- Alertas: filas en rojo y aviso en pantalla cuando stock ≤ mínimo.
- Historial de movimientos por producto (más reciente primero).
- Lista de compras por local con cantidad sugerida para llegar al mínimo.
- Exportación del inventario a Excel.
- Búsqueda por nombre o categoría (HU12, MoSCoW: Could).

Excluido:
- Ventas en caja, boletas, integración con SII.
- Facturación y contabilidad.
- Venta online y pagos en línea.
- Aplicación móvil.
- Hardware, redes, instalación de servidor.

## Historias de usuario

| ID   | Historia                                                    | Pts | MoSCoW | Depende de |
|------|-------------------------------------------------------------|-----|--------|------------|
| HU01 | Registrar producto con stock y stock mínimo                 | 3   | Must   | —          |
| HU02 | Editar producto (nombre, categoría, stock mínimo)           | 3   | Must   | HU01       |
| HU03 | Registrar entrada con fecha                                 | 5   | Must   | HU01       |
| HU04 | Registrar salida con fecha                                  | 3   | Must   | HU01       |
| HU05 | Rechazar salida mayor al stock                              | 3   | Must   | HU04       |
| HU06 | Confirmar antes de dar de baja                              | 3   | Should | HU01       |
| HU07 | Ver productos y movimientos por local                       | 5   | Must   | HU01       |
| HU08 | Alertas de stock mínimo (aviso y filas en rojo)             | 5   | Must   | HU03, HU04 |
| HU09 | Historial de movimientos por producto                       | 3   | Should | HU03, HU04 |
| HU10 | Lista de compras                                            | 3   | Must   | HU08       |
| HU11 | Exportar inventario a Excel                                 | 3   | Should | HU01       |
| HU12 | Buscar por nombre o categoría                               | 5   | Could  | HU01       |

Fuente: `OneDrive_2026-11-20/3ra Evaluacion/Documentos/06_Product_Backlog.xlsx`.

## Reglas de negocio

- Cantidades de stock y stock mínimo: enteros ≥ 0 (HU01). Cantidad de movimiento: entero > 0 (HU03, HU04).
- Campos obligatorios: nombre, categoría, local, stock y stock mínimo. No se guarda si falta uno.
- Toda entrada y salida guarda fecha y local.
- Salida > stock disponible: no se registra y se muestra el stock disponible.
- Baja de producto: solo tras confirmación. Cancelar no cambia nada.
- Alerta: stock ≤ mínimo. El aviso se actualiza después de cada movimiento.
- Lista de compras: solo productos en alerta. Muestra local y cantidad sugerida (mínimo − stock).

## Hitos

| Fecha      | Hito                                                       |
|------------|------------------------------------------------------------|
| 13-11-2026 | Interfaces de productos, entradas y salidas (Sprint 1)     |
| 20-11-2026 | BD, alertas, lista de compras (Sprint 2)                   |
| 27-11-2026 | Datos reales de los 3 locales. Pruebas de entradas, salidas y alertas |
| 11-12-2026 | Entrega e implementación en los 3 locales                  |

Entregas de la 3ra Evaluación:
- Nota 3: acta, planning, product backlog (06-11). Daily, Sprint 1 y Review (13-11). Daily, Sprint 2 y Review (20-11). Retrospectiva, scrumboard y tablero activo (27-11).
- Nota 4: defensa (11-12).

## Documentos Scrum

Ubicación: `OneDrive_2026-11-20/3ra Evaluacion/Documentos/`

- `01_Acta_Constitucion_Proyecto.docx`
- `02_Daily_Scrum.docx` (formato vacío)
- `03_Sprint_Planning.docx` (Sprint 1 y 2)
- `04_Sprint_Review.docx` (formato vacío)
- `05_Sprint_Retrospectiva.docx` (formato vacío)
- `06_Product_Backlog.xlsx` (fuente de verdad de HU)
- `07_Scrumboard.xlsx` (formato vacío)
- `08_Tablero_Activo.xlsx` (formato vacío)

La nota de evaluación es individual; la asistencia descuenta 0,5.

## Estructura del repositorio

- `CLAUDE.md`: este archivo.
- `OneDrive_2026-11-20.zip`: archivo original.
- `OneDrive_2026-11-20/`: contenido extraído del zip. Solo documentación Scrum. Tratar como referencia, no editar salvo que se pida.
- `app.py`: rutas Flask (HU01 a HU12).
- `db.py`: acceso a MySQL, validaciones y reglas de stock.
- `schema.sql`: tablas `locales`, `productos`, `movimientos` y datos de los 3 locales.
- `templates/`: vistas HTML.
- `tests/`: pruebas con pytest. Usan la base `botellas_test`, nunca `botellas`.
- `requirements.txt`: dependencias.

Ejecutar:
```
pip install -r requirements.txt
export DB_USER=... DB_PASSWORD=...   # credenciales MySQL, no commitear
flask --app app init-db
flask --app app run --debug
pytest -q tests
```

## Convenciones

- Idioma de la interfaz, comentarios y documentación: español.
- Nombres de código en español o inglés de forma consistente. Elegir uno al inicio y mantenerlo.
- Validar siempre en servidor (salidas > stock, campos obligatorios, enteros). La validación en cliente es solo ayuda visual.
- Toda escritura a la base de datos que cambie stock debe ser atómica (una transacción con su movimiento).
- No borrar productos de la base de datos: la baja es lógica salvo que se pida otra cosa. Verificar con el PO antes de cambiar esto.
- Nunca comitear credenciales de MySQL. Usar variables de entorno o archivo de configuración ignorado por git.

## Pruebas

- Probar entradas, salidas, rechazo de salida mayor al stock, alertas y lista de compras en los 3 locales.
- Registro de pruebas requerido por el Sprint Planning (criterio de término de cada HU).
