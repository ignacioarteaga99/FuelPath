# Plan de FuelPath

Prioridad del producto: **saber qué comer hoy para llegar bien a la carrera, y
cumplirlo**. El cálculo es simple; el valor está en el seguimiento diario y en
que el plan de carrera esté probado antes.

## Arquitectura

```
iPhone (web móvil, instalable)  ──►  API FuelPath (FastAPI)
                                       ├─ carga.py, reparto.py, alimentos.py: la pauta comida a comida
                                       ├─ cuentas + sesión (de PacePath)
                                       ├─ correo (Resend/SMTP, de PacePath)
                                       └─ Postgres (Neon): cuentas, datos sincronizados, registro
```

Detalle y qué archivos traer de PacePath: `docs/ARQUITECTURA.md`.

## Fase 0 — Esqueleto
- [x] Repo, FastAPI, pytest, Dockerfile, Blueprint de Render y CI con tests.
- [x] La lógica de la pauta con los rangos de los consensos y sus tests (hoy en `carga.py`).
- [x] App móvil con 4 pestañas (Hoy, Pauta, Carrera, Perfil), ES/EN/PT, modo
      noche, instalable (manifest + service worker), mismos tokens que PacePath.
- [ ] Dominio propio (¿fuelpathapp.com o subdominio de PacePath?). Mientras, la URL de Render.
- [ ] Servicio en Render y base en Neon (lo crea Ignacio: ver «Puesta en marcha» en `README.md`).
- [x] Cuentas: correo y clave, Google y Microsoft (`cuentas.py`, `oauth.py`,
      `entrar.html`, middleware `_con_cuenta`), con consentimiento explícito para datos de salud.
- [x] Datos del teléfono en la cuenta (`DATOS_CUENTA`: perfil, agenda, agua, planes anteriores).
- [x] Registro y panel `/admin`: `registro.py`, `uso.py`, `acceso.py` (beta cerrada) y `admin.html`.
- [x] Correos de verificación y recuperación (`correo.py`), apagados hasta configurar Resend.
- [x] Páginas legales (privacidad y términos) adaptadas a datos de salud; descargar y borrar la cuenta.

## Fase 1 — La pauta (función principal)
- [x] Formulario: evento, distancia (10K, 21K, 42K, 70.3, Ironman, gran
      fondo u otra), tiempo, fecha y hora, peso en kg o lb, régimen
      (8/10/12 g/kg o 7/8/10 en 21K), horarios, estómago sensible, sudor
      salado, restricciones y alergias, y derivación si hay condición médica.
- [x] Base de ~45 alimentos con medida casera (rebanada, taza, vaso…), sus
      nutrientes y alérgenos. Se eligen al armar la pauta.
- [x] Agenda de 36–48 h (o 24 h) comida a comida, con hora, medidas caseras y
      topes por comida. El día de carrera: desayuno, sales y refuerzo.
- [x] Marcar como hecho, a medias o no. Subir o bajar porciones y, al marcar,
      proponer el recálculo hacia las comidas que vienen (con topes).
- [x] Cambiar, mover o sacar un alimento. «Ajustar lo que queda» a mano con
      la suma y el rango.
- [x] KPIs del día (hecho, proyectado, rango, sodio, g/kg) y agua aparte.
- [x] En carrera: g/h, líquido y sodio por hora, y minuto y km de cada gel y
      cada dosis de sal.
- [x] Vista para PC (menú lateral y panel a la derecha).
- [x] Al terminar: feedback, plan anterior guardado y consejos para la próxima.
- [ ] Sodio y líquido personales con un test de sudor: peso antes y después
      de un entrenamiento de 1 h, más lo que tomó.
- [ ] Recordatorios: comida previa y geles. Notificaciones web; en iOS sólo
      funcionan con la app instalada.
- [ ] Alimentos propios (con los datos de la etiqueta) y más alimentos en la base.
- [ ] Ritmo en vez de tiempo, y millas (como en PacePath).

## Fase 2 — La pauta del nutricionista
- [ ] Cargar una pauta propia: por día, comidas con gramos o porciones. La
      plantilla calculada queda como sugerencia.
- [ ] Compartir el cumplimiento con el nutricionista por correo con el formato
      de la app, como «Enviar al entrenador» de PacePath.
- [ ] Cumplimiento por día y por comida (sí, a medias, no) y nota de cómo se
      sintió el estómago.

## Fase 3 — Entrenar el plan
- [ ] Ensayos en los fondos: «hoy prueba 2 geles a 60 g/h», y anotar cómo cayó.
- [ ] Con Strava (OAuth propio): detectar los fondos y preguntar qué se comió.
- [ ] Conectar con PacePath: la carrera objetivo de la bitácora crea la pauta.
- [ ] Después de la carrera: qué funcionó, para la próxima.

## Ideas para después
- Historias para Instagram del plan de carrera (como las de PacePath).
- Lista de compras de la semana de carga.
- Ajuste por calor y altura.
