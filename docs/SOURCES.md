# Fuentes, corte y trazabilidad

Corte documental: 22 de septiembre de 2026. Repositorio base contrastado mediante
árbol público GitHub: ef15483af9765c32e7f86e2091a7709bbd387bb9 (1.1.0).
La implementación es nueva; no se presenta como código oficial de Nous ni como
contenido copiado de Hermes Bible. Se consultaron contratos pertinentes, no se
afirma lectura íntegra línea por línea de ambos sitios.

| Fuente | Uso técnico |
|---|---|
| https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban | CLI pública, idempotency-key, estados, dependencias, workspace y límites. |
| https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban-multi-gateway | Dispatcher único y suscripciones/wake por gateway. |
| https://hermes-agent.nousresearch.com/docs/user-guide/features/cron | cronjob_manage, skills, workdir, pre-script, wakeAgent, sesiones nuevas y errores. |
| https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files | SOUL por perfil, AGENTS según contexto; carga explícita. |
| https://hermes-agent.nousresearch.com/docs/user-guide/features/goals | Goal no implica crear Kanban automáticamente. |
| https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban-worker-lanes | Fases y revisión nativa; no sustituir por aceptación ficticia. |
| https://hermes-agent.nousresearch.com/docs/user-guide/profiles | Identidad/aislamiento y perfiles ejecutables. |
| https://hermes-agent.nousresearch.com/docs/user-guide/profile-distributions | distribution_owned y preservación de config/credenciales/memoria. |
| https://hermes-agent.nousresearch.com/docs/user-guide/security | Aprobaciones, controles y alcance de allowlists. |
| https://www.hermesbible.com/flows/soul-md-operating-contract-template | Patrón del contrato de responsabilidad, no fuente de API. |
| https://www.hermesbible.com/flows/hermes-as-personal-ai-operating-system | Patrón conceptual; las afirmaciones de integración se contrastan con docs oficiales. |
| https://github.com/unsulabs/donna/tree/ef15483af9765c32e7f86e2091a7709bbd387bb9 | Base pública, no estado privado de la instalación. |
| https://github.com/actions/checkout | Acción oficial de checkout para CI, con credenciales no persistidas. |
| https://github.com/actions/setup-python | Acción oficial para matriz Python. |

La auditoría anterior proporcionada por el usuario se tradujo a código y pruebas.
La documentación pública gana sobre ejemplos comunitarios cuando hay discrepancias.
La ayuda/schema efectivos de la instalación se verifican antes de activarla.

El contenedor de desarrollo no pudo obtener una clonación completa de GitHub ni
instalar Hermes por red. Por ello la entrega es un overlay con preimages del árbol
público, no un clone completo, y sus tests nativos son doubles explícitos. El intento
de recuperar el módulo kanban.py mediante el scraper devolvió rate limiting; no se
infiere su contenido ni se afirma auditoría del core de Hermes.
