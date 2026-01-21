import {
  Button,
  ButtonGroup,
  CompoundTag,
  EntityTitle,
  H5,
  Tab,
  TabPanel,
  Tabs,
  type TabId,
} from "@blueprintjs/core";
import { useQuery } from "@tanstack/react-query";
import { useId, useState } from "react";
import type { WorkflowRun } from "../types";
import { API_BASE, titleCase } from "../utils";
import FieldActionsTable from "./field-actions-table";
import LogsTable from "./logs-table";
import RecordActionsTable from "./record-actions-table";
import TimingsTimeline from "./timings-timeline";

export default function ChangesetPanel({
  workflowId,
  runId,
}: {
  workflowId: string;
  runId: string;
}) {
  const { data } = useQuery({
    queryKey: ["workflows", workflowId, runId],
    queryFn: async () => {
      const res = await fetch(
        `${API_BASE}/workflows/${workflowId}/${runId}`,
      );
      return (await res.json()) as WorkflowRun;
    },
  });
  const TABS_PARENT_ID = useId();
  const [selectedTabId, setSelectedTabId] = useState<TabId>("field");
  const created =
    (data?.results?.field_actions.filter((a) => a.TYPE === "CREATE").length ??
      0) +
    (data?.results?.record_actions.filter((a) => a.TYPE === "CREATE").length ??
      0);
  const updated =
    (data?.results?.field_actions.filter((a) => a.TYPE === "UPDATE").length ??
      0) +
    (data?.results?.record_actions.filter((a) => a.TYPE === "UPDATE").length ??
      0);
  const deleted =
    (data?.results?.field_actions.filter((a) => a.TYPE === "DELETE").length ??
      0) +
    (data?.results?.record_actions.filter((a) => a.TYPE === "DELETE").length ??
      0);
  return (
    <div className="h-full">
      <div className="px-3 py-2 flex flex-row items-center gap-3">
        <EntityTitle
          title={titleCase(data?.params.name ?? "")}
          subtitle="Result changeset"
          heading={H5}
          icon="changes"
        />
        <Tabs
          id={TABS_PARENT_ID}
          className="flex flex-col flex-1 min-h-0 ml-3"
          onChange={setSelectedTabId}
          selectedTabId={selectedTabId}
        >
          <Tab
            id="field"
            title="Field actions"
            tagContent={data?.results?.field_actions.length ?? "0"}
            icon="text-highlight"
            tagProps={{
              minimal: false,
            }}
          />
          <Tab
            id="records"
            title="Record actions"
            tagContent={data?.results?.record_actions.length ?? "0"}
            icon="th-derived"
            tagProps={{
              minimal: false,
            }}
          />
          <Tab
            id="logs"
            title="Logs"
            icon="outdated"
            tagContent={data?.results?.logs?.length ?? "0"}
          />
          <Tab id="timings" title="Timings" icon="updated" />
        </Tabs>
        <CompoundTag leftContent={created} intent="success" minimal>
          creations
        </CompoundTag>
        <CompoundTag leftContent={updated} intent="warning" minimal>
          updates
        </CompoundTag>
        <CompoundTag leftContent={deleted} intent="danger" minimal>
          deletions
        </CompoundTag>
        <ButtonGroup variant="outlined">
          <Button text="Validate" intent="success" icon="cloud-tick" />
          <Button text="Discard" intent="danger" icon="trash" />
        </ButtonGroup>
      </div>
      <TabPanel
        id={selectedTabId}
        selectedTabId={selectedTabId}
        parentId={TABS_PARENT_ID}
        className="h-full mt-0!"
        panel={
          selectedTabId === "field" ? (
            <FieldActionsTable
              fieldActions={data?.results?.field_actions ?? []}
            />
          ) : selectedTabId === "records" ? (
            <RecordActionsTable
              recordActions={data?.results?.record_actions ?? []}
            />
          ) : selectedTabId === "timings" ? (
            <TimingsTimeline timings={data?.timings ?? null} />
          ) : (
            <LogsTable logs={data?.results?.logs ?? []} />
          )
        }
      />
    </div>
  );
}
