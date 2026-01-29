from pydantic import BaseModel
from rich.console import Console
from rich.table import Table
from rich.text import Text

from scripts.dtos import SchemaFieldDTO
from scripts.models import Changeset


def op_type_to_style(t: str) -> str:
    if t == "CREATE":
        return "bold on green"
    elif t == "UPDATE":
        return "bold on yellow"
    return "bold on red"


def diff_models(old: BaseModel, new: BaseModel, *, prefix: str = "") -> Text:
    """
    Produce a Rich Text diff between two Pydantic models.
    """
    text = Text()
    old_data = old.model_dump(exclude_none=True)
    new_data = new.model_dump(exclude_none=True)

    all_keys = sorted(set(old_data) | set(new_data))

    for key in all_keys:
        old_val = old_data.get(key)
        new_val = new_data.get(key)

        if old_val == new_val:
            continue

        label = f"{prefix}{key}"

        text.append(f"{label}:\n", style="bold")
        text.append(f"  - {old_val}\n", style="red")
        text.append(f"  + {new_val}\n", style="green")

    return text


def diff_schema_field(old: SchemaFieldDTO, new: SchemaFieldDTO) -> Text:
    text = Text()

    # Diff top-level fields (excluding type_parameters)
    top_old = old.model_dump(exclude={"type_parameters"}, exclude_none=True)
    top_new = new.model_dump(exclude={"type_parameters"}, exclude_none=True)

    for key in sorted(set(top_old) | set(top_new)):
        if top_old.get(key) != top_new.get(key):
            text.append(f"{key}:\n", style="bold")
            text.append(f"  - {top_old.get(key)}\n", style="red")
            text.append(f"  + {top_new.get(key)}\n", style="green")

    # Diff type parameters
    if old.type_parameters or new.type_parameters:
        text.append("type_parameters:\n", style="bold underline")

        if old.type_parameters and new.type_parameters:
            text += diff_models(
                old.type_parameters,
                new.type_parameters,
                prefix="  "
            )
        else:
            text.append(f"  - {old.type_parameters}\n", style="red")
            text.append(f"  + {new.type_parameters}\n", style="green")

    return text


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
        if update.TYPE == "UPDATE":
            changes = diff_schema_field(update.old, update.new)
        elif update.TYPE == "CREATE":
            changes.append("created\n", style="green")
            changes.append(str(update.model_dump(exclude={"order", "TYPE"})), style="dim")
        elif update.TYPE == "DELETE":
            changes.append("deleted\n", style="red")
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
