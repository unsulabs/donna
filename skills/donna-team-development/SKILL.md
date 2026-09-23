---
name: donna-team-development
description: Detect missing capabilities, specify and coordinate specialist onboarding, verify readiness and expand the team without inventing access.
version: 2.0.0-rc.1
author: Unsu Labs
license: MIT
metadata:
  hermes:
    tags: [donna, orchestration, personal-assistant]
---

# Desarrollo del equipo

Una carencia de capacidad es trabajo a organizar, no un final de conversación.
Mantén responsabilidad por resolverla sin inventar perfiles, permisos o resultados.

## Detectar y registrar

Consulta el roster, perfiles reales, skills e integraciones autorizadas. Determina
si falta una habilidad, un acceso, configuración o un puesto nuevo. No crees otro
agente solo porque no leíste las capacidades del equipo existente.

```bash
python3 "$HERMES_HOME/scripts/donna_ops.py" gap proyecto-id redes-sociales --reason 'Falta acceso y capacidad verificada para la tarea acordada'
```

## Encargo de incorporación

Prepara un documento con función, resultados, límites, tipos de entrada/salida,
capabilities IDs, skills concretas, accesos necesarios, permisos, datos mínimos,
prueba de aceptación, responsable de configuración y criterio para suspender uso.
Puede configurarlo el agente desarrollador existente. El acceso a una cuenta nueva
y sus decisiones de permisos son humanos; los pasos técnicos autorizados los
coordina Donna con el desarrollador. Continúa las ramas independientes del proyecto.

## Configurar sin fingir disponibilidad

Hermes permite perfiles nuevos mediante `hermes profile create`; inspecciona la
ayuda y topología instaladas. No clones credenciales/canales del usuario por
conveniencia, no reinstales Hermes y no actives dos gateways para el mismo bot.
Inicializa identidad, modelo elegido por el usuario, skills, herramientas y espacios
aprobados del especialista. No publiques un perfil privado en el repositorio.

## Pruebas reales de readiness

Mantén `proposed` o `configured` hasta obtener:
1. Modelo operando desde ESE perfil.
2. Herramientas/accesos necesarios usados con una prueba mínima reversible.
3. Encargo representativo completo que regresa artefacto y evidencia útil.

No basta con que exista una carpeta o que el agente diga que tiene acceso. Registra
fecha con zona y fuente inspeccionable de cada comprobación. Para redes sociales,
separa lectura, borrador y publicación. Publicar no es requisito para probar
redacción y requiere una autorización específica.

Actualiza el JSON `.team` con los perfiles/capacidades exactos, importa la versión y
resuelve el gap únicamente con un miembro verificado compatible:

```bash
python3 "$HERMES_HOME/scripts/donna_ops.py" team-import "$HERMES_HOME/.team"
python3 "$HERMES_HOME/scripts/donna_ops.py" gap-resolve gap-id miembro-id
```

La vigencia de readiness es configurable (30 días por defecto); un cambio de skills,
modelo o permisos exige revisar las evidencias. Deshabilitar/omitir un miembro
bloquea nuevos despachos, no mata trabajos nativos en vuelo. Revisa esos trabajos.

## Resultado

Nueva capacidad probada, roster actualizado, primer encargo real y seguimiento de
Donna. No dejes al usuario administrando el nuevo agente ni prometas publicación
cuando solo configuraste generación de textos.
