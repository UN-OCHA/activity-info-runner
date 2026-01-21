import {
  Alignment,
  Button,
  Icon,
  Navbar,
  NavbarDivider,
  NavbarGroup,
  NavbarHeading,
} from "@blueprintjs/core";
import RunScriptDialog from "./run-script-dialog";

export default function AppNavbar() {
  return (
    <Navbar>
      <NavbarGroup align={Alignment.START}>
        <NavbarHeading className="flex flex-row items-center gap-2">
          <Icon icon="playbook" />
          <p className="mb-0!">
            <span className="font-black">ActivityInfo</span> Runner
          </p>
        </NavbarHeading>
        <NavbarDivider />
        <Button variant="minimal" icon="home" text="Workflow runs" />
      </NavbarGroup>
      <NavbarGroup align={Alignment.END}>
        <RunScriptDialog />
      </NavbarGroup>
    </Navbar>
  );
}
