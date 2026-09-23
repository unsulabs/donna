# Contratos de datos y validaciones

## Configuración privada · schema_version 1

`donna-ops.json` se crea con `init`. No se guarda en Git. No contiene credenciales.
`instance_id` es UUID y participa en claves; nunca regenerarlo para una instancia
que ya despachó. `profile`, `profile_home`, `vault`, `state_dir`, `area`, `board` y
`timezone` son explícitos. El estado queda dentro del perfil y fuera de la bóveda.
`area` es relativa, normalizada y no puede apuntar a `.obsidian`, `.git` o escapar.
`hermes_command` es argv local de confianza; no aceptarlo de documentos o agentes.
`workspace_roots` permite raíces específicas de trabajo adicionales, no acceso
universal al disco. `human_capacity_hours` es número 0–168 o null (desconocido).
Los límites y rangos válidos están en `scripts/donna_runtime/config.py`.

## Plan · schema_version 1

Raíz: `project` y `tasks`. Ver `examples/plan.json`.

Proyecto: id, title, kind, outcome, criteria, priority (1–5), next_review (ISO con
zona), allocation_hours_week, assumptions[], context_refs[], acceptance_owner
(user/donna), deadline opcional `{date, source}`, target_date opcional YYYY-MM-DD.
Clases: aspiration, responsibility, routine, project, commitment.

Tarea: id, title, owner `{kind,id}`, outcome, brief, criteria[], dependencies[],
capabilities[], skills[], action_class, source_refs[], duration_days `{low,high}`,
human_hours `{low,high}`, not_before opcional con zona, deadline opcional, workspace
opcional absoluto dentro de raíces aprobadas. Roles: user, human, donna, agent.
Acciones: internal, publish, payment, destructive, account_change.

IDs: minúsculas, números, guiones y guiones bajos; máximo 64; primer carácter
alfanumérico. Son únicos en la instancia, no solo por proyecto. No usar títulos
como clave. Las dependencias se limitan al proyecto y deben ser acíclicas.
La pertenencia al proyecto es `project_id`, no un parent nativo que cause bloqueo.

Si se omiten estimaciones, el runtime registra incertidumbre y no emite un rango
final como si el trabajo fuera de duración cero. Los intervalos no son reservas
calendario. No se inventan fechas externas a partir de estimaciones.

## Roster privado `.team` · schema_version 2

Formato JSON estricto, no YAML informal. Miembros: id, profile, role, capabilities,
skills, doctrine_paths, status, verified_at, checks. Estado: proposed, configured,
verified, disabled. Para verified se exigen comprobaciones model/tools/handoff con
passed true, source real, fecha vigente, capacidades y doctrina. No hay miembros
activos de fábrica. Omitir uno al importar deshabilita ese registro para nuevos
encargos. Un roster editado invalida el import hasta su revisión/reimportación.

`checks` es testimonio trazable de pruebas reales; no una certificación criptográfica.
El despacho comprueba además la existencia del perfil por el CLI nativo. Las skills
pedidas deben estar en el inventario verificado del destinatario.

## Evidencia

Raíz: reviewer, source, summary, checks[] y receipt para una aceptación humana.
Cada check: criterion, passed (booleano true), source, observation y opcionalmente
artifact `{path,sha256}`. Debe cubrir exactamente todos los IDs de criterio una vez.
El archivo se lee bajo raíces autorizadas; el hash tiene 64 caracteres hex minúsculos.
No se ejecutan comandos incluidos en source/observation. Una prueba de calidad o
aprobación no se inventa llenando este JSON. Ver examples/evidence.json.

## Revisiones y cambios

`project-amend`: title, outcome, priority, next_review, assumptions, context_refs,
target_date; necesita revisión optimista vigente. allocation se cambia con allocate.
`task-revise`: contrato completo solo mientras el intento no esté preparado/despachado;
requiere revisión y autorización de alcance. `task-add` no borra tareas existentes.
No hay comando de borrado masivo o cierre silencioso.

Reporte review-finish: summary, next_at futuro hasta 7 días, items[]. Cada item tiene
id, disposition resolved/deferred/escalated, source y next_at para pendientes. Debe
cubrir la unión de elementos de la lease y la cola actual. El digest debe ser el
actual y un elemento presente no puede declararse resuelto.

Los campos desconocidos se rechazan en los contratos principales. La evolución de
esquemas requiere migración explícita y nuevas pruebas, no ignorar silenciosamente
los campos que el código no entiende.
