import {
  Button,
  Dialog,
  DialogBody,
  DialogFooter,
  FormGroup,
  InputGroup,
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
    queryKey: ["scripts"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/scripts`);
      return (await res.json()) as string[];
    },
  });
  const { mutate } = useMutation({
    mutationFn: async () =>
      await fetch(
        `${API_BASE}/workflows/${scriptName}?database_id=${databaseId}`,
        {
          method: "POST",
        },
      ),
    onSuccess: () => {
      setOpen(false);
      queryClient.invalidateQueries({
        queryKey: ["workflows"],
      });
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
      >
        <DialogBody>
          <FormGroup
            label="Database ID"
            labelFor="database-id-input"
            helperText="The ActivityInfo database ID for which to execute the script"
          >
            <InputGroup
              id="database-id-input"
              placeholder="Enter ID here..."
              value={databaseId}
              onValueChange={setDatabaseId}
            />
          </FormGroup>
          {data && (
            <FormGroup
              label="Script name"
              labelFor="database-id-input"
              helperText="The script to run for the selected database"
            >
              <Select
                activeItem={scriptName}
                items={data}
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
            />,
          ]}
        />
      </Dialog>
    </>
  );
}
