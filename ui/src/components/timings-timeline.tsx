import { Position, Tooltip } from "@blueprintjs/core";
import { differenceInMilliseconds, format } from "date-fns";
import type { WorkflowRun } from "../types";

export default function TimingsTimeline({
  timings,
}: {
  timings: WorkflowRun["timings"];
}) {
  if (!timings || timings.length === 0) {
    return <div className="p-3 text-gray-500">No timing data available.</div>;
  }

  // Convert strings to Dates and find bounds
  const processedTimings = timings.map((t) => ({
    ...t,
    startDate: new Date(t.start_time),
    endDate: t.end_time ? new Date(t.end_time) : new Date(), // Use now if running? Or just start time
  }));

  const minTime = Math.min(
    ...processedTimings.map((t) => t.startDate.getTime()),
  );
  const maxTime = Math.max(...processedTimings.map((t) => t.endDate.getTime()));
  const totalDuration = maxTime - minTime;

  // Helper to calculate percent position/width
  const getPosition = (start: Date, end: Date) => {
    if (totalDuration === 0) return { left: "0%", width: "100%" };
    const startOffset = start.getTime() - minTime;
    const duration = end.getTime() - start.getTime();
    return {
      left: `${(startOffset / totalDuration) * 100}%`,
      width: `${Math.max((duration / totalDuration) * 100, 0.5)}%`, // Min width for visibility
    };
  };

  // Sort by start time for the waterfall effect
  const sortedTimings = [...processedTimings].sort(
    (a, b) => a.startDate.getTime() - b.startDate.getTime(),
  );

  return (
    <div className="flex-1 min-h-0 overflow-auto p-4">
      <div className="flex flex-col gap-2">
        <div className="flex justify-between text-xs text-gray-400 mb-2 border-b border-gray-200 pb-1">
          <span>{format(minTime, "HH:mm:ss.SSS")}</span>
          <span>Duration: {(totalDuration / 1000).toFixed(2)}s</span>
          <span>{format(maxTime, "HH:mm:ss.SSS")}</span>
        </div>

        {sortedTimings.map((timing, i) => {
          const { left, width } = getPosition(timing.startDate, timing.endDate);
          const isWorkflow = timing.type === "workflow";
          const colorClass = isWorkflow ? "bg-blue-500" : "bg-blue-200";
          const label = timing.name;
          const durationSec = (
            differenceInMilliseconds(timing.endDate, timing.startDate) / 1000
          ).toFixed(2);

          return (
            <div key={i} className="flex items-center gap-4 text-sm group">
              <div
                className="w-xs shrink-0 truncate text-right font-mono text-xs text-gray-600"
                title={label}
              >
                {label}
              </div>
              <div className="grow relative rounded-sm h-5">
                <Tooltip
                  content={
                    <div className="text-xs">
                      <div className="font-bold">{label}</div>
                      <div>
                        Start: {format(timing.startDate, "HH:mm:ss.SSS")}
                      </div>
                      <div>End: {format(timing.endDate, "HH:mm:ss.SSS")}</div>
                      <div>Duration: {durationSec}s</div>
                    </div>
                  }
                  position={Position.BOTTOM}
                >
                  <div
                    className={`top-0 absolute h-full rounded opacity-80 hover:opacity-100 transition-opacity cursor-pointer ${colorClass} ${isWorkflow ? "opacity-40" : ""}`}
                    style={{ left, width }}
                  />
                </Tooltip>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
