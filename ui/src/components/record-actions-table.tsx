import { HTMLTable, Icon, Link, Tag } from "@blueprintjs/core";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import type { RecordAction } from "../types";

const columnHelper = createColumnHelper<RecordAction>();

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
    header: "Form name",
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

  columnHelper.accessor("record_id", {
    header: "Record",
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

  columnHelper.accessor("old_field_value", {
    header: "Old value",
    cell: (info) => (
      <span className="text-red-600 font-bold">{info.getValue() ?? "—"}</span>
    ),
  }),

  columnHelper.accessor("field_value", {
    header: "New value",
    cell: (info) => (
      <span className="text-green-600 font-bold">{info.getValue() ?? "—"}</span>
    ),
  }),
];

export default function RecordActionsTable({
  recordActions,
}: {
  recordActions: RecordAction[];
}) {
  const table = useReactTable({
    data: recordActions,
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
                <td key={cell.id} className="text-xs">
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
