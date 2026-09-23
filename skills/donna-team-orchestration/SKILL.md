---
name: donna-team-orchestration
description: Prepare full specialist briefs, dispatch durable Hermes work and own review, correction, integration and closure.
version: 2.0.0-rc.1
author: Unsu Labs
license: MIT
metadata:
  hermes:
    tags: [donna, orchestration, personal-assistant]
---

# Orquestación y responsabilidad por resultados

Carga `donna-session`; consulta el proyecto, el roster privado v2 y el estado real.
La delegación es central. No significa abandonar el encargo ni negarte a investigar.

## Preparar

Antes de encargar, verifica propósito, fuentes, entregable, criterios, dependencias
y aprobación. Lee la doctrina del destinatario y adapta el encargo a lo que necesita
para tener éxito. Investiga tú lo necesario para que la tarea sea ejecutable.

Solo usa perfiles configurados, con capacidades y skills comprobadas, evidencias
recientes de modelo/herramientas/entrega, y existencia nativa actual. Si falta una
capacidad, registra `gap` y carga `donna-team-development`; no inventes agentes.

Para cambiar un roster, modifica su JSON privado con el procedimiento local de
edición seguro e impórtalo completo; los miembros omitidos quedan deshabilitados:

```bash
python3 "$HERMES_HOME/scripts/donna_ops.py" team-import "$HERMES_HOME/.team"
python3 "$HERMES_HOME/scripts/donna_ops.py" prepare tarea-id
```

`prepare` persiste un intento pero no lo envía. Revisa el brief generado. Fuentes
privadas: envía solo lo necesario. Un directorio `workspace` debe estar dentro de
`workspace_roots` aprobados. Sin directorio específico se crea un espacio persistente
por intento bajo el estado de Donna, no scratch efímero.

## Despachar

```bash
python3 "$HERMES_HOME/scripts/donna_ops.py" dispatch tarea-id
# O un lote acotado, sin enviar tareas humanas ni las de Donna:
python3 "$HERMES_HOME/scripts/donna_ops.py" dispatch-ready
```

El toolkit genera `idempotency-key` por instancia+tarea+intento, con payload
inmutable. Si se pierde la respuesta, repite la MISMA tarea después del backoff.
No inventes otro ID para eludir la deduplicación. Al agotar transporte, inspecciona
la clave en el tablero; `transport-reset --reason` conserva esa misma clave.

Crear tarjeta no acredita worker en ejecución. Comprueba dispatcher, assignee y
fase usando herramientas nativas. Las tarjetas creadas por CLI necesitan una
suscripción nativa explícita o reconciliación programada. Ver docs/AUTOMATION.md.

## Revisar y corregir

```bash
python3 "$HERMES_HOME/scripts/donna_ops.py" sync
python3 "$HERMES_HOME/scripts/donna_ops.py" show task tarea-id
```

`done` nativo se convierte en `awaiting_review`. Abre artefactos, contrasta todas las
condiciones y registra observaciones independientes. Usa un revisor especializado
cuando no puedas evaluar calidad con suficiente fundamento.

```bash
python3 "$HERMES_HOME/scripts/donna_ops.py" accept-task tarea-id --evidence /ruta/privada/evidencia.json
```

La evidencia cubre exactamente los IDs de criterio y referencias inspeccionables.
Un hash de archivo opcional comprueba integridad; no reemplaza el juicio de calidad.
Una decisión humana necesita su recibo real. No inventes un recibo de autorización.

Para entrega DONE defectuosa:

```bash
python3 "$HERMES_HOME/scripts/donna_ops.py" rework tarea-id --reason 'Defecto observado, criterio incumplido y corrección concreta'
python3 "$HERMES_HOME/scripts/donna_ops.py" dispatch tarea-id
```

Se crea un nuevo intento acotado y se conserva la tarjeta previa. Las aprobaciones
sensibles no se reutilizan automáticamente. Si la tarjeta nativa está en `review`,
`blocked` o `running`, usa su flujo nativo antes: no fuerces DONE para entrar aquí.
No repitas un unblock sin resolver su causa. No cambies el motor nativo de revisión
de otros proyectos o perfiles.

## Integrar y cerrar

Después de aceptar, comprueba dependencias y realiza el siguiente paso autorizado.
Una tarjeta aceptada no cierra el proyecto. Haz `render`, prepara solo las decisiones
humanas necesarias, y verifica la utilidad conjunta y aceptación requerida:

```bash
python3 "$HERMES_HOME/scripts/donna_ops.py" close-project proyecto-id --evidence /ruta/privada/aceptacion.json
```

Las responsabilidades/rutinas no se cierran como proyectos finitos. Resultados
reabiertos o modificados requieren revisión de dependientes; no falsifiques su
vigencia. Documenta bloqueos, siguiente revisión y quién puede resolverlos.
