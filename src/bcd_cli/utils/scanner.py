"""
Scanner input utilities

Handles barcode scanner input (keyboard wedge mode).
"""

from typing import List

from .display import console


def read_barcode_input(prompt: str) -> str:
    """
    Read input from barcode scanner or keyboard.

    Barcode scanners act as keyboard devices and send the barcode
    followed by Enter. This function handles both scanner and manual input.

    Args:
        prompt: Input prompt to display

    Returns:
        Input string (barcode or manual entry)
    """
    try:
        user_input = console.input(f"{prompt}: ").strip()
        return user_input
    except EOFError:
        return ""
    except KeyboardInterrupt:
        raise


def read_multiple_barcodes(
    prompt: str, finish_prompt: str = "Scan item barcode (Enter to finish)"
) -> List[str]:
    """
    Read multiple barcode inputs until Enter is pressed.

    Args:
        prompt: Initial prompt
        finish_prompt: Prompt for subsequent inputs

    Returns:
        List of scanned barcodes
    """
    barcodes = []

    console.print()
    console.print(f"[bold cyan]{prompt}[/bold cyan]")
    console.print("[dim](Scannez les codes-barres, Entrée pour terminer)[/dim]")
    console.print("[dim](Scan barcodes, Enter to finish)[/dim]")
    console.print()

    while True:
        try:
            barcode = console.input(f"{finish_prompt}: ").strip()

            if not barcode:
                # Empty input = done
                break

            barcodes.append(barcode)
            console.print(f"  [green]✓[/green] Ajouté / Added: {barcode}")

        except EOFError:
            break
        except KeyboardInterrupt:
            raise

    return barcodes


def read_selection_from_list(
    max_items: int, prompt: str = "Sélectionner / Select"
) -> List[int]:
    """
    Read item selections from numbered list.

    Args:
        max_items: Maximum number of items
        prompt: Selection prompt

    Returns:
        List of selected indices (1-based)
    """
    console.print()
    user_input = console.input(f"{prompt} (ex: 1,2,3): ").strip()

    if not user_input:
        return []

    # Parse comma-separated numbers
    selected = []
    for part in user_input.split(","):
        part = part.strip()
        if "-" in part:
            # Range: 1-3
            try:
                start, end = part.split("-")
                start_idx = int(start.strip())
                end_idx = int(end.strip())
                selected.extend(range(start_idx, end_idx + 1))
            except ValueError:
                console.print(
                    f"[yellow]⚠ Format invalide / Invalid format: {part}[/yellow]"
                )
        else:
            # Single number
            try:
                num = int(part)
                if 1 <= num <= max_items:
                    selected.append(num)
                else:
                    console.print(
                        f"[yellow]⚠ Hors limites / Out of range: {num}[/yellow]"
                    )
            except ValueError:
                console.print(
                    f"[yellow]⚠ Format invalide / Invalid format: {part}[/yellow]"
                )

    return list(set(selected))  # Remove duplicates
