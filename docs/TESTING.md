# Pruebas reproducibles

## Suite offline (sin red, modelo ni credenciales)

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests
```

Fixtures sintéticos para estado, archivo y perfiles. `MemoryNative` simula la cola
en memoria y `tests/fake_hermes.py` implementa respuestas de contrato por procesos
con SQLite temporal propio. NINGUNO es Hermes ni valida su implementación real.
Prueban cómo responde nuestro código ante éxito, fallo, esquemas imprevistos,
reinicios y resultados adversos.

Cobertura opcional, con coverage previamente instalado en un entorno de desarrollo:

```bash
python3 -m coverage run --branch --source=scripts/donna_runtime -m unittest discover -s tests -v
python3 -m coverage report -m
```

Una cobertura alta no garantiza ausencia de bugs ni corrección semántica del agente.
Los resultados ejecutados en el entorno de entrega están en reports/ dentro del
paquete. La CI de GitHub es configuración preparada; solo será ejecución real
cuando el workflow corra sobre la rama y muestre sus resultados.

## Familias comprobadas

Validación de contratos/rutas/fechas; transacciones y concurrencia; mandato y
capacidad; tareas humanas; readiness; transporte/idempotencia/backoff; separación
de entrega/aceptación; rework acotado; invalidación transitiva; hashes de artefactos;
proyección/ediciones/conflictos; leases/wake/review; errores de subprocess; migración;
aplicación de overlay con preimages, colisiones y rollback.

## Límites y regresiones

Límites reales: no se han usado las cuentas, gateway, modelo o GUI del usuario en
estas pruebas. El doble de CLI no demuestra compatibilidad binaria contra cada
versión de Hermes. Captura shapes reales en staging (sin secretos) y añade fixtures
si difieren. Fail-closed no significa compatible, significa no inventar una respuesta.

No relajes un test de aceptación para hacer pasar un resultado incorrecto. Cada
incompatibilidad corregida debe incluir una regresión. Los recibos positivos de
fixtures nunca se copian a producción como evidencia de readiness o aprobación.
