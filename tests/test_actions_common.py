import pytest
from unittest.mock import AsyncMock, MagicMock
from actions.common import resolve_form_from_prefix, DatabaseTreeResourceType, collect_field_mappings
from api.models import FormSchema, TypeParameters
from actions.dtos import SchemaFieldUpdateDTO, FieldType, FieldTypeParametersUpdateDTO

@pytest.mark.asyncio
async def test_resolve_form_from_prefix():
    # Mock client and its API
    mock_client = MagicMock()
    mock_client.api = MagicMock()
    
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
    
    mock_client.api.get_database_tree = AsyncMock(return_value=mock_db_tree)
    
    # Test successful resolution
    resource = await resolve_form_from_prefix(mock_client, "db_id", "EXT")
    assert resource is not None
    assert resource.id == "form_abc"
    
    # Test unsuccessful resolution
    resource = await resolve_form_from_prefix(mock_client, "db_id", "NONEXISTENT")
    assert resource is None

@pytest.mark.asyncio
async def test_collect_field_mappings():
    mock_client = MagicMock()
    mock_client.api = MagicMock()

    # Form 1 (Root) -> References Form 2
    form1 = FormSchema(
        id="f1", schemaVersion=1, databaseId="db", label="F1",
        elements=[
            SchemaFieldUpdateDTO(id="f1_field1", code="CODE1", label="L1", type=FieldType.FREE_TEXT, required=False),
            SchemaFieldUpdateDTO(
                id="f1_ref", code="REF_F2", label="Ref", type=FieldType.reference, required=False,
                typeParameters=FieldTypeParametersUpdateDTO(range=[{"formId": "f2"}])
            )
        ]
    )

    # Form 2 -> References Form 3 (Recursive check)
    form2 = FormSchema(
        id="f2", schemaVersion=1, databaseId="db", label="F2",
        elements=[
            SchemaFieldUpdateDTO(id="f2_field1", code="CODE2", label="L2", type=FieldType.FREE_TEXT, required=False),
            SchemaFieldUpdateDTO(
                id="f2_ref", code="REF_F3", label="Ref3", type=FieldType.reference, required=False,
                typeParameters=FieldTypeParametersUpdateDTO(range=[{"formId": "f3"}])
            )
        ]
    )
    
    # Form 3 (Leaf)
    form3 = FormSchema(
        id="f3", schemaVersion=1, databaseId="db", label="F3",
        elements=[
            SchemaFieldUpdateDTO(id="f3_field1", code="CODE3", label="L3", type=FieldType.FREE_TEXT, required=False)
        ]
    )

    # Mock get_form_schema to return appropriate form based on ID
    async def get_schema_side_effect(form_id):
        if form_id == "f1": return form1
        if form_id == "f2": return form2
        if form_id == "f3": return form3
        raise ValueError("Unknown form")
    
    mock_client.api.get_form_schema = AsyncMock(side_effect=get_schema_side_effect)

    # EXECUTE
    mappings = await collect_field_mappings(mock_client, "f1")

    # VERIFY
    # Should contain mappings from all visited forms
    expected = {
        "f1_field1": "CODE1",
        "f1_ref": "REF_F2",
        "f2_field1": "CODE2",
        "f2_ref": "REF_F3",
        "f3_field1": "CODE3"
    }
    assert mappings == expected

@pytest.mark.asyncio
async def test_collect_field_mappings_deep_nested():
    """
    Test case mimicking the user's issue: IND.MM.REFCODE
    IND (Form1) -> MM (Form2) -> REFCODE (Form3)
    """
    mock_client = MagicMock()
    mock_client.api = MagicMock()

    # Form 1: Has IND (Ref to Form 2)
    form1 = FormSchema(
        id="form1", schemaVersion=1, databaseId="db", label="Form1",
        elements=[
            SchemaFieldUpdateDTO(
                id="ind_id", code="IND", label="Indicator", type=FieldType.reference, required=False,
                typeParameters=FieldTypeParametersUpdateDTO(range=[{"formId": "form2"}])
            )
        ]
    )

    # Form 2: Has MM (Ref to Form 3)
    form2 = FormSchema(
        id="form2", schemaVersion=1, databaseId="db", label="Form2",
        elements=[
            SchemaFieldUpdateDTO(
                id="c5vwsj1mj1jdd7wi9", code="MM", label="MM Ref", type=FieldType.reference, required=False,
                typeParameters=FieldTypeParametersUpdateDTO(range=[{"formId": "form3"}])
            )
        ]
    )

    # Form 3: Has REFCODE
    form3 = FormSchema(
        id="form3", schemaVersion=1, databaseId="db", label="Form3",
        elements=[
            SchemaFieldUpdateDTO(
                id="cl9n6rdmfnv79alw", code="REFCODE", label="Ref Code", type=FieldType.FREE_TEXT, required=False
            )
        ]
    )

    async def get_schema_side_effect(form_id):
        if form_id == "form1": return form1
        if form_id == "form2": return form2
        if form_id == "form3": return form3
        raise ValueError(f"Unknown form {form_id}")

    mock_client.api.get_form_schema = AsyncMock(side_effect=get_schema_side_effect)

    # EXECUTE
    mappings = await collect_field_mappings(mock_client, "form1")

    # VERIFY
    # Check if we have mappings for MM and REFCODE
    assert "c5vwsj1mj1jdd7wi9" in mappings
    assert mappings["c5vwsj1mj1jdd7wi9"] == "MM"
    
    assert "cl9n6rdmfnv79alw" in mappings
    assert mappings["cl9n6rdmfnv79alw"] == "REFCODE"

@pytest.mark.asyncio
async def test_collect_field_mappings_subform():
    """
    Test recursion into SUBFORM fields.
    SUB (Form1) -> FIELD (Form2 - Subform)
    """
    mock_client = MagicMock()
    mock_client.api = MagicMock()

    # Form 1: Has SUB (Subform pointing to Form 2)
    form1 = FormSchema(
        id="form1", schemaVersion=1, databaseId="db", label="Form1",
        elements=[
            SchemaFieldUpdateDTO(
                id="sub_id", code="SUB", label="Subform", type=FieldType.subform, required=False,
                typeParameters=FieldTypeParametersUpdateDTO(form_id="form2")
            )
        ]
    )

    # Form 2: Subform Schema
    form2 = FormSchema(
        id="form2", schemaVersion=1, databaseId="db", label="Form2",
        elements=[
            SchemaFieldUpdateDTO(
                id="field_id", code="FIELD", label="Field", type=FieldType.FREE_TEXT, required=False
            )
        ]
    )

    async def get_schema_side_effect(form_id):
        if form_id == "form1": return form1
        if form_id == "form2": return form2
        raise ValueError(f"Unknown form {form_id}")

    mock_client.api.get_form_schema = AsyncMock(side_effect=get_schema_side_effect)

    # EXECUTE
    mappings = await collect_field_mappings(mock_client, "form1")

    # VERIFY
    assert "field_id" in mappings
    assert mappings["field_id"] == "FIELD"