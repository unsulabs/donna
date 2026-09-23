# Seguridad y límites de confianza

El toolkit reduce errores operativos; no constituye aislamiento de agentes que
comparten el mismo usuario del sistema. Un proceso con permisos de escritura sobre
el journal puede alterarlo. Configuración, argv nativo, fuentes de autorización y
registros de readiness son entradas locales de confianza, no mecanismos de login.

El adaptador usa argv sin shell, perfil explícito, tiempo/salida limitados y no
reproduce errores nativos crudos que podrían incluir secretos. Rechaza su uso como
coordinador desde un scope de worker heredado, sin borrar variables para eludirlo.
No utiliza cuentas ni pide passwords. No escribe bases internas de Hermes.

Los paths administrados rechazan symlinks/escapes y se usan archivos privados,
transacciones y compare-and-swap conservador. No es protección completa frente a
un adversario del mismo usuario ni ante todos los escenarios TOCTOU. No configura
por sí solo sandbox de sistema, egress ni permisos de terceros.

Una autorización sensible necesita fuente real, por tarea e intento. El código
valida el registro pero no sabe si la conversación fue auténtica. Donna y la capa
nativa deben respetar la autoridad humana. Una anotación `passed:true` no verifica
por sí sola calidad, permiso o veracidad; requiere prueba/observación real.

No enviar a especialistas más datos que los necesarios. No guardar secretos en
briefs, tarjetas, argumentos, proyecciones, recibos o fuentes. El journal puede
contener información personal y sus backups deben permanecer privados. `.gitignore`
no borra un secreto ya versionado: revisar git diff y contenido antes de publicar.

No desactivar aprobaciones como reparación. Una allowlist demasiado amplia de
heredoc o -c permite más de lo necesario. La distribución nueva no la incluye;
la migración del permiso efectivo es explícita y probada en staging.

El paquete es unsigned: checksums comprueban integridad, no identidad del autor.
Verifica procedencia/base/diff antes de ejecutarlo. Las tareas de CI usan permisos
mínimos y no reciben credenciales de modelos. Los fixtures son sintéticos.

## Límites operativos importantes

No hay exactamente-una-vez universal de efectos externos. No se puede deshacer
un pago/publicación enviando un comando al journal. Pausar no mata workers. No hay
sincronización libre automática de todos los formatos Obsidian ni comprensión
semántica garantizada de evidencias. Ningún test offline prueba una personalidad
o proactividad real del modelo. Las pruebas live cubren esas diferencias.
