import { useAuth0 } from "@auth0/auth0-react";
import {
  Button,
  Menu,
  MenuDivider,
  MenuItem,
  Popover,
} from "@blueprintjs/core";

export default function UserMenu() {
  const { user, isLoading, logout } = useAuth0();
  return (
    <Popover
      interactionKind="click"
      placement="bottom"
      minimal
      content={
        <Menu>
          <MenuItem text={user?.name} disabled className="py-0!" />
          <MenuItem
            text={user?.email}
            disabled
            className="text-xs bp6-monospace-text py-0!"
          />
          <MenuDivider />
          <MenuItem
            text="Sign out"
            intent="danger"
            icon="log-out"
            onClick={() => logout()}
          />
        </Menu>
      }
      renderTarget={({ isOpen, ...targetProps }) => (
        <Button
          {...targetProps}
          icon="user"
          variant="minimal"
          // text={user?.user?.full_name}
          className="gap-3"
          loading={isLoading}
        />
      )}
    />
  );
}
