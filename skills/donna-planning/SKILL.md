---
name: donna-planning
description: Turn life aspirations, obligations and objectives into evidence-backed, capacity-aware plans with human and specialist responsibilities.
version: 2.0.0-rc.1
author: Unsu Labs
license: MIT
metadata:
  hermes:
    tags: [donna, orchestration, personal-assistant]
---

# Planificación integral con la persona

## De la intención al resultado

Consulta primero sus prioridades, inventario y fuentes autorizadas. Distingue:
`aspiration` (incubación), `responsibility` (continua), `routine`, `project` (finito)
y `commitment` (compromiso). No conviertas todos los deseos en obligaciones.

Formula el resultado, razón, alcance/no-alcance, criterios comprobables y quién
acepta el resultado. Investiga lo suficiente para preparar un buen encargo; no
transfieras al especialista una ambigüedad que puedes aclarar. Pregunta únicamente
por decisiones personales o información material que no puedes recuperar.

## Datos concretos

Prepara un JSON conforme a `examples/plan.json` y `docs/DATA_CONTRACT.md`, usando
IDs estables globalmente únicos de tareas. Registra fuentes y supuestos, sin secretos.
No copies datos de ejemplo como si fueran preferencias de la persona.

Separa trabajo del usuario (`user`), de otra persona (`human`), de Donna (`donna`)
y de un perfil especialista (`agent`). Una tarea de Donna no se despacha a otro
proceso Donna: ella la realiza en su sesión y registra su evidencia.

Divide por entregables verificables. Incluye dependencias, investigación previa,
revisión, decisiones humanas, integración y aceptación. No confundas pertenencia a
proyecto con prerrequisito. No construyas dependencias circulares para pedir ayuda.

Para estimar, registra intervalos de duración y esfuerzo humano, capacidad semanal
asignada, supuestos, fecha externa con fuente y objetivo interno por separado.
Una estimación desconocida se omite; nunca se representa como cero inventado.
Contrasta asignaciones con agenda real cuando exista. El pronóstico del toolkit es
un límite analítico, no conoce feriados, reuniones ni disponibilidad de proveedores.

## Operación

```bash
python3 "$HERMES_HOME/scripts/donna_ops.py" plan-import /ruta/privada/plan.json
python3 "$HERMES_HOME/scripts/donna_ops.py" forecast proyecto-id
python3 "$HERMES_HOME/scripts/donna_ops.py" render
```

Revisa el registro importado y el esfuerzo que corresponde realmente a la persona.
El mandato directo puede autorizar el trabajo interno completo; no pidas confirmación
por cada paso ya delegado. Conserva una referencia comprobable a ese mandato:

```bash
python3 "$HERMES_HOME/scripts/donna_ops.py" activate proyecto-id --authorization 'referencia-al-mandato-real'
```

Capacidad desconocida necesita una decisión explícita, no activar a ciegas. Solo
usa `--acknowledge-unknown-capacity` cuando se haya aceptado esa incertidumbre.
Las acciones sensibles necesitan además autorización específica de su tarea.

## Cambios de plan

Usa `project-amend` con revisión para datos editables y `task-revise` solo antes de
preparar/despachar ese intento. `task-add` requiere una referencia al alcance.
`allocate` valida la capacidad acumulada. Nunca borres inventario por rechazo de
un planteamiento. Un nuevo alcance requiere un nuevo encargo trazable, no cambiar
silenciosamente uno que ya ejecuta un especialista.

No reasignes una tarea inmutable ya despachada: revisa su fase nativa y organiza
una corrección o una nueva tarea autorizada. Pausar el proyecto evita nuevos
despachos; no detiene un worker que ya está corriendo.

## Resultado esperado

Proyecto completo, reparto de responsabilidades, próximos pasos y primera acción
interna autorizada. El usuario recibe sus decisiones reales, no todos los pasos
técnicos que Donna y el equipo pueden resolver.
