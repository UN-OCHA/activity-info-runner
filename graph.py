import asyncio
import os
import re
from typing import Dict, List, Tuple, Set

from dotenv import load_dotenv
from neo4j import GraphDatabase

from actions.common import DatabaseTreeResourceType
from api import ActivityInfoClient
from api.client import BASE_URL

URI = "neo4j://localhost"
PATH_RE = re.compile(r'\b[a-z0-9_]{3,}(?:\.[a-z0-9_]{3,})*\b', re.IGNORECASE)
KEYWORDS = {"IF", "AND", "OR", "NOT", "ISBLANK", "ISNONBLANK", "VALUE", "TEXT", "CONCAT", "TEXTJOIN", "SEARCH",
            "COALESCE", "SUM", "MIN", "MAX", "AVG", "COUNT", "TODAY", "NOW", "DATE", "MONTH", "YEAR", "WEEKDAY", "ABS",
            "ROUND", "FLOOR", "CEILING", "LEN", "UPPER", "LOWER", "TRIM", "SUBSTITUTE", "REPLACE", "LEFT", "RIGHT",
            "MID", "TRUE", "FALSE"}


class FieldDef:
    def __init__(self, form_id, form_label, element):
        self.form_id = form_id
        self.form_label = form_label
        self.id = element.id
        self.code = getattr(element, "code", None)
        self.element = element

    @property
    def is_reference(self) -> bool:
        tp = getattr(self.element, "type_parameters", None)
        if not tp: return False
        if getattr(tp, "range", None): return True
        if str(getattr(self.element, "type", "")).lower() == "subform" and getattr(tp, "form_id", None): return True
        return False

    @property
    def reference_form(self) -> str | None:
        if not self.is_reference: return None
        tp = self.element.type_parameters
        if getattr(tp, "range", None): return tp.range[0]["formId"]
        if str(getattr(self.element, "type", "")).lower() == "subform": return getattr(tp, "form_id", None)
        return None


def safe_formula(element):
    tp = getattr(element, "type_parameters", None)
    if not tp: return []
    formulas = []
    if hasattr(tp, "formula") and tp.formula: formulas.append(tp.formula)
    if hasattr(tp, "prefix_formula") and tp.prefix_formula: formulas.append(tp.prefix_formula)
    if hasattr(tp, "lookup_configs") and tp.lookup_configs:
        for cfg in tp.lookup_configs:
            if hasattr(cfg, "formula") and cfg.formula: formulas.append(cfg.formula)
    return formulas


def extract_paths(expr: str) -> Set[Tuple[str, ...]]:
    if not expr: return set()
    paths = set()
    for match in PATH_RE.findall(expr):
        if match.upper() in KEYWORDS: continue
        paths.add(tuple(match.split(".")))
    return paths


def resolve_path(path: List[str], fields_by_form: Dict[str, Dict[str, FieldDef]],
                 all_fields_by_code: Dict[str, List[FieldDef]], context_form_id: str) -> Tuple[str, str] | None:
    if not path: return None
    first_code = path[0]
    field = fields_by_form.get(context_form_id, {}).get(first_code)
    if not field:
        candidates = all_fields_by_code.get(first_code, [])
        if not candidates: return None
        field = next((f for f in candidates if f.is_reference), candidates[0])
    current_form = field.form_id
    if len(path) > 1 and field.is_reference: current_form = field.reference_form
    for field_code in path[1:]:
        fields_in_form = fields_by_form.get(current_form, {})
        next_field = fields_in_form.get(field_code)
        if not next_field:
            global_candidates = all_fields_by_code.get(field_code)
            if global_candidates:
                next_field = global_candidates[0]
                current_form = next_field.form_id
            else:
                return None
        field = next_field
        if field.is_reference and field_code != path[-1]: current_form = field.reference_form
    return current_form, field.id


async def main():
    load_dotenv()
    driver = GraphDatabase.driver(URI)
    driver.verify_connectivity()
    client = ActivityInfoClient(BASE_URL, api_token=os.getenv("API_TOKEN"))
    tree = await client.api.get_database_tree("cay0dkxmkcry89w2")
    fields_by_form: Dict[str, Dict[str, FieldDef]] = {}
    form_labels: Dict[str, str] = {}
    forms_to_visit = []
    visited_forms = set()
    for res in tree.resources:
        if res.type == DatabaseTreeResourceType.FORM: forms_to_visit.append(res.id)
    while forms_to_visit:
        form_id = forms_to_visit.pop(0)
        if form_id in visited_forms: continue
        visited_forms.add(form_id)
        try:
            schema = await client.api.get_form_schema(form_id)
        except Exception as e:
            print(f"Warning: Failed to fetch schema for form {form_id}: {e}"); continue
        form_labels[form_id] = schema.label
        fields_by_form[form_id] = {}
        for element in schema.elements:
            fdef = FieldDef(form_id, schema.label, element)
            fields_by_form[form_id][element.id] = fdef
            if getattr(element, "code", None): fields_by_form[form_id][element.code] = fdef
            tp = getattr(element, "type_parameters", None)
            if not tp: continue
            if str(getattr(element, "type", "")).lower() == "subform":
                sub_id = getattr(tp, "form_id", None)
                if sub_id and sub_id not in visited_forms and sub_id not in forms_to_visit: forms_to_visit.append(
                    sub_id)
            ranges = getattr(tp, "range", []) or []
            for r in ranges:
                ref_id = r.get("formId")
                if ref_id and ref_id not in visited_forms and ref_id not in forms_to_visit: forms_to_visit.append(
                    ref_id)
    all_fields_by_code: Dict[str, List[FieldDef]] = {}
    for fdict in fields_by_form.values():
        for field in set(fdict.values()):
            all_fields_by_code.setdefault(field.id, []).append(field)
            if field.code: all_fields_by_code.setdefault(field.code, []).append(field)
    dependencies = []
    for form_id, fdict in fields_by_form.items():
        for field in set(fdict.values()):
            expressions = [("relevance", getattr(field.element, "relevance_condition", None)),
                           ("validation", getattr(field.element, "validation_condition", None))]
            for f in safe_formula(field.element): expressions.append(("formula", f))
            for kind, expr in expressions:
                for path in extract_paths(expr):
                    resolved = resolve_path(list(path), fields_by_form, all_fields_by_code, form_id)
                    if resolved:
                        dst_form, dst_field_id = resolved
                        if not (form_id == dst_form and field.id == dst_field_id): dependencies.append(
                            (form_id, field.id, dst_form, dst_field_id, kind))
    with driver.session() as session:
        for form_id, form_label in form_labels.items():
            session.run("MERGE (f:Form {id: $form_id}) SET f.label = $form_label", form_id=form_id,
                        form_label=form_label)
            fields = fields_by_form.get(form_id, {})
            for field in set(fields.values()):
                session.run(
                    """MATCH (f:Form {id: $form_id}) MERGE (fld:Field {id: $id}) SET fld.form_id = $form_id, fld.code = $code, fld.label = $label MERGE (f)-[:HAS_FIELD]->(fld)""",
                    form_id=field.form_id, id=field.id, code=field.code, label=field.element.label)
                if field.is_reference: session.run(
                    """MATCH (src:Field {id: $src_id}) MATCH (dst:Form {id: $dst_form}) MERGE (src)-[:REFERENCES]->(dst)""",
                    src_id=field.id, dst_form=field.reference_form)
        print(f"Creating {len(dependencies)} DEPENDS_ON edges...")
        for src_form, src_field_id, dst_form, dst_field_id, kind in dependencies:
            session.run(
                """MATCH (src:Field {id: $src_id}) MATCH (dst:Field {id: $dst_id}) MERGE (src)-[:DEPENDS_ON {type: $kind}]->(dst)""",
                src_id=src_field_id, dst_id=dst_field_id, kind=kind)
    driver.close()


if __name__ == "__main__": asyncio.run(main())
