# Arquitectura de FuelPath (heredada de PacePath)

FuelPath copia la forma de PacePath: un solo servicio FastAPI que sirve la API y
la app web móvil instalable. Corre en Render gratis, con Postgres en Neon. Esta
guía dice cómo está armado y **qué archivo de PacePath traer para cada cosa**.
La referencia es el commit `58ecb41` de `ignacioarteaga99/PacePath`.

## Piezas

```
web/index.html      toda la app en un archivo: HTML + CSS + JS, sin build ni framework
web/sw.js           service worker mínimo (instalable; sin caché de la app)
web/manifest.webmanifest, web/icons/   ícono y nombre al instalar
web/vendor/         librerías y fuentes servidas por la app (nada de CDNs)
fuelpath/api.py     FastAPI: middlewares, endpoints, archivos fijos
fuelpath/idioma.py  idioma por petición (ContextVar) y tr(es, en, pt)
fuelpath/pauta.py   la lógica del producto, pura y con tests
tests/              pytest + TestClient
render.yaml         Blueprint de Render · Dockerfile · .github/workflows/tests.yml
```

## Reglas de diseño que vienen de PacePath

1. **La lógica va en módulos puros y testeados.** `api.py` sólo valida con
   pydantic y llama.
   - Ejemplos en PacePath: `coach.py`, `bitacora.py`.
   - Aquí: `pauta.py`.
2. **Los textos del servidor también se traducen.**
   - El servidor usa `tr("es", "en", "pt")`.
   - La app manda la cabecera `X-Idioma`, que el middleware `_idioma` lee.
   - Al cambiar de idioma, la app vuelve a pedir lo que tiene en pantalla.
3. **La app es un solo `index.html`.**
   - Traducciones en los diccionarios `EN` y `PT`, con el texto en español
     como clave, y `t("…", {vars})`.
   - Los textos fijos del HTML llevan `data-i18n` y se traducen en `aplicarIdioma()`.
4. **Los datos del usuario viven primero en el teléfono.**
   - Están en `localStorage` con prefijo `fp_`, leídos y escritos con
     `pref()` / `guardar()` dentro de `try`.
   - Con cuenta se suben y bajan enteros: `GET` y `PUT /api/cuenta/datos`, con
     la lista `DATOS_CUENTA` y el tope `DATOS_MAX`.
5. **Nada persistente en el disco del servidor.**
   - Render borra el disco al dormir.
   - Lo que deba durar va a Neon. Lo grande y fijo se descarga de una Release
     de GitHub.
6. **Tráfico:** Render gratis da 5 GB al mes.
   - GZip para todo.
   - Una semana de caché para `/vendor` y `/icons`.
   - `no-cache` para `index.html` y `sw.js`.
7. **Cuidar la memoria:** 512 MB.
   - `MALLOC_ARENA_MAX=2`.
   - Nada pesado en memoria por usuario.

## Qué traer de PacePath y cómo adaptarlo

| Necesidad | Archivo(s) en PacePath | Al traerlo |
|---|---|---|
| Cuentas: correo y clave (scrypt), sesión por cookie con hash del token, bloqueo por intentos, códigos de verificar o recuperar | `pacepath/cuentas.py` | Tablas `pp_usuarios`/`pp_sesiones` → `fp_…`, cookie `pp_sesion` → `fp_sesion`. Quitar `strava_de` y `guardar_strava` si no hay Strava |
| Entrar con Google o Microsoft | `pacepath/oauth.py` + endpoints `/api/auth/*` de `api.py` | Cookie `pp_oauth` → `fp_oauth`. Nuevas apps OAuth con la URL de FuelPath |
| Página de entrada | `web/entrar.html` | Marca y textos |
| Obligar a tener cuenta y beta cerrada | Middleware `_con_cuenta`, `_ABIERTAS` y `_pendiente` en `api.py`, y `pacepath/acceso.py` | `PACEPATH_ACCESO_LIBRE` → `FUELPATH_ACCESO_LIBRE` (nunca en Render) |
| Registro de eventos en Neon, con SQLite en /tmp como respaldo y escritor en un hilo | `pacepath/registro.py`, `pacepath/uso.py` | Tabla `pp_eventos` → `fp_eventos`; las columnas de rutas (comuna, tipo…) se cambian por las de FuelPath |
| Panel `/admin` (usuarios, beta, eventos, prueba de correo, variables que faltan) | `web/admin.html` + endpoints `/api/admin/*` | Sacar motor y mapa; dejar usuarios, acceso, eventos y correo |
| Correos con la plantilla de la marca (Resend por API o SMTP, `responder_a`, tarjetas de datos) | `pacepath/correo.py` (`_correo`, `enviar`, `faltan`, `activo`) | Variables `PACEPATH_CORREO_*` → `FUELPATH_CORREO_*`; plantilla con el logo de FuelPath |
| Enviar un resumen a un tercero (entrenador → nutricionista), con 15 envíos al día como máximo | `/api/bitacora/enviar` en `api.py` y `correo.sesion_entrenador` | Resumen de cumplimiento de la pauta |
| Sincronizar los datos del teléfono, exportar y borrar la cuenta | `/api/cuenta/datos`, `/api/cuenta/exportar`, `/api/cuenta/borrar` en `api.py`; `DATOS_CUENTA` en `index.html` | Claves `fp_*` |
| Dominio propio: redirigir desde `*.onrender.com` | Middleware `_dominio_propio` | `FUELPATH_URL` |
| HEAD como GET (los filtros de correo revisan enlaces con HEAD) | Middleware `_head` | Tal cual |
| Páginas legales | `web/privacidad.html`, `web/terminos.html` | Reescribir: aquí hay **datos de salud** (peso, comidas). Pedir consentimiento explícito y dejar borrar todo |
| Strava (Fase 3) | `pacepath/strava.py` + middleware `_strava_en_cuenta` | Sólo leer actividades del dueño, borrar al desconectar y mostrar el logo oficial |
| Historias para Instagram (canvas 1080×1920, fuentes PP Display/Mono) | `historiaDatos`, `pintarHistoria` y `DISENOS` en `index.html` | Plan de carrera o resumen de la carga |

## Variables de entorno (Render)

| Variable | Para qué | Secreta |
|---|---|---|
| `FUELPATH_URL` | Dominio público y enlaces de los correos | no |
| `FUELPATH_ADMIN` | Clave del panel `/admin` | **sí** |
| `DATABASE_URL` | Neon | **sí** |
| `FUELPATH_CORREO_ACTIVO`, `_SMTP`, `_USUARIO`, `_CLAVE`, `_DE` | Correos. ACTIVO=«1» sólo con las otras cuatro | `_CLAVE` **sí** |
| `FUELPATH_CORREO_AVISOS` | (Opcional) a quién avisar de cada cuenta nueva | no |
| `FUELPATH_SOPORTE` | (Opcional) correo de soporte de los correos y las páginas legales; si no, el remitente | no |
| `FUELPATH_ACCESO_LIBRE` | Sin cuenta obligatoria: **sólo tests y local, nunca en Render** | — |
| `GOOGLE_CLIENT_ID/SECRET`, `MICROSOFT_CLIENT_ID/SECRET` | Entrar con Google o Microsoft | los SECRET **sí** |

## Lo que ya se trajo de PacePath (Fase 0)

- `registro.py`, `uso.py`, `acceso.py`, `cuentas.py`, `oauth.py`, `correo.py`: copiados del commit `58ecb41` con
  tablas `fp_…`, cookies `fp_sesion` / `fp_oauth`, variables `FUELPATH_*` y sin Strava, comunas ni motor.
- Lo propio de FuelPath:
  - **consentimiento** para datos de salud (`fp_usuarios.consentimiento`). Se marca al crear la cuenta, antes de ir
    a Google o Microsoft (`?consiento=1`) o después, en `POST /api/cuenta/consentimiento`. Sin él, `_pendiente`
    devuelve `consentimiento` y la app no abre;
  - el registro de consultas **no guarda datos de salud**: sólo la consulta, la distancia y si salió bien.
- `DATOS_CUENTA` = `fp_perfil`, `fp_plan`, `fp_agua`, `fp_historial`, `fp_idioma`, `fp_noche` (tope `DATOS_MAX`, 1 MB).

## Despliegue

- Ramas como en PacePath:
  - una rama de producción conectada a Render con `autoDeploy`;
  - el trabajo nuevo va en otra rama y pasa a producción por fast-forward
    cuando pytest pasa.
- La salud se revisa en `/api/salud`.
- El primer arranque después de dormir tarda ~30 s: la app no debe depender
  de que el servidor esté despierto para mostrar lo guardado en el teléfono.
