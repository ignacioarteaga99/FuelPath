"""Correos de la app: verificar la cuenta, recuperar la clave, bienvenida,
acceso a la beta y el aviso al equipo de cada registro nuevo.

Copiado de PacePath (pacepath/correo.py, commit 58ecb41) y adaptado: variables
FUELPATH_CORREO_*, marca y consejos de FuelPath; sin los correos de rutas.

Todos con la misma plantilla (logo, tarjeta, botón naranjo y al pie los
enlaces de la app: Términos y Privacidad), en HTML con su versión en texto plano.

APAGADO hasta configurar el remitente del dominio propio en Resend (o SMTP).
Lección de PacePath: FUELPATH_CORREO_ACTIVO tiene que ser «1» y deben estar
las cuatro variables; si falta alguna, `faltan()` dice cuál (el panel la muestra).

  FUELPATH_CORREO_ACTIVO=1             lo enciende (sin esto no se manda nada)
  FUELPATH_CORREO_SMTP=smtp.resend.com:465
  FUELPATH_CORREO_USUARIO=resend       usuario SMTP del servicio
  FUELPATH_CORREO_CLAVE=…              clave o API key (nunca en el repo)
  FUELPATH_CORREO_DE=FuelPath <hola@tu-dominio>
  FUELPATH_CORREO_AVISOS=…             (opcional) a quién avisar de cada cuenta nueva

Mientras esté apagado: no se pide verificar el correo para entrar y la opción
«¿Olvidaste tu clave?» no aparece (el admin puede poner una clave nueva).
"""
from __future__ import annotations

import contextvars
import html
import json
import os
import smtplib
import ssl
import threading
import time
import urllib.error
import urllib.request
from email.message import EmailMessage
from email.utils import make_msgid

from . import idioma
from .idioma import tr


VARIABLES = ("FUELPATH_CORREO_SMTP", "FUELPATH_CORREO_USUARIO", "FUELPATH_CORREO_CLAVE", "FUELPATH_CORREO_DE")


def activo() -> bool:
    return not faltan()


def faltan() -> list[str]:
    """Qué le falta al envío para encenderse (sólo los nombres, nunca los valores)."""
    out = [] if os.environ.get("FUELPATH_CORREO_ACTIVO", "").strip() == "1" else ["FUELPATH_CORREO_ACTIVO=1"]
    return out + [k for k in VARIABLES if not os.environ.get(k, "").strip()]


def enviar(para: str, asunto: str, texto: str, html_: str | None = None, responder_a: str | None = None) -> None:
    if not activo():
        raise RuntimeError("el envío de correos está apagado")
    host, _, puerto = os.environ["FUELPATH_CORREO_SMTP"].partition(":")
    try:
        # Render gratis no deja salir conexiones a los puertos SMTP (25/465/587):
        # con Resend se manda por su API web (HTTPS), con la misma clave.
        if "resend" in host:
            _por_resend(para, asunto, texto, html_, responder_a)
        else:
            _por_smtp(host, int(puerto or 465), para, asunto, texto, html_, responder_a)
    except Exception as exc:
        estado.update(error=f"{type(exc).__name__}: {exc}"[:300], error_ts=time.time())
        print(f"[correo] falló «{asunto}»: {estado['error']}", flush=True)
        raise
    estado.update(ok_ts=time.time(), error=None)
    print(f"[correo] enviado «{asunto}» a …@{para.rpartition('@')[2]} (por {'Resend' if 'resend' in host else host})", flush=True)


# Último envío (en memoria), para mostrarlo en el panel.
estado: dict = {"ok_ts": None, "error": None, "error_ts": None}


def _por_resend(para: str, asunto: str, texto: str, html_: str | None, responder_a: str | None = None) -> None:
    cuerpo = {"from": os.environ["FUELPATH_CORREO_DE"], "to": [para], "subject": asunto, "text": texto}
    if responder_a:
        cuerpo["reply_to"] = responder_a
    if html_:
        cuerpo["html"] = html_
    req = urllib.request.Request("https://api.resend.com/emails", data=json.dumps(cuerpo).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {os.environ['FUELPATH_CORREO_CLAVE']}",
                                          "Content-Type": "application/json", "User-Agent": "FuelPath/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            r.read()
    except urllib.error.HTTPError as exc:
        detalle = exc.read().decode("utf-8", "replace")[:300]
        try:
            detalle = json.loads(detalle).get("message", detalle)
        except ValueError:
            pass
        raise RuntimeError(f"Resend respondió {exc.code}: {detalle}") from None


def _por_smtp(host: str, puerto: int, para: str, asunto: str, texto: str, html_: str | None,
              responder_a: str | None = None) -> None:
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = os.environ["FUELPATH_CORREO_DE"], para, asunto
    if responder_a:
        m["Reply-To"] = responder_a
    m["Message-ID"] = make_msgid(domain=(soporte().rpartition("@")[2] or "fuelpath.app"))
    m.set_content(texto)
    if html_:
        m.add_alternative(html_, subtype="html")
    contexto = ssl.create_default_context()
    if puerto in (465, 2465):
        with smtplib.SMTP_SSL(host, puerto, context=contexto, timeout=15) as s:
            s.login(os.environ["FUELPATH_CORREO_USUARIO"], os.environ["FUELPATH_CORREO_CLAVE"])
            s.send_message(m)
    else:
        with smtplib.SMTP(host, puerto, timeout=15) as s:
            s.starttls(context=contexto)
            s.login(os.environ["FUELPATH_CORREO_USUARIO"], os.environ["FUELPATH_CORREO_CLAVE"])
            s.send_message(m)


def en_fondo(fn, *args, lang: str | None = None) -> None:
    """Manda sin hacer esperar al pedido. En `lang` (el idioma de la cuenta:
    es/en) o, si no se sabe, en el del pedido. Un error sólo queda en el log:
    el correo caído no debe romper nada."""
    ctx = contextvars.copy_context()
    if lang:
        ctx.run(idioma.usar, lang)

    def correr():
        try:
            ctx.run(fn, *args)
        except Exception as exc:  # noqa: BLE001
            print(f"[correo] no pude mandar {getattr(fn, '__name__', fn)}: {type(exc).__name__}: {exc}", flush=True)
    threading.Thread(target=correr, name="correo", daemon=True).start()


# ── Plantilla ───────────────────────────────────────────────────────────────
ACENTO, TINTA, SUAVE, FONDO = "#f2541b", "#1d1d21", "#6b6b75", "#f4f4f6"


def _base() -> str:
    return os.environ.get("FUELPATH_URL", "https://fuelpath.onrender.com").rstrip("/")


def soporte() -> str:
    """A quién escribir: FUELPATH_SOPORTE o, si no está, el remitente (lo de <…>)."""
    s = os.environ.get("FUELPATH_SOPORTE", "").strip()
    if s:
        return s
    de = os.environ.get("FUELPATH_CORREO_DE", "")
    return de.rpartition("<")[2].rstrip(">").strip() if "<" in de else de.strip()


def _pie() -> list[tuple[str, str]]:
    b = _base()
    return [(tr("Abrir FuelPath", "Open FuelPath", "Abrir o FuelPath"), b),
            (tr("Términos", "Terms", "Termos"), f"{b}/terminos"),
            (tr("Privacidad", "Privacy", "Privacidade"), f"{b}/privacidad")]


def _correo(titulo: str, parrafos: list[str], boton: tuple[str, str] | None = None,
            nota: str | None = None, lista: list[str] | None = None, motivo: str | None = None,
            kpis: list[tuple[str, str]] | None = None) -> tuple[str, str]:
    """(texto plano, HTML). Los párrafos son texto (se escapa); `lista` son
    viñetas; `nota` va chica bajo el botón; `motivo`, al pie, por qué le llega."""
    e = html.escape
    pie = _pie()
    soporte_ = soporte()
    motivo = motivo or tr("Recibes este correo por tu cuenta en FuelPath.",
                          "You're getting this email because of your FuelPath account.",
                          "Você recebe este e-mail por causa da sua conta no FuelPath.")
    # Texto plano
    t = [titulo, ""] + [p + "\n" for p in parrafos]
    t += [f"{k}: {v}" for k, v in (kpis or [])] + ([""] if kpis else [])
    t += [f"  · {x}" for x in (lista or [])] + ([""] if lista else [])
    if boton:
        t += [f"{boton[0]}: {boton[1]}", ""]
    if nota:
        t += [nota, ""]
    t += ["—", "FuelPath · " + tr("tu carga de carbohidratos, comida a comida",
                                  "your carb load, meal by meal",
                                  "sua carga de carboidratos, refeição por refeição"),
          " · ".join(f"{n}: {u}" for n, u in pie), motivo]
    if soporte_:
        t.append(tr(f"¿Dudas? Escríbenos a {soporte_}", f"Questions? Write to {soporte_}",
                    f"Dúvidas? Escreva para {soporte_}"))
    texto = "\n".join(t)
    # HTML (tablas y estilos en línea: es lo que entienden Gmail, Outlook y Apple Mail)
    fuente = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
    cuerpo = "".join(f'<p style="margin:0 0 14px;font-size:16px;line-height:1.55;color:{TINTA}">{e(p)}</p>'
                     for p in parrafos)
    if kpis:
        # Fichas de 3 por fila (tablas: es lo que respetan todos los clientes de correo).
        filas = [kpis[i:i + 3] for i in range(0, len(kpis), 3)]
        cuerpo += '<table role="presentation" width="100%" cellpadding="0" cellspacing="6" style="margin:0 -6px 12px">' + "".join(
            "<tr>" + "".join(f'<td width="33%" style="background:{FONDO};border-radius:12px;padding:10px 12px;vertical-align:top">'
                             f'<div style="font-size:11px;font-weight:700;letter-spacing:.3px;text-transform:uppercase;color:{SUAVE}">{e(k)}</div>'
                             f'<div style="font-size:17px;font-weight:800;color:{TINTA};margin-top:2px;white-space:nowrap">{e(v)}</div></td>'  for k, v in fila)
            + "".join('<td width="33%"></td>' for _ in range(3 - len(fila))) + "</tr>" for fila in filas) + "</table>"
    if lista:
        cuerpo += '<table role="presentation" cellpadding="0" cellspacing="0" style="margin:4px 0 18px">' + "".join(
            f'<tr><td style="vertical-align:top;padding:4px 10px 4px 0;color:{ACENTO};font-size:16px">●</td>'
            f'<td style="padding:4px 0;font-size:15px;line-height:1.5;color:{TINTA}">{e(x)}</td></tr>' for x in lista) + "</table>"
    if boton:
        cuerpo += (f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:8px 0 18px"><tr>'
                   f'<td style="border-radius:12px;background:{ACENTO}"><a href="{e(boton[1])}" '
                   f'style="display:inline-block;padding:14px 26px;font:700 16px {fuente};color:#ffffff;'
                   f'text-decoration:none;border-radius:12px">{e(boton[0])}</a></td></tr></table>'
                   f'<p style="margin:0 0 14px;font-size:12px;line-height:1.5;color:{SUAVE}">'
                   + tr("Si el botón no funciona, copia este enlace:", "If the button doesn't work, copy this link:",
                                                                       "Se o botão não funcionar, copie este link:")
                   + f'<br><a href="{e(boton[1])}" style="color:{SUAVE};word-break:break-all">{e(boton[1])}</a></p>')
    if nota:
        cuerpo += f'<p style="margin:0;font-size:13px;line-height:1.5;color:{SUAVE}">{e(nota)}</p>'
    enlaces = ' <span style="color:#c4c4cc">·</span> '.join(
        f'<a href="{e(u)}" style="color:{SUAVE};text-decoration:underline">{e(n)}</a>' for n, u in pie)
    html_ = f"""<!doctype html><html lang="{tr('es', 'en',
                                                     'pt-BR')}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light">
<title>{e(titulo)}</title></head>
<body style="margin:0;padding:0;background:{FONDO};font-family:{fuente}">
<div style="display:none;max-height:0;overflow:hidden">{e(parrafos[0] if parrafos else titulo)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{FONDO}"><tr><td align="center" style="padding:28px 14px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px">
<tr><td style="padding:0 6px 18px">
  <a href="{_base()}" style="text-decoration:none;color:{TINTA}"><img src="{_base()}/icons/icono-192.png" width="40" height="40" alt=""
   style="vertical-align:middle;border-radius:10px;border:0"> <span style="vertical-align:middle;font:800 20px {fuente};color:{TINTA};letter-spacing:-.3px">FuelPath</span></a>
</td></tr>
<tr><td style="background:#ffffff;border-radius:20px;padding:30px 28px;border:1px solid #e7e7ec">
  <div style="width:44px;height:4px;border-radius:2px;background:{ACENTO};margin:0 0 18px"></div>
  <h1 style="margin:0 0 16px;font:800 26px/1.2 {fuente};color:{TINTA};letter-spacing:-.4px">{e(titulo)}</h1>
  {cuerpo}
</td></tr>
<tr><td style="padding:22px 10px 0;text-align:center;font-size:13px;line-height:1.7;color:{SUAVE}">
  <div style="margin-bottom:8px">{enlaces}</div>
  <div>{e(motivo)}</div>
  {f'<div>{tr("¿Dudas? Escríbenos a", "Questions? Write to", "Dúvidas? Escreva para")} <a href="mailto:{soporte_}" style="color:{SUAVE}">{soporte_}</a></div>' if soporte_ else ""}
  <div style="margin-top:8px;color:#9a9aa3">{tr("Hecho en Santiago de Chile", "Made in Santiago, Chile",
                                                                              "Feito em Santiago, Chile")} 🇨🇱</div>
</td></tr>
</table></td></tr></table></body></html>"""
    return texto, html_


def _hola(nombre: str | None) -> str:
    return tr(f"Hola, {nombre}:", f"Hi {nombre},",
                                  f"Olá, {nombre}!") if nombre else tr("Hola:", "Hi,",
                                                                              "Olá!")


# ── Los correos ─────────────────────────────────────────────────────────────

def verificar(para: str, nombre: str | None, enlace: str, beta_pendiente: bool = False) -> None:
    parrafos = [_hola(nombre), tr("Confirma tu correo para terminar de crear tu cuenta de FuelPath.",
                                  "Confirm your email to finish creating your FuelPath account.",
                                  "Confirme seu e-mail para terminar de criar sua conta no FuelPath.")]
    if beta_pendiente:
        parrafos.append(tr("FuelPath está en beta privada: después de confirmar, tu cuenta queda en la lista de "
                           "espera y te avisamos por correo apenas te habilitemos.",
                           "FuelPath is in private beta: after you confirm, your account goes on the waiting "
                           "list and we'll email you as soon as you're in.",
                           "O FuelPath está em beta fechado: depois de confirmar, sua conta entra na lista de "
                           "espera e avisamos por e-mail assim que você for liberado."))
    texto, h = _correo(tr("Confirma tu correo", "Confirm your email",
                                                "Confirme seu e-mail"), parrafos,
                       (tr("Confirmar mi correo", "Confirm my email",
                                                  "Confirmar meu e-mail"), enlace),
                       tr("El enlace vale 48 horas. Si no creaste una cuenta, ignora este correo.",
                          "The link is valid for 48 hours. If you didn't create an account, ignore this email.",
                          "O link vale por 48 horas. Se você não criou uma conta, ignore este e-mail."))
    enviar(para, tr("Confirma tu correo en FuelPath", "Confirm your email on FuelPath",
                                                      "Confirme seu e-mail no FuelPath"), texto, h)


def recuperar(para: str, nombre: str | None, enlace: str) -> None:
    texto, h = _correo(tr("Cambia tu clave", "Reset your password",
                                             "Troque sua senha"),
                       [_hola(nombre), tr("Pediste cambiar tu clave de FuelPath. Elige una nueva aquí:",
                                          "You asked to reset your FuelPath password. Choose a new one here:",
                                          "Você pediu para trocar sua senha do FuelPath. Escolha uma nova aqui:")],
                       (tr("Elegir una clave nueva", "Choose a new password",
                                                     "Escolher uma senha nova"), enlace),
                       tr("El enlace vale 1 hora y sirve una sola vez. Si no lo pediste, ignora este correo: tu clave no cambia.",
                          "The link is valid for 1 hour and works once. If you didn't ask for it, ignore this email: "
                          "your password stays the same.",
                          "O link vale por 1 hora e funciona uma vez. Se você não pediu, ignore este e-mail: "
                          "sua senha continua a mesma."))
    enviar(para, tr("Cambia tu clave de FuelPath", "Reset your FuelPath password",
                                                   "Troque sua senha do FuelPath"), texto, h)


def _consejos() -> list[str]:
    return [tr("Arma tu pauta con tu carrera, tu peso y tus horarios: la carga de 36–48 h queda comida a comida.",
               "Build your plan with your race, weight and schedule: the 36–48 h load is laid out meal by meal.",
               "Monte seu plano com sua prova, seu peso e seus horários: a carga de 36–48 h fica refeição por refeição."),
            tr("Marca cada comida al comerla. Si comes más o menos, FuelPath reparte la diferencia en lo que queda.",
               "Tick each meal as you eat it. If you eat more or less, FuelPath spreads the difference over what's left.",
               "Marque cada refeição ao comer. Se comer mais ou menos, o FuelPath distribui a diferença no que falta."),
            tr("El día de la carrera tienes el desayuno, las sales y cada gel con su minuto y su km.",
               "On race day you get breakfast, salts and every gel with its minute and km.",
               "No dia da prova você tem o café da manhã, os sais e cada gel com seu minuto e seu km."),
            tr("Es una guía general: si tienes la pauta de tu nutricionista, sigue esa.",
               "It's general guidance: if you have a plan from your dietitian, follow that one.",
               "É um guia geral: se você tem o plano do seu nutricionista, siga esse.")]


def bienvenida(para: str, nombre: str | None, beta_pendiente: bool) -> None:
    """Al quedar registrado (con correo: al confirmarlo; con Google/Microsoft: al crearla)."""
    if beta_pendiente:
        texto, h = _correo(tr("¡Registro exitoso!", "You're registered!",
                                                    "Cadastro feito!"),
                           [_hola(nombre), tr("Tu cuenta de FuelPath ya está creada. Estamos en beta privada, así que "
                                              "quedaste en la lista de espera: te escribimos apenas te habilitemos.",
                                              "Your FuelPath account is ready. We're in private beta, so you're on "
                                              "the waiting list: we'll write as soon as you're in.",
                                              "Sua conta no FuelPath está pronta. Estamos em beta fechado, então você está na "
                                              "lista de espera: escrevemos assim que você for liberado."),
                            tr("Mientras, esto es lo que vas a poder hacer:", "Meanwhile, here's what you'll be able to do:",
                                                                              "Enquanto isso, veja o que você vai poder fazer:")],
                           lista=_consejos(),
                           nota=tr("¿Te invitó alguien? Respóndenos este correo y te habilitamos antes.",
                                   "Did someone invite you? Reply to this email and we'll let you in sooner.",
                                   "Alguém te convidou? Responda a este e-mail e liberamos você antes."))
    else:
        texto, h = _correo(tr("¡Registro exitoso!", "You're registered!",
                                                    "Cadastro feito!"),
                           [_hola(nombre), tr("Bienvenido a FuelPath: tu carga de carbohidratos antes de la carrera, comida a comida.",
                                              "Welcome to FuelPath: your pre-race carb load, meal by meal.",
                                              "Boas-vindas ao FuelPath: sua carga de carboidratos antes da prova, refeição por refeição."),
                            tr("Para empezar:", "To get started:",
                                                "Para começar:")],
                           (tr("Abrir FuelPath", "Open FuelPath",
                                                 "Abrir o FuelPath"), _base()), lista=_consejos())
    enviar(para, tr("¡Bienvenido a FuelPath!", "Welcome to FuelPath!",
                                               "Boas-vindas ao FuelPath!"), texto, h)


def acceso_beta(para: str, nombre: str | None, invitado: bool) -> None:
    """Cuando el admin la habilita (o la crea ya habilitada: una invitación)."""
    b = _base()
    if invitado:
        texto, h = _correo(tr("Te invitamos a la beta", "You're invited to the beta",
                                                        "Você foi convidado para o beta"),
                           [_hola(nombre), tr(f"Te habilitamos para probar FuelPath antes que nadie. Entra con este "
                                              f"correo ({para}): con Google, si es una cuenta de Google, o creando una clave.",
                                              f"You're in to try FuelPath before anyone else. Sign in with this email "
                                              f"({para}): with Google if it's a Google account, or by creating a password.",
                                              f"Você foi liberado para testar o FuelPath antes de todo mundo. Entre com este e-mail "
                                              f"({para}): com o Google se for uma conta Google, ou criando uma senha.")],
                           (tr("Entrar a FuelPath", "Sign in to FuelPath",
                                                    "Entrar no FuelPath"), f"{b}/entrar"), lista=_consejos(),
                           motivo=tr("Recibes este correo porque te invitaron a la beta de FuelPath.",
                                     "You're getting this email because you were invited to the FuelPath beta.",
                                     "Você recebe este e-mail porque foi convidado para o beta do FuelPath."))
    else:
        texto, h = _correo(tr("¡Ya tienes acceso!", "You're in!",
                                                    "Você está dentro!"),
                           [_hola(nombre), tr("Te habilitamos en la beta de FuelPath. Ya puedes entrar y armar tu primera pauta.",
                                              "You've been let into the FuelPath beta. You can sign in and build your first plan.",
                                              "Você foi liberado no beta do FuelPath. Já pode entrar e montar seu primeiro plano.")],
                           (tr("Abrir FuelPath", "Open FuelPath",
                                                 "Abrir o FuelPath"), b), lista=_consejos(),
                           nota=tr("Estamos afinándola: si algo falla o se te ocurre una mejora, respóndenos este correo.",
                                   "We're still fine-tuning it: if something breaks or you have an idea, reply to this email.",
                                   "Ainda estamos ajustando: se algo quebrar ou você tiver uma ideia, responda a este e-mail."))
    enviar(para, tr("Ya puedes entrar a FuelPath", "You can now use FuelPath",
                                                   "Você já pode usar o FuelPath") if not invitado
           else tr("Te invitamos a la beta de FuelPath", "You're invited to the FuelPath beta",
                                                         "Você foi convidado para o beta do FuelPath"), texto, h)


def aviso_registro(correo_: str, nombre: str | None, metodo: str, beta_pendiente: bool) -> None:
    """Al equipo (FUELPATH_CORREO_AVISOS): alguien se registró."""
    para = os.environ.get("FUELPATH_CORREO_AVISOS", "").strip()
    if not para:
        return
    estado = "esperando que lo habilites en la beta" if beta_pendiente else "ya puede usar la app"
    texto, h = _correo("Cuenta nueva", [f"{nombre or 'Alguien'} ({correo_}) creó una cuenta con {metodo}: {estado}."],
                       ("Abrir el panel", f"{_base()}/admin"),
                       motivo="Aviso del equipo de FuelPath (FUELPATH_CORREO_AVISOS).")
    enviar(para, f"FuelPath · cuenta nueva: {correo_}" + (" (beta pendiente)" if beta_pendiente else ""), texto, h)


def prueba(para: str) -> None:
    """Desde el panel: comprobar que el envío funciona."""
    texto, h = _correo("Prueba de correo", ["Si lees esto, FuelPath ya puede mandar correos. "],
                       ("Abrir el panel", f"{_base()}/admin"), motivo="Prueba enviada desde el panel de FuelPath.")
    enviar(para, "FuelPath · prueba de correo", texto, h)