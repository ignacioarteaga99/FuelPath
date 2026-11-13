"""Plan de carga de carbohidratos: la agenda de comidas de los días previos y del día de carrera.

Con el evento, el peso, el régimen elegido (g/kg/día), los horarios y los
alimentos del corredor, arma una agenda con cada comida, su hora y sus
alimentos en medidas caseras. La agenda es la que se va marcando en la app.

Referencias (detalle en docs/NUTRICION.md):
  · Thomas, Erdman y Burke. Nutrition and Athletic Performance. Posición conjunta
    ACSM / Academy of Nutrition and Dietetics / Dietitians of Canada, 2016.
  · Consenso del COI sobre nutrición deportiva (Maughan et al., 2018).
  · Burke et al., 2011; Bussau et al., 2002; Jeukendrup, 2014.
Es una guía general: si el corredor tiene la pauta de su nutricionista, esa manda
(Fase 2 del PLAN). Ningún texto promete resultados ni reemplaza a un profesional.

Criterios:
  · Carga larga (42K, 70.3, Ironman, gran fondo; o más de 2,5 h): 36–48 h
    previas, 8–12 g/kg/día (recomendado 10). Son los dos días antes de la carrera.
  · Carga corta (21K; o entre 75 min y 2,5 h): 24 h previas, 7–10 g/kg
    (recomendado 8). Es el día antes.
  · 10K o menos de 75 min: sin carga; sólo el desayuno del día.
  · Rango aceptable del día: del régimen − 0,5 al régimen + 1 g/kg (sin pasar 12,5).
  · Cada comida tiene un tope en g/kg para no reventar ninguna: la cena del
    día antes y la colación de la noche, más bajos para dormir bien.
  · Desayuno de carrera: 2–2,5 g/kg 3 h antes (carga larga), 2 g/kg 2,5 h
    antes (corta) y 1,5 g/kg 2 h antes (sin carga). Con estómago sensible,
    media hora más de margen y algo menos de cantidad.
  · Agua: unos 35 ml/kg al día aparte de las bebidas con carbohidratos.
  · Sodio: no se restringe. Referencia de 3 g/día (4 g si suda con sal).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from . import alimentos as al
from .alimentos import POR_ID
from .idioma import tr
from .reparto import ajustar, gramos

DISTANCIAS = {"10k": (10.0, "correr"), "21k": (21.1, "correr"), "42k": (42.2, "correr"),
              "703": (113.0, "tri"), "im": (226.0, "tri"), "fondo": (120.0, "bici"), "otra": (None, None)}
DEPORTES = ("correr", "bici", "tri")
REGIMENES = {"larga": (8, 10, 12), "corta": (7, 8, 10)}
RECOMENDADO = {"larga": 10, "corta": 8}

ORDEN = ("desayuno", "colacion", "almuerzo", "once", "cena", "noche")
PESOS = {"desayuno": .19, "colacion": .10, "almuerzo": .25, "once": .18, "cena": .20, "noche": .08}
PESOS_SENSIBLE = {"desayuno": .17, "colacion": .13, "almuerzo": .22, "once": .18, "cena": .18, "noche": .12}
TOPES = {"desayuno": 2.5, "colacion": 1.5, "almuerzo": 3.0, "once": 2.5, "cena": 2.5, "noche": 1.2}
TOPES_VISPERA = {"cena": 2.2, "noche": 1.0}       # para dormir bien la noche antes

PANES = ["pan_molde", "marraqueta", "pan_sg", "hallulla", "cereal", "pan_integral", "avena"]
UNTABLES = ["mermelada", "miel", "membrillo", "manjar"]
FRUTAS = ["platano", "uvas", "manzana"]
BASES = ["fideos", "arroz", "fideos_sg", "noquis", "cuscus", "quinoa"]
PROTEINAS = ["pollo", "pescado", "tofu", "huevo"]
SALADOS = ["galletas_agua", "galletas_arroz", "pretzels"]
PLANTILLAS = {
    "desayuno": [PANES, UNTABLES, FRUTAS, ["jugo", "nectar", "leche_choco", "leche_choco_sl", "isotonica"]],
    "colacion": [["isotonica", "nectar", "jugo"], SALADOS, ["barra", "gomitas", "datiles", "pasas", "galletas_maria"]],
    "almuerzo": [BASES, PROTEINAS, ["jugo", "nectar", "gaseosa"], ["jalea", "duraznos", "arroz_leche", "yogur"]],
    "once": [["pan_molde", "marraqueta", "pan_sg", "hallulla", "galletas_maria"], ["miel", "mermelada", "membrillo", "manjar"],
             ["leche_choco", "leche_choco_sl", "yogur", "nectar"], FRUTAS, ["gomitas", "datiles", "pasas"]],
    "cena": [BASES, ["papa", "pure"], PROTEINAS, ["duraznos", "jalea", "arroz_leche"]],
    "noche": [SALADOS, ["jugo", "nectar", "isotonica"]],
}
PLANTILLA_CARRERA = [["pan_molde", "pan_sg", "marraqueta", "cereal", "hallulla"], ["miel", "mermelada", "membrillo"],
                     ["platano", "uvas"], ["isotonica", "jugo", "nectar"]]


@dataclass
class Perfil:
    fecha: date
    hora: time
    peso_kg: float
    distancia: str
    tiempo_min: float
    regimen: float | None = None
    evento: str = ""
    deporte: str | None = None         # sólo con distancia «otra»
    km: float | None = None            # sólo con distancia «otra»
    levanta: time = time(7, 0)
    acuesta: time = time(23, 0)
    primera_carga: bool = False
    estomago_sensible: bool = False
    sudor_salado: bool = False
    restricciones: tuple[str, ...] = ()
    elegidos: tuple[str, ...] | None = None
    gel_g: float = 25.0
    intestino_entrenado: bool = False

    def __post_init__(self):
        if not 30 <= self.peso_kg <= 200:
            raise ValueError("peso_fuera_de_rango")
        if self.distancia not in DISTANCIAS:
            raise ValueError("distancia_invalida")
        km, deporte = DISTANCIAS[self.distancia]
        if self.distancia == "otra":
            if not self.km or self.km <= 0 or self.deporte not in DEPORTES:
                raise ValueError("otra_sin_km_o_deporte")
        else:
            self.km, self.deporte = km, deporte
        if not 10 <= self.tiempo_min <= 24 * 60:
            raise ValueError("tiempo_invalido")
        if not time(4, 0) <= self.levanta <= time(11, 0):
            raise ValueError("levanta_invalido")
        if not (self.acuesta >= time(20, 0) or self.acuesta <= time(1, 0)):
            raise ValueError("acuesta_invalido")
        bad = [r for r in self.restricciones if r not in al.RESTRICCIONES]
        if bad:
            raise ValueError("restriccion_invalida")
        if self.elegidos is not None and any(e not in POR_ID for e in self.elegidos):
            raise ValueError("alimento_invalido")
        tipo = tipo_carga(self)
        if tipo is None:
            self.regimen = None
        else:
            self.regimen = self.regimen or RECOMENDADO[tipo]
            if not 6 <= self.regimen <= 12.5:
                raise ValueError("regimen_invalido")


def tipo_carga(p: Perfil) -> str | None:
    if p.distancia in ("42k", "703", "im", "fondo"):
        return "larga"
    if p.distancia == "21k":
        return "corta"
    if p.distancia == "10k":
        return None
    return "larga" if p.tiempo_min > 150 else "corta" if p.tiempo_min > 75 else None


def _min(t: time) -> int:
    return t.hour * 60 + t.minute


def _hhmm(m: float, cada: int = 15) -> str:
    m = int(round(m / cada) * cada) % (24 * 60)
    return f"{m // 60:02d}:{m % 60:02d}"


def horarios(p: Perfil) -> dict[str, str]:
    """Horas de cada comida según a qué hora se levanta y se acuesta."""
    lev, aco = _min(p.levanta), _min(p.acuesta)
    if aco < lev:
        aco += 24 * 60
    desayuno = lev + 30
    noche = aco - 90
    cena = min(aco - 210, 20 * 60 + 30)
    almuerzo = min(max(desayuno + 6 * 60, 13 * 60), 14 * 60)
    return {"desayuno": _hhmm(desayuno), "colacion": _hhmm((desayuno + almuerzo) / 2), "almuerzo": _hhmm(almuerzo),
            "once": _hhmm((almuerzo + cena) / 2), "cena": _hhmm(cena), "noche": _hhmm(noche)}


def _r10(x: float) -> int:
    return int(round(x / 10) * 10)


def rango(p: Perfil) -> tuple[int, int]:
    return _r10((p.regimen - 0.5) * p.peso_kg), _r10(min(p.regimen + 1, 12.5) * p.peso_kg)


def objetivos_comidas(total: float, peso: float, vispera: bool, sensible: bool) -> dict[str, dict]:
    """Reparte el total del día entre las comidas respetando el tope de cada una."""
    pesos = PESOS_SENSIBLE if sensible else PESOS
    topes = {m: (TOPES_VISPERA.get(m, TOPES[m]) if vispera else TOPES[m]) * peso for m in ORDEN}
    obj = {m: pesos[m] * total for m in ORDEN}
    for _ in range(10):
        sobra = sum(max(0.0, obj[m] - topes[m]) for m in ORDEN)
        if sobra < 0.5:
            break
        obj = {m: min(obj[m], topes[m]) for m in ORDEN}
        holgura = {m: topes[m] - obj[m] for m in ORDEN}
        th = sum(holgura.values())
        if th <= 0:
            break
        obj = {m: obj[m] + sobra * holgura[m] / th for m in ORDEN}
    return {m: {"objetivo": obj[m], "tope": topes[m]} for m in ORDEN}


def _elegidos(p: Perfil) -> list[str]:
    base = list(p.elegidos) if p.elegidos is not None else al.por_defecto(p.restricciones, p.estomago_sensible)
    return [e for e in base if al.permitido(POR_ID[e], p.restricciones, p.estomago_sensible)]


def _elegir(candidatos: list[str], elegidos: set[str], evitar: set[str]) -> str | None:
    for c in candidatos:
        if c in elegidos and c not in evitar:
            return c
    for c in candidatos:                     # si sólo queda el repetido, se repite
        if c in elegidos:
            return c
    return None


def escala(p: Perfil) -> float:
    """Las porciones máximas crecen con el peso: a 100 kg cabe más arroz en un plato que a 55."""
    return max(1.0, p.peso_kg / 70)


def armar_comida(slots: list[list[str]], elegidos: set[str], objetivo: float, tope: float,
                 evitar: set[str] = frozenset(), extra: tuple[str, ...] = (), esc: float = 1.0,
                 topes_item: dict[str, float] | None = None) -> list[dict]:
    items, usados = [], set()
    for cands in slots:
        a = _elegir(cands, elegidos, set(evitar) | usados)
        if a and a not in usados:
            it = {"a": a, "p": POR_ID[a]["ini"]}
            if topes_item and a in topes_item:
                it["mx"] = topes_item[a]
            items.append(it)
            usados.add(a)
    for a in extra:
        if a in elegidos and a not in usados:
            items.append({"a": a, "p": POR_ID[a]["ini"]})
    items = ajustar(items, objetivo, techo=tope, escala=esc)
    return [it for it in items if it["p"] > 0]


def dia_carga(p: Perfil, fecha: date, n: int, de: int, elegidos: set[str]) -> dict:
    """Un día de carga: `n` de `de` (el último es la víspera)."""
    vispera = n == de
    total = p.regimen * p.peso_kg
    objs = objetivos_comidas(total, p.peso_kg, vispera, p.estomago_sensible)
    horas = horarios(p)
    comidas, bases = [], {}
    for m in ORDEN:
        slots = [list(s) for s in PLANTILLAS[m]]
        evitar: set[str] = set()
        if m == "almuerzo":                 # variedad: cada día parte con otra base
            slots[0] = BASES[n - 1:] + BASES[:n - 1]
        if m == "cena":
            evitar = {bases.get("base"), bases.get("proteina")} - {None}
        extra = ("caldo",) if m == "cena" and p.sudor_salado else ()
        items = armar_comida(slots, elegidos, objs[m]["objetivo"], objs[m]["tope"], evitar, extra, escala(p))
        if m == "almuerzo":
            for it in items:
                rol = POR_ID[it["a"]]["rol"]
                if rol in ("base", "proteina"):
                    bases[rol] = it["a"]
        g = gramos(items)
        comidas.append({"id": m, "hora": horas[m], "objetivo_g": round(g), "tope_g": round(objs[m]["tope"]),
                        "min_g": round(0.5 * objs[m]["objetivo"]), "items": items})
    notas = [tr("Carbohidratos en cada comida; baja la fibra y la grasa para que quepa todo sin pesadez.",
                "Carbs at every meal; cut back on fibre and fat so it all fits without feeling heavy.",
                "Carboidratos em cada refeição; reduza fibras e gordura para caber tudo sem pesar.")]
    if p.primera_carga:
        notas.append(tr("Primera carga: si te sientes muy lleno, prioriza los líquidos con carbohidratos.",
                        "First load: if you feel too full, lean on carb drinks.",
                        "Primeira carga: se você se sentir muito cheio, priorize os líquidos com carboidratos."))
    if p.sudor_salado:
        notas.append(tr("Sala normal tus comidas y suma el caldo: llegas con el sodio arriba.",
                        "Salt your meals as usual and add the broth: you'll start with sodium topped up.",
                        "Salgue normalmente as refeições e inclua o caldo: você chega com o sódio em dia."))
    if vispera:
        notas.append(tr("Cena temprano algo que ya conozcas. Nada nuevo la noche antes.",
                        "Have an early dinner you already know. Nothing new the night before.",
                        "Jante cedo algo que você já conhece. Nada novo na véspera."))
    lo, hi = rango(p)
    return {"fecha": fecha.isoformat(), "tipo": "carga", "n": n, "de": de, "objetivo_g": _r10(total),
            "rango_g": [lo, hi], "escala": round(escala(p), 2), "agua_ml": int(round(35 * p.peso_kg / 250) * 250),
            "sodio_mg": 4000 if p.sudor_salado else 3000, "reparto": True, "notas": notas, "comidas": comidas}


def dia_carrera(p: Perfil, elegidos: set[str]) -> dict:
    tipo = tipo_carga(p)
    horas_antes = {"larga": 3.0, "corta": 2.5, None: 2.0}[tipo] + (0.5 if p.estomago_sensible else 0)
    g_kg = {"larga": 2.5, "corta": 2.0, None: 1.5}[tipo] - (0.5 if p.estomago_sensible and tipo == "larga" else 0)
    salida = _min(p.hora)
    objetivo = g_kg * p.peso_kg
    # Antes de largar: líquido justo (5–7 ml/kg), no más de una bebida.
    items = armar_comida(PLANTILLA_CARRERA, elegidos, objetivo, objetivo * 1.15, esc=escala(p),
                         topes_item={"isotonica": 1, "jugo": 1, "nectar": 1})
    comidas = [{"id": "desayuno_carrera", "hora": _hhmm(salida - horas_antes * 60), "objetivo_g": round(gramos(items)),
                "tope_g": round(objetivo * 1.15), "min_g": round(objetivo * 0.5), "items": items}]
    if p.sudor_salado:
        comidas.append({"id": "sodio", "hora": _hhmm(salida - 45, 5), "objetivo_g": 0, "tope_g": 0, "min_g": 0,
                        "items": [{"a": "sales", "p": 1}]})
    if p.tiempo_min > 60:
        comidas.append({"id": "refuerzo", "hora": _hhmm(salida - 20, 5), "objetivo_g": 25, "tope_g": 25, "min_g": 0,
                        "items": [{"a": "gel", "p": 1}]})
    total = sum(c["objetivo_g"] for c in comidas)
    notas = [tr("Lo mismo que probaste antes de un entrenamiento largo: nada nuevo el día de la carrera.",
                "The same thing you tried before a long session: nothing new on race day.",
                "O mesmo que você testou antes de um treino longo: nada novo no dia da prova."),
             tr("La isotónica, a sorbos hasta una hora antes de largar.",
                "Sip the sports drink until an hour before the start.",
                "O isotônico, aos goles, até uma hora antes da largada.")]
    return {"fecha": p.fecha.isoformat(), "tipo": "carrera", "objetivo_g": total, "escala": round(escala(p), 2),
            "rango_g": [round(total * 0.85), round(total * 1.15)], "agua_ml": None,
            "sodio_mg": None, "reparto": False, "notas": notas, "comidas": comidas}


def en_carrera(p: Perfil) -> dict:
    """Carbohidratos, líquido y sodio por hora, y minuto (y km) de cada gel y cada dosis de sal."""
    t, h = p.tiempo_min, p.tiempo_min / 60
    if t < 45:
        g_h = (0, 0)
    elif t <= 75:
        g_h = (0, 30)
    elif h <= 2.5:
        g_h = (30, 60)
    else:
        g_h = (60, 90) if p.intestino_entrenado or p.deporte in ("bici", "tri") else (60, 70)
    con_km = p.deporte != "tri"

    def km(m):
        return round(p.km * m / t, 1) if con_km else None

    objetivo = (g_h[0] + g_h[1]) / 2
    geles = []
    if objetivo > 0 and t > 60:
        cada = max(15, int(60 * p.gel_g / objetivo // 5 * 5))
        m = 30 if t > 90 else 25
        while m < t - 10:
            geles.append({"min": m, "km": km(m)})
            m += cada
    sal = []
    if p.sudor_salado and h > 1.5:
        m = 60
        while m < t - 15:
            sal.append({"min": m, "km": km(m), "mg": 250})
            m += 60
    notas = []
    if geles:
        notas.append(tr("Practica este plan en tus fondos: el intestino también se entrena.",
                        "Practise this plan in your long sessions: your gut can be trained too.",
                        "Pratique este plano nos treinos longos: o intestino também se treina."))
    if p.deporte == "tri" and h > 2.5:
        notas.append(tr("En triatlón, la mayor parte va en la bici: ahí se tolera mejor. Combina geles con bebida y barras que hayas probado.",
                        "In triathlon most of it goes on the bike, where it's best tolerated. Mix gels with drink and bars you've tried.",
                        "No triatlo, a maior parte vai na bike, onde se tolera melhor. Combine géis com bebida e barras que você já testou."))
    notas.append(tr("El sodio depende de cuánto y cómo sudas. Haz el test de sudor en un entrenamiento de 1 h para afinarlo.",
                    "Sodium depends on how much and how salty you sweat. Do the sweat test in a 1 h session to fine-tune it.",
                    "O sódio depende de quanto e como você sua. Faça o teste de suor num treino de 1 h para ajustar."))
    return {"carbo_g_h": g_h, "liquido_ml_h": (400, 800) if h > 1 else None,
            "sodio_mg_h": ((500, 800) if p.sudor_salado else (300, 600)) if h > 1 else None,
            "geles": geles, "sal": sal, "gel_g": p.gel_g, "total_carbo_g": round(len(geles) * p.gel_g), "notas": notas}


def plan(p: Perfil) -> dict:
    elegidos = set(_elegidos(p)) | {"gel", "sales"}
    tipo = tipo_carga(p)
    de = {"larga": 2, "corta": 1, None: 0}[tipo]
    dias = [dia_carga(p, p.fecha - timedelta(days=de - i), i + 1, de, elegidos) for i in range(de)]
    dias.append(dia_carrera(p, elegidos))
    notas = []
    if tipo is None:
        notas.append(tr("Para esta distancia no necesitas carga: come normal, con carbohidratos en cada comida, y cuida el desayuno del día.",
                        "At this distance you don't need to carb-load: eat normally, with carbs at every meal, and get race-day breakfast right.",
                        "Nessa distância você não precisa de carga: coma normalmente, com carboidratos em cada refeição, e capriche no café da manhã da prova."))
    if tipo:
        notas.append(tr("Es normal subir 1–2 kg con la carga: el glucógeno se guarda con agua. No es grasa.",
                        "Gaining 1–2 kg while loading is normal: glycogen is stored with water. It isn't fat.",
                        "É normal ganhar 1–2 kg com a carga: o glicogênio é armazenado com água. Não é gordura."))
    inicio = datetime.combine(p.fecha, p.hora)
    return {"evento": p.evento, "distancia": p.distancia, "deporte": p.deporte, "km": p.km,
            "fecha": p.fecha.isoformat(), "hora": p.hora.strftime("%H:%M"), "peso_kg": p.peso_kg,
            "tiempo_min": p.tiempo_min, "regimen": p.regimen, "tipo_carga": tipo,
            "inicio_carga": (inicio - timedelta(hours=48 if tipo == "larga" else 24)).isoformat() if tipo else None,
            "elegidos": sorted(elegidos - {"gel", "sales"}), "dias": dias, "carrera": en_carrera(p), "notas": notas,
            "aviso": tr("Guía general basada en consensos de nutrición deportiva (ACSM 2016, COI 2018). No reemplaza a "
                        "tu nutricionista: si tienes su pauta, sigue esa.",
                        "General guidance based on sports nutrition consensus (ACSM 2016, IOC 2018). It doesn't replace "
                        "your dietitian: if you have their plan, follow that one.",
                        "Guia geral baseada em consensos de nutrição esportiva (ACSM 2016, COI 2018). Não substitui seu "
                        "nutricionista: se você tem o plano dele, siga esse."),
            "fuente": al.fuente()}
