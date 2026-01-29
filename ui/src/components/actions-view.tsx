import {
  Divider,
  EntityTitle,
  H6,
  NonIdealState,
  Tab,
  TabPanel,
  Tabs,
  type IconName,
  type TabId,
} from "@blueprintjs/core";
import React from "react";
import { Group, Panel } from "react-resizable-panels";
import type { Changeset, MaterializedBoundary } from "../types";
import {
  databaseColumns,
  formColumns,
  getFieldColumns,
  getRecordColumns,
} from "./action-columns";
import GenericTable from "./generic-table";

export default function ActionsView({
  changeset,
  materializedBoundary,
}: {
  changeset: Changeset;
  materializedBoundary?: MaterializedBoundary;
}) {
  const TABS_PARENT_ID = React.useId();
  const [selectedTabId, setSelectedTabId] = React.useState<TabId>("db");

  const recordColumns = React.useMemo(
    () => getRecordColumns(materializedBoundary),
    [materializedBoundary],
  );
  const fieldColumns = React.useMemo(
    () => getFieldColumns(materializedBoundary),
    [materializedBoundary],
  );

  const tabs = [
    {
      id: "db",
      title: "Database",
      icon: "database" as IconName,
      data: changeset.database_actions,
      columns: databaseColumns,
      noun: "databases",
    },
    {
      id: "form",
      title: "Form",
      icon: "form" as IconName,
      data: changeset.form_actions,
      columns: formColumns,
      noun: "forms",
    },
    {
      id: "field",
      title: "Field",
      icon: "text-highlight" as IconName,
      data: changeset.field_actions,
      columns: fieldColumns,
      noun: "fields",
    },
    {
      id: "record",
      title: "Record",
      icon: "th-derived" as IconName,
      data: changeset.record_actions,
      columns: recordColumns,
      noun: "records",
    },
  ];

  return (
    <Group className="h-full">
      <Panel
        minSize={145}
        defaultSize={145}
        className="p-2 flex flex-col gap-2"
      >
        <EntityTitle title="Action type" heading={H6} />
        <Tabs
          id={TABS_PARENT_ID}
          onChange={setSelectedTabId}
          selectedTabId={selectedTabId}
          vertical
          fill
        >
          {tabs.map((tab) => (
            <Tab
              key={tab.id}
              id={tab.id}
              title={tab.title}
              icon={tab.icon}
              tagContent={tab.data.length}
            />
          ))}
        </Tabs>
      </Panel>
      <Divider />
      <Panel>
        {tabs.map((tab) => (
          <TabPanel
            key={tab.id}
            id={tab.id}
            selectedTabId={selectedTabId}
            parentId={TABS_PARENT_ID}
            className="mt-1!"
            panel={
              tab.data.length === 0 ? (
                <NonIdealState
                  title={`No ${tab.title.toLowerCase()} actions`}
                  icon="info-sign"
                  description={`This script did not emit any changes to ${tab.noun}`}
                />
              ) : (
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                <GenericTable data={tab.data} columns={tab.columns as any} />
              )
            }
          />
        ))}
      </Panel>
    </Group>
  );
}
