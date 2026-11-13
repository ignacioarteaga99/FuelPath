"""Pauta nutricional precarrera: carga de carbohidratos, comida previa y plan en carrera.

Es la función principal de FuelPath. Con el peso, la carrera (distancia y
tiempo estimado) y la hora de salida, arma día a día lo que toca comer los
días antes, la comida previa y cuánto tomar y comer durante la carrera.

Los rangos vienen de los consensos de nutrición deportiva (posición conjunta
ACSM / Academy of Nutrition and Dietetics / Dietitians of Canada, 2016, y el
consenso del COI sobre nutrición deportiva, 2018):

  · Carga de carbohidratos: carreras de más de 90 min → 10–12 g/kg/día las
    36–48 h previas. Más cortas → 7–12 g/kg las 24 h previas.
  · Comida previa: 1–4 g/kg de carbohidratos, 1 a 4 h antes de la salida.
  · Durante: menos de 45 min, nada; 45–75 min, poco o enjuague bucal;
    1–2,5 h, 30–60 g/h; más de 2,5 h, hasta 90 g/h (glucosa + fructosa,
    sólo si se entrenó el intestino).
  · Bajo en fibra y residuos las 24–48 h previas si hay problemas digestivos.
  · Líquido y sodio: muy personales (dependen de la tasa de sudor); como
    punto de partida, 400–800 ml/h y 300–600 mg de sodio por hora.

Es una guía general: si el usuario tiene la pauta de su nutricionista, esa
manda (se carga en `pauta_propia`, Fase 2 del PLAN). Ningún texto de la app
promete resultados ni reemplaza a un profesional.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from .idioma import tr

PESO_MIN, PESO_MAX = 30.0, 200.0


@dataclass
class Carrera:
    peso_kg: float
    distancia_km: float
    tiempo_min: float                 # tiempo estimado de carrera
    fecha: date
    hora: time = time(8, 0)
    gel_g: float = 25.0               # carbohidratos por gel del usuario
    intestino_entrenado: bool = False  # ¿ha probado > 60 g/h en entrenamientos?

    def __post_init__(self):
        if not PESO_MIN <= self.peso_kg <= PESO_MAX:
            raise ValueError("peso_fuera_de_rango")
        if self.distancia_km <= 0 or self.tiempo_min <= 0:
            raise ValueError("carrera_invalida")
        if not 5 <= self.gel_g <= 100:
            raise ValueError("gel_invalido")


@dataclass
class Dia:
    fecha: date
    etiqueta: str
    carbo_g: tuple[int, int] | None    # rango del día (None: comer normal)
    notas: list[str] = field(default_factory=list)


def _r(x: float, paso: int = 10) -> int:
    return int(round(x / paso) * paso)


def carga(c: Carrera) -> list[Dia]:
    """Días previos a la carrera: carga de carbohidratos según la duración."""
    larga = c.tiempo_min > 90
    dias_carga = 2 if larga else 1
    g_kg = (10, 12) if larga else (7, 10)
    out = []
    for n in range(3, 0, -1):                   # D-3, D-2, D-1
        f = c.fecha - timedelta(days=n)
        if n <= dias_carga:
            notas = [tr("Carbohidratos en cada comida y colación: arroz, pasta, pan, papas, fruta, jugos.",
                        "Carbs at every meal and snack: rice, pasta, bread, potatoes, fruit, juice.",
                        "Carboidratos em cada refeição e lanche: arroz, massa, pão, batata, fruta, sucos."),
                     tr("Baja la fibra y la grasa para que quepa todo sin pesadez.",
                        "Cut back on fibre and fat so it all fits without feeling heavy.",
                        "Reduza fibras e gordura para caber tudo sem pesar.")]
            if n == 1:
                notas.append(tr("Cena temprano algo que ya conozcas. Nada nuevo la noche antes.",
                                "Have an early dinner you already know. Nothing new the night before.",
                                "Jante cedo algo que você já conhece. Nada novo na véspera."))
            out.append(Dia(f, tr(f"Faltan {n} días", f"{n} days to go", f"Faltam {n} dias") if n > 1
                           else tr("Día antes", "Day before", "Véspera"),
                           (_r(g_kg[0] * c.peso_kg), _r(g_kg[1] * c.peso_kg)), notas))
        else:
            out.append(Dia(f, tr(f"Faltan {n} días", f"{n} days to go", f"Faltam {n} dias"), None,
                           [tr("Come normal, con carbohidratos en cada comida. Hidrátate bien.",
                               "Eat normally, with carbs at every meal. Stay well hydrated.",
                               "Coma normalmente, com carboidratos em cada refeição. Hidrate-se bem.")]))
    return out


def comida_previa(c: Carrera) -> dict:
    """Comida previa: 1–4 g/kg, más carbohidratos mientras más lejos de la salida."""
    salida = datetime.combine(c.fecha, c.hora)
    opciones = []
    for horas, g_kg in ((3, (2, 3)), (2, (1, 2))):
        opciones.append({"hora": (salida - timedelta(hours=horas)).strftime("%H:%M"), "horas_antes": horas,
                         "carbo_g": (_r(g_kg[0] * c.peso_kg, 5), _r(g_kg[1] * c.peso_kg, 5))})
    return {"opciones": opciones,
            "notas": [tr("Lo mismo que probaste antes de un entrenamiento largo.",
                         "The same thing you tried before a long run.",
                         "O mesmo que você testou antes de um treino longo."),
                      tr("Poca fibra, poca grasa y poca proteína.", "Low fibre, low fat, low protein.",
                         "Pouca fibra, pouca gordura e pouca proteína.")]}


def en_carrera(c: Carrera) -> dict:
    """Carbohidratos, líquido y sodio por hora, y cuándo tomar cada gel."""
    h = c.tiempo_min / 60
    if c.tiempo_min < 45:
        g_h = (0, 0)
    elif c.tiempo_min <= 75:
        g_h = (0, 30)
    elif h <= 2.5:
        g_h = (30, 60)
    else:
        g_h = (60, 90) if c.intestino_entrenado else (60, 70)
    objetivo = (g_h[0] + g_h[1]) / 2
    geles = []
    if objetivo > 0 and c.tiempo_min > 60:
        cada = max(15, int(60 * c.gel_g / objetivo // 5 * 5))   # minutos entre geles, múltiplo de 5
        t = 30 if c.tiempo_min > 90 else 25
        while t < c.tiempo_min - 10:
            km = c.distancia_km * t / c.tiempo_min
            geles.append({"min": t, "km": round(km, 1)})
            t += cada
    return {"carbo_g_h": g_h, "liquido_ml_h": (400, 800) if h > 1 else None,
            "sodio_mg_h": (300, 600) if h > 1.5 else None, "geles": geles,
            "total_carbo_g": round(len(geles) * c.gel_g),
            "notas": [tr("Practica este plan en tus fondos: el intestino también se entrena.",
                         "Practise this plan on your long runs: your gut can be trained too.",
                         "Pratique este plano nos longões: o intestino também se treina.")]
            if geles else []}


def pauta(c: Carrera) -> dict:
    return {"dias": [{"fecha": d.fecha.isoformat(), "etiqueta": d.etiqueta,
                      "carbo_g": d.carbo_g, "notas": d.notas} for d in carga(c)],
            "previa": comida_previa(c), "carrera": en_carrera(c),
            "aviso": tr("Guía general basada en consensos de nutrición deportiva. Si tienes la pauta de tu "
                        "nutricionista, sigue esa.",
                        "General guidance based on sports nutrition consensus. If you have a plan from "
                        "your dietitian, follow that one.",
                        "Guia geral baseada em consensos de nutrição esportiva. Se você tem o plano do "
                        "seu nutricionista, siga esse.")}


def ritmo_a_tiempo(distancia_km: float, ritmo_s_km: float) -> float:
    """Minutos de carrera a partir del ritmo objetivo (s/km)."""
    return math.ceil(distancia_km * ritmo_s_km / 60)
