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
   playwright install chromium
   ```

---

## ⚙️ Configuración del Motor Semántico (Opcional - LLM / Local / Nube)

MarketPulse incluye un **Asesor Semántico Universal** capaz de entender cualquier artículo del mercado (informática, cafeteras, taladros, bicicletas, etc.) y generar preguntas inteligentes de afinado.

La aplicación funciona de forma **completamente autónoma por defecto** sin necesidad de configurar nada. Si deseas activar la inteligencia artificial para cualquier tipo de producto, puedes elegir cualquiera de estas opciones:

### 1. Activar la plantilla de configuración `.env`
Copia el archivo de plantilla `.env.example` como `.env` en la raíz del proyecto:
```bash
# En Windows (PowerShell)
Copy-Item .env.example .env

# En Linux / macOS
cp .env.example .env
```
*(El archivo `.env` está en `.gitignore` y **nunca** se subirá a repositorios públicos).*

---

### Opciones de Conexión Disponibles:

#### 🔹 Opción A: Ollama (Instancia Local - Sin API Keys, 100% privado)
Si tienes instalado [Ollama](https://ollama.com/) en tu ordenador:
1. Arranca Ollama y descarga un modelo ligero (ej. Llama 3.2):
   ```bash
   ollama run llama3.2
   ```
2. En tu `.env` (o déjalo en `LLM_BACKEND=auto` ya que se auto-detecta):
   ```env
   LLM_BACKEND=ollama
   OLLAMA_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.2
   ```

#### 🔹 Opción B: Google Gemini (Nube - Gratuito y ultrarrápido)
1. Obtén tu API Key gratuita en [Google AI Studio](https://aistudio.google.com/).
2. Configúrala en tu `.env` o como variable de entorno de tu sistema operativo:
   ```env
   LLM_BACKEND=gemini
   GEMINI_API_KEY=AIzaSyTuClaveAqui...
   GEMINI_MODEL=gemini-1.5-flash
   ```

#### 🔹 Opción C: LM Studio Local o OpenAI Compatible
1. Si usas **LM Studio** en local con el servidor de inferencia encendido en el puerto 1234:
   ```env
   LLM_BACKEND=openai
   OPENAI_BASE_URL=http://localhost:1234/v1
   OPENAI_API_KEY=lm-studio
   OPENAI_MODEL=local-model
   ```
2. Si usas la API oficial de **OpenAI**:
   ```env
   LLM_BACKEND=openai
   OPENAI_API_KEY=sk-...
   OPENAI_MODEL=gpt-4o-mini
   ```

#### 🔹 Opción D: Modo sin IA (Reglas clásicas)
Si no deseas usar ningún modelo de lenguaje, no necesitas configurar nada o puedes fijar:
```env
LLM_BACKEND=none
```
El motor heurístico local funcionará automáticamente.

---

## 🌐 Interfaz Web Interactiva (Recomendada)

MarketPulse incluye una **aplicación web moderna, visual y reactiva**:
* 🎙️ **Búsqueda por Voz:** Habla directamente usando el botón del micrófono (reconocimiento nativo sin librerías externas).
* 🎛️ **Control Deck Dinámico:** Modifica especificaciones en vivo (RAM de 16GB a 32GB, arquitectura CPU, disco SSD, presupuesto o tiendas) con un solo clic y relanza la búsqueda inmediatamente sin reiniciar.
* 📊 **Parrilla de Resultados Ordenable:** Ordena las ofertas por precio (menor a mayor / mayor a menor), afinidad (% Match) o tienda.
* 🛡️ **Auditoría de Descartes Transparente:** Inspecciona qué productos fueron descartados y por qué motivo exacto (accesorios, piezas sueltas, etc.).

### 🚀 Cómo arrancar la Web App:
* **En Windows (un solo clic):**
  Ejecuta el archivo `run_web.bat`.
* **Desde la terminal:**
  ```bash
  python -m marketpulse.web
  ```
  Se abrirá automáticamente en tu navegador en `http://localhost:8000` (o accesible desde tu móvil u otros dispositivos en `http://TU_IP_LOCAL:8000`).

### 🐳 Despliegue en NAS / Docker:
MarketPulse está listo para ejecutarse en cualquier NAS (Synology Container Manager, QNAP Container Station, Unraid, Portainer):
```bash
docker-compose up -d
```

---

## 💻 Uso desde Terminal (CLI)

Si prefieres la interfaz tradicional por consola:

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
