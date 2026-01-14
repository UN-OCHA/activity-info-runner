from typing import Optional, Dict, Any

from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table
from rich.text import Text

class FormChangesetPlan(BaseModel):
    calc_order: int = Field(default=0, alias='calcOrder')
    form_id: str = Field(alias='formId')
    field_code: str = Field(alias='fieldCode')
    new_expression: str = Field(alias='newExpression')

class FormChangesetEntry(FormChangesetPlan):
    old_expression: str = Field(alias='oldExpression')
    field_id: str = Field(alias='fieldId')

class FormChangeset(BaseModel):
    entries: list[FormChangesetEntry] = Field(alias='entries')
    action: str = Field(alias='action')
    title: str = Field(default="", alias='title')

    def pretty_print_table(self):
        console = Console()
        console.rule(f"[bold blue]{self.action}[/bold blue]")  # Header

        table = Table(show_header=True, header_style="bold magenta", title=self.title)
        table.add_column("Order", style="green", no_wrap=True, justify="center")
        table.add_column("Form ID", style="cyan", no_wrap=True)
        table.add_column("Field ID", style="yellow")
        table.add_column("Expression", style="white")

        for entry in self.entries:
            expr = Text()
            expr.append(entry.old_expression, style="red")
            expr.append(" → \n")
            expr.append(entry.new_expression, style="green")
            table.add_row(str(entry.calc_order), entry.form_id, entry.field_id, expr)

        console.print(table)


class RecordChangesetEntry(BaseModel):
    calc_order: int = Field(default=0, alias='calcOrder')
    form_id: str = Field(alias='formId')
    record_id: str = Field(alias='recordId')
    parent_record_id: Optional[str] = Field(alias='parentRecordId')
    fields: Dict[str, Any] = Field(alias='fields')
    old_fields: Dict[str, Any] = Field(alias='oldFields')

    def pretty_print_delta(self):
        console = Console()
        console.rule(f"[bold blue]Record ID: {self.record_id}[/bold blue]")  # Header
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Field Code", style="cyan", no_wrap=True)
        table.add_column("Old Value", style="red")
        table.add_column("New Value", style="green")
        for field_code, new_value in self.fields.items():
            old_value = self.old_fields.get(field_code, "")
            if old_value != new_value:
                table.add_row(field_code, str(old_value), str(new_value))
        console.print(table)

class RecordChangeset(BaseModel):
    entries: list[RecordChangesetEntry] = Field(alias='entries')
    action: str = Field(alias='action')
    title: str = Field(default="", alias='title')

    def pretty_print_table(self):
        console = Console()
        console.rule(f"[bold blue]{self.action}[/bold blue]")
        table = Table(
            show_header=True,
            header_style="bold magenta",
            title=self.title,
            expand=True,
        )
        table.add_column("Order", style="green", justify="center", no_wrap=True)
        table.add_column("Form ID", style="cyan", no_wrap=True)
        table.add_column("Record ID", style="yellow", no_wrap=True)
        table.add_column("Changes", style="white")
        for entry in self.entries:
            changes = Text()
            for field, new_value in entry.fields.items():
                old_value = entry.old_fields.get(field)
                if old_value != new_value:
                    changes.append(f"{field}: ", style="bold")
                    changes.append(str(old_value), style="red")
                    changes.append(" → ")
                    changes.append(str(new_value), style="green")
            if not changes.plain:
                changes.append("No changes", style="dim")
            table.add_row(
                str(entry.calc_order),
                entry.form_id,
                entry.record_id,
                changes,
            )
        console.print(table)
