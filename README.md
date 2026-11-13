# FuelPath

**Tu carga de carbohidratos antes de la carrera, comida a comida.**

Con tu carrera, tu peso, tus horarios y los alimentos que te gustan, FuelPath arma
la agenda de las 36–48 h previas (o 24 h en un 21K) en medidas caseras. Ahí vas
marcando lo que comes y, si comes más o menos, la app reparte la diferencia en lo
que queda del día, sin pasar el tope de ninguna comida. También arma el desayuno
del día, las sales y el plan en carrera (geles, líquido y sodio por hora), y al
terminar guarda tu feedback para la próxima.

Es una guía general basada en consensos de nutrición deportiva (ver
[`docs/NUTRICION.md`](docs/NUTRICION.md)). No reemplaza a tu nutricionista.

App hermana de [PacePath](https://github.com/ignacioarteaga99/PacePath): misma
arquitectura (FastAPI + web móvil instalable, Render + Neon) y mismo estilo.

## Desarrollo

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
# Sin cuenta obligatoria (SÓLO en local):
FUELPATH_ACCESO_LIBRE=1 uvicorn fuelpath.api:app --reload   # http://localhost:8000
# Con cuentas y panel /admin, con una SQLite local:
FUELPATH_ADMIN=una-clave DATABASE_URL=/tmp/fuelpath.sqlite uvicorn fuelpath.api:app --reload
```

## Puesta en marcha (Render + Neon)

1. **Neon** (neon.tech, gratis): crea el proyecto «fuelpath» y copia la *connection string* (`postgresql://…`).
   Las tablas `fp_…` se crean solas al primer uso.
2. **Render** → New → **Blueprint** → este repo. Usa `render.yaml`, que despliega la rama `produccion`. Pega en
   Render (nunca en el repo):
   - `DATABASE_URL`: la de Neon.
   - `FUELPATH_ADMIN`: una clave larga inventada para el panel `/admin`.
   - `FUELPATH_URL`: vacía hasta tener dominio propio.
3. Entra a la app, **crea tu cuenta** y en `/admin` márcate con **beta**. La beta parte cerrada: sólo entran
   las cuentas marcadas.
4. Correos (cuando haya dominio): verifica el dominio en **Resend**. En Render pega `FUELPATH_CORREO_CLAVE`
   (la API key) y `FUELPATH_CORREO_DE` (`FuelPath <hola@tu-dominio>`), y cambia `FUELPATH_CORREO_ACTIVO` a `1`.
   El panel dice si falta algo y manda un correo de prueba.
5. Google y Microsoft (opcional): crea las apps OAuth con la vuelta `{URL}/api/auth/google/vuelta` y
   `{URL}/api/auth/microsoft/vuelta`, y pega `GOOGLE_CLIENT_ID/SECRET` y `MICROSOFT_CLIENT_ID/SECRET`.

`FUELPATH_ACCESO_LIBRE` es sólo para tests y desarrollo local: **nunca** en Render.

Plan de trabajo: [`PLAN.md`](PLAN.md) · Arquitectura y qué se trae de PacePath:
[`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) · Estilo: [`docs/ESTILO.md`](docs/ESTILO.md).

## Licencia

Copyright © 2026 Ignacio Arteaga. Todos los derechos reservados: el código es
público sólo para leerlo. Ver [`LICENSE`](LICENSE).
