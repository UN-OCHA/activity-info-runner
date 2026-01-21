import { HTMLTable, Icon, Link, Tag } from "@blueprintjs/core";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import type { JSX } from "react";
import type { FieldAction } from "../types";

const columnHelper = createColumnHelper<FieldAction>();

// Get all leaf-level changed paths
function getChangedPaths(oldObj: any, newObj: any, prefix = ""): Set<string> {
  const changed = new Set<string>();

  if (oldObj === newObj) return changed;

  if (
    typeof oldObj !== "object" ||
    oldObj === null ||
    typeof newObj !== "object" ||
    newObj === null
  ) {
    changed.add(prefix || "(root)");
    return changed;
  }

  const keys = Array.from(
    new Set([...Object.keys(oldObj), ...Object.keys(newObj)]),
  );
  for (const k of keys) {
    const newPrefix = prefix ? `${prefix}.${k}` : k;
    for (const p of getChangedPaths(oldObj?.[k], newObj?.[k], newPrefix)) {
      changed.add(p);
    }
  }

  return changed;
}

// Render object recursively, highlighting only changed leaves
function renderObjectWithDiff(
  obj: any,
  pathPrefix: string,
  changedPaths: Set<string>,
  highlightColor: "red" | "green" = "red",
): JSX.Element {
  if (typeof obj !== "object" || obj === null) {
    const isChanged = changedPaths.has(pathPrefix);
    const colorClass = isChanged
      ? highlightColor === "red"
        ? "font-black text-red-600"
        : "font-black text-green-600"
      : "text-gray-400";

    return <span className={colorClass}>{JSON.stringify(obj)}</span>;
  }

  return (
    <span className="ml-2">
      {"{"}
      {Object.entries(obj).map(([key, value], i, arr) => {
        const path = pathPrefix ? `${pathPrefix}.${key}` : key;
        return (
          <div key={path} className="ml-2">
            <span className="text-gray-500">{key}: </span>
            {renderObjectWithDiff(value, path, changedPaths, highlightColor)}
            {i < arr.length - 1 ? "," : ""}
          </div>
        );
      })}
      {"}"}
    </span>
  );
}

const columns = [
  columnHelper.accessor("TYPE", {
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

  columnHelper.accessor("form_name", {
    header: "Form",
    cell: (info) => (
      <Link
        href={`https://3w.humanitarianaction.info/app#form/${info.row.original.form_id}/display`}
        target="_blank"
        className="flex flex-row justify-between items-center w-full"
      >
        {info.getValue()}
        <Icon icon="share" size={10} />
      </Link>
    ),
  }),

  columnHelper.accessor("field_code", {
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

  columnHelper.accessor("old", {
    header: "Old schema",
    cell: (info) => {
      const changedPaths = getChangedPaths(
        info.getValue(),
        info.row.original.new,
      );
      return (
        <div className="flex flex-col gap-0.5 text-[10px] font-mono">
          {renderObjectWithDiff(info.getValue(), "", changedPaths, "red")}
        </div>
      );
    },
  }),

  columnHelper.accessor("new", {
    header: "New schema",
    cell: (info) => {
      const changedPaths = getChangedPaths(
        info.row.original.old,
        info.getValue(),
      );
      return (
        <div className="flex flex-col gap-0.5 text-[10px] font-mono">
          {renderObjectWithDiff(info.getValue(), "", changedPaths, "green")}
        </div>
      );
    },
  }),
];

export default function FieldActionsTable({
  fieldActions,
}: {
  fieldActions: FieldAction[];
}) {
  const table = useReactTable({
    data: fieldActions,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="flex-1 min-h-0 h-full overflow-y-auto pb-14">
      <HTMLTable bordered compact striped className="w-full">
        <thead className="sticky top-0 bg-white z-10">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((h) => (
                <th key={h.id}>
                  {flexRender(h.column.columnDef.header, h.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody className="overflow-y-scroll h-full">
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id}>
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="text-xs align-top">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </HTMLTable>
    </div>
  );
}
