una propuesta comercial estilo Shark Tank. Cada equipo trabajará con un conjunto de exactamente con roles definidos, desarrollando meioras tecnológicas y presentando 10 puntos discretos.

## Obietivo General
Estructura
General
de
Cada
Estudio
de
Caso
necesidad concreta de interpolación • Contexto empresarial ficticio con una
. Conjunto de datos discretos de 10 pares (ai, yi).
. Roles:
cúbicos) define métricas de éxito y lidera la propuesta de mejora. 1. Ingeniero de Proyecto: Traduce necesidades del negocio, selecciona el método (splines 2. Ingeniero de Algoritmos: Implementa la interpolación en Python (usando scipy. interpol y crea un prototipo funcional ○ implementación propia), genera gráficos, calcula errores (RMSE, validación cruzada, 3. Coordinador de Comunicación 4 Branding: Evalúa resultados, redacta el informe técnico, diseña la identidad visual de la solución y presenta el pitch final (3-5 min) en simulación Shark Tank.
• Entregable: Informe técnico (formato IEEE o similar) que incluya introducción, metodo- logía, implementación (código comentado), resultados (tablas, gráficas, análisis de error) y conclusiones con la propuesta de mejora. Además, diapositivas para el Shark Tank.
• Mejora tecnológica obligatoria: Cada caso debe incorporar una funcionalidad más allá de la interpolación básica ( integración con sensores en tiempo real, alert as predictivas, dashboard interactivo. simulación Monte Carlo, etc.).
Trabajo escrito (50% de la nota
⁃ Contenido: resumen eiecutivo, introducción, fundamentos matemáticos de splines cúbicos (ecuaciones. condiciones de continuidad, selección de condiciones de borde), implementación (código Pvthon completo y comentado), resultados (figura comparativa puntos vs spline, pro- puesta de mejora tecnológica (con diagrama de bloques o mockup), conclusiones y referencias (mínimo 3).
Presentación Shark Tank (50% de la nota
• Duración máxima 5 minutos: 3 minutos de pitch t 2 minutos de preguntas.
◦ Contenido: problema real, solución basada en splines cúbicos, ventaja competitiva frente a interpolación lineal o polinómica, modelo de negocio o implementación, Ilamado a la acción.
⁃ Material: diapositivas atractivas, logo del proyecto, prototipo funcional mostrado en vivo o en video corto

---

## Estudio de Caso 1: Optimización de Rutas en Flota de Taxis Autónomos

AutoMove City -  OPera una flota de 200 taxis autonomos en Bogotá. Cada vehiculo reporta su ubicación y demanda de
pasajeros cada 3 horas, pero el sistema de despacho necesita estimar la deamnda **cada minuto** para reasignar vehiculos
de forma dinamica y reducir tiempos de espera de los usuarios

### Problema numérico

Se tienen mediciones de demanda (solicitudes por minuto) cada 3 horas durante un día (24 horas), totalizando 10 puntos.Se
requiere interpolar para obtener la demanda en cada minuto (1440 valores).

| Hora (decimal) | Demanda (solicitudes/min) |
| -------------- | ------------------------- |
| 0.0            | 15                        |
| 1,5            | 18                        |
| 3,0            | 12                        |
| 6,0            | 45                        |
| 9,0            | 120                       |
| 12,0           | 180                       |
| 15,0           | 150                       |
| 18,0           | 98                        |
| 19,5           | 75                        |
| 21,0           | 55                        |

_Nota:_ (El punto a las 24:0 es equivalente a 0:0 del día siguiente, no se duplica)

### Roles y tareas específicas

- **Ingeniero de Proyecto:** Entender la necesidad de la empresa. Justificar splines cúbicos frente a Lagrange lineal.
  Proponer sistema de reasignación dinámica basado en demanda interpolada cada minuto. KPI: reducir tiempo de espera 20%.

- **Ingeniero de Algoritmos:** Implementar splines con CubicSpline. Generar gráfica com- parativa (puntos originales vs
  curva suave). Calcular RMSE en validación (dejar dos puntos fuera). Simular dashboard en tiempo real con
  matplotlib.animation.

- **Coordinador+Branding:** Crear nombre y logo (ej. MovePredict). Pitch destacando ahorro de combustible y mejora en
  satisfacción. Presentar tabla de errores

### Mejora tecnológica

Integración con modelo **ARIMA** ligero que combine splines con predicción a 30 minutos usande datos históricos. Simular
alertas cuando demanda supere 150 solicitudes / min.
