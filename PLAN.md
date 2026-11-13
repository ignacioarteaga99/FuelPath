# Plan de FuelPath

Prioridad del producto: **saber qué comer hoy para llegar bien a la carrera, y
cumplirlo**. El cálculo es simple; el valor está en el seguimiento diario y en
que el plan de carrera esté probado antes.

## Arquitectura

```
iPhone (web móvil, instalable)  ──►  API FuelPath (FastAPI)
                                       ├─ pauta.py: carga, comida previa, plan en carrera
                                       ├─ cuentas + sesión (de PacePath)
                                       ├─ correo (Resend/SMTP, de PacePath)
                                       └─ Postgres (Neon): cuentas, datos sincronizados, registro
```

Detalle y qué archivos traer de PacePath: `docs/ARQUITECTURA.md`.

## Fase 0 — Esqueleto
- [x] Repo, FastAPI, pytest, Dockerfile, Blueprint de Render y CI con tests.
- [x] `pauta.py` con los rangos de los consensos y sus tests.
- [x] App móvil con 4 pestañas (Hoy, Pauta, Carrera, Perfil), ES/EN/PT, modo
      noche, instalable (manifest + service worker), mismos tokens que PacePath.
- [ ] Dominio y servicio en Render (¿fuelpathapp.com o subdominio de PacePath?).
- [ ] Cuentas: correo y clave, Google y Microsoft. Se trae `cuentas.py`,
      `oauth.py`, `entrar.html` y el middleware `_con_cuenta`.
- [ ] Datos del teléfono en la cuenta (como `DATOS_CUENTA` de PacePath).
- [ ] Registro y panel `/admin`: `registro.py`, `acceso.py` (beta cerrada) y `admin.html`.
- [ ] Correos de verificación y recuperación (`correo.py`).
- [ ] Páginas legales (privacidad y términos) adaptadas a datos de salud.

## Fase 1 — La pauta (función principal)
- [x] Carga de carbohidratos por día según la duración de la carrera.
- [x] Comida previa: dos opciones (3 h y 2 h antes) con gramos.
- [x] En carrera: g/h, líquido, sodio y minuto y km de cada gel.
- [x] Hoy: gramos del día con botones +25/+50/+100.
- [ ] Registrar comidas con alimentos comunes de Chile, cada uno con sus
      gramos de carbohidratos (marraqueta, arroz, fideos, plátano, jugo,
      barra…). Una porción con un toque, en vez de sumar gramos a mano.
- [ ] Cambiar el gel por el del usuario: marca, gramos, cafeína y sodio. Mezclar
      geles y bebida isotónica.
- [ ] Sodio y líquido personales con un test de sudor: peso antes y después
      de un entrenamiento de 1 h, más lo que tomó.
- [ ] Recordatorios: comida previa y geles. Notificaciones web; en iOS sólo
      funcionan con la app instalada.
- [ ] Varias carreras (temporada) y la próxima como principal.
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
