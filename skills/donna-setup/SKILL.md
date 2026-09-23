---
name: donna-setup
description: Install or migrate Donna safely, attach an existing vault, preserve models and memory, verify runtime and enable only approved native automation.
version: 2.0.0-rc.1
author: Unsu Labs
license: MIT
metadata:
  hermes:
    tags: [donna, orchestration, personal-assistant]
---

# Instalación e incorporación segura

No uses este procedimiento como excusa para reorganizar una vida o una bóveda.
Distingue instalar una distribución, configurar una instancia y validar operación.
La versión es candidata hasta superar `docs/ACCEPTANCE.md` en el entorno real.

## 0. Inspección sin cambios

Identifica perfil/HERMES_HOME reales, versión/CLI de Hermes, canal usado, bóveda
existente y capacidades disponibles. Comprueba qué gateway posee el dispatcher y
qué proceso ejecuta cron/entrega avisos. Lee docs/MIGRATION.md y docs/AUTOMATION.md.
No muestres credenciales ni vuelques `.env`, `auth.json` o toda la configuración.

## 1. Elegir rama

**Instalación existente (predeterminada si hay datos):** preservar memoria/proveedor,
modelos, `.team`, configuración, notas, plugins y otras skills. Respaldar de forma
privada; no subir el respaldo. Pausar/revisar los cron antiguos de board-notify y
config-guard ANTES de sustituir scripts. Staging separado antes de producción.

**Instalación nueva:** usar el instalador nativo de distribución. El equipo y la
bóveda se conectan solo con el alcance acordado. El viejo starter PARA se mantiene
como opcional; `scaffold_vault.py --apply` acepta solo un destino nuevo. No crees
otra bóveda si la persona ya tiene una que quiere usar.

## 2. Acuerdo de operación

Recupera lo ya conocido. Resuelve en un solo pase solo los datos faltantes: ubicación
aprobada dentro de la bóveda, capacidad humana inicial o incertidumbre aceptada,
prioridades/áreas, autonomía interna, acciones sensibles, horario/canal y presupuesto
de revisiones. Identidad, idioma y zona salen del usuario, no del autor del paquete.
La disponibilidad declarada es insumo inicial; no sustituye revisar agenda.

## 3. Configuración local explícita

Ejemplo con rutas ya resueltas (no ejecutar los nombres de ejemplo literalmente):

```bash
python3 "$HERMES_HOME/scripts/donna_ops.py" --config "$HERMES_HOME/donna-ops.json" init \
  --profile donna --profile-home "$HERMES_HOME" --vault /ruta/boveda-existente \
  --area 'Operaciones/Donna' --board donna-ops --timezone America/Mexico_City --human-capacity 6
```

Primero devuelve una propuesta sin cambios. Añade `--apply` con acuerdo de esas
rutas. El fichero debe ser nuevo: jamás reemplaza una configuración vigente.
Mantén `OBSIDIAN_VAULT_PATH` coherente para skills nativas que lo usan; no cambies
proveedores ni tokens. Para `workspace_roots`, registra únicamente ubicaciones
adicionales acordadas. No uses `/` o la carpeta personal entera como atajo.

## 4. Roster y compatibilidad

Una instancia nueva parte de `.team.example` vacío. No lleva agentes falsamente
activos. En v1, usa `scripts/donna_migrate_team.py` hacia archivo NUEVO, primero sin
`--apply`; si el origen es YAML el intérprete necesita PyYAML ya revisado. El script
no instala dependencias. Todas las readiness se restablecen para comprobación.
Revisa el candidato y acuerda sustituir el roster privado con respaldo, nunca en Git.

```bash
python3 "$HERMES_HOME/scripts/donna_ops.py" doctor --native
```

Verifica existencia de tablero y perfiles mediante ayuda/API nativas. La ayuda
compatible no acredita el modelo ni un dispatcher funcionando. No cambies una
configuración global por no haber identificado el gateway correcto. El toolkit usa
el CLI público, nunca tablas internas ni procesos paralelos improvisados.

## 5. Canary de extremo a extremo

Usa una copia aprobada de notas y un tablero de prueba, fuentes sintéticas y perfiles
con canales externos deshabilitados. Importa un proyecto pequeño con investigación
Donna, decisión humana y especialista. Verifica una entrega defectuosa, corrección,
aceptación, proyección, edición de usuario, reinicio y ausencia de duplicación.
Aplica los escenarios y registra evidencias reales; no copies resultados de tests
sintéticos como si fueran ejecución de Hermes.

## 6. Proactividad nativa

Solo con consentimiento de horario, costos y entrega, configura el cron descrito en
docs/AUTOMATION.md primero PAUSADO, con `script=donna_review_gate.py`, skills correctas,
herramientas locales, `no_agent=false`, workdir del perfil y destino explícito.
Prueba un tick real con los permisos que tendrá desatendido, un tick silencioso,
falla recuperable y recepción desde el canal cotidiano. Luego activar.

Las suscripciones `notify+wake` son complemento, no fuente de verdad. No instales
un segundo daemon. No actives otra instancia con el mismo token de mensajería.

## 7. Memoria y extras

Preserva el proveedor que ya funciona. Mnemosyne, Google, Telegram, TTS y otras
integraciones son opciones separadas; las credenciales se configuran solo mediante
flujos oficiales privados. El nuevo journal no reemplaza memoria o historial.

## 8. Entrega de instancia

Reporta configuración aplicada, pruebas verificadas, dudas, bloqueos y reversión.
No declares lista la operación por haber escrito SOUL o porque un cron esté listado.
El criterio es que Donna organice, encargue, revise, corrija y continúe el trabajo
real sin convertir al usuario en intermediario.
