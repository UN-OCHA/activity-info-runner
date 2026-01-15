from typing import Optional, Dict, Any

from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table
from rich.text import Text


class FormChangesetPlan(BaseModel):
    """A planned change to a form field's calculation expression."""
    calc_order: int = Field(default=0, alias='calcOrder')
    form_id: str = Field(alias='formId')
    field_code: str = Field(alias='fieldCode')
    new_expression: str = Field(alias='newExpression')


class FormChangesetEntry(FormChangesetPlan):
    """An executed change to a form field's calculation expression, including the old expression and the form name."""
    old_expression: str = Field(alias='oldExpression')
    form_name: str = Field(default=None, alias='formName')
    field_id: str = Field(alias='fieldId')


class FormChangeset(BaseModel):
    """A set of changes made to form fields' calculation expressions."""
    entries: list[FormChangesetEntry] = Field(alias='entries')
    action: str = Field(alias='action')
    title: str = Field(default="", alias='title')

    def pretty_print_table(self):
        console = Console()
        console.rule(f"[bold blue]{self.action}[/bold blue]")  # Header
        table = Table(show_header=True, header_style="bold magenta", title=self.title)
        table.add_column("Order", style="white", no_wrap=True, justify="center")
        table.add_column("Form", style="cyan", no_wrap=True)
        table.add_column("Field", style="yellow")
        table.add_column("Expression", style="white")
        for entry in self.entries:
            expr = Text()
            expr.append(entry.old_expression, style="red")
            expr.append(" → \n")
            expr.append(entry.new_expression, style="green")
            field = Text()
            field.append(entry.field_code)
            field.append(f"\n({entry.field_id})", style="dim")
            form = Text()
            form.append(entry.form_name)
            form.append(f"\n({entry.form_id})", style="dim")
            table.add_row(str(entry.calc_order), form, field, expr)
        console.print(table)


class RecordChangesetEntry(BaseModel):
    """A change made to a record's fields."""
    calc_order: int = Field(default=0, alias='calcOrder')
    form_id: str = Field(alias='formId')
    form_name: str = Field(default=None, alias='formName')
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
    """A set of changes made to records' fields."""
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
        table.add_column("Form", style="cyan", no_wrap=True)
        table.add_column("Record", style="yellow", no_wrap=True)
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
            form = Text()
            form.append(entry.form_name)
            form.append(f" ({entry.form_id})", style="dim")
            table.add_row(
                str(entry.calc_order),
                form,
                entry.record_id,
                changes,
            )
        console.print(table)
