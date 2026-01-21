import { OverlayToaster, type Toaster } from "@blueprintjs/core";
import { QueryClient } from "@tanstack/react-query";

export const toaster: Toaster = await OverlayToaster.create({
  position: "bottom",
});

export const queryClient = new QueryClient();

export const titleCase = (s: string) =>
  s.replace(/^_*(.)|_+(.)/g, (_s, c, d) =>
    c ? c.toUpperCase() : " " + d.toUpperCase(),
  );
