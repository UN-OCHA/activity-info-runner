import { Icon, Link, Tag } from "@blueprintjs/core";
import { createColumnHelper } from "@tanstack/react-table";
import type { JSX } from "react";
import type {
  DatabaseAction,
  FieldAction,
  FormAction,
  MaterializedBoundary,
  RecordAction,
} from "../types";

function getChangedPaths(
  oldObj: unknown,
  newObj: unknown,
  prefix = "",
): Set<string> {
  const changed = new Set<string>();

  if (oldObj === newObj) return changed;

  if (oldObj instanceof Date || newObj instanceof Date) {
    if (
      !(oldObj instanceof Date) ||
      !(newObj instanceof Date) ||
      oldObj.getTime() !== newObj.getTime()
    ) {
      changed.add(prefix);
    }
    return changed;
  }

  if (
    typeof oldObj !== "object" ||
    oldObj === null ||
    typeof newObj !== "object" ||
    newObj === null
  ) {
    changed.add(prefix);
    return changed;
  }

  const oldAsRecord = oldObj as Record<string, unknown>;
  const newAsRecord = newObj as Record<string, unknown>;

  const keys = Array.from(
    new Set([...Object.keys(oldAsRecord), ...Object.keys(newAsRecord)]),
  );

  for (const k of keys) {
    const newPrefix = prefix ? `${prefix}.${k}` : k;
    for (const p of getChangedPaths(
      oldAsRecord[k],
      newAsRecord[k],
      newPrefix,
    )) {
      changed.add(p);
    }
  }

  return changed;
}

function renderObjectWithDiff(
  obj: unknown,
  pathPrefix: string,
  changedPaths: Set<string>,
  highlightColor: "red" | "green" = "red",
  forceHighlight = false,
): JSX.Element {
  const isChanged = forceHighlight || changedPaths.has(pathPrefix);

  const baseText = "font-mono text-[10px]";
  const colorClass = isChanged
    ? highlightColor === "red"
      ? "font-bold text-red-600 line-through decoration-red-600"
      : "font-bold text-green-600"
    : "text-gray-600";

  if (typeof obj !== "object" || obj === null) {
    let displayValue: string;
    if (obj === undefined) displayValue = "undefined";
    else if (obj === null) displayValue = "null";
    else displayValue = JSON.stringify(obj);

    return <span className={`${baseText} ${colorClass}`}>{displayValue}</span>;
  }

  if (Array.isArray(obj)) {
    return (
      <span className={`ml-2 ${isChanged ? colorClass : ""}`}>
        {"["}
        <div className="pl-2 border-l border-gray-200">
          {obj.map((value, i) => {
            const path = pathPrefix ? `${pathPrefix}.${i}` : `${i}`;
            return (
              <div key={path}>
                {renderObjectWithDiff(
                  value,
                  path,
                  changedPaths,
                  highlightColor,
                  isChanged,
                )}
                {i < obj.length - 1 ? "," : ""}
              </div>
            );
          })}
        </div>
        {"]"}
      </span>
    );
  }

  const objAsRecord = obj as Record<string, unknown>;
  return (
    <span className={`ml-2 ${isChanged ? colorClass : ""}`}>
      {"{"}
      <div className="pl-2 border-l border-gray-200">
        {Object.entries(objAsRecord)
          .filter(([, value]) => value !== undefined)
          .map(([key, value], i, arr) => {
            const path = pathPrefix ? `${pathPrefix}.${key}` : key;
            return (
              <div key={path}>
                <span className={isChanged ? colorClass : "text-gray-500"}>
                  {key}:{" "}
                </span>
                {renderObjectWithDiff(
                  value,
                  path,
                  changedPaths,
                  highlightColor,
                  isChanged,
                )}
                {i < arr.length - 1 ? "," : ""}
              </div>
            );
          })}
      </div>
      {"}"}
    </span>
  );
}

const dbColumnHelper = createColumnHelper<DatabaseAction>();
export const databaseColumns = [
  dbColumnHelper.accessor("TYPE", {
    header: "Type",
    cell: (info) => (
      <Tag
        minimal
        className="font-bold"
        intent={
          info.getValue() == "UPDATE"
            ? "warning"
            : info.getValue() == "DELETE"
              ? "danger"
              : "success"
        }
      >
        {info.getValue()}
      </Tag>
    ),
  }),

  dbColumnHelper.accessor("database_id", {
    header: "Database ID",
    cell: (info) => (
      <Link
        href={`https://3w.humanitarianaction.info/app#database/${info.getValue()}`}
        target="_blank"
        className="flex flex-row justify-between items-center w-full"
      >
        {info.getValue()}
        <Icon icon="share" size={10} />
      </Link>
    ),
  }),

  dbColumnHelper.accessor("origin", {
    header: "Origin",
    cell: (info) => <span className="text-gray-500">{info.getValue()}</span>,
  }),
];

const formColumnHelper = createColumnHelper<FormAction>();
export const formColumns = [
  formColumnHelper.accessor("TYPE", {
    header: "Type",
    cell: (info) => (
      <Tag
        minimal
        className="font-bold"
        intent={
          info.getValue() == "UPDATE"
            ? "warning"
            : info.getValue() == "DELETE"
              ? "danger"
              : "success"
        }
      >
        {info.getValue()}
      </Tag>
    ),
  }),

  formColumnHelper.accessor("form_id", {
    header: "Form ID",
    cell: (info) => (
      <Link
        href={`https://3w.humanitarianaction.info/app#form/${info.getValue()}`}
        target="_blank"
        className="flex flex-row justify-between items-center w-full"
      >
        {info.getValue()}
        <Icon icon="share" size={10} />
      </Link>
    ),
  }),

  formColumnHelper.accessor("database_id", {
    header: "Database ID",
    cell: (info) => (
      <Link
        href={`https://3w.humanitarianaction.info/app#database/${info.getValue()}`}
        target="_blank"
        className="flex flex-row justify-between items-center w-full"
      >
        {info.getValue()}
        <Icon icon="share" size={10} />
      </Link>
    ),
  }),
];

const fieldColumnHelper = createColumnHelper<FieldAction>();
export const getFieldColumns = (
  materializedBoundary?: MaterializedBoundary,
) => {
  const dbLookup = new Map<string, string>();
  const formLookup = new Map<string, string>();
  const fieldLookup = new Map<string, string>();

  materializedBoundary?.databases.forEach((db) => {
    dbLookup.set(db.databaseId, db.label || db.databaseId);

    db.forms.forEach((form) => {
      formLookup.set(form.id, form.label);
      form.fields.forEach((field) => {
        fieldLookup.set(field.id, field.label || field.code);
      });
    });
  });

  return [
    fieldColumnHelper.accessor("TYPE", {
      header: "Type",
      cell: (info) => (
        <Tag
          minimal
          className="font-bold"
          intent={
            info.getValue() == "UPDATE"
              ? "warning"
              : info.getValue() == "DELETE"
                ? "danger"
                : "success"
          }
        >
          {info.getValue()}
        </Tag>
      ),
    }),

    fieldColumnHelper.accessor("database_id", {
      header: "Database",
      cell: (info) => {
        const dbId = info.getValue();
        const dbName = dbLookup.get(dbId) || dbId;
        return (
          <Link
            href={`https://3w.humanitarianaction.info/app#database/${dbId}`}
            target="_blank"
            className="flex flex-row justify-between items-center w-full"
          >
            {dbName}
            <Icon icon="share" size={10} className="ml-1" />
          </Link>
        );
      },
    }),

    fieldColumnHelper.accessor("form_id", {
      header: "Form",
      cell: (info) => {
        const formId = info.getValue();
        const formName = formLookup.get(formId) || formId;
        return (
          <Link
            href={`https://3w.humanitarianaction.info/app#form/${formId}/design`}
            target="_blank"
            className="flex flex-row justify-between items-center w-full"
          >
            {formName}
            <Icon icon="share" size={10} className="ml-1" />
          </Link>
        );
      },
    }),

    fieldColumnHelper.accessor("field_id", {
      header: "Field",
      cell: (info) => {
        const fieldId = info.getValue();
        const formId = info.row.original.form_id;
        const fieldName = fieldLookup.get(fieldId) || fieldId;

        return (
          <Link
            href={`https://3w.humanitarianaction.info/app#form/${formId}/design`}
            target="_blank"
            className="flex flex-row justify-between items-center w-full"
          >
            {fieldName}
            <Icon icon="share" size={10} className="ml-1" />
          </Link>
        );
      },
    }),

    fieldColumnHelper.display({
      id: "diff",
      header: "Field Changes",
      cell: (info) => {
        const {
          old_field: oldField,
          new_field: newField,
          TYPE,
        } = info.row.original;

        if (TYPE === "CREATE") {
          return (
            <div className="bg-green-50 p-2 rounded border border-green-100 font-mono text-[10px]">
              {renderObjectWithDiff(newField, "", new Set(), "green", true)}
            </div>
          );
        }

        if (TYPE === "DELETE") {
          return (
            <div className="bg-red-50 p-2 rounded border border-red-100 font-mono text-[10px]">
              {renderObjectWithDiff(oldField, "", new Set(), "red", true)}
            </div>
          );
        }

        const changedPaths = getChangedPaths(oldField, newField);

        return (
          <div className="flex flex-row gap-2 font-mono text-[10px]">
            <div className="flex-1 bg-red-50 p-2 rounded border border-red-100">
              {renderObjectWithDiff(oldField, "", changedPaths, "red")}
            </div>
            <div className="flex-1 bg-green-50 p-2 rounded border border-green-100">
              {renderObjectWithDiff(newField, "", changedPaths, "green")}
            </div>
          </div>
        );
      },
    }),
  ];
};

const recordColumnHelper = createColumnHelper<RecordAction>();
export const getRecordColumns = (
  materializedBoundary?: MaterializedBoundary,
) => {
  const formLookup = new Map<string, string>();
  materializedBoundary?.databases.forEach((db) => {
    db.forms.forEach((form) => {
      formLookup.set(form.id, form.label);
    });
  });

  return [
    recordColumnHelper.accessor("TYPE", {
      header: "Type",
      cell: (info) => (
        <Tag
          minimal
          className="font-bold"
          intent={
            info.getValue() == "UPDATE"
              ? "warning"
              : info.getValue() == "DELETE"
                ? "danger"
                : "success"
          }
        >
          {info.getValue()}
        </Tag>
      ),
    }),

    recordColumnHelper.accessor("form_id", {
      header: "Form",
      cell: (info) => {
        const formId = info.getValue();
        const formLabel = formLookup.get(formId) || formId;
        return (
          <Link
            href={`https://3w.humanitarianaction.info/app#form/${formId}/display`}
            target="_blank"
            className="flex flex-row justify-between items-center w-full"
          >
            {formLabel}
            <Icon icon="share" size={10} className="ml-1" />
          </Link>
        );
      },
    }),

    recordColumnHelper.accessor("field_code", {
      header: "Field",
      cell: (info) => (
        <Link
          href={`https://3w.humanitarianaction.info/app#form/${info.row.original.form_id}/design`}
          target="_blank"
          className="flex flex-row justify-between items-center w-full"
        >
          {info.getValue()}
          <Icon icon="share" size={10} />
        </Link>
      ),
    }),

    recordColumnHelper.accessor("record_id", {
      header: "Record ID",
      cell: (info) => (
        <Link
          href={`https://3w.humanitarianaction.info/app#form/${info.row.original.form_id}/table:_id=${info.getValue()}`}
          target="_blank"
          className="flex flex-row justify-between items-center w-full"
        >
          {info.getValue()}
          <Icon icon="share" size={10} />
        </Link>
      ),
    }),

    recordColumnHelper.accessor("field_value", {
      header: "New value",
      cell: (info) => (
        <span className="font-bold text-green-700">{info.getValue()}</span>
      ),
    }),
  ];
};
