import { useQuery } from "@tanstack/react-query";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { api, apiBaseUrl } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import { authApi, authRequired, camille, errorBody } from "@/test/authApi";
import { server } from "@/test/server";
import { renderAuth } from "./authTestkit";

const settle = () => new Promise((resolve) => setTimeout(resolve, 60));

/** Deux lectures qui partent ensemble depuis la mise en page (une rafale de 401 possible). */
function Probes() {
  const first = useQuery({
    queryKey: ["probe", 1],
    queryFn: async () => unwrap(await api.GET("/health")),
    retry: false,
  });
  const second = useQuery({
    queryKey: ["probe", 2],
    queryFn: async () => unwrap(await api.GET("/health")),
    retry: false,
  });
  return <p>{first.isError || second.isError ? "Lecture refusée" : "Lecture en cours"}</p>;
}

describe("SessionGate", () => {
  it("gate renders children when signed in", async () => {
    server.use(...authApi({ me: camille }).handlers);
    renderAuth("/");
    expect(screen.getByRole("status")).toHaveTextContent("Vérification de ta connexion");
    expect(await screen.findByText("Chemin : /")).toBeInTheDocument();
  });

  it("gate redirects to /connexion on 401", async () => {
    const api401 = authApi({ me: null });
    server.use(...api401.handlers);
    const { visited } = renderAuth("/");
    await waitFor(() => expect(screen.getByRole("heading", { name: "Connexion" })).toHaveFocus());
    expect(screen.queryByText("Chemin : /")).toBeNull();
    expect(visited).toEqual(["/", "/connexion"]);
  });

  it("gate shows a retryable error when me fails for another reason", async () => {
    const failing = authApi({ me: camille, meFails: true });
    server.use(...failing.handlers);
    const { user } = renderAuth("/");
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Connexion" })).toBeNull();
    server.use(...authApi({ me: camille }).handlers);
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByText("Chemin : /")).toBeInTheDocument();
  });

  it("a 401 mid-session leads once to /connexion", async () => {
    const session = authApi({ me: camille });
    server.use(
      ...session.handlers,
      http.get(`${apiBaseUrl}/api/v1/health`, () =>
        HttpResponse.json(authRequired, { status: 401 }),
      ),
    );
    const { visited } = renderAuth("/", <Probes />);
    await waitFor(() => expect(screen.getByRole("heading", { name: "Connexion" })).toHaveFocus());
    await settle();
    // Une seule redirection malgré deux 401 : la porte ne relit pas `me` (il répondrait 401, donc
    // émettrait de nouveau) et la page de connexion ne renvoie pas vers la porte.
    expect(visited).toEqual(["/", "/connexion"]);
    expect(session.meCalls).toBe(1);
    expect(screen.getByRole("link", { name: "Se connecter avec Google" })).toBeInTheDocument();
  });

  it("a 401 mid-session does not loop when me itself answers 401 afterwards", async () => {
    const session = authApi({ me: camille });
    server.use(
      ...session.handlers,
      http.get(`${apiBaseUrl}/api/v1/health`, () => {
        // La session a expiré côté serveur : `me` ne répond plus 200 non plus.
        server.use(...authApi({ me: null }).handlers);
        return HttpResponse.json(authRequired, { status: 401 });
      }),
    );
    const { visited, client } = renderAuth("/", <Probes />);
    await screen.findByRole("heading", { name: "Connexion" });
    await client.refetchQueries({ queryKey: ["auth", "me"] });
    await settle();
    expect(visited).toEqual(["/", "/connexion"]);
  });

  it("ignores other 401 codes: only auth_required opens the login", async () => {
    server.use(
      ...authApi({ me: camille }).handlers,
      http.get(`${apiBaseUrl}/api/v1/health`, () =>
        HttpResponse.json(errorBody("bad_token", "Jeton refusé."), { status: 401 }),
      ),
    );
    const { visited } = renderAuth("/", <Probes />);
    expect(await screen.findByText("Lecture refusée")).toBeInTheDocument();
    await waitFor(() => expect(visited).toEqual(["/"]));
  });
});
