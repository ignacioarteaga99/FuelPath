"""API de FuelPath (FastAPI). Misma forma que la de PacePath (pacepath/api.py, commit 58ecb41).

    GET  /                       la app (web/index.html); sin sesión, la página de entrada
    GET  /api/salud              Render revisa que el servicio esté vivo
    GET  /api/alimentos          base de alimentos (con las restricciones: permitidos y marcados de partida)
    POST /api/carga              plan de carga: agenda de comidas de los días previos y del día de carrera
    POST /api/reparto            propuesta para recalcular lo que queda del día
    POST /api/pauta              pauta resumida (rangos por día; versión anterior, sin agenda)

    Cuentas (de PacePath: cuentas.py, oauth.py, acceso.py, correo.py)
    POST /api/auth/registro · /api/auth/entrar · /api/auth/salir   cuenta con correo
    GET  /api/auth/google · /api/auth/microsoft      entrar con Google o Microsoft
    POST /api/auth/recuperar · /api/auth/nueva-clave · /api/auth/reenviar · GET /api/auth/verificar
    GET  /api/cuenta             quién soy, si puedo entrar y qué falta (verificar, consentimiento, beta)
    POST /api/cuenta/consentimiento   acepta el tratamiento de datos de salud
    GET/PUT /api/cuenta/datos    lo del teléfono que viaja con la cuenta (DATOS_CUENTA)
    GET  /api/cuenta/exportar    todo lo tuyo en JSON · POST /api/cuenta/borrar  borra la cuenta

    Panel (cabecera X-Admin-Clave = FUELPATH_ADMIN)
    GET  /admin · /api/admin/eventos · /api/admin/acceso · /api/admin/usuarios[/id] · /api/admin/consumo
    POST /api/admin/correo/prueba
    GET  /entrar · /privacidad · /terminos
"""
from __future__ import annotations

import json
import os
import re
import secrets
import time as reloj
from contextlib import asynccontextmanager
from datetime import date, time, timedelta
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import acceso, alimentos, carga, correo, cuentas, idioma, oauth, pauta, registro, reparto, uso
from .idioma import tr

WEB = Path(__file__).resolve().parent.parent / "web"

@asynccontextmanager
async def _vida(_app):
    yield
    registro.vaciar()          # al apagarse (Render duerme): guardar lo pendiente del registro


app = FastAPI(title="FuelPath", version="0.1.0", lifespan=_vida)
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


# ── Acceso: siempre con cuenta; con la beta cerrada, sólo testers ──────────
# Sin sesión (o si la cuenta aún no puede entrar), las páginas de la app
# muestran la de entrada y la API responde 401. Qué falta, en orden:
#   · verificar el correo (si el envío de correos está encendido);
#   · el consentimiento para tratar datos de salud (peso, comidas);
#   · la beta (si está cerrada, sólo entran las cuentas marcadas en /admin).
# FUELPATH_ACCESO_LIBRE=1 quita la cuenta obligatoria: sólo para tests y
# desarrollo local, NUNCA en Render.
_ABIERTAS = {"/admin", "/entrar", "/api/salud", "/api/cuenta", "/api/cuenta/consentimiento", "/api/cuenta/borrar",
             "/manifest.webmanifest", "/sw.js", "/favicon.ico", "/privacidad", "/privacy", "/terminos", "/terms"}
_ABIERTAS_PREFIJO = ("/api/admin/", "/api/auth/", "/vendor/", "/icons/")


def _pendiente(u: dict | None) -> str | None:
    """Por qué esta sesión no puede usar la app (None: puede)."""
    if not u:
        return "sin_sesion"
    if cuentas.falta_verificar(u, correo.activo()):
        return "verificar"
    if not u.get("consentimiento"):
        return "consentimiento"
    if acceso.activo() and not u["beta"]:
        return "beta"
    return None


def _usuario(request: Request) -> dict | None:
    try:
        return cuentas.de_cookie(request.cookies.get(cuentas.COOKIE))
    except Exception as exc:  # noqa: BLE001 — la base caída no tumba la app
        print(f"[cuentas] no pude leer la sesión: {type(exc).__name__}: {exc}", flush=True)
        return None


@app.middleware("http")
async def _con_cuenta(request: Request, call_next):
    ruta = request.url.path
    if (ruta in _ABIERTAS or ruta.startswith(_ABIERTAS_PREFIJO)
            or os.environ.get("FUELPATH_ACCESO_LIBRE") == "1"
            or _pendiente(_usuario(request)) is None):
        return await call_next(request)
    _anotar(evento="sin_acceso")
    if ruta.startswith("/api/"):
        return JSONResponse({"detail": tr("Entra con tu cuenta de FuelPath.", "Sign in with your FuelPath account.",
                                          "Entre com sua conta do FuelPath.")}, status_code=401)
    return FileResponse(WEB / "entrar.html", headers={"Cache-Control": "no-store"})


# ── Registro de consultas (panel /admin) ────────────────────────────────────
# Sólo estas direcciones (no los archivos, ni /api/salud, que Render consulta
# cada pocos segundos, ni la sincronización de datos, que va cada 20 s).
CONSULTAS = {
    "/": "visita", "/privacidad": "privacidad", "/privacy": "privacidad", "/terminos": "terminos", "/terms": "terminos",
    "/api/carga": "carga", "/api/reparto": "reparto", "/api/alimentos": "alimentos",
    "/api/auth/registro": "cuenta_registro", "/api/auth/entrar": "cuenta_entrar", "/api/auth/salir": "cuenta_salir",
    "/api/auth/google/vuelta": "cuenta_google", "/api/auth/microsoft/vuelta": "cuenta_microsoft",
    "/api/cuenta/exportar": "cuenta_exportar", "/api/cuenta/borrar": "cuenta_borrar",
}
COOKIE_USUARIO = "fp_u"          # identificador anónimo del teléfono: al azar
_DISPOSITIVOS = (("iphone", "iPhone"), ("ipad", "iPad"), ("android", "Android"),
                 ("macintosh", "Mac"), ("windows", "Windows"), ("linux", "Linux"))


def _dispositivo(ua: str) -> str:
    ua = ua.lower()
    return next((nombre for clave, nombre in _DISPOSITIVOS if clave in ua), "otro")


@app.middleware("http")
async def _registrar(request: Request, call_next):
    consulta = CONSULTAS.get(request.url.path)
    if consulta is None or request.scope.get("fp_head"):
        return await call_next(request)
    usuario = request.cookies.get(COOKIE_USUARIO, "")
    nuevo = not re.fullmatch(r"[0-9a-f]{10}", usuario)
    if nuevo:
        usuario = secrets.token_hex(5)
    lang = request.headers.get("x-idioma") or request.query_params.get("lang") \
        or request.headers.get("accept-language", "es")
    cuenta = _usuario(request)
    largo = request.headers.get("content-length", "")
    info: dict = {"consulta": consulta, "usuario": usuario, "idioma": idioma.normalizar(lang),
                  "disp": _dispositivo(request.headers.get("user-agent", "")),
                  "cuenta": cuenta["id"] if cuenta else None, "bytes_in": int(largo) if largo.isdigit() else 0}
    marca = uso.consulta.set(info)
    t0 = reloj.perf_counter()

    def terminar() -> None:
        info.setdefault("ms", round((reloj.perf_counter() - t0) * 1000))
        info.setdefault("exito", info.get("estado", 500) < 400)
        info.setdefault("evento", consulta)
        registro.anotar(info)
    try:
        resp = await call_next(request)
    except Exception as exc:
        info.update(estado=500, exito=False, error=f"{type(exc).__name__}: {exc}")
        uso.consulta.reset(marca)
        terminar()
        raise
    uso.consulta.reset(marca)
    info["estado"] = resp.status_code
    info["ms"] = round((reloj.perf_counter() - t0) * 1000)
    if nuevo:
        resp.set_cookie(COOKIE_USUARIO, usuario, max_age=400 * 24 * 3600, httponly=True,
                        samesite="lax", secure=_base(request).startswith("https"))
    cuerpo = resp.body_iterator

    async def contar():
        n = 0
        try:
            async for trozo in cuerpo:
                n += len(trozo)
                yield trozo
        finally:
            info["bytes_out"] = n
            terminar()
    resp.body_iterator = contar()
    return resp


@app.middleware("http")
async def _dominio_propio(request: Request, call_next):
    """Con dominio propio (FUELPATH_URL), quien entra por *.onrender.com va al
    dominio. Sólo las páginas: la API sigue respondiendo en la dirección vieja
    (y Render revisa /api/salud ahí)."""
    destino = os.environ.get("FUELPATH_URL", "").rstrip("/")
    host = request.headers.get("host", "").split(":")[0].lower()
    if (destino and host.endswith(".onrender.com") and host not in destino
            and request.method in ("GET", "HEAD") and not request.url.path.startswith("/api/")):
        q = f"?{request.url.query}" if request.url.query else ""
        return RedirectResponse(destino + request.url.path + q, status_code=301)
    return await call_next(request)


@app.middleware("http")
async def _head(request: Request, call_next):
    """HEAD responde como GET, sin cuerpo: los filtros de correo revisan los
    enlaces con HEAD y un 405 les parece sospechoso. No se registra."""
    if request.method != "HEAD":
        return await call_next(request)
    request.scope["method"] = "GET"
    request.scope["fp_head"] = True
    resp = await call_next(request)
    async for _ in resp.body_iterator:
        pass
    headers = {k: v for k, v in resp.headers.items() if k.lower() != "content-length"}
    return Response(status_code=resp.status_code, headers=headers)


def _anotar(**campos) -> None:
    """Agrega datos a la consulta en curso (si se está registrando)."""
    info = uso.consulta.get()
    if info is not None:
        info.update({k: v for k, v in campos.items() if v is not None})


def _base(request: Request) -> str:
    """URL pública de la app. Render termina el HTTPS antes: el esquema real viene en X-Forwarded-Proto."""
    if os.environ.get("FUELPATH_URL"):
        return os.environ["FUELPATH_URL"].rstrip("/")
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    return f"{proto}://{host}"


def _poner_cookie(resp: Response, request: Request, nombre: str, valor: str, max_age: int) -> None:
    resp.set_cookie(nombre, valor, max_age=max_age, httponly=True, samesite="lax",
                    secure=_base(request).startswith("https"))


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
    uso.registrar("carga", tipo=p.distancia)
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


# ── Cuentas: registro e inicio de sesión (de PacePath) ─────────────────────
_MENSAJES = {
    "correo_invalido": ("Ese correo no parece válido.", "That email doesn't look valid.", "Esse e-mail não parece válido."),
    "correo_existe": ("Ya hay una cuenta con ese correo: entra con ella.", "There's already an account with that email: sign in.",
                      "Já existe uma conta com esse e-mail: entre com ela."),
    "correo_existe_otro_metodo": ("Ya hay una cuenta con ese correo: entra con el método que usaste al crearla.",
                                  "There's already an account with that email: sign in the way you created it.",
                                  "Já existe uma conta com esse e-mail: entre do jeito que você a criou."),
    "clave_corta": (f"La clave debe tener al menos {cuentas.CLAVE_MIN} caracteres.",
                    f"The password must be at least {cuentas.CLAVE_MIN} characters.",
                    f"A senha precisa ter pelo menos {cuentas.CLAVE_MIN} caracteres."),
    "clave_incorrecta": ("Correo o clave incorrectos.", "Wrong email or password.", "E-mail ou senha incorretos."),
    "demasiados_intentos": ("Demasiados intentos: espera unos minutos.", "Too many attempts: wait a few minutes.",
                            "Muitas tentativas: espere alguns minutos."),
    "bloqueada": ("Esta cuenta está desactivada.", "This account is disabled.", "Esta conta está desativada."),
    "sin_correo": ("Tu cuenta no compartió un correo: prueba otro método.", "Your account didn't share an email: try another method.",
                   "Sua conta não compartilhou um e-mail: tente outro método."),
    "no_existe": ("Esa cuenta no existe.", "That account doesn't exist.", "Essa conta não existe."),
    "usa_google": ("Esta cuenta se creó con Google: entra con «Continuar con Google» (tu clave de Gmail se escribe en "
                   "Google, nunca aquí).", "This account was created with Google: use “Continue with Google” (your Gmail "
                   "password is typed on Google, never here).", "Esta conta foi criada com o Google: use “Continuar com o "
                   "Google” (sua senha do Gmail é digitada no Google, nunca aqui)."),
    "usa_microsoft": ("Esta cuenta se creó con Microsoft: entra con «Continuar con Microsoft».",
                      "This account was created with Microsoft: use “Continue with Microsoft”.",
                      "Esta conta foi criada com a Microsoft: use “Continuar com a Microsoft”."),
    "datos_grandes": ("Tus datos guardados superan el máximo: borra planes anteriores.",
                      "Your saved data is over the limit: delete some past plans.",
                      "Seus dados salvos passaram do limite: apague alguns planos anteriores."),
    "codigo_invalido": ("El enlace venció o ya se usó: pide uno nuevo.", "The link expired or was already used: ask for a new one.",
                        "O link expirou ou já foi usado: peça um novo."),
    "correo_apagado": ("La recuperación por correo todavía no está disponible: escríbenos y te ayudamos.",
                       "Email recovery isn't available yet: write to us and we'll help.",
                       "A recuperação por e-mail ainda não está disponível: escreva para nós e ajudamos você."),
    "falta_consentimiento": ("Para usar FuelPath tienes que aceptar el tratamiento de tus datos de salud.",
                             "To use FuelPath you need to accept the processing of your health data.",
                             "Para usar o FuelPath você precisa aceitar o tratamento dos seus dados de saúde."),
}


def _error_cuenta(exc: cuentas.ErrorCuenta, codigo: int = 400) -> HTTPException:
    es, en_, *pt = _MENSAJES.get(str(exc), (str(exc), str(exc)))
    return HTTPException(codigo, {"codigo": str(exc), "mensaje": tr(es, en_, *pt)})


def _con_sesion(u: dict, request: Request, resp: Response) -> Response:
    if u.get("idioma") != idioma.actual():          # sus correos, en el idioma con que usa la app
        cuentas.actualizar(u["id"], idioma=idioma.actual())
    _poner_cookie(resp, request, cuentas.COOKIE, cuentas.abrir_sesion(u), cuentas.DURACION)
    return resp


def _espera_beta(u: dict) -> bool:
    return acceso.activo() and not u["beta"]


class Registro(BaseModel):
    correo: str = Field(max_length=200)
    clave: str = Field(max_length=200)
    nombre: str | None = Field(default=None, max_length=80)
    consiento: bool = False


class Ingreso(BaseModel):
    correo: str = Field(max_length=200)
    clave: str = Field(max_length=200)


@app.post("/api/auth/registro", include_in_schema=False)
def auth_registro(body: Registro, request: Request) -> Response:
    if not body.consiento:
        raise _error_cuenta(cuentas.ErrorCuenta("falta_consentimiento"))
    try:
        u = cuentas.crear(body.correo, body.nombre, body.clave, idioma=idioma.actual(), consentimiento=True)
    except cuentas.ErrorCuenta as exc:
        _anotar(exito=False, error=str(exc))
        raise _error_cuenta(exc, 409 if str(exc) == "correo_existe" else 400) from exc
    uso.registrar("cuenta_nueva", "correo")
    _mandar_verificacion(u, request)
    if correo.activo():
        correo.en_fondo(correo.aviso_registro, u["correo"], u["nombre"], "correo y clave", _espera_beta(u), lang="es")
    return _con_sesion(u, request, JSONResponse({"usuario": cuentas.publico(u)}))


def _mandar_verificacion(u: dict, request: Request) -> None:
    if not correo.activo():
        return
    try:
        enlace = f"{_base(request)}/api/auth/verificar?codigo={cuentas.nuevo_codigo(u['id'], 'verificar')}"
        correo.verificar(u["correo"], u["nombre"], enlace, _espera_beta(u))
    except Exception as exc:  # noqa: BLE001 — el correo caído no impide crear la cuenta
        _anotar(error=f"no pude mandar el correo de verificación: {type(exc).__name__}: {exc}")


@app.post("/api/auth/reenviar", include_in_schema=False)
def auth_reenviar(request: Request) -> dict:
    u = _usuario(request)
    if not u:
        raise HTTPException(401, "Not signed in")
    if not correo.activo():
        raise _error_cuenta(cuentas.ErrorCuenta("correo_apagado"), 503)
    _mandar_verificacion(u, request)
    return {"ok": True}


@app.get("/api/auth/verificar", include_in_schema=False)
def auth_verificar(codigo: str = "") -> Response:
    try:
        u = cuentas.usar_codigo(codigo, "verificar")
    except cuentas.ErrorCuenta:
        return RedirectResponse("/?cuenta=codigo_invalido")
    u = cuentas.actualizar(u["id"], verificado=True)
    uso.registrar("cuenta_verificada")
    if correo.activo():
        correo.en_fondo(correo.bienvenida, u["correo"], u["nombre"], _espera_beta(u), lang=u["idioma"])
    return RedirectResponse("/?cuenta=verificado")


class PedidoRecuperar(BaseModel):
    correo: str = Field(max_length=200)


@app.post("/api/auth/recuperar", include_in_schema=False)
def auth_recuperar(body: PedidoRecuperar, request: Request) -> dict:
    """Responde lo mismo exista o no la cuenta (que no sirva para averiguar quién está registrado)."""
    if not correo.activo():
        raise _error_cuenta(cuentas.ErrorCuenta("correo_apagado"), 503)
    try:
        u = cuentas.por_correo(cuentas.normalizar_correo(body.correo))
    except cuentas.ErrorCuenta as exc:
        raise _error_cuenta(exc) from exc
    if u and u["activo"]:
        try:
            enlace = f"{_base(request)}/entrar?recuperar={cuentas.nuevo_codigo(u['id'], 'recuperar')}"
            correo.recuperar(u["correo"], u["nombre"], enlace)
        except Exception as exc:  # noqa: BLE001
            _anotar(error=f"no pude mandar el correo de recuperación: {type(exc).__name__}: {exc}")
    return {"ok": True}


class NuevaClave(BaseModel):
    codigo: str = Field(max_length=200)
    clave: str = Field(max_length=200)


@app.post("/api/auth/nueva-clave", include_in_schema=False)
def auth_nueva_clave(body: NuevaClave, request: Request) -> Response:
    if len(body.clave) < cuentas.CLAVE_MIN:
        raise _error_cuenta(cuentas.ErrorCuenta("clave_corta"))
    try:
        u = cuentas.usar_codigo(body.codigo, "recuperar")
        u = cuentas.actualizar(u["id"], clave=body.clave, verificado=True)
    except cuentas.ErrorCuenta as exc:
        raise _error_cuenta(exc) from exc
    uso.registrar("cuenta_nueva_clave")
    return _con_sesion(u, request, JSONResponse({"usuario": cuentas.publico(u)}))


@app.post("/api/auth/entrar", include_in_schema=False)
def auth_entrar(body: Ingreso, request: Request) -> Response:
    try:
        u = cuentas.entrar_con_clave(body.correo, body.clave)
    except cuentas.ErrorCuenta as exc:
        reloj.sleep(1)                       # que adivinar claves sea lento
        _anotar(exito=False, error=str(exc))
        raise _error_cuenta(exc, 429 if str(exc) == "demasiados_intentos" else 401) from exc
    uso.registrar("cuenta_entrar", "correo")
    return _con_sesion(u, request, JSONResponse({"usuario": cuentas.publico(u)}))


@app.post("/api/auth/salir", include_in_schema=False)
def auth_salir(request: Request) -> Response:
    cuentas.cerrar_sesion(request.cookies.get(cuentas.COOKIE))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(cuentas.COOKIE)
    return resp


@app.get("/api/auth/proveedores", include_in_schema=False)
def auth_proveedores() -> dict:
    return oauth.configurados()


COOKIE_IDIOMA_OAUTH = "fp_idioma_oauth"
COOKIE_CONSIENTO_OAUTH = "fp_consiento"


@app.get("/api/auth/{proveedor}", include_in_schema=False)
def auth_ir(proveedor: Literal["google", "microsoft"], request: Request, correo: str = "", consiento: str = "") -> Response:
    if not oauth.configurados()[proveedor]:
        raise HTTPException(503, tr("Ese inicio de sesión no está configurado.", "That sign-in isn't configured.",
                                    "Essa forma de entrar não está configurada."))
    pista = correo.strip()[:200] if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo.strip()) else None
    url, estado = oauth.iniciar(proveedor, f"{_base(request)}/api/auth/{proveedor}/vuelta", pista)
    resp = RedirectResponse(url)
    _poner_cookie(resp, request, oauth.COOKIE_ESTADO, estado, 600)
    _poner_cookie(resp, request, COOKIE_IDIOMA_OAUTH, idioma.actual(), 600)
    if consiento == "1":                     # marcó la casilla antes de ir a Google o Microsoft
        _poner_cookie(resp, request, COOKIE_CONSIENTO_OAUTH, "1", 600)
    return resp


@app.get("/api/auth/{proveedor}/vuelta", include_in_schema=False)
def auth_vuelta(proveedor: Literal["google", "microsoft"], request: Request, code: str | None = None,
                state: str | None = None, error: str | None = None) -> Response:
    idioma.usar(request.cookies.get(COOKIE_IDIOMA_OAUTH))
    if error or not code:
        uso.registrar("cuenta_cancelada", proveedor)
        return RedirectResponse("/?cuenta=cancelada")
    consiento = request.cookies.get(COOKIE_CONSIENTO_OAUTH) == "1"
    try:
        datos = oauth.terminar(proveedor, code, state or "", request.cookies.get(oauth.COOKIE_ESTADO),
                               f"{_base(request)}/api/auth/{proveedor}/vuelta")
        u = cuentas.entrar_con_proveedor(proveedor, datos["sub"], datos["correo"], datos["nombre"],
                                         datos["correo_confiable"], consentimiento=consiento)
        if consiento and not u.get("consentimiento"):
            u = cuentas.actualizar(u["id"], consentimiento=cuentas._ahora()) | {"nueva": u.get("nueva", False)}
    except cuentas.ErrorCuenta as exc:
        uso.registrar("cuenta_error", proveedor, str(exc), exito=False)
        return RedirectResponse(f"/?cuenta={exc}")
    except oauth.ErrorOAuth as exc:
        uso.registrar("cuenta_error", proveedor, exito=False)
        _anotar(error=str(exc))
        return RedirectResponse("/?cuenta=error")
    uso.registrar("cuenta_entrar", proveedor)
    if u.get("nueva") and correo.activo():
        correo.en_fondo(correo.bienvenida, u["correo"], u["nombre"], _espera_beta(u), lang=u["idioma"])
        correo.en_fondo(correo.aviso_registro, u["correo"], u["nombre"], proveedor.capitalize(), _espera_beta(u),
                        lang="es")
    resp = _con_sesion(u, request, RedirectResponse("/"))
    resp.delete_cookie(oauth.COOKIE_ESTADO)
    resp.delete_cookie(COOKIE_CONSIENTO_OAUTH)
    return resp


@app.get("/entrar", include_in_schema=False)
def pagina_entrar() -> FileResponse:
    return FileResponse(WEB / "entrar.html", headers={"Cache-Control": "no-store"})


@app.get("/api/cuenta", include_in_schema=False)
def cuenta(request: Request) -> dict:
    """Quién soy (si hay sesión), si puedo usar la app y qué opciones hay."""
    u = _usuario(request)
    if u and request.headers.get("x-idioma") and u.get("idioma") != idioma.actual():
        u = cuentas.actualizar(u["id"], idioma=idioma.actual())     # cambió el idioma de la app
    return {"usuario": cuentas.publico(u) if u else None, "pendiente": _pendiente(u),
            "beta_cerrada": acceso.activo(), "proveedores": oauth.configurados(),
            "correo_activo": correo.activo(), "libre": os.environ.get("FUELPATH_ACCESO_LIBRE") == "1"}


class Consentimiento(BaseModel):
    acepto: Literal[True]


@app.post("/api/cuenta/consentimiento", include_in_schema=False)
def cuenta_consentimiento(body: Consentimiento, request: Request) -> dict:
    """Quien entró con Google o Microsoft sin marcar la casilla la acepta aquí."""
    u = _usuario(request)
    if not u:
        raise HTTPException(401, "Not signed in")
    u = cuentas.actualizar(u["id"], consentimiento=cuentas._ahora())
    uso.registrar("cuenta_consentimiento")
    return {"usuario": cuentas.publico(u), "pendiente": _pendiente(u)}


# ── Lo que viaja con la cuenta: los datos del teléfono (como DATOS_CUENTA de PacePath)
DATOS_CUENTA = {"fp_perfil", "fp_plan", "fp_agua", "fp_historial", "fp_idioma", "fp_noche"}


class DatosCuenta(BaseModel):
    datos: dict[str, str]


@app.get("/api/cuenta/datos", include_in_schema=False)
def cuenta_datos(request: Request) -> dict:
    u = _usuario(request)
    if not u:
        raise HTTPException(401, "Not signed in")
    datos, ts = cuentas.datos_de(u["id"])
    return {"datos": datos, "actualizado": ts}


@app.put("/api/cuenta/datos", include_in_schema=False)
def cuenta_guardar_datos(body: DatosCuenta, request: Request) -> dict:
    u = _usuario(request)
    if not u:
        raise HTTPException(401, "Not signed in")
    try:
        ts = cuentas.guardar_datos(u["id"], {k: v for k, v in body.datos.items() if k in DATOS_CUENTA})
    except cuentas.ErrorCuenta as exc:
        raise _error_cuenta(exc, 413) from exc
    return {"actualizado": ts}


# ── Tus datos (Ley 19.628 y 21.719 de Chile, GDPR): descargarlos y borrar la cuenta
@app.get("/api/cuenta/exportar", include_in_schema=False)
def cuenta_exportar(request: Request) -> Response:
    u = _usuario(request)
    if not u:
        raise HTTPException(401, "Not signed in")
    registro.vaciar()
    datos, ts = cuentas.datos_de(u["id"])
    leidos = {}
    for k, v in datos.items():
        try:
            leidos[k] = json.loads(v)
        except ValueError:
            leidos[k] = v
    eventos = registro.sql("SELECT ts, consulta, evento, tipo, detalle, exito FROM fp_eventos "
                           "WHERE cuenta = ? ORDER BY ts", (u["id"],), traer=True)
    cuerpo = {"generado": registro.ahora()[0], "cuenta": cuentas.publico(u) | {"idioma": u.get("idioma")},
              "datos": {"contenido": leidos, "actualizado": ts},
              "uso": [dict(zip(("ts", "consulta", "evento", "tipo", "detalle", "exito"), f)) for f in eventos]}
    return Response(json.dumps(cuerpo, ensure_ascii=False, indent=2), media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="fuelpath-mis-datos.json"'})


class BorrarCuenta(BaseModel):
    confirmo: Literal[True]


@app.post("/api/cuenta/borrar", include_in_schema=False)
def cuenta_borrar(body: BorrarCuenta, request: Request) -> Response:
    """Borra tu cuenta y todo lo suyo: datos, sesiones y tu nombre en el registro de uso."""
    u = _usuario(request)
    if not u:
        raise HTTPException(401, "Not signed in")
    cuentas.borrar(u["id"])
    uso.registrar("cuenta_borrada")
    if (info := uso.consulta.get()) is not None:
        info["cuenta"] = None                 # ni esta última consulta queda ligada a la cuenta
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(cuentas.COOKIE)
    return resp


# ── Panel /admin (clave en la cabecera X-Admin-Clave = FUELPATH_ADMIN) ──────
def _es_admin(clave: str) -> bool:
    admin = os.environ.get("FUELPATH_ADMIN", "")
    return bool(admin) and secrets.compare_digest(clave.encode(), admin.encode())


def _solo_admin(request: Request) -> None:
    if not _es_admin(request.headers.get("x-admin-clave", "")):
        reloj.sleep(1)                       # que adivinar la clave sea lento
        raise HTTPException(404, "Not Found")


@app.get("/admin", include_in_schema=False)
def panel_admin() -> FileResponse:
    return FileResponse(WEB / "admin.html", headers={"X-Robots-Tag": "noindex", "Cache-Control": "no-store"})


@app.get("/api/admin/eventos", include_in_schema=False)
def admin_eventos(request: Request, desde: str | None = None, hasta: str | None = None) -> dict:
    _solo_admin(request)
    hoy = date.fromisoformat(registro.hoy())
    try:
        d = date.fromisoformat(desde) if desde else hoy - timedelta(days=29)
        h = date.fromisoformat(hasta) if hasta else hoy
    except ValueError as exc:
        raise HTTPException(422, "Fechas en formato AAAA-MM-DD.") from exc
    return registro.consultar(d.isoformat(), h.isoformat())


def _estado_acceso() -> dict:
    return acceso.estado() | {"correo_activo": correo.activo(), "correo_estado": correo.estado,
                              "correo_faltan": correo.faltan(), "proveedores": oauth.configurados(),
                              "url": os.environ.get("FUELPATH_URL", ""),
                              "libre": os.environ.get("FUELPATH_ACCESO_LIBRE") == "1"}


class AjustesAcceso(BaseModel):
    activo: bool | None = None


@app.get("/api/admin/acceso", include_in_schema=False)
def admin_acceso(request: Request) -> dict:
    _solo_admin(request)
    return _estado_acceso()


@app.post("/api/admin/acceso", include_in_schema=False)
def admin_cambiar_acceso(body: AjustesAcceso, request: Request) -> dict:
    _solo_admin(request)
    try:
        acceso.configurar(body.activo)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"No pude guardar en la base de datos: {type(exc).__name__}") from exc
    return _estado_acceso()


class PruebaCorreo(BaseModel):
    para: str = Field(max_length=200)


@app.post("/api/admin/correo/prueba", include_in_schema=False)
def admin_prueba_correo(body: PruebaCorreo, request: Request) -> dict:
    _solo_admin(request)
    if not correo.activo():
        raise HTTPException(503, {"mensaje": "El envío está apagado. En Render falta: " + ", ".join(correo.faltan())})
    try:
        correo.prueba(cuentas.normalizar_correo(body.para))
    except cuentas.ErrorCuenta as exc:
        raise _error_cuenta(exc) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, {"mensaje": f"No se pudo mandar: {type(exc).__name__}: {exc}"}) from exc
    return {"ok": True}


@app.get("/api/admin/consumo", include_in_schema=False)
def admin_consumo(request: Request) -> dict:
    """Tamaño de la base (vs 0,5 GB de Neon gratis) y el correo de cada cuenta (el registro guarda sólo su id)."""
    _solo_admin(request)
    return {"base": registro.tamanos(), "cuentas": {u["id"]: u["correo"] for u in cuentas.listar()}}


class NuevoUsuario(BaseModel):
    correo: str = Field(max_length=200)
    nombre: str | None = Field(default=None, max_length=80)
    clave: str | None = Field(default=None, max_length=200)
    beta: bool = False
    avisar: bool = True


class CambioUsuario(BaseModel):
    correo: str | None = Field(default=None, max_length=200)
    nombre: str | None = Field(default=None, max_length=80)
    clave: str | None = Field(default=None, max_length=200)
    beta: bool | None = None
    activo: bool | None = None
    avisar: bool = True


@app.get("/api/admin/usuarios", include_in_schema=False)
def admin_usuarios(request: Request) -> list[dict]:
    _solo_admin(request)
    return cuentas.listar()


@app.post("/api/admin/usuarios", include_in_schema=False)
def admin_crear_usuario(body: NuevoUsuario, request: Request) -> dict:
    """Crear una cuenta para habilitar a un tester antes de que entre (al entrar con ese correo, queda vinculada).
    El consentimiento lo da la persona al entrar: no se marca aquí."""
    _solo_admin(request)
    try:
        u = cuentas.crear(body.correo, body.nombre, body.clave or None, beta=body.beta)
    except cuentas.ErrorCuenta as exc:
        raise _error_cuenta(exc, 409 if str(exc) == "correo_existe" else 400) from exc
    if body.beta and body.avisar and acceso.activo() and correo.activo():
        correo.en_fondo(correo.acceso_beta, u["correo"], u["nombre"], True)
    return cuentas.publico(u)


@app.patch("/api/admin/usuarios/{uid}", include_in_schema=False)
def admin_cambiar_usuario(uid: str, body: CambioUsuario, request: Request) -> dict:
    _solo_admin(request)
    antes = cuentas.por_id(uid)
    try:
        u = cuentas.actualizar(uid, **body.model_dump(exclude_none=True, exclude={"avisar"}))
    except cuentas.ErrorCuenta as exc:
        raise _error_cuenta(exc, 404 if str(exc) == "no_existe" else 409 if str(exc) == "correo_existe" else 400) from exc
    if (antes and not antes["beta"] and u["beta"] and u["activo"] and body.avisar
            and acceso.activo() and correo.activo()):
        nunca_entro = not (u.get("clave") or u.get("google") or u.get("microsoft"))
        correo.en_fondo(correo.acceso_beta, u["correo"], u["nombre"], nunca_entro, lang=u["idioma"])
    return cuentas.publico(u)


@app.delete("/api/admin/usuarios/{uid}", include_in_schema=False)
def admin_borrar_usuario(uid: str, request: Request) -> dict:
    _solo_admin(request)
    if not cuentas.por_id(uid):
        raise HTTPException(404, "Not Found")
    cuentas.borrar(uid)
    return {"ok": True}


def _pagina_legal(nombre: str) -> HTMLResponse:
    """Las páginas legales llevan el correo de soporte (FUELPATH_SOPORTE o el remitente), que no va en el repo."""
    html = (WEB / nombre).read_text(encoding="utf-8")
    sop = correo.soporte()
    html = html.replace('<a href="mailto:{{SOPORTE}}">{{SOPORTE}}</a>', f'<a href="mailto:{sop}">{sop}</a>' if sop
                        else tr("el correo con que te escribimos", "the address we email you from", "o e-mail que te enviamos"))
    return HTMLResponse(html)


@app.get("/privacidad", include_in_schema=False)
@app.get("/privacy", include_in_schema=False)
def privacidad() -> HTMLResponse:
    return _pagina_legal("privacidad.html")


@app.get("/terminos", include_in_schema=False)
@app.get("/terms", include_in_schema=False)
def terminos() -> HTMLResponse:
    return _pagina_legal("terminos.html")


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(WEB / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js")
def sw():
    return FileResponse(WEB / "sw.js", media_type="text/javascript", headers={"Cache-Control": "no-cache"})


@app.get("/")
def inicio():
    return FileResponse(WEB / "index.html", headers={"Cache-Control": "no-cache"})
