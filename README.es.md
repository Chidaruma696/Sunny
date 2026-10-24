[🇬🇧 English](README.md)

<div align="center">
  <br/>
  <img src="sunny/assets/sunny.png" width="180" alt="Icono de Sunny" />

# Sunny

**サニー · Formato condicional para Excel, dicho en palabras.**

<br/>

![Windows 10/11](https://img.shields.io/badge/windows-10%2F11%20x64-0078d4?style=for-the-badge&logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/python-3.11%2B-3776ab?style=for-the-badge&logo=python&logoColor=white)
![Qt](https://img.shields.io/badge/qt-pyside6-41cd52?style=for-the-badge&logo=qt&logoColor=white)
![Licencia Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-1b150d?style=for-the-badge)

<br/>

[![Descargar instalador](https://img.shields.io/github/v/release/Chidaruma696/Sunny?label=%E2%AC%87%EF%B8%8F%20DESCARGAR%20INSTALADOR&style=for-the-badge&color=f0a020)](https://github.com/Chidaruma696/Sunny/releases/latest)

<br/>

*Arrastras el Excel, dices qué quieres resaltar, revisas lo que entendió, aplicas · el original no se toca*

</div>

---

> [!IMPORTANT]
> **Nada sale de tu máquina.** Sunny entiende las órdenes en español por sí sola, sin internet, sin cuenta y sin
> clave. Opcionalmente puede preguntarle a Claude (con tu propia clave de API, apagado por defecto); incluso entonces
> solo manda las cabeceras de las columnas, su tipo y tu frase, nunca un valor de celda. El repositorio ignora
> `*.xlsx` para que los archivos de la oficina nunca acaben en git por accidente.

<br/>

## 📲 Descargar

1. Abre la [última release](https://github.com/Chidaruma696/Sunny/releases/latest) y baja `Sunny-x.y.z-setup.exe`.
2. Ejecútalo. Se instala para tu usuario sin pedir permisos de administrador. No hace falta Python ni nada más.
3. Abre Sunny desde el menú Inicio. Ya está: no hay nada que configurar.

<br/>

## ☀️ Qué hace

| Tú escribes | Sunny entiende | Excel recibe |
| --- | --- | --- |
| *«Pinta de rojo las filas donde Estado sea PENDIENTE, de verde donde sea PAGADO, y en negrita los importes mayores de 50 mil»* | Tres reglas, cada una con la columna que mira, la condición, el estilo y cuántas celdas tocaría ahora mismo | Tres reglas de **formato condicional** de verdad, escritas en una copia `<nombre> - Sunny.xlsx` |

Como el resultado es formato condicional de Excel (no celdas pintadas), sigue funcionando cuando cambian los datos, y el archivo sigue siendo un libro normal que cualquiera abre y edita.

Lo que una regla puede decir: igual, distinto, mayor / menor / entre (números y fechas), contiene, empieza o termina por, está vacío o no, está en una lista, está repetido en su columna. Lo que puede pintar: color de fondo, color de letra, negrita, cursiva, tachado; la celda que mira o toda la fila.

Antes de escribir nada ves cada regla como una línea («Filas con Estado PENDIENTE en rojo · 37 filas»), puedes desmarcar las que no quieras y guardar el conjunto como JSON para reutilizarlo el mes que viene sin volver a preguntar al modelo.

<br/>

## ⚙️ Cómo funciona

1. `workbook.py` lee la forma de la hoja: cabeceras, tipo de cada columna (número, fecha, texto), cuántas filas, y qué valores de texto viven en qué columna.
2. `parser.py` entiende la frase en español, sin modelo: la parte en órdenes (comas, «y», «pero», «;»), lee las palabras de estilo (*rojo, verde, amarillo, azul, naranja, gris, morado, negrita, cursiva, tachado*, o un `#hex`), el alcance (*fila* o *celda*), la columna (una cabecera que nombres, en singular o plural, o la columna que contiene el valor que dices: *«rojo los PENDIENTE»* encuentra *Estado* sola) y la condición (*sea, no sea, mayor de, más de, menor que, entre, contenga, empiece por, termine en, vacío, sin, repetido, X o Y*). Los números entienden *50 mil*, *$12,000.50*, *1.5 millones*; las fechas *31/01/2026*. Lo que no entiende lo dice tal cual, nunca lo adivina.
3. `rules.py` valida cada regla (columna conocida, operador con sentido, color real) y descarta la rara sin perder las demás. Opcionalmente, `planner.py` puede preguntarle a Claude en vez de al intérprete (Ajustes → *Usar Claude*, con tu clave de API): mismo esquema JSON, mismas reglas, y solo viajan las cabeceras.
4. `workbook.py` cuenta las coincidencias en Python para la vista previa y, al pulsar **APLICAR**, escribe `FormulaRule`s con [openpyxl](https://openpyxl.readthedocs.io/) en una copia. Las fórmulas fijan la columna que miran (`$C2="PENDIENTE"`), protegen las comparaciones numéricas con `ISNUMBER` para que un texto nunca cuente como «mayor que», y expresan las fechas como `DATE(a,m,d)`.

La ventana es Qt ([PySide6](https://doc.qt.io/qtforpython-6/)) con la estética Komi: papel y tinta, esquinas rectas, sombras duras, paleta de sol. La interfaz está en español.

<br/>

## ⌨️ Línea de comandos

El mismo ejecutable (o `python -m sunny`) acepta argumentos:

```
Sunny.exe ventas.xlsx                                           # abre la ventana con ese archivo
Sunny.exe --cli ventas.xlsx "rojo donde Estado sea PENDIENTE"   # entiende, enseña la vista previa, escribe «ventas - Sunny.xlsx»
Sunny.exe --cli ventas.xlsx --reglas mes.json -o listo.xlsx     # aplica reglas guardadas
```

| Opción | Efecto |
| --- | --- |
| `-s HOJA` | Hoja con la que trabajar (por defecto, la activa) |
| `-o ARCHIVO.xlsx` | Dónde guardar (por defecto, `<nombre> - Sunny.xlsx` junto al original) |
| `--reglas REGLAS.json` | Aplicar reglas guardadas en vez de entender una frase |
| `--guardar-reglas REGLAS.json` | Guardar las reglas obtenidas |
| `--claude` | Que la frase la entienda Claude en vez del intérprete propio (necesita clave de API) |
| `--modelo MODELO` | Modelo de Claude, con `--claude` |
| `--cli` | Trabajar sin abrir la ventana |

Con `--claude`, la clave de la API sale de los ajustes que guarda la ventana o de `ANTHROPIC_API_KEY`.

<br/>

## 🛠️ Compilar

Hace falta Python 3.11+ y, para el instalador, [Inno Setup 6](https://jrsoftware.org/isdl.php).

```powershell
git clone https://github.com/Chidaruma696/Sunny.git
cd Sunny
.\build.ps1                # .venv + deps + PyInstaller + Inno Setup → dist\Sunny-X.Y.Z-setup.exe
.\build.ps1 -NoInstaller   # solo dist\Sunny\Sunny.exe
.\build.ps1 -Test          # las pruebas
```

Para desarrollar sin compilar:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m sunny
.\.venv\Scripts\python -m pytest
```

Mapa:

```
sunny/rules.py      Modelo de regla, esquema JSON, validación
sunny/parser.py     La orden en español entendida sin modelo (trozos, estilos, columnas, condiciones)
sunny/workbook.py   Forma de la hoja, índice de valores, conteo para la vista previa, formato condicional con openpyxl
sunny/planner.py    Opcional: llamada a Claude con salida estructurada (cabeceras + orden entran, reglas salen)
sunny/settings.py   Clave de la API y modelo, compartidos por ventana y CLI
sunny/gui.py        Ventana PySide6 (arrastrar y soltar, tabla de vista previa, aplicar)
sunny/theme.py      QSS Komi, paleta Sunny
sunny/cli.py        Argumentos y punto de entrada
tests/              pytest: reglas, fórmulas, conteos, libro escrito
sunny.spec          PyInstaller (una carpeta, sin consola)
installer/Sunny.iss Inno Setup
build.ps1           Todo lo anterior en un paso
```

<br/>

## 🗺️ Hoja de ruta

- [ ] Más maneras de decir las cosas (el intérprete aprende de frases reales de oficina; manda las que no entienda).
- [ ] Formatos de número y anchos de columna como parte de la orden.
- [ ] Varias hojas de una vez.
- [ ] Tema oscuro.

<br/>

## ⚖️ Legal

Sunny es software libre bajo la licencia [Apache 2.0](LICENSE). Los componentes de terceros y sus licencias están en [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Touhou Project y sus personajes pertenecen a Team Shanghai Alice (ZUN); obra de fans no oficial hecha según sus directrices para obras derivadas, sin afiliación ni respaldo.

<br/>

<div align="center">

サニー

</div>
