import { Checkbox, HTMLTable, Icon } from "@blueprintjs/core";
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import React, { useState } from "react";

export default function GenericTable<T>({
  data,
  columns,
}: {
  data: T[];
  columns: ColumnDef<T, unknown>[];
}) {
  const [selectedTypes, setSelectedTypes] = useState<string[]>([
    "CREATE",
    "UPDATE",
    "DELETE",
  ]);
  const [sorting, setSorting] = useState<SortingState>([]);

  const hasTypeColumn = React.useMemo(
    () =>
      columns.some(
        (c) =>
          typeof c === "object" &&
          c !== null &&
          "accessorKey" in c &&
          c.accessorKey === "TYPE",
      ),
    [columns],
  );

  const filteredData = React.useMemo(() => {
    if (!hasTypeColumn) return data;
    return data.filter((d) => {
      const item = d as Record<string, unknown>;
      return typeof item.TYPE === "string" && selectedTypes.includes(item.TYPE);
    });
  }, [data, selectedTypes, hasTypeColumn]);

  const table = useReactTable({
    data: filteredData,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    state: {
      sorting,
    },
  });

  const toggleType = (type: string) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type],
    );
  };

  return (
    <div className="flex flex-col flex-1 min-h-0 h-full w-full">
      {hasTypeColumn && (
        <div className="flex flex-row gap-4 px-2 py-2 border-b border-gray-200 bg-gray-50 text-xs items-center sticky top-0 z-20">
          <span className="font-semibold text-gray-500 uppercase tracking-wider">
            Filter:
          </span>
          <Checkbox
            checked={selectedTypes.includes("CREATE")}
            onChange={() => toggleType("CREATE")}
            label="Create"
            className="mb-0!"
          />
          <Checkbox
            checked={selectedTypes.includes("UPDATE")}
            onChange={() => toggleType("UPDATE")}
            label="Update"
            className="mb-0!"
          />
          <Checkbox
            checked={selectedTypes.includes("DELETE")}
            onChange={() => toggleType("DELETE")}
            label="Delete"
            className="mb-0!"
          />
        </div>
      )}
      <div className="flex-1 min-h-0 overflow-y-auto pb-8">
        <HTMLTable bordered compact striped className="w-full">
          <thead className="sticky top-0 bg-white z-10">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => (
                  <th
                    key={h.id}
                    onClick={h.column.getToggleSortingHandler()}
                    className={
                      h.column.getCanSort()
                        ? "cursor-pointer select-none hover:bg-gray-100"
                        : ""
                    }
                  >
                    <div className="flex flex-row items-center gap-1">
                      {flexRender(h.column.columnDef.header, h.getContext())}
                      {{
                        asc: <Icon icon="sort-asc" size={12} />,
                        desc: <Icon icon="sort-desc" size={12} />,
                      }[h.column.getIsSorted() as string] ?? null}
                    </div>
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
    </div>
  );
}
