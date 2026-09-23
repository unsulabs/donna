# Proyección Obsidian y protección de intención

El toolkit se conecta a una bóveda existente y a una subcarpeta visible aprobada.
Solo administra allí `Board.md`, `Projects/<id>.md` y `Tasks/<id>.md`. No toca
`.obsidian`, instala plugins, reubica otras notas ni crea una bóveda como reparación.
El Markdown es legible sin plugin; la interfaz visual del plugin Kanban se debe
validar en la versión instalada de Obsidian.

Los archivos tienen exactamente un bloque `DONNA:BEGIN v1` / `DONNA:END`.
Las notas fuera del bloque se conservan al renderizar. Dentro se comprueba un hash
contra la última proyección. Un bloque modificado, archivo borrado, marcas alteradas
o archivo desconocido en esa ruta crean conflicto, no una sobrescritura silenciosa.

## Editar desde Obsidian

Las notas de proyecto ofrecen un JSON con `id`, `revision` y `editable`. Edita los
valores de editable; Donna detecta la diferencia, entiende la intención y usa
`resolve --action import-project` con el hash observado. Las revisiones incompatibles
se rechazan. El texto anterior se respalda en edit-backups fuera de la bóveda.

Arrastrar una tarjeta o marcarla como completa no tiene autoridad para finalizar
un worker o certificar un resultado. Donna lee esa intención, compara evidencia y
realiza la operación válida. Si no corresponde modificar, resuelve `keep-state`
con un motivo real y conservando la copia editada. Un conflicto relevante bloquea
nuevos despachos después de detectarse; el CLI renderiza antes de despachar para
no ignorar cambios de intención ya presentes en disco.

No se importan silenciosamente cualquier campo, Markdown libre o instrucciones
dentro de títulos. Los IDs son estables. Los títulos se escapan para no introducir
links, separadores o marcas de control no deseadas.

## Recuperación

`conflicts` enumera las diferencias y el hash actual. Resuelve solo la versión que
leíste. Si se vuelve a editar, refresca; nunca uses un hash antiguo por conveniencia.
Una eliminación solicita revisar intención; no equivale a borrar el proyecto.
La copia de seguridad de la proyección no reemplaza el backup del vault ni del journal.

El esquema de conciliación no constituye un bloqueo distribuido frente a todos
los editores. Ante escritura concurrente externa extrema puede conservarse un
conflicto que requiera reparación. No se garantiza sincronización instantánea libre
ni seguridad frente a un proceso malicioso con el mismo usuario del sistema.
