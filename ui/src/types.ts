export interface WorkflowRun {
  workflow_id: string;
  run_id: string;
  type: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  start_time: string; // ISO datetime
  close_time: string | null;

  params: {
    name: string;
    database_id: string;
  };

  results: {
    field_actions: FieldAction[];
    record_actions: RecordAction[];
    logs: string[] | null;
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

interface FieldDefinition {
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
  type_parameters: unknown | null;
}

export interface FieldAction {
  TYPE: string;
  database_id: string;
  field_code: string;
  form_id: string;
  form_name: string;
  order: number;
  origin: string;

  old: FieldDefinition;
  new: FieldDefinition;
}

export interface RecordAction {
  TYPE: string;
  record_id: string;
  parent_record_id: string | null;

  form_id: string;
  form_name: string;

  field_code: string;
  field_value: number;
  old_field_value: number;

  order: number;
  origin: string;
}
