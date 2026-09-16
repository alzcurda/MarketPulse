# Arquitectura del Sistema: MarketPulse

Este documento detalla los componentes, el flujo de datos y las directrices de diseño de **MarketPulse**.

---

## 1. Diagrama de Flujo

```
               [ Usuario / Comprador ]
                         │
                         ▼
        ┌──────────────────────────────────┐
        │  CLI Interactiva (Rich Console)  │
        └────────────────┬─────────────────┘
                         │
        ┌────────────────▼─────────────────┐
        │        Criteria Advisor          │
        │  (Extracción y afinado de specs) │
        └────────────────┬─────────────────┘
                         │ (SearchCriteria)
        ┌────────────────▼─────────────────┐
        │          Store Router            │
        │   (Recomendación Tiendas España) │
        └────────────────┬─────────────────┘
                         │ (Lista de tiendas seleccionadas)
        ┌────────────────▼─────────────────┐
        │      Store Providers Engine      │
        │   ┌──────────────┬─────────────┐ │
        │   │ PcComponentes│  Amazon ES  │ │
        │   ├──────────────┼─────────────┤ │
        │   │  MediaMarkt  │ AliEx Plaza │ │
        │   └──────────────┴─────────────┘ │
        └────────────────┬─────────────────┘
                         │ (List[ProductResult])
        ┌────────────────▼─────────────────┐
        │      Aggregator & Ranking        │
        │  (Normalización, scoring, orden) │
        └────────────────┬─────────────────┘
                         │
                         ▼
       [ Tabla Comparativa y Enlaces Directos ]
```

---

## 2. Descripción de Componentes

### 2.1. `marketpulse.models`
Contiene los contratos de datos unificados mediante `pydantic`:
* `SearchCriteria`: Términos de búsqueda, categoría deducida, presupuesto mín/máx, especificaciones clave (ej. "16GB RAM", "RTX 4060"), orden deseado.
* `ProductResult`: Modelo estándar que representa un artículo encontrado:
  * `title`: Nombre completo del producto.
  * `price`: Precio numérico en euros (€).
  * `original_price`: Precio sin descuento si aplica.
  * `store_name`: Nombre de la tienda.
  * `url`: Enlace directo al producto.
  * `in_stock`: Disponibilidad.
  * `ships_from_spain`: Booleano que indica si el envío es nacional / europeo.
  * `match_score`: Puntuación de afinidad con los criterios del usuario (0 - 100).
* `StoreRecommendation`: Motivo y puntuación por la cual una tienda es adecuada para la búsqueda.

### 2.2. `marketpulse.core.criteria_advisor`
Módulo conversacional que analiza la petición en lenguaje natural:
* Detecta la categoría (Informática, Audio, Fotografía, Electrodomésticos, etc.).
* Extrae requerimientos implícitos y explícitos.
* Si el usuario dice *"quiero un portátil para trabajar y programar"*, el asesor sugiere criterios como mínimo 16GB RAM, procesador de alta eficiencia y pantalla FHD/QHD, preguntando al usuario si desea fijar esos filtros.

### 2.3. `marketpulse.core.store_router`
Base de conocimiento de comercio electrónico en España:
* Mapea categorías contra tiendas especializadas:
  * **Informática / Componentes:** `PcComponentes` (prioridad 1), `Amazon.es`, `MediaMarkt`.
  * **Electrónica general / Móviles:** `MediaMarkt`, `Amazon.es`, `PcComponentes`.
  * **Ofertas / Gadgets:** `AliExpress Plaza` (garantizando entrega 3-5 días y envío local).
* Permite al usuario desmarcar o añadir tiendas antes de lanzar la búsqueda.

### 2.4. `marketpulse.stores` (Conectores Modulares)
Cada tienda implementa la interfaz `BaseStoreProvider`:
* Define métodos comunes: `search(criteria: SearchCriteria) -> List[ProductResult]`.
* Incluye estrategias de resiliencia:
  * Cabeceras HTTP estándar de navegador de escritorio.
  * Control de latencia y pausas entre llamadas.
  * Parsing selectivo de resultados.

### 2.5. `marketpulse.core.aggregator`
* Recibe los resultados brutos de todos los conectores activos.
* Normaliza precios y elimina duplicados.
* Aplica el algoritmo de scoring de afinidad según los criterios del usuario.
* Ordena por precio, puntuación o relevancia.

---

## 3. Extensibilidad

Para agregar una nueva tienda (por ejemplo, *Coolmod* o *El Corte Inglés*):
1. Crear `marketpulse/stores/coolmod.py` heredando de `BaseStoreProvider`.
2. Registrar la tienda en `marketpulse/core/store_router.py` asociándola a las categorías correspondientes.
3. El sistema la incluirá automáticamente en las recomendaciones y búsquedas sin modificar el resto de la aplicación.
