# Memoria heredada (de las sesiones de PacePath)

Lo que se aprendió trabajando con Ignacio en PacePath, para seguir igual aquí.
Complementa `CLAUDE.md`.

## Cómo le gusta trabajar
- **Idioma y tono:** responder siempre en español de Chile, informal y directo.
  Explicaciones cortas, con lo concreto primero.
- **Diseños:** cuando pide diseños o ideas visuales, quiere **ver opciones
  antes de implementar**, con mockups en PNG. Elige, y después se construye.
- **Ideas:** no le gustan las listas genéricas de ideas (las rechazó dos
  veces). Las sugerencias deben estar atadas a lo que ya usa, priorizadas,
  con una recomendación clara.
- **Producción:** lo que se termina se sube a producción después de que pasa
  pytest. Su patrón es «dale» y que quede andando.
- **Pruebas:** prueba todo en su iPhone. Lo que falla en Safari iOS (deslizar,
  zoom, safe-area) es lo primero que nota.
- **Botones:** serios, sin emojis del teclado. Los símbolos funcionales
  (✎ ⧉ ⤓ ✓ ← ✕ ↻ ☾ ☀) sí van.
- **Selectores:** no los quiere para lo que ya está elegido en la app. Por
  ejemplo, las historias siguen el idioma y las unidades de la app.
- **Datos personales:** no publicar su correo en ningún lado. Los secretos los
  pega él en Render o GitHub Secrets, nunca en el chat.

## Contexto del usuario
- Corredor de Santiago con mucho volumen: semanas de 100–120 km, series en
  pista, fondos de 30 km.
- Objetivos que ha nombrado: 10K Fedachi y 42K MDS (Maratón de Santiago).
- Tiene entrenador y le envía sus sesiones (por eso PacePath tiene «Enviar al
  entrenador»).
  - En FuelPath, lo análogo es enviarle el cumplimiento de la pauta al
    nutricionista.

## PacePath hoy (referencia)
- Producción: pacepathapp.com.
  - Rama `fase-0-1-series`, desplegada en Render con autoDeploy.
  - El trabajo se hace en la rama `coach` y pasa a producción por fast-forward.
- Funciones:
  - rutas por sesión sobre grafos OSM (motor RaceEngine);
  - Strava (mapa de calor, pasaporte);
  - Coach (plan semanal con sensaciones, pausas y días elegidos);
  - bitácora del corredor (series desde las vueltas de Strava, KPIs,
    objetivos, envío al entrenador por correo o WhatsApp);
  - historias para Instagram (11 diseños en canvas).
- Correo con Resend y el dominio propio, ya funcionando. La lección:
  `PACEPATH_CORREO_ACTIVO` tiene que ser «1».

## Decisiones de FuelPath hasta ahora
- **Nombre y repo:** FuelPath, repo público `ignacioarteaga99/FuelPath`, rama
  `main`.
- **Arquitectura y estilo:** los mismos de PacePath. Los módulos se copian y
  adaptan, no se importan.
- **Pauta:** basada en consensos (ACSM 2016, COI 2018). Es una guía general:
  la del nutricionista manda.
- **Pauta (definida con Ignacio, nov 2026):** ver `docs/NUTRICION.md`.
  - Agenda tipo B (tarjetas por comida, se abre la de ahora) con KPIs arriba y
    agua aparte. El desayuno parte con pan de molde.
  - Subir o bajar gramos de un alimento; al marcarlo, ventana para recalcular
    **sólo en las comidas que vienen**, con topes. Si come de más, baja lo que
    viene sin dejar comidas muy chicas.
  - En PC: menú a la izquierda y panel a la derecha.
  - Al terminar la carrera: feedback y plan guardado como plan anterior.
  - Mockups en `docs/mockups/`.
- **Fase 0 (nov 2026):** cuentas, panel, registro, correo y páginas legales traídos de PacePath.
  - Consentimiento explícito para datos de salud (casilla al crear la cuenta).
  - Render despliega la rama `produccion`; se trabaja en `main` y se pasa por fast-forward.
- **Pendiente de decidir:** dominio propio (¿fuelpathapp.com?) o subdominio de
  pacepathapp.com.
- **Próximo paso sugerido:**
  1. Fase 0 de `PLAN.md`: cuentas y Neon, copiando de PacePath.
  2. Servicio en Render.
  3. Después, registrar comidas con alimentos chilenos.
