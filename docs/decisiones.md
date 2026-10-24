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

Pendiente de decidir: si las reglas de la misma columna que se pisan deben llevar `stopIfTrue`.

## 2026-10-24 · Sin clave: el español se entiende aquí (0.2.0)

La 0.1.0 pedía una clave de la API de Anthropic nada más abrirla, y eso se cayó a la primera: «¿cómo que pide clave? sin nada de eso». Tenía razón: para la gente de oficina una clave, una cuenta y un cobro por uso son tres barreras, y el abanico de órdenes que Sunny acepta es lo bastante corto como para entenderlo sin modelo. Así que `parser.py` entiende la frase en español por sí solo y Claude pasa a ser opcional, apagado por defecto (Ajustes → «Usar Claude», o `--claude` en la terminal).

Cómo entiende:

- **Trozos.** Separa por `;`, salto de línea, punto, «pero», «mientras que». Una coma o una «y» separa dos órdenes solo cuando a cada lado hay una palabra de estilo propia; si no, pertenece a la orden («entre 1 y 5», «PAGADO o CANCELADO»).
- **Estilo.** Colores en español con sus plurales y femeninos (rojo, verde, amarillo, azul, naranja, gris, morado/lila/violeta), cada uno con el relleno y la letra oscura de los preajustes de Excel; `#hex` tal cual; negrita, cursiva, tachado. «Letra roja» pinta solo la letra.
- **Alcance.** «fila», «renglón», «línea», «registro» → la fila entera; «celda» o nada → la celda. Una orden sin columna ni alcance («…, verde las PAGADO») hereda el alcance de la anterior: es una continuación.
- **Columna.** La cabecera que se nombre, sin tildes ni mayúsculas, y tolerando singular/plural («Importes» para «Importe»). Si no se nombra ninguna, se busca el valor dicho en un índice local de valores de texto por columna («rojo los PENDIENTE» → Estado); si está en varias columnas, se pide que la nombre; si en ninguna, se dice qué columnas hay. El índice se calcula en la máquina y nunca sale de ella.
- **Condición.** sea / es / igual a (y listas con «o» → `in`), no sea / distinto de, mayor que / más de / superior a / >, mayor o igual / a partir de / al menos, menor que / menos de / <, menor o igual / hasta / como máximo, entre X y Y, contenga / incluya / diga, no contenga, empiece por, termine en, vacío / en blanco / sin X / que no tenga X, con dato / no vacío, repetido / duplicado. Sin operador, el resto de la frase es el valor («Estado PENDIENTE»). Números: «50 mil», «1.5 millones», «$12,000.50», «50.000»; fechas: `31/01/2026` y `2026-01-31`.
- **Lo que no entiende lo dice**, con la frase citada y el motivo («no dice qué color poner», «no sé qué columna mirar; nómbrala (…)»), y sigue con las demás. Nunca adivina una regla.

Primera frase real que falló (0.2.1): «pinta todo lo que diga vocho de verde». «Diga» se entendía bien como *contiene*, pero al no nombrar columna se buscaba «vocho» como valor exacto de celda, y en la hoja va dentro de textos más largos («VW VOCHO 2001»). Ahora, con contiene / empieza / termina, la columna se deduce buscando el trozo dentro de los valores, y el índice de valores ya no salta las columnas de texto libre (antes, más de 500 valores distintos = fuera), que son justo donde se busca por trozos.

## 2026-10-24 · Claude fuera del todo (0.3.0)

En la 0.2.0 Claude quedó como opción apagada, pero seguía asomando: una casilla en Ajustes, una clave que guardar, `--claude` en la terminal, una dependencia de 20 MB y párrafos en el README. Para la gente a la que va dirigida Sunny todo eso es ruido y una pregunta que no quieren contestar. Se quita entero: `planner.py`, el SDK, los ajustes y las menciones. Lo que entiende Sunny lo entiende el intérprete, y cada frase que falle se arregla ahí. Lo de arriba sobre el planificador queda como historia.

## 2026-10-24 · Actualizarse desde GitHub (0.3.0)

Las correcciones del intérprete van a salir a menudo (cada frase de oficina que no entienda es una), y pedirle a la gente que vuelva a bajar un instalador no funciona. Sunny se actualiza sola desde las releases del repositorio, sin servidor propio:

- Al abrir (y con «Buscar actualización» abajo), `updater.py` pide `/releases/latest` a la API pública de GitHub con la biblioteca estándar, sin cuenta ni token; 60 consultas por hora y por IP sobran. Compara la etiqueta con la versión como números, así `0.10` gana a `0.9`.
- Solo cuenta un activo `*-setup.exe` servido por GitHub (`github.com` u `objects.githubusercontent.com`) por HTTPS. Junto a él, `build.ps1` publica `*-setup.exe.sha256`, y la descarga se comprueba contra esa huella antes de instalar; si no coincide, se borra y no se instala. No es una firma (quien pueda publicar en el repo puede publicar las dos cosas), pero sí garantiza que lo bajado es lo que se subió.
- Nunca se instala sin pulsar ACTUALIZAR y confirmar. Entonces el instalador se lanza con `/SILENT /SP- /SUPPRESSMSGBOXES /NORESTART /RELAUNCH` y Sunny se cierra para que puedan reemplazarse sus archivos. `/RELAUNCH` es un parámetro propio: la entrada `[Run]` normal lleva `skipifsilent` y en silencio no abriría nada, así que hay otra entrada con `Check: Relaunch` ([Code]) que solo corre con ese parámetro.
- Sin red o con GitHub caído, la comprobación de arranque calla; la de a mano avisa. Se puede apagar en Ajustes.
- En desarrollo (sin PyInstaller) el botón abre la página de la release en el navegador en vez de instalar.

Las descripciones que ve el usuario las genera `describe` a partir de la regla («Filas con Estado igual a PENDIENTE, en rojo»), así son iguales vengan del intérprete, de Claude o de un JSON guardado. Probado con 23 pruebas de frases, además de las de reglas y libro.
