import {
  Button,
  Dialog,
  DialogBody,
  DialogFooter,
  FormGroup,
  MenuItem,
} from "@blueprintjs/core";
import { Select } from "@blueprintjs/select";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { API_BASE, queryClient, titleCase, toaster } from "../utils";

export default function RunScriptDialog() {
  const [open, setOpen] = useState(false);
  const [databaseId, setDatabaseId] = useState<string | undefined>(undefined);
  const [scriptName, setScriptName] = useState<string | undefined>(undefined);
  const { data } = useQuery({
    queryKey: ["entities"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/entities`);
      return (await res.json()) as {
        scripts: string[];
        databases: {
          databaseId: string;
          label: string;
          description: string;
        }[];
      };
    },
  });

  const effectiveDatabaseId = databaseId ?? data?.databases[0]?.databaseId;

  const { mutate } = useMutation({
    mutationFn: async () =>
      await fetch(
        `${API_BASE}/workflows/${scriptName}?database_id=${effectiveDatabaseId}`,
        {
          method: "POST",
        },
      ),
    onSuccess: () => {
      setOpen(false);
      queryClient.invalidateQueries({
        queryKey: ["workflows"],
      });
      setScriptName(undefined);
      toaster.show({
        message: "Script started successfully",
        intent: "success",
        icon: "run-history",
      });
    },
    onError: () => {
      toaster.show({
        message: "Script could not be queued",
        intent: "danger",
        icon: "run-history",
      });
    },
  });
  const activeDatabase = data?.databases.find(
    (d) => d.databaseId === effectiveDatabaseId,
  );

  return (
    <>
      <Button
        icon="run-history"
        text="Run script"
        intent="primary"
        onClick={() => setOpen(true)}
      />
      <Dialog
        isOpen={open}
        onClose={() => setOpen(false)}
        title="Run script"
        icon="run-history"
        lazy
      >
        <DialogBody>
          <FormGroup
            label="Database"
            helperText="The ActivityInfo database for which to execute the script"
          >
            <Select
              activeItem={activeDatabase}
              items={data?.databases ?? []}
              itemRenderer={(item, { handleClick, handleFocus, modifiers }) => {
                if (!modifiers.matchesPredicate) {
                  return null;
                }
                return (
                  <MenuItem
                    active={modifiers.active}
                    disabled={modifiers.disabled}
                    key={item.databaseId}
                    text={item.label}
                    onClick={handleClick}
                    onFocus={handleFocus}
                    roleStructure="listoption"
                    label={item.description}
                  />
                );
              }}
              onItemSelect={(item) => {
                setDatabaseId(item.databaseId);
              }}
            >
              <Button
                text={
                  activeDatabase ? activeDatabase.label : "Select a database"
                }
                endIcon="double-caret-vertical"
                alignText="start"
                fill
              />
            </Select>
          </FormGroup>
          {data && (
            <FormGroup
              label="Script name"
              helperText="The script to run for the selected database"
            >
              <Select
                activeItem={scriptName}
                items={data.scripts}
                itemRenderer={(
                  item,
                  { handleClick, handleFocus, modifiers },
                ) => {
                  if (!modifiers.matchesPredicate) {
                    return null;
                  }
                  return (
                    <MenuItem
                      active={modifiers.active}
                      disabled={modifiers.disabled}
                      key={item}
                      text={titleCase(item)}
                      onClick={handleClick}
                      onFocus={handleFocus}
                      roleStructure="listoption"
                    />
                  );
                }}
                onItemSelect={(item) => {
                  setScriptName(item);
                }}
              >
                <Button
                  text={
                    scriptName ? titleCase(scriptName) : "Select a script type"
                  }
                  endIcon="double-caret-vertical"
                  alignText="start"
                  fill
                />
              </Select>
            </FormGroup>
          )}
        </DialogBody>
        <DialogFooter
          actions={[
            <Button text="Cancel" onClick={() => setOpen(false)} />,
            <Button
              icon="play"
              text="Submit"
              intent="primary"
              onClick={() => mutate()}
              disabled={
                effectiveDatabaseId === undefined || scriptName === undefined
              }
            />,
          ]}
        />
      </Dialog>
    </>
  );
}
