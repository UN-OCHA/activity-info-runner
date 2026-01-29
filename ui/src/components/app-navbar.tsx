import {
  Alignment,
  Button,
  Icon,
  Navbar,
  NavbarDivider,
  NavbarGroup,
  NavbarHeading,
} from "@blueprintjs/core";
import { useLocation, useNavigate } from "slim-react-router";
import RunScriptDialog from "./run-script-dialog";
import UserMenu from "./user-menu";
import WorkerStatusIndicator from "./worker-status";

export default function AppNavbar() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
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
        <div className="flex flex-row gap-2">
          <Button
            variant="minimal"
            icon="home"
            text="Workflow runs"
            active={pathname == "/"}
            onClick={() => navigate("/")}
          />
          {/* <Button
            disabled
            variant="minimal"
            icon="graph"
            text="Database graph"
            active={pathname == "/graph"}
            onClick={() => navigate("/graph")}
          /> */}
        </div>
      </NavbarGroup>
      <NavbarGroup align={Alignment.END}>
        <WorkerStatusIndicator />
        <NavbarDivider />
        <RunScriptDialog />
        <NavbarDivider />
        <UserMenu />
      </NavbarGroup>
    </Navbar>
  );
}
