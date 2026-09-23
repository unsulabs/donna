# Arquitectura y decisiones de diseño

## 1. Cuatro responsabilidades, no cuatro copias de la misma verdad

La bóveda conserva el propósito, notas, referencias y decisiones de la persona.
El journal de Donna es su índice operacional: contratos de proyecto/tarea, acciones
humanas, evidencias, dependencias, intentos y aceptación. La proyección Markdown
expone ese índice en la bóveda y admite cambios humanos controlados. Hermes conserva
el estado real del worker y su cola durable. La memoria conversacional existente
permanece separada; no se reemplaza por el journal.

No se incorporan automáticamente todas las notas de una bóveda ni se extraen
conclusiones de la vida del usuario sin leer fuentes. Donna debe vincular las
fuentes relevantes en el contrato antes de activar trabajo.

## 2. Componentes implementados

| Módulo | Responsabilidad |
|---|---|
| common/config | Validación, rutas, zona, configuración privada, escritura protegida |
| models | Contratos, roles, criterios, grafo acíclico, readiness y evidencia |
| store | SQLite propio, revisiones optimistas, transacciones y log de eventos |
| engine | Planes, capacidad, aprobaciones, outbox, despacho, revisión y cierre |
| hermes | Adaptador estrecho al CLI público, argv sin shell, límites y errores seguros |
| projection | Bloques Markdown, tablero, propuestas y conservación de conflictos |
| review | Cola de atención, leases, presupuesto y acuse después de actuar |
| cli | Comandos JSON inspeccionables y códigos de salida |

No hay acceso directo al SQLite de Hermes, scraping de su GUI, un segundo scheduler,
ni una implementación alternativa del agente LLM. Hermes sigue eligiendo y ejecutando
sus herramientas según sus propias instrucciones y controles.

## 3. Ciclo y estados

Proyecto: `incubating/planned → active → paused/closed`. Reabrir un cerrado lo deja
`planned` para revisar alcance; no inicia trabajo silenciosamente. `responsibility`
y `routine` se revisan o pausan; no se cierran como proyectos finitos.

Tarea especialista: `planned → dispatching → dispatched → awaiting_review → verified`.
`waiting` conserva un bloqueo/fase nativa que requiere atención. Una entrega DONE
rechazada pasa a `needs_changes`, incrementa intento y vuelve a despacharse con
clave nueva acotada. Un transporte fallido NO incrementa el intento semántico.

Las tareas humanas y propias de Donna pasan de plan a evidencia sin asignarse a
un perfil worker. La verificación requiere dependencias verificadas y proyecto
activo/pausado. Registrar una evidencia no ejecuta el contenido de esa evidencia.

## 4. Entrega, aceptación y dependencias

El motor nativo conoce DONE; no conoce necesariamente la satisfacción real del
usuario. Por eso el toolkit no despacha un dependiente hasta `verified`. Los
prerrequisitos nativos son una capa adicional, nunca la única.

La aceptación requiere evidencia por todos los criterios, referencias, observaciones
y recibo humano cuando corresponde. Hashes opcionales comprueban bytes. La verdad
semántica de las observaciones sigue siendo responsabilidad de quien revisa: no
existe una prueba universal automática de que una afirmación sea cierta.

Rework conserva el DONE original, crea intento nuevo y vuelve a exigir permisos
sensibles. Invalida aceptaciones dependientes; no mata automáticamente workers
que ya corren. Antes de cerrar, se releen entregas nativas y hashes registrados.

## 5. Interrupciones e idempotencia

Antes del efecto externo se persiste intención, payload y clave. Si el CLI creó
la tarjeta pero se perdió la respuesta, se repite la misma clave. Esto depende
del contrato público de idempotencia nativa. El toolkit detecta IDs contradictorios;
no afirma exactly-once universal ni garantiza contra mutaciones fuera del sistema.

SQLite conserva transacciones y revisiones; la propia proyección tiene control de
hash para cambios humanos. No hay transacción distribuida entre archivos, SQLite,
Hermes y Obsidian. Una interrupción puede dejar una vista retrasada o un conflicto;
la reparación conservadora evita aceptar silenciosamente pérdida de intención.

## 6. Presupuestos

Por defecto: hasta 4 despachos por lote, 40 observaciones por tick con rotación,
3 intentos de transporte con backoff, 2 correcciones semánticas, 3 wakes sin cierre,
lease de 900 segundos y revisión de readiness a 30 días. Todos son límites locales
configurables, no plazos de proyecto. Los límites nativos del worker también se
transmiten. El equipo puede requerir concurrencia menor según hardware/proveedor.

`max_sync_per_run` implica que un tablero grande requiere varios ticks para una
pasada completa. El resultado informa scanned/total/full_pass; no afirma conocer
instantáneamente todo el tablero. La revisión detecta trabajo pendiente incluso
si falla una notificación; si falla el CLI, informa el fallo en vez de simular silencio.

## 7. Decisiones explícitas

No un `/goal` indefinido para toda la vida. No confundir el descomponedor genérico
con Donna planificando con su contexto. No duplicar una bóveda. No desactivar todas
las aprobaciones. No prometer sincronización bidireccional libre: la proyección
acepta un conjunto de campos; los demás cambios requieren resolver intención.

La arquitectura permite incorporar tipos de tarea y especialistas sin convertir a
Donna en quien produce todo. Las skills describen el método; los registros y pruebas
hacen observables sus compromisos.
