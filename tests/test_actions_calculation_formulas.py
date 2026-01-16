import pytest
from unittest.mock import AsyncMock, MagicMock
from actions.calculation_formulas import (
    get_operation_calculation_changesets,
    OperationCalculationApplyType,
    CALCULATION_FORMULAS_FORM_PREFIX
)
from actions.common import DatabaseTreeResourceType
from api.models import OperationCalculationFormulasField, FormSchema, FormElement, TypeParameters

@pytest.mark.asyncio
async def test_get_operation_calculation_changesets():
    mock_client = MagicMock()
    mock_client.api = MagicMock()

    # 1. Setup Formulas Fields (1 Internal, 1 External)
    internal_field = OperationCalculationFormulasField(
        id="f1", last_edit_time=1, ref_order=1, description="desc",
        apply=OperationCalculationApplyType.INTERNAL,
        sys_prefix="INT", sys_field="calc_field", filter="true", formula="1 + 1",
        errors=None
    )
    external_field = OperationCalculationFormulasField(
        id="f2", last_edit_time=1, ref_order=2, description="desc",
        apply=OperationCalculationApplyType.EXTERNAL,
        sys_prefix="EXT", sys_field="calc_field_ext", filter="status == \"active\"", formula="quantity * 2",
        errors=None
    )
    
    mock_client.api.get_operation_calculation_formulas_fields = AsyncMock(
        return_value=[internal_field, external_field]
    )

    # 2. Setup Database Tree (Resolve Form IDs)
    mock_db_tree = MagicMock()
    # The code looks for a form starting with CALCULATION_FORMULAS_FORM_PREFIX
    config_form = MagicMock(label=CALCULATION_FORMULAS_FORM_PREFIX + "Config", type=DatabaseTreeResourceType.FORM, id="form_config")
    
    r1 = MagicMock(label="INT_Form", type=DatabaseTreeResourceType.FORM, id="form_int")
    r2 = MagicMock(label="EXT_Form", type=DatabaseTreeResourceType.FORM, id="form_ext")
    mock_db_tree.resources = [config_form, r1, r2]
    mock_client.api.get_database_tree = AsyncMock(return_value=mock_db_tree)

    # 3. Setup Internal Logic (get_form_schema)
    mock_schema = FormSchema(
        id="form_int", schemaVersion=1, databaseId="db1", label="Int Form",
        elements=[
            FormElement(
                id="field_id_1", code="calc_field_ICALC", label="Calc Field", type="CALCULATED",
                typeParameters=TypeParameters(formula="old_formula")
            )
        ]
    )
    mock_client.api.get_form_schema = AsyncMock(return_value=mock_schema)

    # 4. Setup External Logic (get_form query)
    records = [
        {"@id": "rec1", "status": "active", "quantity": 10, "calc_field_ext": 0},
        {"@id": "rec2", "status": "active", "quantity": 10, "calc_field_ext": 20.0},
        {"@id": "rec3", "status": "inactive", "quantity": 10, "calc_field_ext": 0},
    ]
    mock_client.api.get_form = AsyncMock(return_value=records)

    # EXECUTE
    changeset = await get_operation_calculation_changesets(mock_client, "db1")

    # VERIFY INTERNAL (Field Actions)
    # We expect 1 field action for the internal calculation
    assert len(changeset.field_actions) == 1
    field_entry = changeset.field_actions[0]
    assert field_entry.form_id == "form_int"
    assert field_entry.field_code == "calc_field_ICALC"
    # Formula wrapped in IF(filter, formula) -> IF(true, 1 + 1)
    assert field_entry.formula == "IF(true, 1 + 1)"
    assert field_entry.old_formula == "old_formula"

    # VERIFY EXTERNAL (Record Actions)
    # We expect 1 record action (rec1 updated, rec2 skipped as same, rec3 skipped as filter fail)
    assert len(changeset.record_actions) == 1
    rec_entry = changeset.record_actions[0]
    assert rec_entry.record_id == "rec1"
    assert rec_entry.form_id == "form_ext"
    assert rec_entry.field_value == 20.0 # 10 * 2
