"""Cuentas (correo, Google, Microsoft), consentimiento, beta, datos que viajan y panel.

Adaptado de los tests de PacePath (tests/test_acceso.py, commit 58ecb41).
"""
import contextvars
import io
import json
import re
import urllib.error

import pytest
from fastapi.testclient import TestClient

from fuelpath import acceso, api, correo, cuentas, idioma, oauth, registro
from fuelpath.api import app

ADMIN = {"X-Admin-Clave": "clave-larga-de-prueba"}
CARGA = {"fecha": "2027-04-25", "hora": "07:00", "peso_kg": 68, "distancia": "42k", "tiempo_min": 185}


@pytest.fixture
def base(monkeypatch, tmp_path):
    """Base nueva (como un servidor recién desplegado), beta activa, sin acceso libre."""
    monkeypatch.setenv("FUELPATH_ADMIN", "clave-larga-de-prueba")
    monkeypatch.delenv("FUELPATH_ACCESO_LIBRE", raising=False)
    monkeypatch.delenv("FUELPATH_URL", raising=False)
    for k in ("FUELPATH_CORREO_ACTIVO", "GOOGLE_CLIENT_ID", "MICROSOFT_CLIENT_ID"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(api.reloj, "sleep", lambda s: None)
    anterior = registro._escritor
    registro.configurar(str(tmp_path / "base.sqlite"))
    acceso.olvidar()
    cuentas._sesiones.clear()
    cuentas._intentos.clear()
    yield
    registro._escritor = anterior
    acceso.olvidar()
    cuentas._sesiones.clear()
    idioma.usar("es")


def registrar(cli, correo_="ana@ejemplo.cl", clave="corre-mucho-2026", nombre="Ana", consiento=True):
    return cli.post("/api/auth/registro", json={"correo": correo_, "clave": clave, "nombre": nombre, "consiento": consiento})


def habilitar(cli, correo_="ana@ejemplo.cl"):
    uid = next(u["id"] for u in cli.get("/api/admin/usuarios", headers=ADMIN).json() if u["correo"] == correo_)
    cli.patch(f"/api/admin/usuarios/{uid}", headers=ADMIN, json={"beta": True})
    return uid


def test_sin_cuenta_se_ve_la_entrada_y_la_api_responde_401(base):
    cli = TestClient(app)
    r = cli.get("/")
    assert r.status_code == 200 and 'id="ingreso"' in r.text
    assert cli.post("/api/carga", json=CARGA).status_code == 401
    assert cli.get("/api/cuenta").json()["pendiente"] == "sin_sesion"


def test_registro_pide_consentimiento_y_beta(base):
    cli = TestClient(app)
    r = registrar(cli, consiento=False)
    assert r.status_code == 400 and r.json()["detail"]["codigo"] == "falta_consentimiento"
    r = registrar(cli)
    assert r.status_code == 200 and r.json()["usuario"]["beta"] is False and r.json()["usuario"]["consentimiento"]
    assert cli.get("/api/cuenta").json()["pendiente"] == "beta"
    assert cli.post("/api/carga", json=CARGA).status_code == 401
    habilitar(cli)
    assert cli.get("/api/cuenta").json()["pendiente"] is None
    assert cli.post("/api/carga", json=CARGA).status_code == 200
    assert 'id="ingreso"' not in cli.get("/").text
    # Beta abierta: cualquiera con cuenta entra; sin cuenta, no.
    cli.post("/api/admin/acceso", headers=ADMIN, json={"activo": False})
    otro = TestClient(app)
    registrar(otro, correo_="beto@ejemplo.cl")
    assert otro.post("/api/carga", json=CARGA).status_code == 200
    assert TestClient(app).post("/api/carga", json=CARGA).status_code == 401


def test_entrar_salir_y_errores(base):
    cli = TestClient(app)
    registrar(cli)
    assert registrar(TestClient(app)).status_code == 409                     # correo repetido
    assert registrar(TestClient(app), correo_="x@y.cl", clave="corta").status_code == 400
    assert cli.post("/api/auth/salir").json() == {"ok": True}
    assert cli.get("/api/cuenta").json()["usuario"] is None
    mal = cli.post("/api/auth/entrar", json={"correo": "ana@ejemplo.cl", "clave": "otra-clave-x"})
    assert mal.status_code == 401 and mal.json()["detail"]["mensaje"] == "Correo o clave incorrectos."
    assert cli.post("/api/auth/entrar", json={"correo": "ANA@ejemplo.cl ", "clave": "corre-mucho-2026"}).status_code == 200
    for _ in range(6):
        cli.post("/api/auth/entrar", json={"correo": "ana@ejemplo.cl", "clave": "mala-mala-mala"})
    assert cli.post("/api/auth/entrar", json={"correo": "ana@ejemplo.cl", "clave": "corre-mucho-2026"}).status_code == 429


def test_crud_del_panel(base):
    cli = TestClient(app)
    assert cli.get("/api/admin/usuarios").status_code == 404                  # sin clave
    u = cli.post("/api/admin/usuarios", headers=ADMIN, json={"correo": "tester@ejemplo.cl", "beta": True}).json()
    assert u["beta"] and u["metodos"] == [] and u["consentimiento"] is None
    assert cli.patch(f"/api/admin/usuarios/{u['id']}", headers=ADMIN, json={"activo": False}).json()["activo"] is False
    assert cli.patch(f"/api/admin/usuarios/{u['id']}", headers=ADMIN, json={"clave": "nueva-clave-2026"}).status_code == 200
    assert cli.post("/api/auth/entrar", json={"correo": "tester@ejemplo.cl", "clave": "nueva-clave-2026"}).status_code == 401
    assert cli.delete(f"/api/admin/usuarios/{u['id']}", headers=ADMIN).json() == {"ok": True}
    assert cli.get("/api/admin/usuarios", headers=ADMIN).json() == []
    a = cli.get("/api/admin/acceso", headers=ADMIN).json()
    assert a["activo"] is True and a["correo_activo"] is False and "FUELPATH_CORREO_ACTIVO=1" in a["correo_faltan"]
    assert cli.get("/api/admin/consumo", headers=ADMIN).json()["base"]["almacen"] == "sqlite"


def _vuelta(monkeypatch, datos):
    monkeypatch.setattr(oauth, "configurados", lambda: {"google": True, "microsoft": True})
    monkeypatch.setattr(oauth, "terminar", lambda *a, **k: datos)


def test_google_con_consentimiento_y_vinculo_por_correo(base, monkeypatch):
    cli = TestClient(app)
    cli.post("/api/admin/usuarios", headers=ADMIN, json={"correo": "maria@gmail.com", "beta": True})
    _vuelta(monkeypatch, {"sub": "g-1", "correo": "maria@gmail.com", "nombre": "María", "correo_confiable": True})
    r = cli.get("/api/auth/google?consiento=1", follow_redirects=False)        # marcó la casilla antes de ir
    assert r.status_code == 307 and cli.cookies.get(api.COOKIE_CONSIENTO_OAUTH) == "1"
    r = cli.get("/api/auth/google/vuelta?code=x&state=y", follow_redirects=False)
    assert r.headers["location"] == "/"
    c = cli.get("/api/cuenta").json()
    assert c["pendiente"] is None and c["usuario"]["consentimiento"] and "google" in c["usuario"]["metodos"]


def test_google_sin_casilla_pide_consentimiento_despues(base, monkeypatch):
    cli = TestClient(app)
    cli.post("/api/admin/acceso", headers=ADMIN, json={"activo": False})
    _vuelta(monkeypatch, {"sub": "g-2", "correo": "pedro@gmail.com", "nombre": "Pedro", "correo_confiable": True})
    cli.get("/api/auth/google/vuelta?code=x&state=y", follow_redirects=False)
    assert cli.get("/api/cuenta").json()["pendiente"] == "consentimiento"
    assert cli.post("/api/carga", json=CARGA).status_code == 401
    assert cli.post("/api/cuenta/consentimiento", json={"acepto": False}).status_code == 422
    assert cli.post("/api/cuenta/consentimiento", json={"acepto": True}).json()["pendiente"] is None
    assert cli.post("/api/carga", json=CARGA).status_code == 200


def test_microsoft_de_empresa_no_vincula_por_correo(base, monkeypatch):
    cli = TestClient(app)
    cli.post("/api/admin/usuarios", headers=ADMIN, json={"correo": "jefe@ejemplo.cl", "beta": True})
    _vuelta(monkeypatch, {"sub": "m-1", "correo": "jefe@ejemplo.cl", "nombre": "X", "correo_confiable": False})
    r = cli.get("/api/auth/microsoft/vuelta?code=x&state=y", follow_redirects=False)
    assert r.headers["location"] == "/?cuenta=correo_existe_otro_metodo"


def test_estado_oauth_y_paginas_abiertas(base, monkeypatch):
    cli = TestClient(app)
    for ruta in ("/entrar", "/admin", "/privacidad", "/terminos", "/api/salud", "/api/cuenta", "/api/auth/proveedores",
                 "/manifest.webmanifest", "/sw.js"):
        assert cli.get(ruta).status_code == 200, ruta
    assert cli.get("/api/auth/google", follow_redirects=False).status_code == 503   # sin credenciales
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secreto")
    r = cli.get("/api/auth/google", follow_redirects=False)
    assert "accounts.google.com" in r.headers["location"] and "code_challenge" in r.headers["location"]
    estado = cli.cookies.get(oauth.COOKIE_ESTADO)
    assert estado.startswith("google.") and oauth.COOKIE_ESTADO == "fp_oauth"
    with pytest.raises(oauth.ErrorOAuth):
        oauth.terminar("google", "code", "otro-estado", estado, "http://x/vuelta")


def test_datos_viajan_con_la_cuenta(base):
    cli = TestClient(app)
    registrar(cli)
    habilitar(cli)
    plan = json.dumps({"evento": "MDS", "dias": []})
    r = cli.put("/api/cuenta/datos", json={"datos": {"fp_plan": plan, "fp_idioma": '"es"', "otra_cosa": "x"}})
    assert r.status_code == 200 and r.json()["actualizado"]
    otro_aparato = TestClient(app)
    otro_aparato.post("/api/auth/entrar", json={"correo": "ana@ejemplo.cl", "clave": "corre-mucho-2026"})
    j = otro_aparato.get("/api/cuenta/datos").json()
    assert j["datos"] == {"fp_plan": plan, "fp_idioma": '"es"'}                 # sólo lo de DATOS_CUENTA
    grande = cli.put("/api/cuenta/datos", json={"datos": {"fp_historial": "x" * (cuentas.DATOS_MAX + 1)}})
    assert grande.status_code == 413


def test_descargar_y_borrar_mi_cuenta(base):
    cli = TestClient(app)
    registrar(cli)
    habilitar(cli)
    cli.put("/api/cuenta/datos", json={"datos": {"fp_perfil": json.dumps({"peso": 68})}})
    cli.post("/api/carga", json=CARGA)
    r = cli.get("/api/cuenta/exportar")
    j = r.json()
    assert "attachment" in r.headers["content-disposition"]
    assert j["cuenta"]["correo"] == "ana@ejemplo.cl" and j["datos"]["contenido"]["fp_perfil"] == {"peso": 68}
    assert any(e["consulta"] == "carga" for e in j["uso"])
    assert cli.post("/api/cuenta/borrar", json={"confirmo": False}).status_code == 422
    assert cli.post("/api/cuenta/borrar", json={"confirmo": True}).json() == {"ok": True}
    assert cli.get("/api/admin/usuarios", headers=ADMIN).json() == []
    registro.vaciar()
    assert registro.sql("SELECT COUNT(*) FROM fp_eventos WHERE cuenta IS NOT NULL", (), traer=True)[0][0] == 0


def test_registro_de_consultas_en_el_panel(base):
    cli = TestClient(app)
    registrar(cli)
    habilitar(cli)
    cli.post("/api/carga", json=CARGA)
    cli.get("/api/salud")                                                     # no se registra
    j = cli.get("/api/admin/eventos", headers=ADMIN).json()
    filas = [dict(zip(j["columnas"], f)) for f in j["filas"]]
    carga = [f for f in filas if f["consulta"] == "carga"]
    assert carga and carga[0]["tipo"] == "42k" and carga[0]["cuenta"] and carga[0]["exito"] == 1
    assert not any(f["consulta"] == "salud" for f in filas)
    assert "peso" not in json.dumps(filas)                                    # nada de datos de salud en el registro


@pytest.fixture
def con_correo(base, monkeypatch):
    for k, v in {"FUELPATH_CORREO_ACTIVO": "1", "FUELPATH_CORREO_SMTP": "smtp.x:465", "FUELPATH_CORREO_USUARIO": "u",
                 "FUELPATH_CORREO_CLAVE": "c", "FUELPATH_CORREO_DE": "FuelPath <hola@fuelpath.test>"}.items():
        monkeypatch.setenv(k, v)
    enviados = []
    monkeypatch.setattr(correo, "enviar", lambda para, asunto, texto, html_=None, responder_a=None: enviados.append((para, asunto, texto)))

    def al_tiro(fn, *a, lang=None):
        ctx = contextvars.copy_context()
        if lang:
            ctx.run(idioma.usar, lang)
        ctx.run(fn, *a)
    monkeypatch.setattr(correo, "en_fondo", al_tiro)
    return enviados


def _enlace(texto):
    return re.search(r"https?://\S+", texto).group(0)


def test_verificar_correo(con_correo):
    cli = TestClient(app)
    cli.post("/api/admin/acceso", headers=ADMIN, json={"activo": False})
    registrar(cli)
    assert cli.get("/api/cuenta").json()["pendiente"] == "verificar"
    para, asunto, texto = con_correo[-1]
    assert para == "ana@ejemplo.cl" and "Confirma" in asunto and "FuelPath" in asunto
    r = cli.get(_enlace(texto).replace("http://testserver", ""), follow_redirects=False)
    assert r.headers["location"] == "/?cuenta=verificado"
    assert cli.get("/api/cuenta").json()["pendiente"] is None
    assert any("Bienvenido a FuelPath" in t for _, _, t in con_correo)


def test_recuperar_clave(con_correo):
    cli = TestClient(app)
    registrar(cli)
    assert cli.post("/api/auth/recuperar", json={"correo": "nadie@ejemplo.cl"}).json() == {"ok": True}   # no delata
    cli.post("/api/auth/recuperar", json={"correo": "ana@ejemplo.cl"})
    codigo = _enlace(con_correo[-1][2]).split("recuperar=")[1]
    otro = TestClient(app)
    assert otro.post("/api/auth/nueva-clave", json={"codigo": codigo, "clave": "clave-nueva-2026"}).status_code == 200
    assert otro.post("/api/auth/nueva-clave", json={"codigo": codigo, "clave": "otra-clave-2026"}).status_code == 400
    assert cli.get("/api/cuenta").json()["usuario"] is None                    # la sesión vieja se cerró


def test_correo_dice_que_falta(monkeypatch):
    for k in ("FUELPATH_CORREO_ACTIVO", *correo.VARIABLES):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("FUELPATH_CORREO_ACTIVO", "true")                       # tiene que ser «1»
    monkeypatch.setenv("FUELPATH_CORREO_SMTP", "smtp.resend.com:465")
    assert correo.faltan() == ["FUELPATH_CORREO_ACTIVO=1", "FUELPATH_CORREO_USUARIO", "FUELPATH_CORREO_CLAVE", "FUELPATH_CORREO_DE"]
    for k, v in {"FUELPATH_CORREO_ACTIVO": "1", "FUELPATH_CORREO_USUARIO": "resend", "FUELPATH_CORREO_CLAVE": "x",
                 "FUELPATH_CORREO_DE": "FuelPath <hola@fuelpath.test>"}.items():
        monkeypatch.setenv(k, v)
    assert correo.faltan() == [] and correo.activo() and correo.soporte() == "hola@fuelpath.test"


def test_plantilla_de_correo(monkeypatch):
    monkeypatch.setenv("FUELPATH_CORREO_DE", "FuelPath <hola@fuelpath.test>")
    texto, html = correo._correo("¡Registro exitoso!", ["Hola, <Ana>:"], ("Abrir FuelPath", "https://fuelpath.test"))
    assert "&lt;Ana&gt;" in html and "<Ana>" not in html
    for enlace in ("/terminos", "/privacidad", "mailto:hola@fuelpath.test"):
        assert enlace in html
    assert "PacePath" not in html and "pacepathapp" not in html


def test_resend_por_https_y_prueba_desde_el_panel(base, monkeypatch):
    for k, v in {"FUELPATH_CORREO_ACTIVO": "1", "FUELPATH_CORREO_SMTP": "smtp.resend.com:465", "FUELPATH_CORREO_USUARIO": "resend",
                 "FUELPATH_CORREO_CLAVE": "re_x", "FUELPATH_CORREO_DE": "FuelPath <hola@fuelpath.test>"}.items():
        monkeypatch.setenv(k, v)
    pedidos = []

    class R(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    def urlopen(req, timeout):
        pedidos.append(req)
        if json.loads(req.data)["to"] == ["mal@ejemplo.cl"]:
            raise urllib.error.HTTPError(req.full_url, 403, "x", {}, io.BytesIO(b'{"message":"domain is not verified"}'))
        return R(b'{"id":"1"}')
    monkeypatch.setattr(correo.urllib.request, "urlopen", urlopen)
    cli = TestClient(app)
    assert cli.post("/api/admin/correo/prueba", json={"para": "yo@ejemplo.cl"}).status_code == 404
    assert cli.post("/api/admin/correo/prueba", headers=ADMIN, json={"para": "yo@ejemplo.cl"}).json() == {"ok": True}
    assert pedidos[-1].full_url == "https://api.resend.com/emails"
    r = cli.post("/api/admin/correo/prueba", headers=ADMIN, json={"para": "mal@ejemplo.cl"})
    assert r.status_code == 502 and "not verified" in r.json()["detail"]["mensaje"]


def test_dominio_propio_y_head(base, monkeypatch):
    c = TestClient(app, base_url="https://fuelpath.onrender.com")
    monkeypatch.setenv("FUELPATH_URL", "https://fuelpath.example")
    r = c.get("/privacidad?lang=en", follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == "https://fuelpath.example/privacidad?lang=en"
    assert c.get("/api/salud").status_code == 200                              # la API no se mueve
    assert TestClient(app).head("/privacidad").status_code == 200


def test_paginas_con_barra_final(base):
    cli = TestClient(app)
    r = cli.get("/admin/", follow_redirects=False)
    assert r.status_code == 308 and r.headers["location"] == "/admin"
    assert "Panel de FuelPath" in cli.get("/admin/").text
    assert cli.get("/privacidad/?lang=en", follow_redirects=False).headers["location"] == "/privacidad?lang=en"
