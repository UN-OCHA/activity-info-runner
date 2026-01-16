import pytest
from unittest.mock import AsyncMock, MagicMock
from actions.metric_configuration import (
    final_formula,
    MetricFieldKind,
    get_operation_metric_configuration_changesets,
    OPERATION_METRIC_CONFIGURATION_FORM_PREFIX
)
from actions.dtos import FieldType
from actions.models import FieldCreateAction, FieldUpdateAction
from api.models import OperationMetricConfigurationField, FormSchema, FormElement, TypeParameters
from actions.common import DatabaseTreeResourceType

def test_final_formula():
    prefix = "AMOUNT_X"
    
    # Case 1: All kinds
    kinds = [MetricFieldKind.MANUAL, MetricFieldKind.INTERNAL_CALC, MetricFieldKind.EXTERNAL_CALC]
    formula = final_formula(prefix, kinds)
    assert "AMOUNT_X_MAN" in formula
    assert "AMOUNT_X_ICALC" in formula
    assert "AMOUNT_X_ECALC" in formula
    assert formula.startswith("COALESCE(")

    # Case 2: Single kind
    kinds = [MetricFieldKind.MANUAL]
    formula = final_formula(prefix, kinds)
    assert formula == "COALESCE(AMOUNT_X_MAN)"

    # Case 3: Error
    with pytest.raises(ValueError):
        final_formula(prefix, [])

@pytest.mark.asyncio
async def test_get_operation_metric_configuration_changesets():
    mock_client = MagicMock()
    mock_client.api = MagicMock()
    
    # 1. Mock Database Tree
    config_form_id = "config_form_id"
    target_form_id = "target_form_id"
    
    mock_config_res = MagicMock()
    mock_config_res.id = config_form_id
    mock_config_res.label = OPERATION_METRIC_CONFIGURATION_FORM_PREFIX + "Config"
    mock_config_res.type = DatabaseTreeResourceType.FORM
    
    mock_target_res = MagicMock()
    mock_target_res.id = target_form_id
    mock_target_res.label = "TRG_TargetForm"
    mock_target_res.type = DatabaseTreeResourceType.FORM

    mock_db_tree = MagicMock()
    mock_db_tree.resources = [mock_config_res, mock_target_res]
    mock_client.api.get_database_tree = AsyncMock(return_value=mock_db_tree)

    # 2. Mock Configuration Fields
    # Create a config that should trigger a CREATE action
    config_field = OperationMetricConfigurationField(
        id="c1",
        last_edit_time=1,
        order=1,
        sort_order="1",
        data_form_prefix="TRG",
        data_form_id="dform1",
        shown_as="MAN",
        global_attachment_metrix="glob",
        reference_code_manual="refman",
        name="Metric Name",
        reference_code="MET1",
        field_name="ccode",
        reference_label="reflabel",
        errors=None
    )
    mock_client.api.get_operation_metric_configuration_fields = AsyncMock(return_value=[config_field])

    # 3. Mock Target Form Schema (Empty initially, so we expect creates)
    mock_schema = FormSchema(
        id=target_form_id,
        schemaVersion=1,
        databaseId="db1",
        label="Target Form",
        elements=[]
    )
    mock_client.api.get_form_schema = AsyncMock(return_value=mock_schema)
    
    # 4. Mock collect_field_mappings (needed for updates, but good to have)
    # Since we are testing creation, this might not be called, but let's mock it safely.
    # Note: collect_field_mappings is imported in metric_configuration.py. 
    # We can mock it if we patch it, or just let it run if it's safe. 
    # It calls get_form_schema, which we mocked.
    
    # EXECUTE
    changeset = await get_operation_metric_configuration_changesets(mock_client, "db1", 0)

    # VERIFY
    # We expect 4 fields created: MAN, ECALC, ICALC, FINAL (order depends on implementation, but defined in sets)
    # The code adds MAN because shown_as starts with MAN. 
    # Plus ECALC, ICALC, FINAL are default.
    assert len(changeset.field_actions) == 4
    
    codes = [a.field_code for a in changeset.field_actions]
    assert "AMOUNT_MET1_MAN" in codes
    assert "AMOUNT_MET1_ICALC" in codes
    assert "AMOUNT_MET1_ECALC" in codes
    assert "AMOUNT_MET1" in codes # Final field
    
    assert all(isinstance(a, FieldCreateAction) for a in changeset.field_actions)

