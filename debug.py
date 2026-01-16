from rich.console import Console
from rich.table import Table
from rich.text import Text

from actions.models import Changeset


def op_type_to_style(t: str) -> str:
    if t == "CREATE":
        return "bold on green"
    elif t == "UPDATE":
        return "bold on yellow"
    return "bold on red"


def pretty_print_changeset(changeset: Changeset):
    console = Console()
    console.rule(f"[bold red]FIELD ACTIONS[/bold red]", style="red")
    table = Table(show_header=True, header_style="bold red", style="red")
    table.add_column("Operation", style="white", no_wrap=True)
    table.add_column("Form", style="purple", no_wrap=True)
    table.add_column("Field code", style="yellow", no_wrap=True)
    table.add_column("Formula update", style="white bold")
    table.add_column("Origin", style="dim")
    for update in changeset.field_actions:
        operation = Text()
        operation.append(f"{update.order} ")
        operation.append(update.TYPE, style=op_type_to_style(update.TYPE))
        form = Text()
        form.append(update.form_name)
        form.append(f"\n({update.form_id})", style="dim")
        changes = Text()
        changes.append(str(update.old_formula), style="red")
        changes.append(" →\n")
        changes.append(str(update.formula) if update.TYPE != "DELETE" else "<deleted>", style="green")
        table.add_row(operation, form, update.field_code, changes, update.origin)
    console.print(table)
    console.rule(f"[bold blue]RECORD ACTIONS[/bold blue]", style="blue")
    table = Table(show_header=True, header_style="bold blue", style="blue")
    table.add_column("Operation", style="white", no_wrap=True)
    table.add_column("Form", style="purple", no_wrap=True)
    table.add_column("Record ID", style="dark_orange", no_wrap=True)
    table.add_column("Field code", style="yellow", no_wrap=True)
    table.add_column("Value update", style="white bold")
    table.add_column("Origin", style="dim")
    for update in changeset.record_actions:
        operation = Text()
        operation.append(f"{update.order} ")
        operation.append(update.TYPE, style=op_type_to_style(update.TYPE))
        form = Text()
        form.append(update.form_name)
        form.append(f"\n({update.form_id})", style="dim")
        changes = Text()
        changes.append(str(update.old_field_value), style="red")
        changes.append(" →\n")
        changes.append(str(update.field_value), style="green")
        table.add_row(operation, form, update.record_id, update.field_code,
                      changes, update.origin)
    console.print(table)
