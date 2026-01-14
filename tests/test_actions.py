import pytest
from actions import (
    build_nested_dict,
    resolve_form_id_from_prefix,
    DatabaseTreeResourceType,
    get_operation_calculation_changesets,
    OperationCalculationApplyType
)
from api.models import OperationCalculationFormulasField, FormSchema, FormElement, TypeParameters
from unittest.mock import AsyncMock, MagicMock

def test_build_nested_dict():
    flat = {
        "foo.bar": 1,
        "foo.baz": 2,
        "qux": 3,
        "a.b.c": 4
    }
    expected = {
        "foo": {"bar": 1, "baz": 2},
        "qux": 3,
        "a": {"b": {"c": 4}}
    }
    assert build_nested_dict(flat) == expected

@pytest.mark.asyncio
async def test_resolve_form_id_from_prefix():
    # Mock client and its API
    mock_client = MagicMock()
    mock_client.api = AsyncMock()
    
    # Mock database tree response
    mock_resource_1 = MagicMock()
    mock_resource_1.label = "EXT_Form1"
    mock_resource_1.type = DatabaseTreeResourceType.FORM
    mock_resource_1.id = "form_abc"
    
    mock_resource_2 = MagicMock()
    mock_resource_2.label = "OTHER_Res"
    mock_resource_2.type = DatabaseTreeResourceType.FORM
    mock_resource_2.id = "form_other"

    mock_db_tree = MagicMock()
    mock_db_tree.resources = [mock_resource_1, mock_resource_2]
    
    mock_client.api.get_database_tree.return_return_value = mock_db_tree
    # Wait, get_database_tree is async
    mock_client.api.get_database_tree = AsyncMock(return_value=mock_db_tree)
    
    # Test successful resolution
    form_id = await resolve_form_id_from_prefix(mock_client, "db_id", "EXT")
    assert form_id == "form_abc"
    
    # Test unsuccessful resolution
    form_id = await resolve_form_id_from_prefix(mock_client, "db_id", "NONEXISTENT")
    assert form_id is None

@pytest.mark.asyncio
async def test_get_operation_calculation_changesets():
    mock_client = MagicMock()
    mock_client.api = MagicMock()

    # 1. Setup Formulas Fields (1 Internal, 1 External)
    internal_field = OperationCalculationFormulasField(
        id="f1", last_edit_time=1, ref_order=1, description="desc",
        apply=OperationCalculationApplyType.INTERNAL,
        sys_prefix="INT", sys_field="calc_field", filter="true", formula="1 + 1"
    )
    external_field = OperationCalculationFormulasField(
        id="f2", last_edit_time=1, ref_order=2, description="desc",
        apply=OperationCalculationApplyType.EXTERNAL,
        sys_prefix="EXT", sys_field="calc_field_ext", filter="status == \"active\"", formula="quantity * 2"
    )
    
    mock_client.api.get_operation_calculation_formulas_fields = AsyncMock(
        return_value=[internal_field, external_field]
    )

    # 2. Setup Database Tree (Resolve Form IDs)
    mock_db_tree = MagicMock()
    r1 = MagicMock(label="INT_Form", type=DatabaseTreeResourceType.FORM, id="form_int")
    r2 = MagicMock(label="EXT_Form", type=DatabaseTreeResourceType.FORM, id="form_ext")
    mock_db_tree.resources = [r1, r2]
    mock_client.api.get_database_tree = AsyncMock(return_value=mock_db_tree)

    # 3. Setup Internal Logic (get_form_schema)
    mock_schema = FormSchema(
        id="form_int", schemaVersion=1, databaseId="db1", label="Int Form",
        elements=[
            FormElement(
                id="field_id_1", code="calc_field", label="Calc Field", type="CALCULATED",
                typeParameters=TypeParameters(formula="old_formula")
            )
        ]
    )
    mock_client.api.get_form_schema = AsyncMock(return_value=mock_schema)

    # 4. Setup External Logic (get_form query)
    # Record 1: Matches filter, value changes -> Changeset Entry
    # Record 2: Matches filter, value same -> Skipped
    # Record 3: No match filter -> Skipped
    records = [
        {"@id": "rec1", "status": "active", "quantity": 10, "calc_field_ext": 0},
        {"@id": "rec2", "status": "active", "quantity": 10, "calc_field_ext": 20.0},
        {"@id": "rec3", "status": "inactive", "quantity": 10, "calc_field_ext": 0},
    ]
    mock_client.api.get_form = AsyncMock(return_value=records)

    # EXECUTE
    form_changeset, record_changeset = await get_operation_calculation_changesets(mock_client, "db1", "config_form_id")

    # VERIFY INTERNAL
    assert form_changeset.action == "operation_calculation_formulas"
    assert len(form_changeset.entries) == 1
    entry = form_changeset.entries[0]
    assert entry.form_id == "form_int"
    assert entry.field_code == "calc_field"
    assert entry.field_id == "field_id_1"
    # Formula wrapped in IF(filter, formula) -> IF(true, 1 + 1)
    assert entry.new_expression == "IF(true, 1 + 1)"
    assert entry.old_expression == "old_formula"

    # VERIFY EXTERNAL
    assert record_changeset.action == "operation_calculation_formulas"
    assert len(record_changeset.entries) == 1
    rec_entry = record_changeset.entries[0]
    assert rec_entry.record_id == "rec1"
    assert rec_entry.form_id == "form_ext"
    assert rec_entry.fields["calc_field_ext"] == 20.0 # 10 * 2
    assert rec_entry.old_fields["calc_field_ext"] == 0
