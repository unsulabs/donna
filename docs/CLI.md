# CLI de coordinación

Invocación: `python3 /ruta/perfil/scripts/donna_ops.py --config /ruta/perfil/donna-ops.json COMANDO`.
El ejemplo puede omitir `--config` únicamente si DONNA_OPS_CONFIG o HERMES_HOME están
correctamente definidos. `init` siempre requiere --config explícito. Los argumentos
globales van antes del subcomando. Ejecuta `COMANDO --help` para su sintaxis exacta.

No son nuevos comandos nativos de Hermes. Es código de esta distribución que usa
su API CLI pública. No escribir SQL ni modificar cron/jobs.json para simularlos.

| Operación | Comando / efecto |
|---|---|
| Proponer/conectar configuración | init; sin --apply no escribe |
| Crear inventario de proyecto | plan-import archivo.json; idéntico se deduplica |
| Activar mandato | activate ID --authorization REFERENCIA |
| Ajustar alcance | task-add PROYECTO archivo.json --authorization REF |
| Revisar contrato no despachado | task-revise TAREA archivo.json --revision N --authorization REF |
| Modificar propósito/prioridad | project-amend ID archivo.json --revision N |
| Capacidad humana | allocate ID --hours N --authorization REF |
| Pausar / reabrir | pause/reopen ID --reason TEXTO |
| Equipo | team-import archivo.json, team-list |
| Carencia | gap PROYECTO CAPACIDAD --reason TEXTO; gap-resolve GAP MIEMBRO |
| Preparar intento | prepare TAREA; persiste clave/payload, sin enviar |
| Despachar | dispatch TAREA o dispatch-ready (lote limitado) |
| Autorización sensible | authorize-task TAREA --reference REF; no elude controles nativos |
| Reconciliar | sync; ronda acotada, errores explícitos |
| Verificar entrega | accept-task TAREA --evidence archivo.json |
| Solicitar corrección | rework TAREA --reason TEXTO; solo entrega nativa DONE |
| Recuperar transporte | transport-reset TAREA --reason TEXTO; misma clave, no duplica intención |
| Cierre de proyecto finito | close-project PROYECTO --evidence archivo.json |
| Previsión | forecast PROYECTO; supuestos y límites visibles |
| Proyección | render, conflicts, resolve (hash+acción+motivo) |
| Cola de atención | review; no ejecuta un modelo |
| Puerta programada | pulse; última línea stdout JSON wakeAgent |
| Cerrar revisión | review-finish --token TOKEN --digest DIGEST --report archivo.json |
| Recuperar revisión atascada | review-reset --reason TEXTO, no usar en cada tick |
| Inspeccionar | status; show project/task/member/gap ID; events --after N --limit N |
| Diagnóstico | doctor [--native]; native no ejecuta LLM |
| Respaldo consistente | backup /ruta/nueva/respaldo.sqlite |

JSON a stdout, errores estructurados a stderr sin volcar salida nativa. Código 0:
operación válida; 2: rechazo/contrato/error; 3: diagnóstico incompleto, sync con
errores, lote fallido o proyección con conflictos. No tratar exit distinto de cero
como tarea exitosa aunque haya un archivo de salida. No todas las operaciones son
read-only: doctor/status abren el journal propio si aún no existe.

La referencia de autorización identifica el mandato real (conversación/documento);
no es una contraseña. No pongas tokens ni contenido sensible innecesario en argumentos.

## Ayuda generada por el parser de esta versión

```text
usage: donna_ops.py [-h] [--version] [--config CONFIG]
                    {init,plan-import,task-add,activate,pause,reopen,project-amend,team-import,team-list,gap,gap-resolve,prepare,dispatch,forecast,dispatch-ready,task-revise,transport-reset,allocate,authorize-task,accept-task,close-project,rework,sync,render,conflicts,review,pulse,status,show,resolve,review-finish,review-reset,doctor,backup,events} ...

Donna coordination toolkit — no implicit installation or background service

positional arguments:
  {init,plan-import,task-add,activate,pause,reopen,project-amend,team-import,team-list,gap,gap-resolve,prepare,dispatch,forecast,dispatch-ready,task-revise,transport-reset,allocate,authorize-task,accept-task,close-project,rework,sync,render,conflicts,review,pulse,status,show,resolve,review-finish,review-reset,doctor,backup,events}
    init                Plan configuration, or create it with --apply; never
                        scaffold the vault

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  --config CONFIG       Absolute path to the private donna-ops.json; otherwise
                        DONNA_OPS_CONFIG/HERMES_HOME
```
