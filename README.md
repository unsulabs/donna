# Donna · asistente personal ejecutiva y orquestadora

**Versión propuesta: 2.0.0-rc.1.** Implementación sobre la distribución 1.1.0,
commit base `ef15483af9765c32e7f86e2091a7709bbd387bb9`.

Donna ayuda a organizar con la persona sus obligaciones, aspiraciones y proyectos
de vida. Investiga para encargar bien, distingue trabajo humano de trabajo de
agentes y conserva la responsabilidad de seguimiento, corrección e integración.
No pretende ejecutar todo personalmente ni delegar la coordinación al usuario.

Esta versión añade código operativo y procedimientos al perfil de Hermes:
planificación, registro persistente, despacho idempotente, revisión independiente,
proyección en Obsidian y revisión programada con límites. **No sustituye Hermes,
no instala otro daemon y no reorganiza la bóveda existente.**

## Leer primero

| Necesidad | Documento |
|---|---|
| Qué hace cada pieza y quién conserva la verdad | [Arquitectura](docs/ARCHITECTURE.md) |
| Pasar de Donna 1.1 a esta versión sin perder datos | [Migración](docs/MIGRATION.md) |
| Comandos y contratos JSON | [CLI](docs/CLI.md), [datos](docs/DATA_CONTRACT.md) |
| Encargos durables y revisión proactiva | [Automatización](docs/AUTOMATION.md) |
| Ediciones en Obsidian | [Proyección y conflictos](docs/OBSIDIAN.md) |
| Pruebas offline y aceptación real | [Aceptación](docs/ACCEPTANCE.md), [testing](docs/TESTING.md) |
| Límites, privacidad y autorizaciones | [Seguridad](docs/SECURITY.md) |
| Fuentes técnicas y decisiones | [Fuentes](docs/SOURCES.md) |

## Estado de entrega

El código determinista tiene pruebas unitarias, de recuperación, de archivos y de
procesos separados con un **doble explícito de la CLI de Hermes**. Ese doble no es
Hermes, no llama modelos y no comprueba cuentas. El informe adjunto a la entrega
registra la ejecución efectivamente realizada. No se presenta una simulación como
prueba de funcionamiento en producción.

La publicación como estable requiere probar el Hermes instalado, el modelo, el
canal habitual, la topología de gateway/dispatcher y la interfaz de Obsidian en un
staging autorizado. El estado `rc` comunica esa separación, no falta de archivos.

## Instalar y configurar

Para una instalación nueva, el mecanismo nativo continúa siendo:

```bash
hermes profile install github.com/unsulabs/donna --alias
```

No ejecutar esa instrucción esperando esta versión hasta que se integre/publicite
la rama adecuada. Para probar el checkout revisado usa el instalador de distribución
con ruta local y un nombre de perfil de staging, verificando la ayuda instalada.
**Una instancia existente debe seguir MIGRATION.md; no usar force-config ni borrar
el perfil como atajo.** Modelos, credenciales, memoria y cuentas son del usuario.

Desde una instancia configurada:

```bash
python3 "$HERMES_HOME/scripts/donna_ops.py" --help
python3 "$HERMES_HOME/scripts/donna_ops.py" doctor
python3 "$HERMES_HOME/scripts/donna_ops.py" doctor --native
```

`init` requiere la bóveda que YA existe, una subcarpeta autorizada, perfil, tablero,
zona y capacidad declarada. Sin `--apply` solo presenta la configuración propuesta.
No crea cron, no conecta cuentas ni toca `.obsidian`.

## Desarrollo y pruebas

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests
```

Runtime principal: biblioteca estándar de Python 3.10+. El migrador opcional de
`.team` YAML necesita PyYAML en el intérprete usado; no lo instala. Los tests
principales no requieren Hermes, modelos, credenciales ni red. La CI define
comprobaciones en Python 3.10–3.13; una matriz declarada no es una matriz ya ejecutada.

## Diferencias que importan

Una tarjeta `done` es una entrega nativa. Donna exige evidencia antes de `verified`.
Un proyecto solo cierra con criterios completos y aceptación humana cuando aplica.
Un movimiento de tarjeta en Obsidian es una intención a resolver, no un resultado.
Un aviso perdido no borra el trabajo; la revisión lee el estado persistente.
Una tarea de Donna se realiza en su sesión; las tareas humanas nunca se despachan.

No hay agentes especialistas ficticios de fábrica: `.team.example` empieza vacío.
Las seis skills determinan cómo planificar, investigar, incorporar capacidades,
coordinar y dar seguimiento. Los scripts ejecutan las transiciones comprobables.

## Licencia

MIT, bajo la licencia existente de Unsu Labs. Conserva LICENSE y los activos
originales del repositorio. No publiques `.env`, `.team`, `donna-ops.json`, backups,
memoria ni el journal operativo del usuario.
