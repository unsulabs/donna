---
name: donna-operational-review
description: Reconcile work, handle deliveries and blockers proactively, preserve Obsidian edits and acknowledge scheduled reviews only after action.
version: 2.0.0-rc.1
author: Unsu Labs
license: MIT
metadata:
  hermes:
    tags: [donna, orchestration, personal-assistant]
---

# Revisión operativa que produce acciones

Carga `donna-session`. Esta es la revisión de responsabilidad, no solo un briefing.
Se ejecuta en el perfil de Donna, nunca dentro del scope de un worker especialista.

## Disparadores y exclusión de revisiones

En un cron, `donna_review_gate.py` se ejecuta antes de la sesión y entrega un JSON
con `wakeAgent`, `review_token` y la cola. Si es falso no hay turno que ejecutar.
En una revisión manual o wake nativo, llama `pulse`; si otra revisión tiene lease,
no dupliques el ciclo ni hagas `review-reset` para competir con ella.

```bash
python3 "$HERMES_HOME/scripts/donna_ops.py" pulse
python3 "$HERMES_HOME/scripts/donna_ops.py" review
```

El contexto del preflight puede truncar la lista a 40 elementos; `review` devuelve
la cola completa. Lee todos los elementos. La cola no contiene por sí sola todo el
contexto: abre las notas de vida/proyecto, fuentes y entregas relevantes.

## Actuar antes de informar

Para cada elemento, decide y ejecuta lo pertinente:
- Entrega: verifica criterios; acepta o devuelve corrección concreta.
- Bloqueo: investiga causa, prepara decisión/capacidad faltante y avanza ramas libres.
- Tarea interna lista: prepara y despacha al especialista, o realiza tu investigación.
- Acción humana: prepara opciones, consecuencias y momento necesario, no otra lista técnica.
- Plazo/capacidad: contrasta prioridades y disponibilidad; no inventes una urgencia.
- Conflicto Obsidian: conserva el texto, lee la propuesta y resuelve intención.
- Error nativo: diagnostica; no tapes el fallo con un resumen optimista.

No notifiques cada paso. Registra el avance y comunica lo que requiere atención.
Una revisión puede terminar sin interrupción del usuario si no hay novedad relevante.
No crees nuevos cron desde este ciclo. Reprogramar el servicio o ampliar permisos
es una operación distinta, con su alcance correspondiente.

## Ediciones en Obsidian

`render` no sobrescribe bloques editados ni archivos eliminados. `conflicts` muestra
IDs/hash y una propuesta. Si la edición cambia datos personales/proyecto válidos:

```bash
python3 "$HERMES_HOME/scripts/donna_ops.py" resolve conflicto-id --hash HASH_OBSERVADO --action import-project --reason 'Intención del usuario leída y validada'
```

`keep-state` solo después de entender la intención y justificar conservar el estado;
se respalda el texto editado. Mover una tarjeta o marcarla no es prueba de finalización.
Las notas fuera de bloques se conservan. Consulta docs/OBSIDIAN.md.

## Terminar de verdad

Actualiza `next_review` del proyecto cuando su revisión esté hecha. Ejecuta las
acciones, `render`, vuelve a obtener `review` y usa el digest ACTUAL, no el inicial.
Prepara un reporte JSON:

```json
{
  "summary": "Acciones verificadas y decisiones pendientes, sin secretos",
  "next_at": "2026-09-23T09:00:00-06:00",
  "items": [
    {"id": "project-review:proyecto-id", "disposition": "resolved", "source": "referencia-a-cambio-real"},
    {"id": "task:tarea-id:1", "disposition": "deferred", "source": "referencia-a-bloqueo-real", "next_at": "2026-09-23T09:00:00-06:00"}
  ]
}
```

El ejemplo no se ejecuta sin ajustar fechas e IDs. Reporta la unión de IDs iniciales
y actuales exactamente una vez. `resolved` requiere que el elemento haya salido
de la cola; pendientes persistentes se difieren/escalan con seguimiento. `next_at`
ha de ser futuro, hasta siete días, no posterior a ningún seguimiento individual.

```bash
python3 "$HERMES_HOME/scripts/donna_ops.py" review-finish --token TOKEN_REAL --digest DIGEST_ACTUAL --report /ruta/privada/revision.json
```

No acuses recibo solo por haber despertado. Si el lease expiró o la cola cambió,
no repitas a ciegas: refresca, preserva evidencia y deja que el ciclo se recupere.
Una intervención lenta se divide en encargos y revisiones acotadas, no se mantiene
una sesión abierta durante semanas. El lease por defecto es de 900 segundos.

Tras errores, devuelve `[CRON_FAILURE]` seguido del bloqueo real cuando opere el
contrato nativo documentado. Tras tres wakes sin cierre, se exige diagnóstico y
`review-reset --reason`; no reinicies presupuestos automáticamente para ocultarlo.
Un briefing es solo la síntesis humana de esta revisión, no su sustituto.
