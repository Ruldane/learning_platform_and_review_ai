import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { onLocalReset } from "@/shared/lib/localReset";
import { authApi, camille, localMe } from "@/test/authApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { AccountMenuSlot } from "./AccountMenuSlot";
import { renderAuth } from "./authTestkit";

describe("AccountMenuSlot", () => {
  it("account menu hidden in local mode", async () => {
    const api = authApi({ me: localMe });
    server.use(...api.handlers);
    render(<AccountMenuSlot />, { wrapper: createQueryWrapper() });
    // `me` est lu : en mode local le menu n'a rien à montrer.
    await waitFor(() => expect(api.meCalls).toBe(1));
    await new Promise((resolve) => setTimeout(resolve, 30));
    expect(screen.queryByRole("group", { name: "Compte" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Se déconnecter" })).toBeNull();
  });

  it("shows the signed-in address in Google mode", async () => {
    server.use(...authApi({ me: camille }).handlers);
    render(<AccountMenuSlot />, { wrapper: createQueryWrapper() });
    expect(await screen.findByRole("group", { name: "Compte" })).toHaveTextContent(
      "camille.exemple@example.org",
    );
  });

  it("logout returns to /connexion", async () => {
    const api = authApi({ me: camille });
    server.use(...api.handlers);
    const { user, visited } = renderAuth("/", <AccountMenuSlot />);
    await user.click(await screen.findByRole("button", { name: "Se déconnecter" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Connexion" })).toHaveFocus());
    expect(api.logoutCalls).toBe(1);
    expect(visited).toEqual(["/", "/connexion"]);
  });

  it("logout clears what the account had read, but not the session state", async () => {
    server.use(...authApi({ me: camille }).handlers);
    const { user, client } = renderAuth("/", <AccountMenuSlot />);
    client.setQueryData(["settings"], { secret: true });
    await user.click(await screen.findByRole("button", { name: "Se déconnecter" }));
    await screen.findByRole("heading", { name: "Connexion" });
    expect(client.getQueryData(["settings"])).toBeUndefined();
    expect(client.getQueryData(["auth", "me"])).toBeNull();
  });

  it("logout also empties what the features keep outside the query cache", async () => {
    const reset = vi.fn();
    onLocalReset(reset);
    server.use(...authApi({ me: camille }).handlers);
    const { user } = renderAuth("/", <AccountMenuSlot />);
    await user.click(await screen.findByRole("button", { name: "Se déconnecter" }));
    await screen.findByRole("heading", { name: "Connexion" });
    expect(reset).toHaveBeenCalledTimes(1);
  });

  it("stays signed in and says so when logout fails", async () => {
    server.use(...authApi({ me: camille }).handlers);
    const { user, router } = renderAuth("/", <AccountMenuSlot />);
    server.use(
      http.post(`${apiBaseUrl}/api/v1/auth/logout`, () => new HttpResponse(null, { status: 500 })),
    );
    await user.click(await screen.findByRole("button", { name: "Se déconnecter" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("La déconnexion a échoué.");
    expect(router.state.location.pathname).toBe("/");
    expect(screen.getByRole("button", { name: "Se déconnecter" })).toBeInTheDocument();
  });
});
