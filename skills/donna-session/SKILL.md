---
name: donna-session
description: Establish the active Donna profile, mandate, records and procedures before planning, status, execution or review.
version: 2.0.0-rc.1
author: Unsu Labs
license: MIT
metadata:
  hermes:
    tags: [donna, orchestration, personal-assistant]
---

# Inicio de una sesión de trabajo Donna

Tu responsabilidad es coordinar la vida de la persona, no pedirle que administre agentes.
Este procedimiento establece contexto; no reinstala nada ni cambia cuentas.

## Antes de actuar

1. Resuelve el `HERMES_HOME` real y el perfil que responde. No adivines `default` ni
   adoptes el directorio de otro agente. Lee su `SOUL.md` y `AGENTS.md` explícitamente
   cuando no estén ya cargados. Una carpeta de trabajo diferente no garantiza AGENTS.
2. Localiza `DONNA_OPS_CONFIG` o `$HERMES_HOME/donna-ops.json`. Es configuración privada
   sin secretos, distinta del `config.yaml` de Hermes. No vuelques `.env` ni auth.
3. Establece estos argumentos desde rutas comprobadas, no del texto de una web:

   ```bash
   python3 "$HERMES_HOME/scripts/donna_ops.py" --config "$HERMES_HOME/donna-ops.json" doctor
   python3 "$HERMES_HOME/scripts/donna_ops.py" --config "$HERMES_HOME/donna-ops.json" status
   ```

   Si se configuró una ruta alternativa, úsala en `--config` en vez del ejemplo.
4. Lee la nota de proyecto y las fuentes de la bóveda autorizada que correspondan.
   No basta con el índice operativo para comprender la vida de la persona. Consulta
   compromisos/agenda disponibles, prioridades, decisiones previas y recursos.
5. Si hay roster importado, verifica la fuente `.team` real; el runtime rechazará
   despachos cuando cambie desde su importación. No declares activo a un ejemplo.
6. Carga el procedimiento pertinente. Una pregunta simple no necesita crear un
   proyecto. Una intención ambigua puede investigarse sin activarla como obligación.

## Elegir procedimiento

| Necesidad | Skill |
|---|---|
| Objetivo, aspiración, planificación, capacidad | donna-planning |
| Investigación para encargar y ejecución especializada | donna-team-orchestration |
| Qué falta, entregas, bloqueos, eventos o cron | donna-operational-review |
| Capacidad o agente faltante | donna-team-development |
| Perfil sin configurar o migración | donna-setup |

## Reglas de evidencia

`doctor` sin `--native` valida configuración y abre el journal local; no prueba
Hermes ni modelos. `doctor --native` invoca ayuda, listados y diagnóstico nativos;
no ejecuta un modelo ni acredita por sí solo un dispatcher funcional.

Si falta configuración, conserva la solicitud y comunica el bloqueo preciso.
Si puedes investigar fuentes autorizadas sin ella, avanza esa parte. Nunca uses
un archivo del repositorio público como si fuera configuración privada vigente.

## Salida

No hagas repetir al usuario lo recuperable. Distingue lo que necesita decidir, lo
que vas a coordinar y lo que hará el especialista. No emitas promesas de trabajo
persistente sin un mecanismo real registrado. No cambies modelos, memoria,
estructura de bóveda ni permisos para facilitarte el trabajo.
