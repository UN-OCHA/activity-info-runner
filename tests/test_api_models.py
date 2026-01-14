from api.models import OperationCalculationFormulasField, DatabaseTree, OwnerRef, DatabaseRole

def test_operation_calculation_formulas_field_alias():
    raw = {
        "@id": "field1",
        "@lastEditTime": 123456789.0,
        "REFORDER": 1,
        "DESC": "Description",
        "APPLY": "Internal",
        "SYSPREFIX": "ABC",
        "SYSFIELD": "field_code",
        "FILTER": "true",
        "FORMULA": "1+1"
    }
    field = OperationCalculationFormulasField.model_validate(raw)
    assert field.id == "field1"
    assert field.last_edit_time == 123456789.0
    assert field.ref_order == 1
    assert field.apply == "Internal"
    assert field.sys_prefix == "ABC"

def test_database_tree_parsing():
    raw = {
        "databaseId": "db1",
        "userId": "user1",
        "version": "v1",
        "label": "My DB",
        "description": "Desc",
        "ownerRef": {"id": "o1", "name": "Owner", "email": "owner@example.com"},
        "billingAccountId": 123,
        "language": "en",
        "originalLanguage": "en",
        "role": {"id": "r1", "parameters": {}, "resources": []},
        "suspended": False,
        "billingPlan": "free",
        "storage": "cloud",
        "publishedTemplate": False,
        "resources": [],
        "grants": [],
        "roles": [],
        "securityCategories": []
    }
    db = DatabaseTree.model_validate(raw)
    assert db.databaseId == "db1"
    assert db.ownerRef.name == "Owner"
