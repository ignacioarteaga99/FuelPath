"""Base de alimentos para la carga de carbohidratos.

Cada alimento se mide en una **unidad casera** (rebanada, taza, vaso,
cucharada…) y trae los nutrientes de UNA unidad. La pauta trabaja en
unidades y en pasos de esa unidad (½ taza, 1 rebanada, 2 galletas), para
que se pueda seguir sin pesar nada.

Valores aproximados, redondeados, de tablas de composición: Tabla de
Composición de Alimentos Chilenos (INTA, Universidad de Chile), Atlas
Fotográfico de Alimentos y Preparaciones Típicas Chilenas (INTA/Minsal, 2010)
para las medidas caseras y USDA FoodData Central (dominio público). Las
preparaciones cocidas (arroz, fideos, papa) incluyen la sal habitual de cocina.
Las marcas cambian: lo que manda es la etiqueta del producto.

Campos de cada alimento:
    nombre      (es, en, pt)
    unidad      ((sing, plural) en es, en, pt)
    peso        gramos o ml de una unidad (para mostrar)
    cho, fibra, grasa, prot   gramos por unidad
    sodio       mg por unidad
    ml          líquido que aporta una unidad (bebidas)
    paso, ini, max   de a cuánto se sube o baja, con cuánto parte y el máximo por comida
    rol         qué papel cumple en una comida (ver ROLES)
    tags        alérgenos y otras marcas (ver RESTRICCIONES)
    base        marcado por defecto en la lista de la pauta
    oculto      no aparece en la lista de la carga (geles, sales: sólo día de carrera)
"""
from __future__ import annotations

from .idioma import actual, tr

# Prioridad al escalar una comida: primero lo que da más carbohidratos con
# menos volumen (la base, el pan), al final el postre. La proteína y el caldo
# no se escalan: acompañan.
ROLES = {"base": 0, "pan": 0, "acomp": 1, "liquido": 2, "lacteo": 2, "fruta": 3, "untable": 4,
         "snack": 5, "salado": 5, "dulce": 5, "postre": 6}
FIJOS = {"proteina", "caldo", "gel", "sales"}

# Qué etiquetas saca cada restricción.
RESTRICCIONES = {
    "sin_gluten": {"gluten"},
    "sin_lactosa": {"lactosa"},
    "vegetariano": {"carne", "pescado", "gelatina"},
    "vegano": {"carne", "pescado", "gelatina", "lacteo", "huevo", "miel"},
    "mani": {"mani"},
    "frutos_secos": {"frutos_secos"},
    "huevo": {"huevo"},
    "soya": {"soya"},
}


def _u(es: str, es_pl: str, en: str, en_pl: str, pt: str, pt_pl: str) -> dict:
    return {"es": (es, es_pl), "en": (en, en_pl), "pt": (pt, pt_pl)}


REBANADA = _u("rebanada", "rebanadas", "slice", "slices", "fatia", "fatias")
UNIDAD = _u("unidad", "unidades", "piece", "pieces", "unidade", "unidades")
TAZA = _u("taza", "tazas", "cup", "cups", "xícara", "xícaras")
VASO = _u("vaso", "vasos", "glass", "glasses", "copo", "copos")
CDA = _u("cucharada", "cucharadas", "tbsp", "tbsp", "colher de sopa", "colheres de sopa")
POTE = _u("pote", "potes", "pot", "pots", "pote", "potes")
BOLSITA = _u("bolsita", "bolsitas", "small bag", "small bags", "saquinho", "saquinhos")
BOTELLA = _u("botella de 500 ml", "botellas de 500 ml", "500 ml bottle", "500 ml bottles",
             "garrafa de 500 ml", "garrafas de 500 ml")
CAJA = _u("caja de 200 ml", "cajas de 200 ml", "200 ml carton", "200 ml cartons",
          "caixinha de 200 ml", "caixinhas de 200 ml")
GALLETA = _u("galleta", "galletas", "cracker", "crackers", "biscoito", "biscoitos")
FILETE = _u("filete", "filetes", "fillet", "fillets", "filé", "filés")
TROZO = _u("trozo", "trozos", "piece", "pieces", "pedaço", "pedaços")
PUNADO = _u("puñado", "puñados", "handful", "handfuls", "punhado", "punhados")
MITAD = _u("mitad", "mitades", "half", "halves", "metade", "metades")
PORCION = _u("porción", "porciones", "serving", "servings", "porção", "porções")
SOBRE = _u("sobre", "sobres", "sachet", "sachets", "sachê", "sachês")
GEL = _u("gel", "geles", "gel", "gels", "gel", "géis")


def _a(id, nombre, unidad, peso, cho, fibra, grasa, prot, sodio, rol, *, ml=0, paso=1.0, ini=1.0, mx=2.0,
       tags=(), base=False, oculto=False):
    return {"id": id, "nombre": nombre, "unidad": unidad, "peso": peso, "cho": cho, "fibra": fibra, "grasa": grasa,
            "prot": prot, "sodio": sodio, "ml": ml, "paso": paso, "ini": ini, "max": mx, "rol": rol,
            "tags": frozenset(tags), "base": base, "oculto": oculto}


ALIMENTOS = [
    # Pan y cereales
    _a("pan_molde", ("Pan de molde blanco", "White sandwich bread", "Pão de forma branco"), REBANADA, 25,
       12.5, 0.6, 0.8, 2.2, 120, "pan", ini=2, mx=6, tags={"gluten"}, base=True),
    _a("marraqueta", ("Marraqueta", "Marraqueta (crusty roll)", "Pão francês"), UNIDAD, 100,
       58, 2.5, 1.5, 8.5, 560, "pan", paso=0.5, ini=1, mx=2, tags={"gluten"}, base=True),
    _a("hallulla", ("Hallulla", "Hallulla (flat roll)", "Hallulla (pão chileno)"), UNIDAD, 90,
       50, 2, 6, 7.5, 520, "pan", paso=0.5, ini=1, mx=2, tags={"gluten"}),
    _a("pan_sg", ("Pan sin gluten", "Gluten-free bread", "Pão sem glúten"), REBANADA, 30,
       14, 0.8, 1.5, 1, 150, "pan", ini=2, mx=6),
    _a("pan_integral", ("Pan integral", "Wholemeal bread", "Pão integral"), REBANADA, 30,
       12, 2.1, 1, 3, 130, "pan", ini=2, mx=6, tags={"gluten", "fibra_alta"}),
    _a("cereal", ("Cereal de maíz (tipo corn flakes)", "Corn flakes", "Flocos de milho"), TAZA, 30,
       25, 0.9, 0.3, 2, 200, "pan", paso=0.5, ini=1, mx=3, tags={"gluten"}),
    _a("avena", ("Avena", "Oats", "Aveia"), TAZA, 80,
       54, 8, 5.5, 10, 4, "pan", paso=0.5, ini=0.5, mx=1, tags={"gluten", "fibra_alta"}),
    _a("barra", ("Barra de cereal", "Cereal bar", "Barra de cereal"), UNIDAD, 25,
       17, 1, 2.5, 1.5, 50, "snack", ini=1, mx=2, tags={"gluten"}, base=True),
    _a("galletas_maria", ("Galletas María", "Maria biscuits", "Biscoito Maria"), GALLETA, 7,
       5, 0.2, 0.8, 0.5, 25, "snack", paso=2, ini=4, mx=10, tags={"gluten"}),
    # Salados
    _a("galletas_agua", ("Galletas de agua", "Water crackers", "Biscoito de água e sal"), GALLETA, 5,
       3.5, 0.1, 0.5, 0.5, 32, "salado", paso=2, ini=6, mx=12, tags={"gluten"}, base=True),
    _a("galletas_arroz", ("Galletas de arroz", "Rice cakes", "Biscoito de arroz"), UNIDAD, 9,
       7, 0.3, 0.3, 0.7, 25, "salado", ini=3, mx=8),
    _a("pretzels", ("Pretzels", "Pretzels", "Pretzels"), PUNADO, 30,
       24, 1, 1, 3, 350, "salado", ini=1, mx=2, tags={"gluten"}),
    _a("caldo", ("Caldo de verduras", "Vegetable broth", "Caldo de legumes"), TAZA, 250,
       2, 0, 0.5, 0.5, 800, "caldo", ml=250, ini=1, mx=1, base=True),
    # Arroz, pastas y papas
    _a("fideos", ("Fideos cocidos", "Cooked pasta", "Macarrão cozido"), TAZA, 140,
       43, 2.5, 1.3, 8, 150, "base", paso=0.5, ini=1, mx=4, tags={"gluten"}, base=True),
    _a("arroz", ("Arroz blanco cocido", "Cooked white rice", "Arroz branco cozido"), TAZA, 160,
       45, 0.6, 3, 4.3, 250, "base", paso=0.5, ini=1, mx=4, base=True),
    _a("fideos_sg", ("Fideos sin gluten cocidos", "Cooked gluten-free pasta", "Macarrão sem glúten cozido"), TAZA, 140,
       44, 1.5, 1, 4, 150, "base", paso=0.5, ini=1, mx=4),
    _a("noquis", ("Ñoquis", "Gnocchi", "Nhoque"), TAZA, 150,
       48, 2, 1.5, 6, 300, "base", paso=0.5, ini=1, mx=3, tags={"gluten"}),
    _a("cuscus", ("Cuscús cocido", "Cooked couscous", "Cuscuz marroquino cozido"), TAZA, 157,
       36, 2.2, 0.3, 6, 150, "base", paso=0.5, ini=1, mx=3, tags={"gluten"}),
    _a("quinoa", ("Quínoa cocida", "Cooked quinoa", "Quinoa cozida"), TAZA, 185,
       39, 5.2, 3.6, 8, 150, "base", paso=0.5, ini=1, mx=3, tags={"fibra_alta"}),
    _a("papa", ("Papa cocida", "Boiled potato", "Batata cozida"), UNIDAD, 150,
       26, 2.2, 0.2, 2.8, 150, "acomp", ini=1, mx=3, base=True),
    _a("pure", ("Puré de papas", "Mashed potatoes", "Purê de batata"), TAZA, 210,
       35, 3, 9, 4, 600, "acomp", paso=0.5, ini=1, mx=2, tags={"lactosa", "lacteo"}),
    # Proteína (acompaña; no aporta carbohidratos)
    _a("pollo", ("Pollo a la plancha", "Grilled chicken", "Frango grelhado"), FILETE, 120,
       0, 0, 4, 31, 90, "proteina", paso=0.5, ini=1, mx=1.5, tags={"carne"}, base=True),
    _a("pescado", ("Pescado blanco (merluza)", "White fish (hake)", "Peixe branco (merluza)"), FILETE, 150,
       0, 0, 2, 27, 130, "proteina", paso=0.5, ini=1, mx=1.5, tags={"pescado"}, base=True),
    _a("huevo", ("Huevo", "Egg", "Ovo"), UNIDAD, 50,
       0.4, 0, 5, 6.3, 70, "proteina", ini=2, mx=3, tags={"huevo"}),
    _a("tofu", ("Tofu", "Tofu", "Tofu"), PORCION, 100,
       2, 0.5, 5, 10, 10, "proteina", ini=1, mx=1.5, paso=0.5, tags={"soya"}),
    # Frutas
    _a("platano", ("Plátano", "Banana", "Banana"), UNIDAD, 120,
       27, 3.1, 0.4, 1.3, 1, "fruta", paso=0.5, ini=1, mx=2, base=True),
    _a("uvas", ("Uvas", "Grapes", "Uvas"), TAZA, 150,
       27, 1.4, 0.3, 1.1, 3, "fruta", paso=0.5, ini=1, mx=2),
    _a("manzana", ("Manzana sin cáscara", "Peeled apple", "Maçã sem casca"), UNIDAD, 150,
       19, 2, 0.2, 0.4, 0, "fruta", ini=1, mx=2),
    _a("duraznos", ("Duraznos en conserva", "Canned peaches", "Pêssego em calda"), MITAD, 60,
       13, 0.8, 0, 0.3, 5, "postre", ini=2, mx=4, base=True),
    _a("pasas", ("Pasas", "Raisins", "Uvas-passas"), PUNADO, 40,
       32, 1.5, 0.2, 1.2, 4, "dulce", paso=0.5, ini=1, mx=1),
    _a("datiles", ("Dátiles", "Dates", "Tâmaras"), UNIDAD, 8,
       6, 0.6, 0, 0.2, 0, "dulce", ini=3, mx=6),
    # Dulces y untables
    _a("mermelada", ("Mermelada", "Jam", "Geleia de fruta"), CDA, 20,
       13, 0.2, 0, 0.1, 6, "untable", ini=1, mx=3, base=True),
    _a("miel", ("Miel", "Honey", "Mel"), CDA, 21,
       17, 0, 0, 0.1, 1, "untable", ini=1, mx=3, tags={"miel"}, base=True),
    _a("membrillo", ("Dulce de membrillo", "Quince paste", "Marmelada de marmelo"), TROZO, 30,
       20, 0.5, 0, 0.1, 3, "untable", ini=1, mx=2, base=True),
    _a("manjar", ("Manjar", "Dulce de leche", "Doce de leite"), CDA, 20,
       11, 0, 1.5, 1.4, 25, "untable", ini=1, mx=2, tags={"lactosa", "lacteo"}),
    _a("jalea", ("Jalea", "Jelly", "Gelatina"), POTE, 125,
       18, 0, 0, 1.5, 50, "postre", ini=1, mx=2, tags={"gelatina"}, base=True),
    _a("gomitas", ("Gomitas", "Gummies", "Balas de goma"), BOLSITA, 30,
       24, 0, 0, 2, 10, "dulce", ini=1, mx=2, tags={"gelatina"}, base=True),
    _a("arroz_leche", ("Arroz con leche", "Rice pudding", "Arroz-doce"), POTE, 150,
       35, 0.3, 4, 5, 80, "postre", ini=1, mx=1, tags={"lactosa", "lacteo"}),
    _a("yogur", ("Yogur con sabor", "Flavoured yoghurt", "Iogurte com sabor"), POTE, 125,
       18, 0, 2, 4, 60, "lacteo", ini=1, mx=2, tags={"lactosa", "lacteo"}),
    # Líquidos con carbohidratos
    _a("jugo", ("Jugo de naranja", "Orange juice", "Suco de laranja"), VASO, 250,
       26, 0.5, 0.5, 1.7, 2, "liquido", ml=250, paso=0.5, ini=1, mx=2, base=True),
    _a("nectar", ("Néctar de durazno", "Peach nectar", "Néctar de pêssego"), VASO, 250,
       33, 0.5, 0, 0.5, 10, "liquido", ml=250, paso=0.5, ini=1, mx=2, base=True),
    _a("isotonica", ("Bebida isotónica", "Sports drink", "Isotônico"), BOTELLA, 500,
       30, 0, 0, 0, 230, "liquido", ml=500, paso=0.5, ini=1, mx=2, base=True),
    _a("leche_choco", ("Leche chocolatada", "Chocolate milk", "Achocolatado"), CAJA, 200,
       22, 1, 3, 6, 120, "lacteo", ml=200, ini=1, mx=2, tags={"lactosa", "lacteo"}, base=True),
    _a("leche_choco_sl", ("Leche chocolatada sin lactosa", "Lactose-free chocolate milk", "Achocolatado sem lactose"),
       CAJA, 200, 22, 1, 3, 6, 120, "lacteo", ml=200, ini=1, mx=2, tags={"lacteo"}),
    _a("gaseosa", ("Bebida gaseosa", "Soft drink", "Refrigerante"), VASO, 250,
       26, 0, 0, 0, 10, "liquido", ml=250, paso=0.5, ini=1, mx=2),
    # Sólo para el día de carrera
    _a("gel", ("Gel energético", "Energy gel", "Gel de carboidrato"), GEL, 40,
       25, 0, 0, 0, 50, "gel", ini=1, mx=1, base=True, oculto=True),
    _a("sales", ("Sobre de sales o cápsula de sal", "Electrolyte sachet or salt capsule", "Sachê de eletrólitos ou cápsula de sal"),
       SOBRE, 5, 0, 0, 0, 0, 500, "sales", ini=1, mx=1, base=True, oculto=True),
]
POR_ID = {a["id"]: a for a in ALIMENTOS}
_IDX = {"es": 0, "en": 1, "pt": 2}

# Si la restricción saca el normal, se ofrece el reemplazo (y queda marcado).
REEMPLAZOS = {"leche_choco": "leche_choco_sl", "pan_molde": "pan_sg", "fideos": "fideos_sg",
              "galletas_agua": "galletas_arroz", "barra": "datiles", "jalea": "duraznos", "gomitas": "pasas",
              "miel": "membrillo", "pollo": "tofu", "pescado": "huevo"}


def excluidas(restricciones, estomago_sensible: bool = False) -> set[str]:
    """Etiquetas que quedan fuera con estas restricciones."""
    fuera = set()
    for r in restricciones or ():
        fuera |= RESTRICCIONES.get(r, set())
    if estomago_sensible:
        fuera.add("fibra_alta")
    return fuera


def permitido(a: dict, restricciones=(), estomago_sensible: bool = False) -> bool:
    return not (a["tags"] & excluidas(restricciones, estomago_sensible))


def por_defecto(restricciones=(), estomago_sensible: bool = False) -> list[str]:
    """Los alimentos que la pauta marca de partida, con los reemplazos que pidan las restricciones."""
    ids = []
    for a in ALIMENTOS:
        if not permitido(a, restricciones, estomago_sensible):
            continue
        if a["base"]:
            ids.append(a["id"])
    for normal, otro in REEMPLAZOS.items():
        if not permitido(POR_ID[normal], restricciones, estomago_sensible) and otro not in ids \
                and permitido(POR_ID[otro], restricciones, estomago_sensible):
            ids.append(otro)
    return [a["id"] for a in ALIMENTOS if a["id"] in ids]       # en el orden de la lista


def nombre(a: dict) -> str:
    return a["nombre"][_IDX[actual()]]


def unidad(a: dict, n: float) -> str:
    sing, pl = a["unidad"][actual()]
    return sing if n <= 1 else pl


def cantidad(a: dict, n: float) -> str:
    """2.5 → «2 ½ tazas» · 0.5 → «½ taza» · 3 → «3 rebanadas»."""
    entero, medio = int(n), abs(n - int(n)) >= 0.25
    num = ("½" if not entero else f"{entero} ½") if medio else str(entero)
    return f"{num} {unidad(a, n)}"


def catalogo() -> list[dict]:
    """Lo que la app necesita de cada alimento, en el idioma de la petición."""
    lang = actual()
    return [{"id": a["id"], "nombre": nombre(a), "unidad": list(a["unidad"][lang]), "peso": a["peso"],
             "cho": a["cho"], "fibra": a["fibra"], "grasa": a["grasa"], "prot": a["prot"], "sodio": a["sodio"],
             "ml": a["ml"], "paso": a["paso"], "ini": a["ini"], "max": a["max"], "rol": a["rol"],
             "tags": sorted(a["tags"]), "base": a["base"], "oculto": a["oculto"]} for a in ALIMENTOS]


def fuente() -> str:
    return tr("Valores aproximados de la Tabla de Composición de Alimentos Chilenos (INTA) y de USDA FoodData "
              "Central. Lo que manda es la etiqueta de tu producto.",
              "Approximate values from the Chilean Food Composition Table (INTA) and USDA FoodData Central. "
              "Your product's label is what counts.",
              "Valores aproximados da Tabela de Composição de Alimentos Chilenos (INTA) e do USDA FoodData "
              "Central. O que vale é o rótulo do seu produto.")
