export interface WorkflowRun {
  workflow_id: string;
  run_id: string;
  type: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  start_time: string; // ISO datetime
  close_time: string | null;

  params: string[];

  results: {
    changeset: Changeset;
    logs: string[];
    warnings?: string[] | null;
    materialized_boundary?: MaterializedBoundary;
  } | null;

  timings:
    | {
        name: string;
        type: string;
        start_time: string;
        end_time: string | null;
        duration_seconds: number | null;
      }[]
    | null;
}

export interface Changeset {
  database_actions: DatabaseAction[];
  field_actions: FieldAction[];
  form_actions: FormAction[];
  record_actions: RecordAction[];
}

export interface DatabaseAction {
  TYPE: string;
  database_id: string;
  origin: string;
}

export interface FormAction {
  TYPE: string;
  form_id: string;
  form_name: string;
  database_id: string;
  origin: string;
}

export interface FieldAction {
  TYPE: string;
  database_id: string;
  field_id: string;
  form_id: string;
  form_name: string;
  order: number;
  origin: string;

  old_field: FieldDefinition;
  new_field: FieldDefinition;
}

export interface FieldDefinition {
  id: string;
  code: string;
  label: string;
  type: string;
  key: boolean;
  required: boolean;
  data_entry_visible: boolean;
  table_visible: boolean;
  relevance_condition: string | null;
  validation_condition: string | null;
  type_parameters: Record<string, unknown> | null;
}

export interface RecordAction {
  TYPE: string;
  record_id: string;
  parent_record_id: string | null;

  form_id: string;

  field_code: string;
  field_value: string;
  old_field_value: unknown;

  order: number;
  origin: string;
}

export interface MaterializedBoundary {
  databases: MaterializedDatabase[];
}

export interface MaterializedDatabase {
  databaseId: string;
  description: string;
  forms: MaterializedForm[];
  label: string;
}

export interface MaterializedForm {
  id: string;
  label: string;
  databaseId: string;
  records: number;
  fields: FieldDefinition[];
}
