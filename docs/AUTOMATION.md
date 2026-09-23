# Automatización nativa: ejecutar, despertar, revisar

No hay daemon Donna nuevo. Los trabajadores durables, el scheduler y sus permisos
siguen siendo de Hermes. Este documento configura una instancia, no cambia el
repositorio automáticamente ni otorga acceso a cuentas.

## 1. Verificar topología y contrato

Ejecuta doctor --native y consulta el diagnóstico de Kanban, gateway y cron del
perfil real. Identifica el único propietario de dispatch. Donna puede conservar
`kanban.dispatch_in_gateway: false` cuando otro gateway despacha. Configurar
`orchestrator_profile: donna` no inyecta su lógica en el descomponedor genérico.

Este diseño crea planes/tarjetas explícitamente desde Donna. Revisa
`kanban.auto_decompose: false` EN EL HOST DE DISPATCH; no lo cambies globalmente sin
analizar otros tableros. No actives un segundo dispatcher para compensar un fallo.
Si la configuración compartida no permite ese cambio, mantén estas tarjetas fuera
de triage genérico y acuerda la topología con el operador.

Las tarjetas se crean por CLI con idempotency-key, tenant, assignee y workspace
persistente. Antes de usar modelos, verifica que la CLI instalada acepte esos flags
y devuelva el esquema esperado. Formas aceptadas: create con id/task_id directo o
objeto task; show directo o task; assignees como lista o envelope assignees/profiles.
Desviaciones no se adivinan: el adaptador falla cerrado y requiere un ajuste probado.

## 2. Avisos nativos opcionales

CLI-created no equivale a suscripción automática. Desde una sesión con origen
concreto, suscribe el ID usando la herramienta nativa disponible o la CLI:

```bash
hermes -p donna kanban --board donna-ops notify-subscribe CARD_ID \
  --platform PLATAFORMA --chat-id CHAT_REAL --user-id USUARIO_REAL \
  --chat-type dm --delivery-mode notify+wake
```

Verifica los flags en la instalación y registra destino/identificador de forma
privada; no publiques chat IDs. El gateway que posee la suscripción debe operar.
Al recibir wake, Donna carga su revisión y usa pulse/lease antes de coordinar.
El aviso por sí solo no decide si aceptar ni continuar el trabajo.

## 3. Reconciliación programada imprescindible para continuidad

Crea un trabajo mediante `cronjob_manage`, schema real de esa versión, PRIMERO
PAUSADO. Es un trabajo con agente, no `no_agent=true`. Sus campos conceptuales:

```json
{
  "action": "create",
  "name": "donna-operational-review",
  "schedule": "HORARIO_ACORDADO",
  "script": "donna_review_gate.py",
  "skills": ["donna-session", "donna-operational-review"],
  "workdir": "/ruta/absoluta/del/perfil",
  "enabled_toolsets": ["file", "terminal", "kanban", "skills", "memory", "session_search", "web"],
  "no_agent": false,
  "paused": true,
  "paused_reason": "Canary de aceptación antes de activar",
  "deliver": "DESTINO_PRIVADO_ACORDADO",
  "prompt": "Carga donna-session y donna-operational-review. Usa el token de la revisión que produjo el preflight; lee review completo. Verifica entregas, corrige, coordina el siguiente paso autorizado y conserva decisiones humanas. No crees otros cron ni cambies permisos/modelos. Renderiza Obsidian conservando conflictos. Finaliza con review-finish solo tras ejecutar y documentar cada disposición; si falla, informa [CRON_FAILURE] y el bloqueo real. No afirmes que notificar equivale a terminar. Comunica únicamente cambios relevantes, decisiones necesarias y bloqueos."
}
```

Esto es una especificación a completar y cotejar, NO un objeto listo para enviar
con placeholders. `deliver` origin solo sirve con una conversación real; desde
CLI/instalación utiliza destino explícito/local válido. No transmitas secretos
como variables de plantilla. Usa herramientas suficientes para actuar, no un
briefing limitado únicamente a web. Conectores concretos se agregan solo si están
configurados y son necesarios.

El script vive en `$HERMES_HOME/scripts`. `DONNA_OPS_CONFIG` se resuelve en ese
entorno, o se usa HERMES_HOME/donna-ops.json. Comprueba el intérprete y las variables
reales del gateway; no des por hecho que coinciden con una terminal interactiva.
Un preflight exitoso puede despertar al agente; la última línea JSON false lo omite.
Un error retorna no-cero para que el scheduler registre el fallo.

## 4. Canary y activación

Inspecciona jobs existentes antes de crear para no duplicar. Con el trabajo aún
pausado, prueba un Run now explícito: tiene que leer journal/tablero, actuar, renderear
y hacer review-finish. Prueba después otro tick sin cambios: debe evitar un turno
LLM innecesario. Prueba pérdida de un wake y respuesta de error. Comprueba runs,
incidents/status y entrega desde el canal cotidiano. Solo luego reanuda la agenda.

La fecha/hora, periodicidad y presupuesto los acuerda el usuario. No se publican
cron/jobs.json, credenciales ni preferencias privadas. Pausar cron no revoca un
permiso ni mata tareas nativas ya iniciadas. No reinicies un gateway desde su propia
sesión: usa la operación externa aprobada.

## 5. Límites y permisos

No reemplaces manual por auto para resolver atascos. Las tareas desatendidas deben
funcionar dentro de reglas estrechas previamente acordadas. Eliminar la antigua
allowlist amplia en un archivo distribuido no modifica la instalación; revisar el
merge y la autorización del script de confianza de forma explícita.

La lease y los presupuestos pertenecen a Donna; native max-runtime/max-retries y
concurrencia pertenecen a Hermes. Son límites complementarios. Al agotarse uno,
conserva pendiente y evidencia y organiza la recuperación. No cambies keys, perfiles,
modelos ni reintentos infinitamente para eludir el límite.

## 6. Legacy

El viejo kanban_board_notify.py era un emisor sin agente. Esta versión falla con
una instrucción de migración en vez de hacerse pasar por revisión. Pausa/reemplaza
su job viejo antes del update. El config_guard pasa a detectar sin restaurar modelos:
actualizar el código no debe provocar cambios automáticos de proveedor.
