# Registro de Decisiones de Arquitectura y Diseño (ADR Log)

Este documento registra todas las decisiones estratégicas, arquitectónicas y técnicas adoptadas en el ciclo de vida de **MarketPulse**, asegurando trazabilidad y contexto para el equipo de desarrollo.

---

## Índice de Decisiones

1. [ADR-0001: Creación del proyecto, propósito y nombre (MarketPulse)](#adr-0001-creación-del-proyecto-propósito-y-nombre-marketpulse)
2. [ADR-0002: Elección del lenguaje base (Python)](#adr-0002-elección-del-lenguaje-base-python)
3. [ADR-0003: Enfoque de búsqueda bajo demanda vs. Scraping masivo continuo](#adr-0003-enfoque-de-búsqueda-bajo-demanda-vs-scraping-masivo-continuo)
4. [ADR-0004: Arquitectura desacoplada y modular (Advisor, Router, Providers, Aggregator)](#adr-0004-arquitectura-desacoplada-y-modular-advisor-router-providers-aggregator)
5. [ADR-0005: Especialización en el mercado español y envíos locales](#adr-0005-especialización-en-el-mercado-español-y-envíos-locales)
6. [ADR-0006: Registro estructurado de decisiones en repositorio (`docs/`)](#adr-0006-registro-estructurado-de-decisiones-en-repositorio-docs)
7. [ADR-0007: Extracción directa de artículos individuales y eliminación de enlaces sustitutivos de búsqueda](#adr-0007-extracción-directa-de-artículos-individuales-y-eliminación-de-enlaces-sustitutivos-de-búsqueda)
8. [ADR-0008: Filtrado estricto de especificaciones técnicas, exclusiones negativas y límites condicionales](#adr-0008-filtrado-estricto-de-especificaciones-técnicas-exclusiones-negativas-y-límites-condicionales)

---

### ADR-0001: Creación del proyecto, propósito y nombre (MarketPulse)
* **Fecha:** 2026-09-16
* **Estado:** Aprobado
* **Contexto:** 
  Los buscadores internos de las tiendas online a menudo arrojan resultados irrelevantes, patrocinados o desordenados cuando el usuario busca productos con requerimientos técnicos concretos. Se necesita una herramienta personalizada que busque y compare productos en múltiples plataformas de forma unificada.
* **Decisión:**
  Nombrar al proyecto **`MarketPulse`** y diseñarlo como un repositorio de código abierto en GitHub, con una identidad profesional y modular.
* **Consecuencias:**
  Proporciona una identidad de marca clara y un repositorio preparado para versionado colaborativo en GitHub.

---

### ADR-0002: Elección del lenguaje base (Python)
* **Fecha:** 2026-09-16
* **Estado:** Aprobado
* **Contexto:**
  Se evaluaron opciones entre Python y TypeScript/Node.js.
* **Decisión:**
  Implementar el núcleo en **Python (>= 3.10)**.
* **Justificación:**
  Python cuenta con el ecosistema más maduro y conciso para procesamiento de texto, extracción de datos (`httpx`, `BeautifulSoup`, `Playwright`), tipado con `Pydantic` y herramientas de CLI enriquecidas (`Rich`).
* **Consecuencias:**
  Desarrollo rápido, sintaxis clara para modelar lógica de negocio y facilidad para añadir componentes de machine learning o LLM en el futuro.

---

### ADR-0003: Enfoque de búsqueda bajo demanda vs. Scraping masivo continuo
* **Fecha:** 2026-09-16
* **Estado:** Aprobado
* **Contexto:**
  Muchos proyectos de scraping intentan escanear catálogos enteros 24/7, lo cual dispara sistemas de defensa WAF (Cloudflare, Akamai, etc.), satura servidores de comercio electrónico y requiere costosas granjas de proxies residenciales.
* **Decisión:**
  MarketPulse operará **exclusivamente bajo demanda (on-demand)**, activado por el usuario cuando necesita realizar una compra o comparación específica. Las peticiones serán dirigidas, con delays humanos, cabeceras realistas y limitación de tasa (*rate-limiting* ético).
* **Consecuencias:**
  Minimiza radicalmente el riesgo de bloqueos IP, reduce costes de infraestructura a cero y garantiza una interacción legal y respetuosa con los sitios web.

---

### ADR-0004: Arquitectura desacoplada y modular (Advisor, Router, Providers, Aggregator)
* **Fecha:** 2026-09-16
* **Estado:** Aprobado
* **Contexto:**
  Un script monolítico de scraping es difícil de mantener, ya que cada tienda tiene APIs o estructuras HTML que evolucionan de forma independiente.
* **Decisión:**
  Dividir el sistema en 4 capas desacopladas:
  1. **Criteria Advisor:** Asistente conversacional para extraer especificaciones técnicas y límites de presupuesto.
  2. **Store Router:** Módulo de recomendación que sabe qué tiendas son idóneas para cada categoría de producto en España.
  3. **Store Providers (`stores/`):** Conectores independientes heredando de `BaseStoreProvider`. Si una tienda cambia su diseño, solo se modifica su archivo.
  4. **Aggregator & Ranking:** Normalizador que elimina duplicados y clasifica por relación calidad/precio o afinidad de criterios.
* **Consecuencias:**
  Alta extensibilidad. Añadir una nueva tienda (por ejemplo El Corte Inglés o Coolmod) es tan sencillo como crear un nuevo archivo en `marketpulse/stores/`.

---

### ADR-0005: Especialización en el mercado español y envíos locales
* **Fecha:** 2026-09-16
* **Estado:** Aprobado
* **Contexto:**
  Comprar desde España presenta particularidades: costes de aduanas e IVA en importaciones fuera de la UE, tiempos de transporte y garantías legales europeas (3 años de garantía en España).
* **Decisión:**
  Priorizar tiendas locales o con almacenes en España (PcComponentes, Amazon.es, MediaMarkt, AliExpress Plaza/Envío desde España). El enrutador y los modelos de datos filtrarán o etiquetarán productos garantizando la viabilidad de entrega sin sorpresas arancelarias.
* **Consecuencias:**
  Experiencia de usuario fiable y adaptada a la realidad del comprador en España.

---

### ADR-0006: Registro estructurado de decisiones en repositorio (`docs/`)
* **Fecha:** 2026-09-16
* **Estado:** Aprobado
* **Contexto:**
  El usuario solicitó explícitamente mantener una traza documentada de todas las decisiones adoptadas en el proyecto.
* **Decisión:**
  Mantener una carpeta `docs/` con `decision_log.md` (registro cronológico de decisiones) y `architecture.md` (diagrama y descripción detallada del sistema). Cada cambio relevante en requerimientos o diseño deberá registrarse aquí.
* **Consecuencias:**
  Total auditabilidad y facilidad para que nuevos colaboradores o el propio usuario retomen el proyecto en cualquier momento.

---

### ADR-0007: Extracción directa de artículos individuales y eliminación de enlaces sustitutivos de búsqueda
* **Fecha:** 2026-09-16
* **Estado:** Aprobado
* **Contexto:**
  Las peticiones HTTP estáticas a plataformas como Amazon.es y AliExpress Plaza se encontraban con retos WAF/antibot (Akamai, Cloudflare), lo que provocaba que los proveedores retornaran la URL del listado de búsqueda (`/s?k=...` o `/w/wholesale-...`) simulando ser un artículo ficticio. El usuario requiere exclusivamente URLs directas a los artículos concretos que cumplen los criterios de compra.
* **Decisión:**
  1. Integrar un gestor de navegador headless con Playwright (`BrowserSession`) que ejecute JavaScript, renderice el DOM completo y resuelva las defensas cliente.
  2. Implementar extracción directa de tarjetas de producto: en Amazon.es mediante ASIN (`/dp/{asin}`), en AliExpress Plaza mediante identificador de artículo (`/item/{id}.html`), y en PcComponentes y MediaMarkt con extracción de rutas directas.
  3. Eliminar por completo los registros de sustitución (*fallback placeholders*) que devolvían URLs de búsqueda como productos.
  4. Introducir en `Aggregator` una regla de descarte explícita que bloquea cualquier URL de listado de búsqueda que pudiera filtrarse.
* **Consecuencias:**
  Los resultados de la tabla comparativa contienen únicamente productos reales con precios actualizados, enlaces directos de compra y puntuación de afinidad.

---

### ADR-0008: Filtrado estricto de especificaciones técnicas, exclusiones negativas y límites condicionales
* **Fecha:** 2026-09-16
* **Estado:** Aprobado
* **Contexto:**
  En consultas complejas con restricciones estrictas (procesadores específicos como N100/N150/i3 de 12.ª gen en adelante, mínimos de 16 GB de RAM y 512 GB de SSD, exclusión explícita de AMD/Ryzen/Celeron/Pentium/antiguos y topes de precio condicionales), el motor de búsqueda anterior contaminaba la query enviando términos de exclusión a las tiendas y carecía de validación dura post-búsqueda, permitiendo que aparecieran equipos no conformes (ej. Celeron N2940 con 8 GB de RAM).
* **Decisión:**
  1. Refactorizar `CriteriaAdvisor` para segregar cláusulas de exclusión (`descartando ...`, `sin ...`, `evitando ...`), impidiendo que términos negativos entren en la consulta enviada a las tiendas o en los specs positivos.
  2. Extraer en el modelo `SearchCriteria`: procesadores permitidos (`allowed_cpus`), capacidades mínimas de hardware (`min_ram_gb`, `min_storage_gb`), topes de precio segmentados por CPU (`max_price_by_cpu`) y consultas dirigidas (`target_search_queries`).
  3. Dotar a `Aggregator` de validaciones matemáticas y regex deterministas:
     - Descarte absoluto ante cualquier término de exclusión en el título (`amd`, `ryzen`, `celeron`, `pentium`, `j4125`, `8gb`, etc.).
     - Descarte de procesadores Intel Core de generaciones 11 o inferiores (`i3-3217U`, `i5-8400T`, etc.).
     - Validación estricta de procesadores permitidos.
     - Detección y verificación de RAM y almacenamiento mínimo frente a barebones o variantes sub-especificadas (8 GB, 256 GB, etc.).
     - Cumplimiento de límites de precio condicionales por CPU.
* **Consecuencias:**
  Garantía absoluta de que ningún equipo que incumpla cualquiera de los requisitos (procesador, generación, memoria, disco o precio) pase el filtro hacia la comparativa final.

---

### ADR-0009: Presentación de enlaces directos no truncados y soporte de codificación UTF-8 en CLI
* **Fecha:** 2026-09-16
* **Estado:** Aprobado
* **Contexto:**
  Las URLs directas de productos de comercio electrónico suelen superar los 100 caracteres sin espacios intermedios. En la salida formateada por `Rich.Table`, las celdas de tabla recortaban las URLs con elipsis (`…`) para ajustarse al ancho de la terminal, impidiendo copiar la dirección completa. Asimismo, en terminales Windows configuradas por defecto en `cp1252`, caracteres especiales provocaban excepciones silenciosas que cortaban la renderización antes de finalizar.
* **Decisión:**
  1. Configurar `sys.stdout.reconfigure(encoding='utf-8')` y `sys.stderr.reconfigure(encoding='utf-8')` al inicio de la CLI en plataformas Windows.
  2. Implementar enlaces hipertexto estándar OSC 8 (`[link={url}]Abrir enlace ↗[/link]`) dentro de la tabla comparativa de `Rich`, permitiendo al usuario abrir el producto directamente con Ctrl+Click desde terminales modernas.
  3. Añadir inmediatamente tras la tabla un panel dedicado (`Panel`) con la lista completa y numerada de URLs directas en texto continuo, garantizando que el usuario pueda copiar y pegar cualquier enlace completo sin cortes ni elipsis.
* **Consecuencias:**
  Salida de consola robusta, sin cortes de ejecución en Windows, y accesibilidad total a los enlaces directos tanto mediante clic interactivo como mediante selección y copia en el portapapeles.

---

### ADR-0010: Exclusión de precios no verificados bajo presupuesto explícito y segmentación dirigida por CPU
* **Fecha:** 2026-09-16
* **Estado:** Aprobado
* **Contexto:**
  Cuando las tiendas aplican desafíos antibot y se recurre a índices de búsqueda secundarios, ciertas fichas de producto se recuperaban sin precio (`price = 0.0` / "Ver en tienda"). En `Aggregator`, la regla de comprobación `prod.price > max_price` resultaba `False` ante `0.0`, lo que permitía que equipos de 500€ o 600€ se colaran en los resultados finales eludiendo los topes de presupuesto de 230€ y 330€. Asimismo, las consultas segmentadas truncaban la lista de CPUs (`[:3]`), omitiendo búsquedas de N100 y N150 en Amazon y AliExpress.
* **Decisión:**
  1. En `Aggregator`: descartar automáticamente cualquier artículo con precio desconocido o nulo (`price <= 0.0`) cuando el usuario haya fijado un presupuesto máximo (general o condicional por CPU). De este modo, únicamente se presentarán productos con precio comprobado dentro del rango solicitado.
  2. En `CriteriaAdvisor`: ordenar los modelos de CPU permitidos según su orden de aparición en el texto del usuario y expandir el límite de consultas dirigidas a 6 variantes sin omitir chips de menor presupuesto.
  3. En `AmazonEsProvider` y `AliExpressEsProvider`: procesar hasta 6 consultas segmentadas aplicando dinámicamente el precio máximo condicional asociado al modelo concreto de procesador en cada consulta (ej. 230€ para N100/N150 y 330€ para i3).
* **Consecuencias:**
  Garantía matemática de que ningún artículo por encima del presupuesto (o sin precio comprobable) se muestre al usuario cuando se exige un límite presupuestario. Las búsquedas en comercios electrónicos ahora cubren la totalidad de los procesadores solicitados respetando sus respectivos techos de coste.

---

### ADR-0011: Normalización universal de precios numéricos y gestión de casos límite en comercio electrónico
* **Fecha:** 2026-09-17
* **Estado:** Aprobado
* **Contexto:**
  El scraping de precios en e-commerce afronta inconsistencias complejas: DOM fragmentado (ej. `.a-price-whole` + `.a-price-fraction` en Amazon), convenciones de formato geográfico (`1.139,00 €` vs `$1,139.00`), captura errónea de PVPs originales tachados (`<del>`, `.a-text-price`), cuotas de pago aplazado o financiación (`14,13 € / mes`), productos promocionados no orgánicos (anuncios patrocinados) y listados inactivos sin stock.
* **Decisión:**
  1. Crear un módulo centralizado `marketpulse.core.pricing` con la función universal `parse_price(raw_text)`:
     - Detección precisa de separadores decimales y de miles: cuando coexisten punto y coma, el último actúa de separador decimal; con separador único, analiza la longitud del último bloque (2 dígitos = decimal, 3 dígitos = millares).
     - Soporte para rangos de precio (`parse_price_range`).
  2. Implementar detectores de casos límite:
     - `is_financing_or_unit_price`: filtra y descarta textos que representan cuotas mensuales o precio por unidad (`/mes`, `/cuota`, `/kg`, `Cofidis`, `Klarna`, `Openbank Pay`).
     - `is_strikethrough_or_old_price`: excluye elementos con `<del>`, `.a-text-price`, `.strike`, etc. para capturar únicamente el precio de venta activo con descuento aplicado.
     - `is_sponsored_card`: identifica y descarta anuncios o tarjetas patrocinadas (`.s-sponsored-label`, `ad-container`, etc.).
     - `is_out_of_stock`: detecta menciones de no disponibilidad (`Actualmente no disponible`, `Agotado`, etc.).
  3. Refactorizar los 4 conectores de tienda (`AmazonEsProvider`, `AliExpressEsProvider`, `PcComponentesProvider`, `MediaMarktProvider`) para aplicar de forma sistemática este módulo de parseo y filtrado.
* **Consecuencias:**
  Extracción robusta de precios que previene lecturas truncadas, elimina falsos positivos de cuotas de financiación, ignora precios tachados desactualizados y garantiza que los precios comparados correspondan exactamente al importe real de compra del producto.





