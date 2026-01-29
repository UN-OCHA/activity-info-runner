import { NonIdealState } from "@blueprintjs/core";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  Group,
  Panel,
  Separator,
  usePanelCallbackRef,
} from "react-resizable-panels";
import "../app.css";
import AppNavbar from "../components/app-navbar";
import ChangesetPanel from "../components/changeset-panel";
import RunsList from "../components/runs-list";
import type { WorkflowRun } from "../types";
import { API_BASE } from "../utils";

function Home() {
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);
  const [changesetPanelRef, setChangesetPanelRef] = usePanelCallbackRef();
  const { data } = useQuery({
    queryKey: ["workflows"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/workflows`);
      return (await res.json()) as WorkflowRun[];
    },
    refetchInterval: 5000,
  });
  const selectedData = data?.filter((d) => d.run_id === selectedId)?.[0];
  return (
    <div className="flex flex-col h-screen">
      <AppNavbar />
      <Group orientation="vertical" className="flex-1 min-h-0">
        <Panel minSize="20%">
          {data ? (
            <RunsList
              runs={data}
              selectedId={selectedId}
              setSelectedId={setSelectedId}
            />
          ) : (
            <div className="flex flex-col items-center h-full">
              <NonIdealState
                title="No running scripts"
                description="Start a script to monitor its progress here"
                icon="info-sign"
              />
            </div>
          )}
        </Panel>
        <Separator className="border border-gray-200" />
        <Panel
          className="flex flex-col min-h-0"
          panelRef={setChangesetPanelRef}
          minSize={300}
          collapsedSize={50}
          collapsible
        >
          {selectedData ? (
            <ChangesetPanel
              workflowId={selectedData.workflow_id}
              runId={selectedData.run_id}
              panelRef={changesetPanelRef}
            />
          ) : (
            <NonIdealState
              title="No selection"
              icon="info-sign"
              description="Select a run above to inspect results"
            />
          )}
        </Panel>
      </Group>
    </div>
  );
}

export default Home;
