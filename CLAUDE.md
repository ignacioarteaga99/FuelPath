# FuelPath — contexto para Claude

App para corredores: **seguimiento de la pauta nutricional previa a una
carrera**. Cubre la carga de carbohidratos de los días antes, la comida previa
y el plan de geles, líquido y sodio en carrera. Ver `README.md`, `PLAN.md`,
`docs/ARQUITECTURA.md` y **`docs/MEMORIA.md`** (cómo trabajar con el usuario y
lo decidido; leerlo al empezar).

## De dónde viene
- Es la app hermana de **PacePath** (`ignacioarteaga99/PacePath`, en
  pacepathapp.com): rutas para el entrenamiento del día, Coach y bitácora del
  corredor. FuelPath copia su arquitectura, su formato y su estilo.
- Cuando haya que traer algo de PacePath (cuentas, correos, panel /admin,
  Strava…), se **copia y adapta** el módulo. No se importa PacePath como
  dependencia.
  - `docs/ARQUITECTURA.md` dice qué archivo traer y qué renombrar.
  - La referencia es el commit `58ecb41` de PacePath.
- El usuario es de Santiago de Chile y habla español (chileno, informal).
  - Interfaz en español, con inglés y portugués de Brasil.
  - Textos con `tr(es, en, pt)` en el servidor y `t("texto en español")` en la app.

## Lecciones de PacePath que aplican aquí
- **Render gratis:** 512 MB de RAM y el servicio se duerme a los 15 min.
  - Al dormir **borra el disco**: nada persistente en disco.
  - Cuentas, datos y registro van en Postgres (Neon).
- **Secretos:** nunca en el chat ni en el repo. Van sólo en Render o en GitHub
  Secrets (`sync: false` en `render.yaml`).
- **Acceso libre:** una variable `FUELPATH_ACCESO_LIBRE` (si se crea, como
  `PACEPATH_ACCESO_LIBRE`) es sólo para tests y desarrollo local. **Nunca**
  en Render.
- **Correo:** Resend o SMTP con el dominio propio.
  - `FUELPATH_CORREO_ACTIVO` debe ser «1» y deben estar las 4 variables.
  - Si falta alguna, el panel debe decir cuál falta (`correo.faltan()` en PacePath).
- **Safari iOS:**
  - inputs a 16 px (si no, hace zoom);
  - safe-area arriba y abajo;
  - controles grandes;
  - no usar `touch-action: none` en algo que deba deslizarse.
- **Botones:** sin emojis del teclado. Los símbolos funcionales (✎ ⧉ ✓ ← ✕ ☾ ☀)
  sí van. Los íconos son SVG de línea.
- **Datos del teléfono:** viven en `localStorage` con prefijo `fp_`. Con
  cuenta se sincronizan como `DATOS_CUENTA` en PacePath (límite `DATOS_MAX`).
- **Strava:** si se agrega, OAuth propio y respetar los términos de la API:
  - los datos son sólo para su dueño;
  - se borran al desconectar;
  - no se guardan las actividades en el servidor.

## Salud y nutrición
- La pauta es **una guía general basada en consensos** (ACSM 2016, COI 2018).
  Las referencias están en `fuelpath/pauta.py`.
- No promete resultados ni reemplaza a un nutricionista.
- Si el usuario carga la pauta de su nutricionista, **esa manda** (Fase 2).
- No dar consejos para condiciones médicas (diabetes, trastornos alimentarios,
  embarazo). En esos casos, derivar a un profesional.

## Cómo trabajar aquí
- **Tests:** con pytest.
  - Comprobar el código de salida (`echo EXIT=${PIPESTATUS[0]}`). No encadenar
    `&&` después de un `tail`.
  - Commit sólo si pasan.
- **Interfaz:** probarla en viewport de iPhone con Playwright (Chromium en
  `/opt/pw-browsers`).
  - Revisar que no haya scroll horizontal y que no haya errores en la consola.
- **uvicorn:** no matarlo (`pkill`) en el mismo comando que lo levanta, porque
  se mata la propia shell.
- **GitHub:**
  - Sin PR salvo que el usuario la pida.
  - Pushes normales: el force push está bloqueado.
  - Commits con el pie de coautoría que indique la sesión.
- **Licencia:** el repo es público pero con todos los derechos reservados (`LICENSE`).
