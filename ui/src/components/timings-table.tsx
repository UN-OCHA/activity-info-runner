import { HTMLTable } from "@blueprintjs/core";
import { format } from "date-fns";
import type { WorkflowRun } from "../types";

export default function TimingsTable({
  timings,
}: {
  timings: WorkflowRun["timings"];
}) {
  if (!timings) {
    return <div className="p-3 text-gray-500">No timing data available.</div>;
  }

  // Sort timings by start time
  const sortedTimings = [...timings].sort(
    (a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
  );

  return (
    <div className="flex-1 min-h-0 overflow-auto">
      <HTMLTable compact striped className="w-full">
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Start Time</th>
            <th>End Time</th>
            <th>Duration (s)</th>
          </tr>
        </thead>
        <tbody>
          {sortedTimings.map((timing, i) => (
            <tr key={i}>
              <td>
                <code>{timing.name}</code>
              </td>
              <td>
                <span
                  className={`bp5-tag ${
                    timing.type === "workflow" ? "bp5-intent-primary" : ""
                  }`}
                >
                  {timing.type}
                </span>
              </td>
              <td>{format(new Date(timing.start_time), "yyyy-MM-dd HH:mm:ss")}</td>
              <td>
                {timing.end_time
                  ? format(new Date(timing.end_time), "yyyy-MM-dd HH:mm:ss")
                  : "-"}
              </td>
              <td className="font-mono text-right">
                {timing.duration_seconds
                  ? Number(timing.duration_seconds).toFixed(2)
                  : "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </HTMLTable>
    </div>
  );
}
