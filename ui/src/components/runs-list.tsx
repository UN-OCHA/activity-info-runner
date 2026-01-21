import { Card, CardList, EntityTitle, Tag } from "@blueprintjs/core";
import TimeAgo from "react-timeago";
import type { WorkflowRun } from "../types";
import { titleCase } from "../utils";

// Helper to format duration in seconds as H:M:S or M:S
function formatDuration(seconds: number) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

export default function RunsList({
  runs,
  selectedId,
  setSelectedId,
}: {
  runs: WorkflowRun[];
  selectedId?: string;
  setSelectedId: (s: string) => void;
}) {
  return (
    <CardList compact className="h-full overflow-y-auto">
      {runs.map((run) => {
        const elapsedSeconds =
          run.start_time && run.close_time
            ? Math.round(
                (new Date(run.close_time).getTime() -
                  new Date(run.start_time).getTime()) /
                  1000,
              )
            : null;

        return (
          <Card
            key={run.run_id}
            selected={run.run_id == selectedId}
            interactive
            className="flex flex-row justify-between gap-4"
            onClick={() => setSelectedId(run.run_id)}
          >
            <EntityTitle
              icon="automatic-updates"
              title={
                <span className="font-bold">{titleCase(run.params.name)}</span>
              }
              subtitle={
                <>
                  On database{" "}
                  <span className="bp6-monospace-text">
                    {run.params.database_id}
                  </span>
                </>
              }
              tags={
                <Tag
                  minimal
                  intent={
                    run.status === "COMPLETED"
                      ? "success"
                      : run.status === "RUNNING"
                        ? "warning"
                        : run.status === "PENDING"
                          ? "none"
                          : "danger"
                  }
                  className="font-bold justify-self-start ml-auto"
                  icon={
                    run.status === "COMPLETED"
                      ? "tick"
                      : run.status === "RUNNING" || run.status === "PENDING"
                        ? "more"
                        : "cross"
                  }
                >
                  {run.status}
                </Tag>
              }
            />
            <div className="bp6-text-muted justify-self-end whitespace-nowrap text-right">
              <TimeAgo date={run.close_time ?? run.start_time} /> (
              {elapsedSeconds !== null ? formatDuration(elapsedSeconds) : "-"})
            </div>
          </Card>
        );
      })}
    </CardList>
  );
}
