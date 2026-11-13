import copy
from datetime import date, time

import pytest
from fastapi.testclient import TestClient

from fuelpath import alimentos as al
from fuelpath import carga, idioma, reparto
from fuelpath.api import app
from fuelpath.reparto import gramos

MDS = dict(fecha=date(2027, 4, 25), hora=time(7, 0), peso_kg=68, distancia="42k", tiempo_min=185)


def _plan(**kw):
    return carga.plan(carga.Perfil(**{**MDS, **kw}))


def _total(dia):
    return sum(gramos(c["items"]) for c in dia["comidas"])


# ── Alimentos ────────────────────────────────────────────────────────────────

def test_alimentos_bien_formados():
    ids = set()
    for a in al.ALIMENTOS:
        assert a["id"] not in ids
        ids.add(a["id"])
        assert len(a["nombre"]) == 3 and set(a["unidad"]) == {"es", "en", "pt"}
        assert a["cho"] >= 0 and a["paso"] > 0 and a["ini"] > 0 and a["max"] >= a["ini"]
        assert a["rol"] in al.ROLES or a["rol"] in al.FIJOS
        assert a["tags"] <= {"gluten", "lactosa", "lacteo", "carne", "pescado", "gelatina", "huevo", "miel",
                             "mani", "frutos_secos", "soya", "fibra_alta", "grasa_alta"}
    for normal, otro in al.REEMPLAZOS.items():
        assert normal in al.POR_ID and otro in al.POR_ID


def test_restricciones_sacan_lo_que_corresponde():
    sg = al.por_defecto(["sin_gluten"])
    assert "pan_molde" not in sg and "fideos" not in sg and "pan_sg" in sg and "fideos_sg" in sg
    veg = al.por_defecto(["vegano"])
    assert not {"miel", "leche_choco", "leche_choco_sl", "pollo", "pescado", "jalea", "gomitas"} & set(veg)
    assert "tofu" in veg
    sl = al.por_defecto(["sin_lactosa"])
    assert "leche_choco" not in sl and "leche_choco_sl" in sl
    assert "avena" not in al.por_defecto([], estomago_sensible=True)


def test_cantidades_caseras():
    idioma.usar("es")
    assert al.cantidad(al.POR_ID["arroz"], 2.5) == "2 ½ tazas"
    assert al.cantidad(al.POR_ID["arroz"], 0.5) == "½ taza"
    assert al.cantidad(al.POR_ID["pan_molde"], 4) == "4 rebanadas"
    assert al.cantidad(al.POR_ID["palta"], 0.25) == "¼ palta" and al.cantidad(al.POR_ID["palta"], 1.75) == "1 ¾ paltas"
    idioma.usar("en")
    assert al.cantidad(al.POR_ID["jugo"], 1) == "1 glass"
    idioma.usar("es")


# ── Plan de carga ────────────────────────────────────────────────────────────

def test_maraton_dos_dias_de_carga_en_rango_y_bajo_los_topes():
    p = _plan()
    assert p["tipo_carga"] == "larga" and p["regimen"] == 10
    assert [d["fecha"] for d in p["dias"]] == ["2027-04-23", "2027-04-24", "2027-04-25"]
    for d in p["dias"][:2]:
        assert d["objetivo_g"] == 680 and d["rango_g"] == [650, 750]
        assert 650 <= _total(d) <= 750
        assert [c["id"] for c in d["comidas"]] == list(carga.ORDEN)
        for c in d["comidas"]:
            assert gramos(c["items"]) <= c["tope_g"] + 0.5
    # la víspera tiene la cena más chica (para dormir bien)
    assert p["dias"][1]["comidas"][4]["tope_g"] < p["dias"][0]["comidas"][4]["tope_g"]
    assert p["inicio_carga"] == "2027-04-23T07:00:00"


def test_desayuno_parte_con_pan_de_molde_y_horarios():
    d = _plan()["dias"][0]
    des = d["comidas"][0]
    assert des["hora"] == "07:30" and des["items"][0]["a"] == "pan_molde"
    assert [c["hora"] for c in d["comidas"]] == ["07:30", "10:30", "13:30", "16:30", "19:30", "21:30"]


def test_variedad_entre_almuerzo_y_cena():
    for d in _plan()["dias"][:2]:
        alm = {it["a"] for it in d["comidas"][2]["items"]}
        cen = {it["a"] for it in d["comidas"][4]["items"]}
        assert not ({"fideos", "arroz"} & alm & cen)


def test_21k_un_dia_a_8_g_kg_y_10k_sin_carga():
    p = _plan(distancia="21k", tiempo_min=100)
    assert p["regimen"] == 8 and len(p["dias"]) == 2 and p["dias"][0]["objetivo_g"] == 540
    p = _plan(distancia="10k", tiempo_min=45)
    assert p["regimen"] is None and [d["tipo"] for d in p["dias"]] == ["carrera"]
    assert p["dias"][0]["comidas"][0]["hora"] == "05:00"           # 2 h antes


@pytest.mark.parametrize("peso,reg", [(45, 8), (68, 12), (95, 10), (130, 12)])
def test_regimenes_y_pesos_quedan_en_rango(peso, reg):
    for d in _plan(peso_kg=peso, regimen=reg, distancia="im", tiempo_min=720)["dias"][:2]:
        assert d["rango_g"][0] <= _total(d) <= d["rango_g"][1]
        for c in d["comidas"]:
            assert gramos(c["items"]) <= c["tope_g"] + 0.5


def test_restricciones_y_elegidos_se_respetan():
    p = _plan(restricciones=("sin_gluten", "vegano"))
    usados = {it["a"] for d in p["dias"] for c in d["comidas"] for it in c["items"]}
    for a in usados:
        assert not (al.POR_ID[a]["tags"] & (al.excluidas(["sin_gluten", "vegano"])))
    p = _plan(elegidos=("pan_molde", "arroz", "jugo", "platano", "galletas_agua"))
    usados = {it["a"] for d in p["dias"] for c in d["comidas"] for it in c["items"]}
    assert usados <= {"pan_molde", "arroz", "jugo", "platano", "galletas_agua", "gel"}


def test_dia_de_carrera_desayuno_sodio_y_refuerzo():
    d = _plan(sudor_salado=True)["dias"][-1]
    assert [c["id"] for c in d["comidas"]] == ["desayuno_carrera", "sodio", "refuerzo"]
    des = d["comidas"][0]
    assert des["hora"] == "04:00" and 140 <= gramos(des["items"]) <= 195
    assert all(it["p"] <= 1 for it in des["items"] if it["a"] in ("isotonica", "jugo", "nectar"))
    assert d["comidas"][1]["hora"] == "06:15" and d["comidas"][2]["hora"] == "06:40"
    sens = _plan(estomago_sensible=True)["dias"][-1]
    assert sens["comidas"][0]["hora"] == "03:30" and [c["id"] for c in sens["comidas"]] == ["desayuno_carrera", "refuerzo"]


def test_en_carrera_sodio_y_triatlon_sin_km():
    r = _plan(sudor_salado=True)["carrera"]
    assert r["sodio_mg_h"] == (500, 800) and [s["min"] for s in r["sal"]] == [60, 120]
    assert r["geles"][0] == {"min": 30, "km": 6.8}
    r = _plan(distancia="im", tiempo_min=720)["carrera"]
    assert r["carbo_g_h"] == (60, 90) and r["geles"][0]["km"] is None and r["sal"] == []


def test_validaciones():
    with pytest.raises(ValueError):
        carga.Perfil(**{**MDS, "distancia": "otra"})
    with pytest.raises(ValueError):
        carga.Perfil(**{**MDS, "levanta": time(13, 0)})
    with pytest.raises(ValueError):
        carga.Perfil(**{**MDS, "restricciones": ("nada",)})
    p = carga.Perfil(**{**MDS, "distancia": "otra", "km": 30, "deporte": "correr", "tiempo_min": 160})
    assert carga.tipo_carga(p) == "larga"


# ── Reparto ──────────────────────────────────────────────────────────────────

def _comer(dia, hasta, menos=None):
    """Marca como comidas las comidas 0..hasta; `menos` = (comida, item, porciones comidas)."""
    for i in range(hasta + 1):
        for it in dia["comidas"][i]["items"]:
            it["c"] = it["p"]
    if menos:
        i, j, n = menos
        dia["comidas"][i]["items"][j]["c"] = n


def test_comer_menos_reparte_solo_hacia_adelante():
    dia = copy.deepcopy(_plan()["dias"][1])
    alm = dia["comidas"][2]
    fid = next(j for j, it in enumerate(alm["items"]) if al.POR_ID[it["a"]]["rol"] == "base")
    _comer(dia, 2, (2, fid, alm["items"][fid]["p"] - 1))           # una taza menos
    r = reparto.proponer(dia, 2)
    assert r["dif_g"] > 30 and r["cambios"]
    assert {c["comida"] for c in r["cambios"]} <= {3, 4, 5}         # ni el almuerzo ni las pasadas
    assert all(c["g"] > 0 for c in r["cambios"])
    assert r["con"] > r["sin"] and r["estado_con"] in ("ok", "bajo")
    nuevo = copy.deepcopy(dia)
    for c in r["cambios"]:
        nuevo["comidas"][c["comida"]]["items"][c["item"]]["p"] = c["p"]
    for c in nuevo["comidas"][3:]:
        assert gramos(c["items"]) <= c["tope_g"] + 0.5
    assert abs(reparto.proyectado(nuevo) - r["con"]) < 1


def test_sacar_mucho_no_revienta_la_noche():
    dia = copy.deepcopy(_plan()["dias"][1])
    _comer(dia, 3)
    for it in dia["comidas"][3]["items"]:
        it["c"] = 0                                                # se saltó la once completa
    r = reparto.proponer(dia, 3)
    for c in r["cambios"]:
        assert c["comida"] in (4, 5)
    assert r["sin_cubrir_g"] > 0 and r["estado_con"] == "bajo"
    assert any("no lo fuerces" in a for a in r["avisos"])
    assert set(r["en_tope"]) == {"cena", "noche"}


def test_comer_de_mas_baja_lo_que_viene_sin_pasar_el_minimo():
    dia = copy.deepcopy(_plan()["dias"][0])
    _comer(dia, 1)
    for it in dia["comidas"][1]["items"]:
        it["c"] = it["p"] * 3
    r = reparto.proponer(dia, 1)
    assert r["dif_g"] < 0 and all(c["g"] < 0 for c in r["cambios"])
    nuevo = copy.deepcopy(dia)
    for c in r["cambios"]:
        nuevo["comidas"][c["comida"]]["items"][c["item"]]["p"] = c["p"]
    for c in nuevo["comidas"][2:]:
        assert gramos(c["items"]) >= c["min_g"] - 0.5


def test_sin_comidas_por_delante():
    dia = copy.deepcopy(_plan()["dias"][1])
    _comer(dia, 5, (5, 0, 0))
    r = reparto.proponer(dia, 5)
    assert r["cambios"] == [] and r["sin"] == r["con"]
    assert any("Ya no quedan" in a for a in r["avisos"])


# ── API ──────────────────────────────────────────────────────────────────────

PEDIDO = {"evento": "Maratón de Santiago", "fecha": "2027-04-25", "hora": "07:00", "peso_kg": 68,
          "distancia": "42k", "tiempo_min": 185, "regimen": 10, "restricciones": ["sin_lactosa"]}


def test_api_alimentos_y_carga():
    cli = TestClient(app)
    r = cli.get("/api/alimentos?restricciones=sin_lactosa").json()
    assert "leche_choco_sl" in r["por_defecto"] and "leche_choco" not in r["permitidos"]
    assert r["alimentos"][0]["nombre"] == "Pan de molde blanco"
    j = cli.post("/api/carga", json=PEDIDO).json()
    assert len(j["dias"]) == 3 and j["evento"] == "Maratón de Santiago"
    usados = {it["a"] for d in j["dias"] for c in d["comidas"] for it in c["items"]}
    assert "leche_choco" not in usados
    en = cli.get("/api/alimentos", headers={"X-Idioma": "en"}).json()
    assert en["alimentos"][0]["nombre"] == "White sandwich bread"
    idioma.usar("es")


def test_api_condicion_medica_deriva():
    j = TestClient(app).post("/api/carga", json={**PEDIDO, "condicion_medica": True}).json()
    assert j["derivar"] is True and "profesional" in j["mensaje"]


def test_api_errores():
    cli = TestClient(app)
    r = cli.post("/api/carga", json={**PEDIDO, "distancia": "otra"})
    assert r.status_code == 422 and "km" in r.json()["detail"]
    assert cli.post("/api/carga", json={**PEDIDO, "distancia": "99k"}).status_code == 422


def test_api_reparto():
    cli = TestClient(app)
    dia = cli.post("/api/carga", json=PEDIDO).json()["dias"][1]
    _comer(dia, 2, (2, 0, dia["comidas"][2]["items"][0]["p"] - 1))
    r = cli.post("/api/reparto", json={"dia": dia, "desde": 2})
    assert r.status_code == 200 and r.json()["cambios"]
    dia["comidas"][0]["items"][0]["a"] = "veneno"
    assert cli.post("/api/reparto", json={"dia": dia, "desde": 2}).status_code == 422


def test_agregados_y_propios_cuentan_pero_no_se_escalan():
    dia = copy.deepcopy(_plan()["dias"][1])
    _comer(dia, 0)
    des = dia["comidas"][0]
    des["items"].append({"a": "palta", "p": 0.25, "c": 0.25})                # ¼ de palta en el pan
    des["items"].append({"a": "p_kuchen", "p": 1, "c": 1, "cho": 40})        # alimento propio
    antes = reparto.proyectado(copy.deepcopy(_plan()["dias"][1]))
    assert abs(reparto.proyectado(dia) - antes - (0.25 * 13 + 40)) < 0.5
    r = reparto.proponer(dia, 0)
    assert r["dif_g"] < 0 and all(c["comida"] > 0 for c in r["cambios"])   # baja lo que viene
    assert not any(c["a"] in ("palta", "p_kuchen") for c in r["cambios"])
    assert "palta" not in al.por_defecto() and "palta" in {a["id"] for a in al.catalogo()}
    # La API acepta el propio con su cho y rechaza uno inventado sin él.
    cli = TestClient(app)
    assert cli.post("/api/reparto", json={"dia": dia, "desde": 0}).status_code == 200
    del des["items"][-1]["cho"]
    assert cli.post("/api/reparto", json={"dia": dia, "desde": 0}).status_code == 422


def test_base_tiene_lo_comun_y_su_version():
    cli = TestClient(app)
    j = cli.get("/api/alimentos").json()
    ids = {a["id"] for a in j["alimentos"]}
    assert {"palta", "queso", "mantequilla", "leche", "mote_huesillo", "queque"} <= ids
    assert len(j["version"]) == 10 and j["version"] == al.version()


def test_nunca_un_litro_de_isotonica_antes_de_dormir():
    """Las bebidas de cada comida tienen tope de ml (antes de dormir, 250), al armar y al recalcular."""
    for kw in ({}, {"regimen": 12, "peso_kg": 95}, {"elegidos": ("pan_molde", "arroz", "isotonica", "platano")}):
        for d in _plan(**kw)["dias"][:2]:
            for c in d["comidas"]:
                assert reparto.mililitros(c["items"]) <= reparto.ml_max(c["id"], d["escala"]) + 1, (kw, c["id"], c["items"])
                if c["id"] == "noche":
                    assert reparto.mililitros(c["items"]) <= 250
    # Se salta la once completa y la noche sólo tiene isotónica: no se llena de líquido.
    dia = copy.deepcopy(_plan()["dias"][0])
    _comer(dia, 3)
    for it in dia["comidas"][3]["items"]:
        it["c"] = 0
    dia["comidas"][5]["items"] = [{"a": "isotonica", "p": 0.5}]
    r = reparto.proponer(dia, 3)
    nuevo = copy.deepcopy(dia)
    for c in r["cambios"]:
        nuevo["comidas"][c["comida"]]["items"][c["item"]]["p"] = c["p"]
    assert reparto.mililitros(nuevo["comidas"][5]["items"]) <= 250
    assert reparto.mililitros(nuevo["comidas"][4]["items"]) <= 400


def test_repartir_corrige_una_noche_con_demasiado_liquido():
    dia = copy.deepcopy(_plan()["dias"][0])
    dia["comidas"][5]["items"] = [{"a": "isotonica", "p": 2}]               # pauta vieja: 1 litro
    r = reparto.proponer(dia, -1)
    nuevo = copy.deepcopy(dia)
    for c in r["cambios"]:
        nuevo["comidas"][c["comida"]]["items"][c["item"]]["p"] = c["p"]
    assert reparto.mililitros(nuevo["comidas"][5]["items"]) <= 250


def test_desayuno_de_carrera_segun_horas_antes():
    assert carga.opciones_desayuno(3) == [2.0, 2.5, 3.0]
    assert carga.opciones_desayuno(1) == [0.5, 0.75, 1.0] and carga.opciones_desayuno(4) == [3.0, 3.5, 4.0]
    d = _plan(peso_kg=61)["dias"][-1]["comidas"][0]
    assert d["horas_antes"] == 3 and d["g_kg"] == 2.5 and d["hora"] == "04:00"
    el = set(al.por_defecto())
    for horas, g in ((2, 1.5), (3, 3.0), (4, 4.0)):
        c = carga.desayuno_carrera(61, time(7, 0), horas, g, el)
        assert c["hora"] == f"{7 - horas:02d}:00" and abs(gramos(c["items"]) - g * 61) <= 0.15 * g * 61, (horas, g, c)
    cli = TestClient(app)
    r = cli.post("/api/desayuno", json={"peso_kg": 61, "hora": "07:00", "horas": 2.5, "elegidos": sorted(el)}).json()
    assert r["hora"] == "04:30" and r["g_kg"] == 2.0
    assert cli.post("/api/desayuno", json={"peso_kg": 61, "hora": "07:00", "horas": 1, "g_kg": 3}).status_code == 422
    assert cli.post("/api/desayuno", json={"peso_kg": 61, "hora": "07:00", "horas": 5}).status_code == 422
