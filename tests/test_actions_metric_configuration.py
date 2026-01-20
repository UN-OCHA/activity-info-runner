import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from actions.metric_configuration import (
    final_formula,
    MetricFieldKind,
    get_operation_metric_configuration_changesets,
    OPERATION_METRIC_CONFIGURATION_FORM_PREFIX,
    FIELD_KIND_CONFIG
)
from actions.dtos import FieldType, FieldTypeParametersUpdateDTO, SchemaFieldUpdateDTO
from actions.models import FieldCreateAction, FieldUpdateAction
from api.models import OperationMetricConfigurationField, FormSchema, TypeParameters
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
async def test_get_operation_metric_configuration_creates():
    with patch("actions.metric_configuration.ActivityInfoClient") as MockClientClass, \
         patch("actions.metric_configuration.collect_field_mappings", new_callable=AsyncMock) as mock_collect, \
         patch("actions.metric_configuration.resolve_form_from_prefix", new_callable=AsyncMock) as mock_resolve:
        
        mock_client = MockClientClass.return_value
        mock_client.api = MagicMock()
        mock_collect.return_value = {}
        
        database_id = "db1"
        target_form_id = "target_form_id"
        
        # 1. Mock Database Tree
        mock_config_res = MagicMock()
        mock_config_res.id = "config_form_id"
        mock_config_res.label = OPERATION_METRIC_CONFIGURATION_FORM_PREFIX + "Config"
        mock_config_res.type = DatabaseTreeResourceType.FORM
        
        mock_target_res = MagicMock()
        mock_target_res.id = target_form_id
        mock_target_res.label = "TRG_TargetForm"
        mock_target_res.type = DatabaseTreeResourceType.FORM
        
        mock_db_tree = MagicMock()
        mock_db_tree.resources = [mock_config_res, mock_target_res]
        mock_client.api.get_database_tree = AsyncMock(return_value=mock_db_tree)
        mock_resolve.return_value = mock_target_res

        # 2. Mock Config
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

        # 3. Mock Schema (Empty)
        mock_schema = FormSchema(
            id=target_form_id,
            schemaVersion=1,
            databaseId=database_id,
            label="Target Form",
            elements=[]
        )
        mock_client.api.get_form_schema = AsyncMock(return_value=mock_schema)

        # EXECUTE
        changeset = await get_operation_metric_configuration_changesets(database_id)

        # VERIFY
        assert len(changeset.field_actions) == 4
        assert all(isinstance(a, FieldCreateAction) for a in changeset.field_actions)

@pytest.mark.asyncio
async def test_metric_configuration_update_no_useless_changelog():
    with patch("actions.metric_configuration.ActivityInfoClient") as MockClientClass, \
         patch("actions.metric_configuration.collect_field_mappings", new_callable=AsyncMock) as mock_collect, \
         patch("actions.metric_configuration.resolve_form_from_prefix", new_callable=AsyncMock) as mock_resolve:
        
        mock_client = MockClientClass.return_value
        mock_client.api = MagicMock()
        mock_collect.return_value = {}
        
        database_id = "db1"
        target_form_id = "target_form_id"
        
        # 1. Mock Database Tree
        mock_config_res = MagicMock()
        mock_config_res.id = "config_form_id"
        mock_config_res.label = OPERATION_METRIC_CONFIGURATION_FORM_PREFIX + "Config"
        mock_config_res.type = DatabaseTreeResourceType.FORM
        
        mock_target_res = MagicMock()
        mock_target_res.id = target_form_id
        mock_target_res.label = "TRG_TargetForm"
        mock_target_res.type = DatabaseTreeResourceType.FORM

        mock_db_tree = MagicMock()
        mock_db_tree.resources = [mock_config_res, mock_target_res]
        mock_client.api.get_database_tree = AsyncMock(return_value=mock_db_tree)
        mock_resolve.return_value = mock_target_res

        # 2. Mock Configuration Fields
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
        
        # 3. Mock Target Form Schema with EXISTING field
        existing_field_code = "AMOUNT_MET1_MAN"
        
        expected_relevance = FIELD_KIND_CONFIG[MetricFieldKind.MANUAL].relevanceCondition(config_field.field_name)

        existing_field = SchemaFieldUpdateDTO(
            id="f1",
            code=existing_field_code,
            label="Metric Name (Manual)",
            type=FieldType.quantity,
            required=False,
            relevanceCondition=expected_relevance,
            typeParameters=FieldTypeParametersUpdateDTO(
                formula="", # Empty string formula
                units=None,
                range=None
            )
        )
        
        mock_schema = FormSchema(
            id=target_form_id,
            schemaVersion=1,
            databaseId=database_id,
            label="Target Form",
            elements=[existing_field]
        )
        mock_client.api.get_form_schema = AsyncMock(return_value=mock_schema)

        # EXECUTE
        changeset = await get_operation_metric_configuration_changesets(database_id)

        # VERIFY
        updates = [a for a in changeset.field_actions if isinstance(a, FieldUpdateAction)]
        
        # Check if we have an update for AMOUNT_MET1_MAN
        man_update = next((u for u in updates if u.field_code == existing_field_code), None)
        
        if man_update:
             pytest.fail(f"Should not update if typeParameters are effectively empty. Found update: {man_update}")