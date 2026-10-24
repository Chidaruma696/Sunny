# Decisiones

## 2026-10-24 · Qué es Sunny y qué no

Hermana pequeña de Cirno, para la misma oficina: la gente sabe qué quiere ver resaltado en un Excel pero pelearse con el formato condicional de Excel les lleva la tarde. Sunny recibe el archivo y una frase («rojo donde Estado sea PENDIENTE») y lo deja hecho. Mismas piezas que Cirno (Python, PySide6, openpyxl, PyInstaller, Inno Setup) y la misma estética Komi, con paleta de sol porque Sunny Milk manipula la luz.

Se queda fuera, a propósito: ordenar, borrar, fórmulas, tablas dinámicas. Todo eso cambia los datos; Sunny solo cambia cómo se ven. Así el riesgo es cero (una copia con colores) y la frase que escribe la gente cabe en un abanico de acciones corto que un esquema puede acotar.

## 2026-10-24 · Un modelo para entender, pero solo ve las cabeceras

Para gente de oficina «escribe lo que quieras» es la gracia; una sintaxis propia de reglas sería otra cosa que aprender. Por eso la orden la entiende Claude (API de Anthropic). Lo que viaja: nombre de la hoja, cuántas filas, cabeceras de las columnas y el tipo de cada una (número, fecha, texto), más la frase. Lo que NO viaja: ningún valor de celda. Las reglas vuelven en JSON con esquema fijo (salida estructurada, `output_config.format`), así nunca hay prosa que parsear, y `rules.py` las valida igualmente: una columna inventada o un color raro se descarta y se avisa, sin perder las demás.

El modelo por defecto es `claude-opus-5-5` con esfuerzo bajo (la tarea es chica); se puede cambiar en Ajustes a Sonnet o Haiku para abaratar. La clave se guarda en el equipo (QSettings, como Cirno) o viene de `ANTHROPIC_API_KEY`. Las reglas se pueden guardar como JSON y volver a aplicar con `--reglas` sin modelo ni red: el mes que viene la misma hoja se formatea igual sin gastar.

## 2026-10-24 · Formato condicional de verdad, en una copia

Pintar celdas con openpyxl era lo fácil, pero deja un archivo muerto: cambias un dato y el color se queda. Sunny escribe reglas de formato condicional de Excel (`FormulaRule`), que siguen vivas y que cualquiera puede ver y quitar desde Excel. Detalles que costaron:

- Las fórmulas van relativas a la primera fila de datos y con la columna fijada (`$C2="PENDIENTE"`): así la misma regla vale para pintar la celda (rango de una columna) o la fila entera (rango de toda la tabla).
- Las comparaciones numéricas van envueltas en `ISNUMBER`: en Excel cualquier texto es «mayor» que cualquier número y sin la guarda las celdas con texto se pintarían.
- Las fechas van como `DATE(a,m,d)`, los textos entre comillas con las comillas dobladas, y «contiene» usa `SEARCH` (sin distinguir mayúsculas) o `FIND` (distinguiendo).
- La vista previa cuenta en Python con la misma semántica que las fórmulas, para que el «37 filas» que ve el usuario sea lo que Excel pinta. Está probado en `tests/`.
- Siempre se escribe en una copia (`<nombre> - Sunny.xlsx`); escribir sobre el original está prohibido en código.

Pendiente de decidir: un modo sin modelo (sintaxis chica de reglas) para quien no quiera clave, y si las reglas de la misma columna que se pisan deben llevar `stopIfTrue`.
