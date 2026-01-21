import { BlueprintProvider } from "@blueprintjs/core";
import { QueryClientProvider } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import { queryClient } from "./utils.tsx";

createRoot(document.getElementById("root")!).render(
  // <StrictMode>
  <QueryClientProvider client={queryClient}>
    <BlueprintProvider>
      <App />
    </BlueprintProvider>
  </QueryClientProvider>,
  // </StrictMode>,
);
