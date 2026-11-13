# Nutrición: en qué se basa la pauta de FuelPath

Guía general basada en consensos. **No reemplaza a un nutricionista**: si el
corredor tiene la pauta de su nutricionista, esa manda. Con diabetes, un
trastorno alimentario o un embarazo, la app no arma pauta y deriva a un
profesional.

## Fuentes

- Thomas, Erdman y Burke. *Nutrition and Athletic Performance*. Posición
  conjunta ACSM / Academy of Nutrition and Dietetics / Dietitians of Canada,
  2016.
- Consenso del COI sobre nutrición deportiva (Maughan et al., 2018).
- Burke et al., *Carbohydrates for training and competition*, J Sports Sci,
  2011.
- Bussau et al., 2002: con 10 g/kg durante 1 día de reposo, el glucógeno
  muscular llega a niveles altos.
- Jeukendrup, 2014: carbohidratos durante el ejercicio; 90 g/h o más con
  glucosa y fructosa.
- Valores de los alimentos:
  - Tabla de Composición de Alimentos Chilenos (INTA, U. de Chile).
  - Atlas Fotográfico de Alimentos y Preparaciones Típicas Chilenas
    (INTA/Minsal, 2010), para las medidas caseras.
  - USDA FoodData Central.

## Lo que decidimos (y está en el código)

| Tema | Criterio | Dónde |
|---|---|---|
| Carga larga: 42K, 70.3, Ironman, gran fondo, o más de 2,5 h | 36–48 h previas. Opciones 8 / **10** / 12 g/kg/día. Son los 2 días antes de la carrera | `carga.py` |
| Carga corta: 21K, o entre 75 min y 2,5 h | 24 h previas. Opciones 7 / **8** / 10 g/kg | `carga.py` |
| 10K o menos de 75 min | Sin carga. Sólo el desayuno del día y el plan en carrera | `carga.py` |
| Rango aceptable del día | Del régimen − 0,5 al régimen + 1 g/kg, sin pasar 12,5 | `carga.rango` |
| Reparto entre comidas | Desayuno 19 %, colación 10 %, almuerzo 25 %, once 18 %, cena 20 % y antes de dormir 8 %. Con estómago sensible se reparte más en las colaciones | `carga.PESOS` |
| Topes por comida (g/kg) | Desayuno 2,5 · colación 1,5 · almuerzo 3 · once 2,5 · cena 2,5 · noche 1,2. La víspera: cena 2,2 y noche 1,0, para dormir bien | `carga.TOPES` |
| Fibra y grasa | Bajas durante la carga. Con estómago sensible se sacan los alimentos altos en fibra | `alimentos.py` |
| Líquidos con carbohidratos | Siempre presentes: sin ellos cuesta llegar a 10 g/kg (unos 700 g para 70 kg) | plantillas en `carga.py` |
| Agua | Unos 35 ml/kg al día, aparte de los jugos y la isotónica. Se lleva en vasos de 250 ml | `carga.dia_carga` |
| Sodio en la carga | No se restringe. La referencia es 3 g/día (4 g si suda con sal). Si suda con sal, la cena lleva caldo | `carga.dia_carga` |
| Desayuno de carrera | Carga larga: 2,5 g/kg 3 h antes. Corta: 2 g/kg 2,5 h antes. Sin carga: 1,5 g/kg 2 h antes. Con estómago sensible, 30 min más de margen y 0,5 g/kg menos. Como máximo 1 bebida (5–7 ml/kg) | `carga.dia_carrera` |
| Antes de largar | Si suda con sal: sales 45 min antes (unos 500 mg de sodio). Si la carrera dura más de 1 h: gel 20 min antes | `carga.dia_carrera` |
| En carrera | Hasta 45 min, nada. De 45 a 75 min, hasta 30 g/h. Hasta 2,5 h, 30–60 g/h. Más de 2,5 h, 60–70 g/h, o 60–90 g/h con el intestino entrenado o en bici y triatlón | `carga.en_carrera` |
| Líquido y sodio en carrera | 400–800 ml/h. Sodio: 300–600 mg/h, o 500–800 mg/h si suda con sal, con una dosis de sal cada hora | `carga.en_carrera` |
| Subir de peso | Es normal subir 1–2 kg (el glucógeno se guarda con agua), y la app lo avisa | `carga.plan` |

## Cuando el corredor se sale del plan

- **Comer más o menos al marcar:** la diferencia con el objetivo del día se
  reparte **sólo en las comidas que vienen**.
  - Nunca en la misma comida ni en las pasadas.
  - Ninguna comida pasa su tope ni baja de la mitad de lo planeado.
  - Si no alcanza, lo que falta queda «sin cubrir» y la app dice que no lo
    fuerce.
  - Está en `reparto.proponer`.
- **Sacar un alimento:** la app primero ofrece cambiarlo por algo parecido.
  Si no, lo reparte.
- **Mover un alimento:** sólo a una comida que viene y en la que quepa.

## Al terminar

Cuando la carrera termina, la app pide feedback: energía, estómago, cómo
cayó la carga, el tiempo final y una nota. El plan queda guardado como plan
anterior, con lo cumplido por día. Los consejos para la próxima son reglas
simples, por ejemplo: si le faltó energía y cumplió menos del 90 %, la app
sugiere apuntar a cumplir la carga completa.
