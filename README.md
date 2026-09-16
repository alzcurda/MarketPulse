# MarketPulse 🛒🔍

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Country](https://img.shields.io/badge/Market-Spain%20%28ES%29-red.svg)]()
[![Documentation](https://img.shields.io/badge/Docs-ADR%20Log-purple.svg)](docs/decision_log.md)

**MarketPulse** es un asistente conversacional e interactivo de búsqueda y comparación de productos online, especialmente optimizado para el **mercado español**.

A diferencia de los buscadores internos de las tiendas (que a menudo muestran productos irrelevantes o publicidad) y de los scrapers masivos 24/7 (que sufren bloqueos y saturan servidores), MarketPulse funciona **bajo demanda**: hablas con la aplicación, defines qué especificaciones necesitas, recomienda en qué tiendas de España tiene sentido buscar (PcComponentes, Amazon.es, MediaMarkt, AliExpress Plaza) y genera una tabla comparativa homogénea con enlaces directos y envíos garantizados.

---

## 🚀 Características Principales

* 🧠 **Criteria Advisor (Asesor de Especificaciones):** Interpreta peticiones en lenguaje natural (ej. *"busco un portátil para programar con 16GB de RAM y menos de 800€"*), sugiere especificaciones clave y genera términos de búsqueda limpios para las tiendas.
* 🇪🇸 **Store Router para España:** Evalúa la categoría del producto y recomienda tiendas locales o con almacenes en España, indicando tiempos de entrega y evitando sorpresas de aduanas.
* 🧩 **Arquitectura Modular de Conectores:** Cada tienda (`pccomponentes`, `amazon_es`, `mediamarkt`, `aliexpress_es`) es un proveedor independiente. Añadir nuevas tiendas requiere únicamente heredar de `BaseStoreProvider`.
* ⚖️ **Ranking y Agregación Inteligente:** Filtra accesorios no deseados (fundas, cables), verifica límites de presupuesto, puntúa la afinidad técnica y presenta los resultados con enlaces clickables en terminal.
* 📜 **Trazabilidad y Decisiones (ADR):** Cada decisión de diseño y arquitectura queda registrada cronológicamente en la carpeta `docs/`.

---

## 📁 Estructura del Proyecto

```text
MarketPulse/
├── docs/
│   ├── decision_log.md         # Registro cronológico de decisiones de diseño (ADR)
│   └── architecture.md         # Documento de arquitectura detallado
├── marketpulse/
│   ├── __init__.py
│   ├── cli.py                  # Interfaz de consola interactiva con Rich
│   ├── config.py               # Configuración global y cabeceras
│   ├── models.py               # Modelos Pydantic (SearchCriteria, ProductResult, etc.)
│   ├── core/
│   │   ├── criteria_advisor.py # Extracción de especificaciones y limpieza de query
│   │   ├── store_router.py     # Lógica de recomendación de tiendas para España
│   │   └── aggregator.py       # Puntuación de afinidad, filtros y comparativa
│   └── stores/
│       ├── base.py             # Clase abstracta BaseStoreProvider
│       ├── pccomponentes.py    # Conector PcComponentes
│       ├── amazon_es.py        # Conector Amazon España
│       ├── mediamarkt.py       # Conector MediaMarkt España
│       └── aliexpress_es.py    # Conector AliExpress Plaza (almacén nacional)
├── tests/
│   ├── test_advisor.py         # Pruebas de extracción de criterios
│   ├── test_router.py          # Pruebas de recomendación de tiendas
│   └── test_aggregator.py      # Pruebas de filtrado y puntuación
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 🛠️ Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/TU_USUARIO/MarketPulse.git
   cd MarketPulse
   ```

2. **Crear y activar un entorno virtual:**
   ```bash
   # En Windows
   python -m venv .venv
   .venv\Scripts\activate

   # En Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 💻 Uso

Ejecuta el asistente interactivo en tu terminal:

```bash
python -m marketpulse.cli
```

### Flujo de interacción:
1. **Petición libre:** Escribe qué necesitas como si hablaras con un experto:
   > *"Quiero un portátil con 16GB de RAM para edición de vídeo y presupuesto de 900€"*
2. **Validación:** El asistente detecta la categoría, te sugiere especificaciones técnicas y confirma tu presupuesto.
3. **Tiendas:** Te muestra las tiendas recomendadas en España (ej. PcComponentes por garantía y entrega 24h, Amazon ES por catálogo, etc.) y te permite seleccionar cuáles consultar.
4. **Comparativa:** Se realizan las consultas bajo demanda y obtienes una tabla unificada con enlaces directos para comprar.

---

## 🧪 Ejecución de Pruebas

El proyecto incluye tests unitarios automatizados para garantizar la estabilidad de los módulos:

```bash
python -m unittest discover tests/
```

---

## 📖 Registro de Decisiones (`docs/`)

Para mantener el control y la trazabilidad de cada cambio, consulta:
* [docs/decision_log.md](docs/decision_log.md): Registro continuo de decisiones de arquitectura (Architecture Decision Records).
* [docs/architecture.md](docs/architecture.md): Especificación técnica de componentes y flujo de datos.

---

## 🛡️ Aviso Legal y Ético

MarketPulse está concebido para uso personal y consultas bajo demanda por parte del usuario final. Respeta las políticas de uso responsable de la información pública disponible en la web, promoviendo compras seguras en comercios autorizados dentro del marco legal español y europeo (RGPD, garantía legal de 3 años).
