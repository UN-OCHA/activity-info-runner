import { Auth0Provider, useAuth0 } from "@auth0/auth0-react";
import { BlueprintProvider } from "@blueprintjs/core";
import { QueryClientProvider } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Switch } from "slim-react-router";
import Home from "./pages/Home.tsx";
import { queryClient } from "./utils.tsx";

createRoot(document.getElementById("root")!).render(
  // <StrictMode>
  <Auth0Provider
    domain={import.meta.env.VITE_AUTH0_DOMAIN}
    clientId={import.meta.env.VITE_AUTH0_CLIENT_ID}
    authorizationParams={{
      redirect_uri: window.location.origin,
    }}
  >
    <Root />,
  </Auth0Provider>,
  // </StrictMode>,
);

function Root() {
  const { isAuthenticated, loginWithRedirect, isLoading } = useAuth0();
  if (!isLoading && !isAuthenticated) loginWithRedirect();
  return (
    <QueryClientProvider client={queryClient}>
      <BlueprintProvider>
        <BrowserRouter>
          <Switch>
            <Route path="/" exact element={<Home />} />
          </Switch>
        </BrowserRouter>
      </BlueprintProvider>
    </QueryClientProvider>
  );
}
