# Estilo de FuelPath (el de PacePath)

## Tokens (`:root` en `web/index.html`)

| Token | Día | Noche (`body.noche`) |
|---|---|---|
| `--acento` | `#f2541b` (naranjo PacePath) | igual; activo en la barra `#ff6a2b` |
| `--acento-osc` | `#c9410f` (botón presionado) | igual |
| `--tinta` | `#1d1d21` | `#f4f4f6` |
| `--suave` | `#6b6b75` | `#9a9aa6` |
| `--linea` | `#e6e6ea` | `#2a2a31` |
| `--gris` (tarjetas, inputs) | `#f5f5f7` | `#22222a` |
| `--fondo` / `--panel` | `#ffffff` | `#141418` |
| `--ok` | `#1f9d55` | igual |

El acento es la única variable que cambiaría si FuelPath quiere un color
propio. Así sigue siendo de la misma familia que PacePath.

## Tipografía

- **Texto:** la del sistema (`-apple-system`, SF Pro), 15 px / 1.4.
- **Números grandes y marca:** «PP Display» (Inter Display 600/700). Se usa
  con `letter-spacing` negativo.
- **Tiempos y minutos:** «PP Mono» (JetBrains Mono Bold).
- Las fuentes son woff2 en `web/vendor/fuentes` (licencia OFL, ver `LEEME.txt`).

## Componentes

- **Barra superior:** fija arriba con safe-area. Tiene la marca (ícono de
  26 px con esquinas de 7 px) y, a la derecha, el idioma (muestra el
  siguiente: ES → EN → PT) y el modo noche.
- **Barra de pestañas:** abajo, con safe-area. Íconos SVG de línea de 24 px,
  `stroke-width 2`. La activa va en el color de acento.
- **Encabezado de sección:** `.tipo` (12 px, mayúsculas, acento, espaciado
  .6px) arriba de un `h2` de 20–22 px.
- **Tarjeta:** fondo `--gris`, radio 16 px, padding 14 px.
- **Botones:**
  - principal: acento, radio 12 px, 16 px, peso 700;
  - secundario `.sec`: gris con borde;
  - sin emojis de teclado;
  - símbolos funcionales (✎ ⧉ ✓ ← ✕ ☾ ☀) sí.
- **Inputs:**
  - 16 px siempre, para que iOS no haga zoom;
  - radio 12 px, fondo `--gris`;
  - foco con `outline 2px #f7c5b2`.
- **Avisos:** `.aviso` (ámbar) para advertencias y para la nota «no
  reemplaza a tu nutricionista»; `.aviso-ok` (verde) para confirmaciones.
- **Rejillas de formulario:** usar `minmax(0,1fr)` para que nada se desborde
  a lo ancho.

## Textos

- Español de Chile, cercano y directo: «Te faltan 120 g», no «Usted debe consumir…».
- Números con el formato del idioma (`toLocaleString`): 14,1 km en español y
  14.1 km en inglés.
- Nada de promesas de salud ni de rendimiento.
