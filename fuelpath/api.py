"""API de FuelPath (FastAPI). Misma forma que la de PacePath (pacepath/api.py).

    GET  /api/salud              Render revisa que el servicio esté vivo
    POST /api/pauta              pauta precarrera (carga, comida previa, en carrera)
    GET  /                       la app (web/index.html)

Pendiente (Fase 0 del PLAN, se trae de PacePath): cuentas y sesión
(cuentas.py, oauth.py), beta cerrada (acceso.py), registro en Neon
(registro.py), correos (correo.py), panel /admin y sincronizar los datos del
teléfono con la cuenta (DATOS_CUENTA).
"""
from __future__ import annotations

from datetime import date, time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import idioma, pauta

WEB = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="FuelPath", version="0.1.0")
app.mount("/vendor", StaticFiles(directory=WEB / "vendor"), name="vendor")
app.mount("/icons", StaticFiles(directory=WEB / "icons"), name="icons")

# Render gratis da 5 GB de tráfico al mes: todo lo de texto va comprimido y lo
# fijo (fuentes, íconos) queda una semana en el teléfono.
app.add_middleware(GZipMiddleware, minimum_size=800)
_CACHE = (("/vendor/", "public, max-age=604800"), ("/icons/", "public, max-age=604800"))


@app.middleware("http")
async def _cache_estaticos(request: Request, call_next):
    resp = await call_next(request)
    for prefijo, valor in _CACHE:
        if request.url.path.startswith(prefijo) and resp.status_code in (200, 304):
            resp.headers["Cache-Control"] = valor
            break
    return resp


@app.middleware("http")
async def _idioma(request: Request, call_next):
    """Idioma de la respuesta: cabecera X-Idioma (la app) o ?lang= (enlaces)."""
    idioma.usar(request.headers.get("x-idioma") or request.query_params.get("lang"))
    return await call_next(request)


@app.get("/api/salud")
def salud():
    return {"ok": True}


class PedidoPauta(BaseModel):
    peso_kg: float = Field(ge=pauta.PESO_MIN, le=pauta.PESO_MAX)
    distancia_km: float = Field(gt=0, le=250)
    tiempo_min: float | None = Field(default=None, gt=0, le=48 * 60)
    ritmo_s_km: float | None = Field(default=None, ge=120, le=1200)
    fecha: date
    hora: time = time(8, 0)
    gel_g: float = Field(default=25, ge=5, le=100)
    intestino_entrenado: bool = False


@app.post("/api/pauta")
def api_pauta(p: PedidoPauta):
    minutos = p.tiempo_min or (pauta.ritmo_a_tiempo(p.distancia_km, p.ritmo_s_km) if p.ritmo_s_km else None)
    if not minutos:
        raise HTTPException(422, idioma.tr("Falta el tiempo estimado o el ritmo.",
                                           "Missing the estimated time or pace.",
                                           "Falta o tempo estimado ou o ritmo."))
    c = pauta.Carrera(p.peso_kg, p.distancia_km, minutos, p.fecha, p.hora, p.gel_g, p.intestino_entrenado)
    return pauta.pauta(c)


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(WEB / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js")
def sw():
    return FileResponse(WEB / "sw.js", media_type="text/javascript", headers={"Cache-Control": "no-cache"})


@app.get("/")
def inicio():
    return FileResponse(WEB / "index.html", headers={"Cache-Control": "no-cache"})
