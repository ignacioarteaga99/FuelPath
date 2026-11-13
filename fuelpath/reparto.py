"""Reparto de carbohidratos entre comidas: armar una comida y recalcular el día.

Dos usos:
  · `ajustar`: lleva una comida a sus gramos objetivo subiendo o bajando las
    porciones de a un paso (½ taza, 1 rebanada…), primero lo que más aporta
    con menos volumen. La usa `carga.py` para armar cada comida.
  · `proponer`: cuando el corredor come más o menos de lo planeado (o saca un
    alimento), reparte la diferencia **sólo en las comidas que vienen**, nunca
    en la misma comida ni en las pasadas, y sin pasar el tope de cada una.
    Si no alcanza, lo que falta queda «sin cubrir»: no se fuerza.

Una comida es un dict con `items` = [{"a": id del alimento, "p": porciones
planeadas, "c": porciones comidas o None si aún no se marca}], y sus
`objetivo_g`, `tope_g` y `min_g`.
"""
from __future__ import annotations

from .alimentos import FIJOS, ROLES, de_item
from .idioma import tr

_EPS = 1e-6


def g_item(it: dict, comido: bool = False) -> float:
    n = it.get("c") if comido and it.get("c") is not None else it["p"]
    return n * de_item(it)["cho"]


def gramos(items: list[dict]) -> float:
    return sum(it["p"] * de_item(it)["cho"] for it in items)


def _minimo(a: dict, p_inicial: float) -> float:
    """La base y el pan no bajan de un paso (si estaban); lo demás puede quedar en cero."""
    return a["paso"] if ROLES.get(a["rol"], 9) == 0 and p_inicial > 0 else 0.0


def maximo(a: dict, escala: float = 1.0, it: dict | None = None) -> float:
    """Porciones máximas de un alimento en una comida. Crece con el peso (escala = peso/70, mínimo 1)."""
    if it and it.get("mx") is not None:
        return it["mx"]
    return max(a["max"], int(a["max"] * escala / a["paso"]) * a["paso"])


def ajustar(items: list[dict], objetivo: float, techo: float | None = None, piso: float | None = None,
            escala: float = 1.0) -> list[dict]:
    """Sube o baja porciones de a un paso hasta quedar lo más cerca posible del objetivo.

    Nunca pasa el `techo` al subir ni baja del `piso` al bajar. Devuelve una
    copia; los ítems pueden quedar en 0 (quien llama decide si los saca).
    Un ítem puede traer `mx` (máximo propio, p. ej. 1 isotónica antes de largar).
    """
    items = [dict(it) for it in items]
    iniciales = [it["p"] for it in items]
    techo = float("inf") if techo is None else techo
    piso = 0.0 if piso is None else piso
    s = gramos(items)
    for _ in range(400):
        forzar = s > techo + _EPS                 # pasado del tope (por las porciones iniciales): bajar sí o sí
        err = (techo - s) if forzar else objetivo - s
        mejor = None
        for i, it in enumerate(items):
            a = de_item(it)
            if a["rol"] in FIJOS or a["cho"] <= 0:
                continue
            prio, paso, inc, mx = ROLES.get(a["rol"], 9), a["paso"], a["paso"] * a["cho"], maximo(a, escala, it)
            if err > 0 and it["p"] + paso <= mx + _EPS and s + inc <= techo + _EPS \
                    and abs(err - inc) < abs(err) - _EPS:
                clave = (it["p"] / mx, prio, i)          # reparte: primero lo menos usado
                cand = (clave, i, paso, inc)
            elif err < 0 and it["p"] - paso >= _minimo(a, iniciales[i]) - _EPS and s - inc >= piso - _EPS \
                    and (forzar or abs(err + inc) < abs(err) - _EPS):
                clave = (-prio, -it["p"] / mx, i)        # baja primero el postre y lo dulce
                cand = (clave, i, -paso, -inc)
            else:
                continue
            if mejor is None or cand[0] < mejor[0]:
                mejor = cand
        if mejor is None:
            break
        _, i, dp, dg = mejor
        items[i]["p"] = round(items[i]["p"] + dp, 2)
        s += dg
    return items


def proyectado(dia: dict) -> float:
    """Lo que va a quedar el día: lo comido donde se marcó y lo planeado donde no."""
    return sum(g_item(it, comido=True) for cm in dia["comidas"] for it in cm["items"])


def hecho(dia: dict) -> float:
    return sum(g_item(it, comido=True) for cm in dia["comidas"] for it in cm["items"] if it.get("c") is not None)


def estado(total: float, rango) -> str:
    return "bajo" if total < rango[0] - _EPS else "sobre" if total > rango[1] + _EPS else "ok"


def marcada(cm: dict) -> bool:
    return any(it.get("c") is not None for it in cm["items"])


def proponer(dia: dict, desde: int) -> dict:
    """Propuesta para volver al objetivo del día repartiendo en las comidas posteriores a `desde`.

    `desde` es la comida que se acaba de marcar o cambiar (-1: desde el inicio
    del día). Sólo se tocan comidas posteriores sin nada marcado.
    """
    comidas, rango, objetivo = dia["comidas"], dia["rango_g"], dia["objetivo_g"]
    escala = dia.get("escala", 1.0)
    total = proyectado(dia)
    dif = objetivo - total
    futuras = [i for i in range(desde + 1, len(comidas)) if not marcada(comidas[i])]
    actuales = {i: gramos(comidas[i]["items"]) for i in futuras}
    if dif > 0:
        holgura = {i: max(0.0, comidas[i]["tope_g"] - actuales[i]) for i in futuras}
    else:
        holgura = {i: max(0.0, actuales[i] - comidas[i]["min_g"]) for i in futuras}
    total_holgura = sum(holgura.values())
    cambios, movido, en_tope = [], 0.0, []
    if abs(dif) >= 1 and total_holgura > 0:
        por_repartir = min(abs(dif), total_holgura)
        for i in futuras:
            parte = por_repartir * holgura[i] / total_holgura
            cm = comidas[i]
            if parte < 1:
                nuevos = cm["items"]
            elif dif > 0:
                nuevos = ajustar(cm["items"], actuales[i] + parte, techo=cm["tope_g"], escala=escala)
            else:
                nuevos = ajustar(cm["items"], actuales[i] - parte, piso=cm["min_g"], escala=escala)
            if dif > 0 and cm["tope_g"] - gramos(nuevos) < _paso_minimo(cm):
                en_tope.append(cm["id"])          # ya no le cabe ni un paso más
            for j, (antes, despues) in enumerate(zip(cm["items"], nuevos)):
                if abs(antes["p"] - despues["p"]) > _EPS:
                    dg = (despues["p"] - antes["p"]) * de_item(antes)["cho"]
                    cambios.append({"comida": i, "item": j, "a": antes["a"], "de": antes["p"], "p": despues["p"],
                                    "g": round(dg)})
                    movido += dg
    con = total + movido
    sin_cubrir = dif - movido
    return {"objetivo_g": objetivo, "rango_g": rango, "sin": round(total), "con": round(con),
            "estado_sin": estado(total, rango), "estado_con": estado(con, rango),
            "dif_g": round(dif), "sin_cubrir_g": round(sin_cubrir), "en_tope": en_tope, "cambios": cambios,
            "avisos": _avisos(dif, sin_cubrir, futuras, en_tope)}


def _paso_minimo(cm: dict) -> float:
    pasos = [de_item(it)["paso"] * de_item(it)["cho"] for it in cm["items"] if de_item(it)["cho"] > 0]
    return min(pasos) if pasos else 0.0


def _avisos(dif: float, sin_cubrir: float, futuras: list[int], en_tope: list[str]) -> list[str]:
    avisos = []
    if dif > 0:
        if not futuras:
            avisos.append(tr("Ya no quedan comidas por delante hoy. Está bien: no lo fuerces.",
                             "There are no meals left today. That's fine: don't force it.",
                             "Não restam refeições hoje. Tudo bem: não force."))
        elif sin_cubrir >= 5:
            avisos.append(tr(f"Te quedan {round(sin_cubrir)} g sin cubrir y está bien: no lo fuerces.",
                             f"{round(sin_cubrir)} g are left uncovered and that's fine: don't force it.",
                             f"Ficam {round(sin_cubrir)} g sem cobrir e tudo bem: não force."))
        if "cena" in en_tope or "noche" in en_tope:
            avisos.append(tr("No cargamos más la noche para que duermas bien.",
                             "We don't load the evening any further so you sleep well.",
                             "Não carregamos mais a noite para você dormir bem."))
    elif dif < 0:
        avisos.append(tr("Bajamos un poco lo que viene, sin dejar ninguna comida muy chica.",
                         "We trim what's coming a little, without leaving any meal too small.",
                         "Reduzimos um pouco o que vem, sem deixar nenhuma refeição pequena demais."))
    return avisos
