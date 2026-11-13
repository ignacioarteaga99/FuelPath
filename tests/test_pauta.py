from datetime import date, time

import pytest
from fastapi.testclient import TestClient

from fuelpath import idioma, pauta
from fuelpath.api import app

MARATON = pauta.Carrera(peso_kg=70, distancia_km=42.2, tiempo_min=210, fecha=date(2027, 4, 11), hora=time(7, 30))
DIEZ_K = pauta.Carrera(peso_kg=70, distancia_km=10, tiempo_min=45, fecha=date(2027, 3, 7))


def test_carga_maraton_dos_dias_a_10_12_g_kg():
    dias = pauta.carga(MARATON)
    assert [d.fecha.isoformat() for d in dias] == ["2027-04-08", "2027-04-09", "2027-04-10"]
    assert dias[0].carbo_g is None
    assert dias[1].carbo_g == dias[2].carbo_g == (700, 840)


def test_carga_10k_solo_el_dia_antes():
    dias = pauta.carga(DIEZ_K)
    assert [d.carbo_g for d in dias] == [None, None, (490, 700)]


def test_comida_previa_horas_y_gramos():
    p = pauta.comida_previa(MARATON)
    assert p["opciones"][0] == {"hora": "04:30", "horas_antes": 3, "carbo_g": (140, 210)}
    assert p["opciones"][1]["hora"] == "05:30"


def test_en_carrera_maraton_geles_repartidos():
    r = pauta.en_carrera(MARATON)
    assert r["carbo_g_h"] == (60, 70)
    mins = [g["min"] for g in r["geles"]]
    assert mins[0] == 30 and all(b - a == 20 for a, b in zip(mins, mins[1:])) and mins[-1] < 200
    assert r["sodio_mg_h"] == (300, 600)


def test_intestino_entrenado_permite_90():
    c = pauta.Carrera(70, 42.2, 210, date(2027, 4, 11), intestino_entrenado=True)
    assert pauta.en_carrera(c)["carbo_g_h"] == (60, 90)


def test_10k_sin_geles():
    r = pauta.en_carrera(DIEZ_K)
    assert r["geles"] == [] and r["total_carbo_g"] == 0


def test_validaciones():
    with pytest.raises(ValueError):
        pauta.Carrera(10, 42, 200, date(2027, 1, 1))


def test_api_pauta_con_ritmo_y_en_ingles():
    cli = TestClient(app)
    r = cli.post("/api/pauta", json={"peso_kg": 70, "distancia_km": 21.1, "ritmo_s_km": 270,
                                     "fecha": "2027-05-02"}, headers={"X-Idioma": "en"})
    assert r.status_code == 200
    j = r.json()
    assert j["carrera"]["carbo_g_h"] == [30, 60]
    assert j["aviso"].startswith("General guidance")
    assert cli.post("/api/pauta", json={"peso_kg": 70, "distancia_km": 10, "fecha": "2027-05-02"}).status_code == 422
    idioma.usar("es")


def test_salud_y_app():
    cli = TestClient(app)
    assert cli.get("/api/salud").json() == {"ok": True}
    assert "FuelPath" in cli.get("/").text
