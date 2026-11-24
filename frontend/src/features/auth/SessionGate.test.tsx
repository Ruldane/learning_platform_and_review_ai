import { useQuery } from "@tanstack/react-query";
import { act, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { api, apiBaseUrl } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import { onLocalReset } from "@/shared/lib/localReset";
import { authApi, authRequired, camille, dominique, errorBody } from "@/test/authApi";
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
    expect(screen.getByRole("status")).toHaveTextContent("Checking your sign-in…");
    expect(await screen.findByText("Chemin : /")).toBeInTheDocument();
  });

  it("gate redirects to /connexion on 401", async () => {
    const api401 = authApi({ me: null });
    server.use(...api401.handlers);
    const { visited } = renderAuth("/");
    await waitFor(() => expect(screen.getByRole("heading", { name: "Sign in" })).toHaveFocus());
    expect(screen.queryByText("Chemin : /")).toBeNull();
    expect(visited).toEqual(["/", "/connexion"]);
  });

  it("gate shows a retryable error when me fails for another reason", async () => {
    const failing = authApi({ me: camille, meFails: true });
    server.use(...failing.handlers);
    const { user } = renderAuth("/");
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Sign in" })).toBeNull();
    server.use(...authApi({ me: camille }).handlers);
    await user.click(screen.getByRole("button", { name: "Retry" }));
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
    await waitFor(() => expect(screen.getByRole("heading", { name: "Sign in" })).toHaveFocus());
    await settle();
    // Une seule redirection malgré deux 401 : la porte ne relit pas `me` (il répondrait 401, donc
    // émettrait de nouveau) et la page de connexion ne renvoie pas vers la porte.
    expect(visited).toEqual(["/", "/connexion"]);
    expect(session.meCalls).toBe(1);
    expect(screen.getByRole("link", { name: "Sign in with Google" })).toBeInTheDocument();
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
    await screen.findByRole("heading", { name: "Sign in" });
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
  it("a 401 mid-session also empties what the features keep outside the query cache", async () => {
    const reset = vi.fn();
    onLocalReset(reset);
    server.use(
      ...authApi({ me: camille }).handlers,
      http.get(`${apiBaseUrl}/api/v1/health`, () =>
        HttpResponse.json(authRequired, { status: 401 }),
      ),
    );
    renderAuth("/", <Probes />);
    await screen.findByRole("heading", { name: "Sign in" });
    expect(reset).toHaveBeenCalled();
  });

  describe("when the tab comes back to the front", () => {
    const show = () => {
      Object.defineProperty(document, "visibilityState", { value: "visible", configurable: true });
      act(() => {
        document.dispatchEvent(new Event("visibilitychange"));
      });
    };

    it("reads me again, and drops everything the other account had read", async () => {
      server.use(...authApi({ me: camille }).handlers);
      const { client } = renderAuth("/");
      await screen.findByText("Chemin : /");
      client.setQueryData(["settings"], { of: "camille" });
      const reset = vi.fn();
      onLocalReset(reset);
      // Dans un autre onglet : déconnexion de Camille, puis connexion de Dominique.
      server.use(...authApi({ me: dominique }).handlers);
      show();
      await waitFor(() => expect(client.getQueryData(["auth", "me"])).toEqual(dominique));
      expect(client.getQueryData(["settings"])).toBeUndefined();
      expect(reset).toHaveBeenCalledTimes(1);
      expect(screen.getByText("Chemin : /")).toBeInTheDocument();
    });

    it("keeps everything when it is still the same account", async () => {
      const session = authApi({ me: camille });
      server.use(...session.handlers);
      const { client } = renderAuth("/");
      await screen.findByText("Chemin : /");
      client.setQueryData(["settings"], { of: "camille" });
      show();
      await waitFor(() => expect(session.meCalls).toBe(2));
      await settle();
      expect(client.getQueryData(["settings"])).toEqual({ of: "camille" });
    });

    it("leads to /connexion when the session ended in the other tab", async () => {
      server.use(...authApi({ me: camille }).handlers);
      const { client, visited } = renderAuth("/");
      await screen.findByText("Chemin : /");
      client.setQueryData(["settings"], { of: "camille" });
      server.use(...authApi({ me: null }).handlers);
      show();
      await screen.findByRole("heading", { name: "Sign in" });
      expect(client.getQueryData(["settings"])).toBeUndefined();
      expect(visited).toEqual(["/", "/connexion"]);
    });
  });
});
