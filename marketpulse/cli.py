import sys
from typing import Dict, List, Type
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from marketpulse.core.criteria_advisor import CriteriaAdvisor
from marketpulse.core.store_router import StoreRouter
from marketpulse.core.aggregator import Aggregator
from marketpulse.stores.base import BaseStoreProvider
from marketpulse.stores.pccomponentes import PcComponentesProvider
from marketpulse.stores.amazon_es import AmazonEsProvider
from marketpulse.stores.mediamarkt import MediaMarktProvider
from marketpulse.stores.aliexpress_es import AliExpressEsProvider
from marketpulse.models import ProductResult, SearchCriteria


console = Console()

STORE_PROVIDER_MAP: Dict[str, Type[BaseStoreProvider]] = {
    "pccomponentes": PcComponentesProvider,
    "amazon_es": AmazonEsProvider,
    "mediamarkt": MediaMarktProvider,
    "aliexpress_es": AliExpressEsProvider,
}


def print_banner():
    banner_text = (
        "[bold cyan]MarketPulse[/bold cyan] [white]• Asistente Inteligente de Compras y Búsqueda Multitienda[/white]\n"
        "[dim]Especializado en el mercado español • Búsqueda limpia bajo demanda • Sin aduanas sorpresa[/dim]"
    )
    console.print(Panel(banner_text, border_style="cyan", expand=False))


def run_interactive_session():
    print_banner()

    advisor = CriteriaAdvisor()
    router = StoreRouter()
    aggregator = Aggregator()

    # 1. Consulta inicial del usuario
    console.print("\n[bold yellow]1. ¿Qué producto estás buscando?[/bold yellow]")
    user_prompt = Prompt.ask(
        "[green]Descríbelo en tus propias palabras (ej: 'Busco un portátil para programar con 16GB RAM y presupuesto de 800€')[/green]"
    )

    if not user_prompt.strip():
        console.print("[red]No has introducido ningún texto. Saliendo...[/red]")
        return

    # 2. Análisis inteligente de criterios
    with console.status("[cyan]Analizando especificaciones y categoría...[/cyan]"):
        criteria: SearchCriteria = advisor.analyze_user_prompt(user_prompt)

    console.print(f"\n[bold green]✓ Categoría detectada:[/bold green] [cyan]{criteria.category.value.upper()}[/cyan]")
    console.print(f"[bold green]✓ Término optimizado de búsqueda:[/bold green] [bold white]'{criteria.clean_query}'[/bold white]")

    # Criterios y recomendaciones técnicas
    suggested = advisor.get_suggested_specs(criteria.category)
    if suggested:
        console.print("\n[bold magenta]💡 Recomendaciones clave para esta categoría:[/bold magenta]")
        for item in suggested:
            console.print(f"  • {item}")

    # Ajuste o confirmación de presupuesto
    if criteria.max_price:
        console.print(f"\n[bold green]✓ Presupuesto máximo detectado:[/bold green] [yellow]{criteria.max_price:,.2f} €[/yellow]")
    else:
        ask_budget = Confirm.ask("\n¿Deseas fijar un presupuesto máximo?", default=False)
        if ask_budget:
            budget_input = Prompt.ask("Indica el importe máximo en euros (ej: 750)")
            try:
                criteria.max_price = float(budget_input.replace("€", "").strip())
            except ValueError:
                console.print("[yellow]Valor no válido, se continuará sin límite de presupuesto.[/yellow]")

    # 3. Recomendación de tiendas en España
    console.print("\n[bold yellow]2. Tiendas recomendadas para comprar desde España:[/bold yellow]")
    recommendations = router.recommend_stores(criteria.category)

    rec_table = Table(show_header=True, header_style="bold cyan")
    rec_table.add_column("#", style="dim", width=4)
    rec_table.add_column("Tienda", style="bold white", width=22)
    rec_table.add_column("Motivo / Especialidad", width=38)
    rec_table.add_column("Envío estimado", style="green", width=20)
    rec_table.add_column("Activa", justify="center", width=8)

    selected_store_ids = []
    for idx, rec in enumerate(recommendations, 1):
        status_mark = "[bold green]SÍ[/bold green]" if rec.enabled_by_default else "[dim]NO[/dim]"
        if rec.enabled_by_default:
            selected_store_ids.append(rec.store_id)
        rec_table.add_row(
            str(idx),
            rec.store_name,
            rec.reason,
            rec.estimated_delivery_days,
            status_mark
        )

    console.print(rec_table)

    confirm_stores = Confirm.ask("¿Quieres buscar en estas tiendas seleccionadas?", default=True)
    if not confirm_stores:
        console.print("[cyan]Introduce los números de las tiendas a consultar separados por comas (ej: 1,2):[/cyan]")
        choices = Prompt.ask("Opciones", default="1,2")
        selected_store_ids = []
        for c in choices.split(","):
            c = c.strip()
            if c.isdigit() and 1 <= int(c) <= len(recommendations):
                selected_store_ids.append(recommendations[int(c) - 1].store_id)

    if not selected_store_ids:
        console.print("[yellow]No se seleccionó ninguna tienda. Usando tiendas por defecto.[/yellow]")
        selected_store_ids = ["pccomponentes", "amazon_es"]

    # 4. Ejecución de búsquedas
    console.print(f"\n[bold yellow]3. Consultando {len(selected_store_ids)} tiendas bajo demanda...[/bold yellow]")
    raw_results: List[ProductResult] = []

    for store_id in selected_store_ids:
        provider_cls = STORE_PROVIDER_MAP.get(store_id)
        if not provider_cls:
            continue
        provider = provider_cls()
        with console.status(f"[cyan]Buscando en {provider.store_name}...[/cyan]"):
            try:
                res = provider.search(criteria)
                raw_results.extend(res)
                console.print(f"  [green]✓[/green] {provider.store_name}: [white]{len(res)} resultados encontrados[/white]")
            except Exception as e:
                console.print(f"  [red]✗[/red] {provider.store_name}: Error en consulta ({e})")
            finally:
                provider.close()

    # 5. Agregación, puntuación y filtrado
    ranked_results = aggregator.filter_and_rank(raw_results, criteria)

    # 6. Presentación de resultados
    console.print("\n[bold yellow]4. Resultados y Comparativa de Mercado:[/bold yellow]")
    if not ranked_results:
        console.print("[red]No se encontraron productos que coincidan con los criterios establecidos.[/red]")
        return

    res_table = Table(show_header=True, header_style="bold magenta", expand=True)
    res_table.add_column("Tienda", style="bold cyan", width=18)
    res_table.add_column("Producto", style="white", min_width=30)
    res_table.add_column("Precio", justify="right", style="bold yellow", width=12)
    res_table.add_column("Afinidad", justify="center", style="green", width=10)
    res_table.add_column("Enlace Directo", style="underline blue")

    for prod in ranked_results:
        price_str = f"{prod.price:,.2f} €" if prod.price > 0 else "Ver en tienda"
        score_str = f"{int(prod.match_score)}%" if prod.match_score > 0 else "-"
        res_table.add_row(
            prod.store_name,
            prod.title[:65] + ("..." if len(prod.title) > 65 else ""),
            price_str,
            score_str,
            prod.url
        )

    console.print(res_table)
    console.print(f"\n[dim]Se han comparado {len(ranked_results)} ofertas con envío garantizado a España.[/dim]\n")


def main():
    try:
        run_interactive_session()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operación cancelada por el usuario.[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()
