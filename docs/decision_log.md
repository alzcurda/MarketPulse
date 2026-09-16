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

