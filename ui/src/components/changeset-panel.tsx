import {
  Button,
  ButtonGroup,
  EntityTitle,
  H6,
  NonIdealState,
  Spinner,
  Tab,
  TabPanel,
  Tabs,
  type TabId,
} from "@blueprintjs/core";
import { useQuery } from "@tanstack/react-query";
import { useId, useState } from "react";
import type { PanelImperativeHandle } from "react-resizable-panels";
import type { WorkflowRun } from "../types";
import { API_BASE, titleCase } from "../utils";
import ActionsTable from "./actions-view";
import BoundariesView from "./boundaries-view";
import LogsTable from "./logs-table";
import TimingsTimeline from "./timings-timeline";

export default function ChangesetPanel({
  workflowId,
  runId,
  panelRef,
}: {
  workflowId: string;
  runId: string;
  panelRef: PanelImperativeHandle | null;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["workflows", workflowId, runId],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/workflows/${workflowId}/${runId}`);
      return (await res.json()) as WorkflowRun;
    },
  });
  const TABS_PARENT_ID = useId();
  const [selectedTabId, setSelectedTabId] = useState<TabId>("actions");
  const hasResults = data?.results?.changeset.field_actions !== undefined;
  if (isLoading) {
    return (
      <div className="flex flex-col justify-center h-full">
        <Spinner />
      </div>
    );
  }
  return (
    <div className="h-full">
      <div className="px-3 py-2 flex flex-row items-center gap-3 justify-between border-b border-b-gray-200 w-full">
        <EntityTitle
          title={titleCase(data?.type ?? "")}
          subtitle="Result changeset"
          heading={H6}
          icon="changes"
        />
        {hasResults && (
          <>
            <Tabs
              id={TABS_PARENT_ID}
              className="flex flex-col flex-1 min-h-0 ml-3"
              onChange={setSelectedTabId}
              selectedTabId={selectedTabId}
            >
              <Tab
                id="actions"
                title="Actions"
                tagContent={
                  (data.results?.changeset.database_actions.length ?? 0) +
                  (data.results?.changeset.form_actions.length ?? 0) +
                  (data.results?.changeset.field_actions.length ?? 0) +
                  (data.results?.changeset.record_actions.length ?? 0)
                }
                icon="take-action"
                tagProps={{
                  minimal: false,
                }}
              />
              <Tab
                id="logs"
                title="Logs & Warnings"
                icon="outdated"
                tagContent={
                  (data?.results?.logs?.length ?? 0) +
                  (data?.results?.warnings?.length ?? 0)
                }
              />
              <Tab
                id="boundaries"
                title="Materialized Boundaries"
                icon="clip"
              />
              <Tab id="timings" title="Timings" icon="updated" />
            </Tabs>
            <ButtonGroup variant="outlined">
              <Button text="Validate" intent="success" icon="cloud-tick" />
              <Button text="Discard" intent="danger" icon="trash" />
            </ButtonGroup>
          </>
        )}
        <Button
          variant="minimal"
          icon={"collapse-all"}
          onClick={() => {
            panelRef?.isCollapsed() ? panelRef.expand() : panelRef?.collapse();
          }}
        />
      </div>
      {hasResults ? (
        <div className="h-full pb-12">
          <TabPanel
            id="actions"
            selectedTabId={selectedTabId}
            parentId={TABS_PARENT_ID}
            className="h-full mt-0!"
            panel={
              <ActionsTable
                changeset={data.results!.changeset}
                materializedBoundary={data.results?.materialized_boundary}
              />
            }
          />
          <TabPanel
            id="logs"
            selectedTabId={selectedTabId}
            parentId={TABS_PARENT_ID}
            className="h-full mt-0!"
            panel={
              <LogsTable
                logs={(data?.results?.logs ?? []).concat(
                  data.results?.warnings ?? [],
                )}
              />
            }
          />
          {data.results?.materialized_boundary && (
            <TabPanel
              id="boundaries"
              selectedTabId={selectedTabId}
              parentId={TABS_PARENT_ID}
              className="h-full mt-0!"
              panel={
                <BoundariesView
                  boundaries={data.results?.materialized_boundary}
                />
              }
            />
          )}
          <TabPanel
            id="timings"
            selectedTabId={selectedTabId}
            parentId={TABS_PARENT_ID}
            className="h-full mt-0!"
            panel={<TimingsTimeline timings={data?.timings ?? null} />}
          />
        </div>
      ) : (
        <NonIdealState
          icon="error"
          title="No changes"
          description="This run did not complete or did not produce a result changeset"
        />
      )}
    </div>
  );
}
