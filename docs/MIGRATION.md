# Migración de repositorio e instalación

## A. Integrar código en GitHub (no equivale a instalar)

La entrega es un overlay de archivos nuevos/reemplazados sobre el commit base
`ef15483af9765c32e7f86e2091a7709bbd387bb9`. Los activos, licencia y archivos no
modificados siguen en el repo original. No es una clonación completa con `.git`.

El paquete tiene manifest de hashes de salida y Git blob preimages. Primero
revisa el código y el prompt de entrega. En un worktree limpio a la base, crea rama
feature y ejecuta `apply_overlay.py --repo RUTA` (dry run); después, `--apply`.
El helper no hace fetch, checkout, commit, push ni modifica una instancia instalada.

Si main avanzó: crea worktree separado en la base, aplica ahí, revisa diff y mergea
los cambios hacia la rama actual con reconciliación de conflictos. Nunca fuerces
el helper contra una base diferente, borres cambios del usuario o uses reset hard.
Cada archivo reemplazado tiene preimage esperada. Nuevos paths no pueden colisionar.

Corre los tests, compileall y revisión de secretos. Usa una PR/rama para revisión
antes de main. No declares publicada una versión porque exista el ZIP local.

## B. Preparar staging operativo

Inventaría lo instalado: versión Hermes, perfil, config efectivo, skills adicionales,
roster, memory provider, vault, scheduler, dispatcher, canal y jobs. No registres
secretos en la PR. Respalda configuración, roster y notas con mecanismos privados;
usa el backup SQLite del toolkit cuando ya exista. `cp` del archivo DB en uso no
es un backup consistente del WAL.

Instala el checkout revisado como un perfil de staging con nombre propio, sin
canales externos heredados, tablero separado y copia/autorización de datos de prueba.
No abras dos procesos independientes con la misma identidad/canales de producción.
La copia de staging de `donna-ops.json` necesita instance_id NUEVO y su board nuevo;
la instancia real conserva su ID durante upgrades normales.

## C. Compatibilidad y datos

No ejecutar `--force-config` ni reemplazar config privado con el del ZIP. El default
nuevo es para instalación nueva; revisa diferencias de toolsets, approvals y
proactividad conservando modelo, proveedor, memoria y cuentas. La versión mínima
numérica no acredita todas las APIs; `doctor --native` y la aceptación real sí
comprueban los contratos requeridos, cada uno con sus límites.

`.team` v1 YAML pasa a v2 JSON. Ejecuta donna_migrate_team.py hacia un archivo nuevo,
primero en seco. Revisa capacidades/skills, aplica y sustituye el privado mediante
un cambio aprobado con respaldo. Readiness se degrada a configured y debe
reacreditarse; no confíes en antiguos `active`. No añadas `.team` vivo al repo.

La distribución no debe escribir memories/USER.md o MEMORY.md sobre la memoria
local. Los viejos seeds públicos quedan como históricos sin autoridad automática;
no son datos personales ni motivo para cambiar el proveedor.

## D. Bóveda y automatización

Conecta la bóveda existente con init, sin scaffold. Define subcarpeta aprobada y
comprueba conflictos en una copia antes de vincular producción. Las notas originales
se usan como fuentes; no se trasladan masivamente al journal.

Pausa los jobs legacy de notificador/guard antes de cambiar sus scripts. Revisa
otras automatizaciones que dependan de ellos. Configura y prueba el nuevo ciclo de
revisión primero pausado. El repositorio no puede conocer los IDs, horarios, tokens
ni topología efectivos de una instalación privada.

## E. Puertas para producción

Ejecuta todos los escenarios de ACCEPTANCE.md con evidencia desde el canal real,
no solo terminal. Comprueba recepción, planificación, investigación, despacho,
rework, cierre, edits, reinicio y permisos desatendidos. Una incompatibilidad nativa
requiere un patch del adaptador y un test de regresión; no un bypass al almacenamiento
interno. Solo con esas pruebas se cambia de rc a estable y se activa producción.

## F. Reversión

Antes del cambio, registra commit previo, archivos privados respaldados, jobs/estados
y tarjetas activas. Para retroceder código, revierte el commit de la PR, no todo el
repo del usuario. Pausa nuevos despachos/revisiones; inspecciona workers en vuelo con
Hermes. El comando pause del toolkit NO los detiene.

No vuelvas a un backup antiguo del journal mientras workers continúan produciendo:
puede perder asociaciones de intento y evidencias. Reconcílialos contra IDs/claves
nativos. Conserva el journal nuevo y las notas editadas como evidencia. Restaura datos
solo con decisión explícita y análisis de divergencias; jamás borres la bóveda.
