"""API de FuelPath (FastAPI). Misma forma que la de PacePath (pacepath/api.py).

    GET  /api/salud              Render revisa que el servicio esté vivo
    GET  /api/alimentos          base de alimentos (con las restricciones: permitidos y marcados de partida)
    POST /api/carga              plan de carga: agenda de comidas de los días previos y del día de carrera
    POST /api/reparto            propuesta para recalcular lo que queda del día
    POST /api/pauta              pauta resumida (rangos por día; versión anterior, sin agenda)
    GET  /                       la app (web/index.html)

Pendiente (Fase 0 del PLAN, se trae de PacePath): cuentas y sesión
(cuentas.py, oauth.py), beta cerrada (acceso.py), registro en Neon
(registro.py), correos (correo.py), panel /admin y sincronizar los datos del
teléfono con la cuenta (DATOS_CUENTA).
"""
from __future__ import annotations

from datetime import date, time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import alimentos, carga, idioma, pauta, reparto

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


@app.get("/api/alimentos")
def api_alimentos(restricciones: str = "", sensible: bool = False):
    r = tuple(x for x in restricciones.split(",") if x in alimentos.RESTRICCIONES)
    return {"alimentos": alimentos.catalogo(), "por_defecto": alimentos.por_defecto(r, sensible),
            "permitidos": [a["id"] for a in alimentos.ALIMENTOS if alimentos.permitido(a, r, sensible)],
            "fuente": alimentos.fuente()}


class PedidoCarga(BaseModel):
    evento: str = Field(default="", max_length=80)
    fecha: date
    hora: time = time(8, 0)
    peso_kg: float = Field(ge=30, le=200)
    distancia: Literal["10k", "21k", "42k", "703", "im", "fondo", "otra"]
    km: float | None = Field(default=None, gt=0, le=1000)
    deporte: Literal["correr", "bici", "tri"] | None = None
    tiempo_min: float = Field(ge=10, le=24 * 60)
    regimen: float | None = Field(default=None, ge=6, le=12.5)
    levanta: time = time(7, 0)
    acuesta: time = time(23, 0)
    primera_carga: bool = False
    estomago_sensible: bool = False
    sudor_salado: bool = False
    restricciones: list[str] = Field(default_factory=list, max_length=12)
    otra_restriccion: str = Field(default="", max_length=120)
    elegidos: list[str] | None = Field(default=None, max_length=len(alimentos.ALIMENTOS))
    gel_g: float = Field(default=25, ge=5, le=100)
    intestino_entrenado: bool = False
    condicion_medica: bool = False


_ERRORES = {
    "otra_sin_km_o_deporte": ("Con «otra» distancia, indica los km y el deporte.",
                              "With «other» distance, enter the km and the sport.",
                              "Com «outra» distância, informe os km e o esporte."),
    "levanta_invalido": ("La hora en que te levantas debe estar entre las 4:00 y las 11:00.",
                         "Wake-up time must be between 4:00 and 11:00.",
                         "O horário de acordar deve estar entre 4:00 e 11:00."),
    "acuesta_invalido": ("La hora en que te acuestas debe estar entre las 20:00 y la 1:00.",
                         "Bedtime must be between 20:00 and 1:00.",
                         "O horário de dormir deve estar entre 20:00 e 1:00."),
}


@app.post("/api/carga")
def api_carga(p: PedidoCarga):
    if p.condicion_medica:
        return {"derivar": True, "mensaje": idioma.tr(
            "Con diabetes, un trastorno alimentario o un embarazo, la carga de carbohidratos tiene que verla un "
            "profesional de la salud. FuelPath no arma una pauta en ese caso: pídele a tu médico o nutricionista "
            "que te ayude con la tuya.",
            "With diabetes, an eating disorder or a pregnancy, carb-loading needs to be handled by a health "
            "professional. FuelPath doesn't build a plan in that case: ask your doctor or dietitian to help you with yours.",
            "Com diabetes, um transtorno alimentar ou gravidez, a carga de carboidratos precisa ser acompanhada por um "
            "profissional de saúde. O FuelPath não monta um plano nesse caso: peça ajuda ao seu médico ou nutricionista.")}
    try:
        perfil = carga.Perfil(fecha=p.fecha, hora=p.hora, peso_kg=p.peso_kg, distancia=p.distancia,
                              tiempo_min=p.tiempo_min, regimen=p.regimen, evento=p.evento.strip(), deporte=p.deporte,
                              km=p.km, levanta=p.levanta, acuesta=p.acuesta, primera_carga=p.primera_carga,
                              estomago_sensible=p.estomago_sensible, sudor_salado=p.sudor_salado,
                              restricciones=tuple(p.restricciones),
                              elegidos=tuple(p.elegidos) if p.elegidos is not None else None,
                              gel_g=p.gel_g, intestino_entrenado=p.intestino_entrenado)
    except ValueError as e:
        msg = _ERRORES.get(str(e))
        raise HTTPException(422, idioma.tr(*msg) if msg else idioma.tr(
            "Revisa los datos de tu carrera.", "Check your race details.", "Confira os dados da sua prova."))
    r = carga.plan(perfil)
    r["otra_restriccion"] = p.otra_restriccion.strip()
    return r


class ItemDia(BaseModel):
    a: str
    p: float = Field(ge=0, le=50)
    c: float | None = Field(default=None, ge=0, le=50)
    mx: float | None = Field(default=None, ge=0, le=50)


class ComidaDia(BaseModel):
    id: str = Field(max_length=30)
    objetivo_g: float = Field(ge=0, le=3000)
    tope_g: float = Field(ge=0, le=3000)
    min_g: float = Field(ge=0, le=3000)
    items: list[ItemDia] = Field(max_length=20)


class DiaReparto(BaseModel):
    objetivo_g: float = Field(gt=0, le=5000)
    rango_g: tuple[float, float]
    escala: float = Field(default=1.0, ge=1, le=3)
    comidas: list[ComidaDia] = Field(max_length=10)


class PedidoReparto(BaseModel):
    dia: DiaReparto
    desde: int = Field(ge=-1, le=10)


@app.post("/api/reparto")
def api_reparto(p: PedidoReparto):
    dia = p.dia.model_dump()
    if any(it["a"] not in alimentos.POR_ID for cm in dia["comidas"] for it in cm["items"]):
        raise HTTPException(422, idioma.tr("Hay un alimento que no conozco.", "There's a food I don't know.",
                                           "Há um alimento que não conheço."))
    return reparto.proponer(dia, p.desde)


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(WEB / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js")
def sw():
    return FileResponse(WEB / "sw.js", media_type="text/javascript", headers={"Cache-Control": "no-cache"})


@app.get("/")
def inicio():
    return FileResponse(WEB / "index.html", headers={"Cache-Control": "no-cache"})
