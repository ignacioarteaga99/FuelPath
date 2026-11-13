# FuelPath

**Tu pauta nutricional para llegar con todo a la carrera.**

FuelPath arma y sigue la pauta de los días previos a una carrera. Pones tu
peso, la carrera, la hora de salida y tu tiempo estimado, y te dice:

| Momento | Qué te dice |
|---|---|
| Días antes | Cuántos gramos de carbohidratos comer cada día (carga de 10–12 g/kg las 36–48 h previas en carreras de más de 90 min) y qué evitar |
| Comida previa | A qué hora y cuántos gramos (1–4 g/kg, 1 a 4 h antes) |
| En carrera | Gramos por hora, líquido y sodio, y en qué minuto y kilómetro va cada gel |
| Hoy | Lo que te toca hoy y cuánto llevas, sumando con un toque |

Es una guía general basada en consensos de nutrición deportiva. Si tienes la
pauta de tu nutricionista, FuelPath te ayuda a seguir esa (Fase 2 del plan).

App hermana de [PacePath](https://github.com/ignacioarteaga99/PacePath): misma
arquitectura (FastAPI + web móvil instalable, Render + Neon) y mismo estilo.

## Desarrollo

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
uvicorn fuelpath.api:app --reload   # http://localhost:8000
```

```bash
curl -X POST localhost:8000/api/pauta -H 'Content-Type: application/json' \
     -d '{"peso_kg": 70, "distancia_km": 42.2, "tiempo_min": 210, "fecha": "2027-04-11", "hora": "07:30"}'
```

## Despliegue en Render (gratis)

`render.yaml` es un Blueprint: en render.com → **New → Blueprint** → este repo.
Imagen Docker, salud en `/api/salud`. Los secretos se pegan en Render, nunca
en el repositorio.

Plan de trabajo: [`PLAN.md`](PLAN.md) · Arquitectura y qué se trae de PacePath:
[`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) · Estilo: [`docs/ESTILO.md`](docs/ESTILO.md).

## Licencia

Copyright © 2026 Ignacio Arteaga. Todos los derechos reservados: el código es
público sólo para leerlo. Ver [`LICENSE`](LICENSE).
