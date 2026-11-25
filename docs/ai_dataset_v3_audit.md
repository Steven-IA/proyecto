# Auditoría de datasets V3 — SentinelAI

## Objetivo
Corregir los problemas identificados en la auditoría estadística de V2 y diseñar una generación con mayor diversidad, menor riesgo de leakage y etiquetas más justificables.

## Problemas de V2
- Network: desbalance de clases (34.5/65.5), escenario fuertemente asociado con la etiqueta.
- Security: 351,625 duplicados por características, dominios pequeños, etiquetas derivadas de score.

## Diseño V3
- Network: distribución objetivo 50/50, escenarios como contexto, etiquetas probabilísticas con solapamiento.
- Security: distribución objetivo 33/33/34, mayor diversidad, reglas no lineales con ruido controlado.
- Metadatos: data_source, scenario, generator_version, seed, family_id.

## Prevención de leakage
- División por grupos (scenario + seed + family_id).
- Eliminación de duplicados exactos antes de dividir.
- Scaler ajustado solo en train.
- Test aislado hasta evaluación final.

## Validación
- Esquema y tipos.
- Nulos, NaN, Inf.
- Rangos.
- Duplicados exactos y por características.
- Cardinalidad y diversidad.
- Correlaciones.
- Dependencia de etiquetas respecto de escenarios.
- Posibles fugas de información.

## Compatibilidad
- Esquema compatible con modelos actuales.
- No se afirma compatibilidad estadística ni de rendimiento.

## Limitaciones
- Datos sintéticos no representan tráfico real.
- Etiquetas sintéticas no son evidencia de amenazas reales.