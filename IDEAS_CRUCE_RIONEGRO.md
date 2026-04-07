# Ideas para cruzar patentes y empresas establecidas en Rionegro

## Objetivo
Identificar que empresas estan **establecidas en Rionegro** aunque una patente aparezca con otra ciudad/region, y listar que patentes tendria cada empresa con un nivel de confianza.

## Problema de fondo
- La ciudad/region en el registro de patente no siempre representa el lugar de operacion principal de la empresa.
- El campo `solicitante` puede venir sucio, con variaciones legales o texto adicional.
- Una misma empresa puede aparecer con multiples nombres (ej. "S.A.", "SAS", abreviaturas, tildes, errores).

## Estrategia recomendada (por capas)

### Capa 1: Normalizacion de datos internos (MVP)
1. Crear un nombre canonico del solicitante:
   - pasar a mayusculas
   - quitar tildes
   - quitar puntuacion y dobles espacios
   - remover sufijos legales comunes (`SAS`, `S A S`, `S.A.`, `LTDA`, `S.A`, `S EN C`, etc.)
2. Separar posibles paises entre parentesis del solicitante (ej. `(CO)`) para no contaminar el nombre.
3. Generar un identificador interno por empresa (`empresa_canonica_id`) basado en ese nombre limpio.

Resultado esperado: menos duplicados y mejor agrupacion de patentes por empresa.

### Capa 2: Reglas de presencia en Rionegro
Definir etiquetas por evidencia:
- `EVIDENCIA_DIRECTA`: la patente ya reporta `ciudad = RIONEGRO`.
- `EVIDENCIA_INDIRECTA`: la empresa aparece en otras fuentes con sede/sucursal en Rionegro.
- `SIN_EVIDENCIA`: no hay prueba suficiente.

Reglas iniciales sugeridas:
1. Si alguna patente de la empresa tiene `ciudad = RIONEGRO` => marcar empresa como "presencia Rionegro probable".
2. Si ninguna patente dice Rionegro, buscar evidencia externa de sede/sucursal en Rionegro.
3. Clasificar resultado final por confianza (alta/media/baja).

### Capa 3: Cruce con fuentes externas
Para validar que la empresa existe/opera en Rionegro:
- Camara de Comercio / RUES (razon social, NIT, municipio).
- Directorios oficiales o datos abiertos locales.
- Sitio web corporativo (direccion de sede/sucursal).
- Otras bases publicas con NIT-municipio.

Nota: idealmente cruzar por `NIT`; si no existe NIT en patentes, usar nombre canonico + fuzzy matching + revision manual.

### Capa 4: Matching (exacto + fuzzy)
Orden recomendado:
1. `MATCH_EXACTO`: nombre canonico exacto.
2. `MATCH_ALIAS`: nombre coincide con alias conocidos de la misma empresa.
3. `MATCH_FUZZY`: similitud de texto mayor a umbral (ej. >= 90).

Siempre guardar trazabilidad:
- metodo de match usado
- puntaje de similitud
- fuente que respalda la presencia en Rionegro

## Puntaje de confianza sugerido
Escala 0-100 por empresa:
- +60: evidencia oficial de sede/sucursal en Rionegro (fuente externa confiable).
- +25: al menos una patente con `ciudad = RIONEGRO`.
- +10: match exacto de nombre canonico en fuente externa.
- +5: match fuzzy alto (>= 95).
- -20: ambiguedad por homonimos (varias empresas similares sin NIT).

Umbrales sugeridos:
- `>= 80`: alta confianza
- `60-79`: media confianza (revisar)
- `< 60`: baja confianza (no concluir)

## Salida final recomendada
Tabla 1: `empresas_rionegro`
- `empresa_canonica`
- `confianza`
- `nivel_confianza`
- `tipo_evidencia`
- `fuente_principal`
- `observaciones`

Tabla 2: `patentes_por_empresa`
- `empresa_canonica`
- `solicitud`
- `titulo`
- `fecha_de_concesion`
- `ciudad_patente`
- `region_patente`
- `naturaleza`

Vista final para negocio:
- Empresa
- Esta establecida en Rionegro? (si/no/probable)
- Confianza
- Numero de patentes
- Lista de patentes principales

## Riesgos y como mitigarlos
- Homonimos empresariales: exigir NIT o evidencia adicional para "alta confianza".
- Datos incompletos: mantener categoria "media/baja confianza" en vez de forzar conclusion.
- Cambios de razon social: mantener tabla de alias historicos por empresa.
- Sucursales vs casa matriz: modelar ambos conceptos por separado.

## Roadmap incremental (practico)
1. **Fase 1 (rapida):** normalizacion + agrupacion de solicitantes + conteo de patentes por empresa.
2. **Fase 2:** reglas de evidencia directa (si aparece Rionegro en ciudad de patente).
3. **Fase 3:** integracion de una fuente externa para sede/sucursal.
4. **Fase 4:** fuzzy matching y puntaje de confianza.
5. **Fase 5:** tablero final con empresas de Rionegro y sus patentes, con trazabilidad.

## Recomendacion operativa
No tomar decisiones finales solo con texto de `solicitante`. Usar el enfoque de "evidencia + confianza" y auditar manualmente primero los casos de mayor impacto (top empresas por numero de patentes).

