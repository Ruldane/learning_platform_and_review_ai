import { act, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { onLocalReset } from "@/shared/lib/localReset";
import { authApi, camille, dominique, errorBody } from "@/test/authApi";
import { API } from "@/test/councilApi";
import { server } from "@/test/server";
import { confirmAndDelete, deleteButton, setup, word } from "./dataPageTestkit";

describe("DataPage, the account changed in another tab", () => {
  it("sends nothing when the session now belongs to another account", async () => {
    const { user, client, deleteBodies, router } = setup("google");
    // L'onglet affiche Camille ; dans un autre onglet, Dominique s'est connecté.
    client.setQueryData(["auth", "me"], camille);
    client.setQueryData(["settings"], { of: "camille" });
    const reset = vi.fn();
    onLocalReset(reset);
    server.use(...authApi({ me: dominique }).handlers);

    await confirmAndDelete(user);

    const message = await screen.findByTestId("delete-failure");
    expect(message).toHaveTextContent("Le compte connecté a changé dans un autre onglet");
    expect(message).toHaveTextContent("Rien n'a été supprimé");
    expect(deleteBodies).toEqual([]);
    expect(client.getQueryData(["settings"])).toBeUndefined();
    expect(client.getQueryData(["auth", "me"])).toEqual(dominique);
    expect(reset).toHaveBeenCalledTimes(1);
    expect(router.state.location.pathname).toBe("/reglages/donnees");
    // La personne peut relire le message, puis recommencer pour le compte affiché maintenant.
    expect(word()).toBeInTheDocument();
  });

  it("sends nothing when the session ended, and leads to the login", async () => {
    const { user, client, deleteBodies } = setup("google");
    client.setQueryData(["auth", "me"], camille);
    server.use(...authApi({ me: null }).handlers);
    await confirmAndDelete(user);
    await vi.waitFor(() => expect(client.getQueryData(["auth", "me"])).toBeNull());
    expect(deleteBodies).toEqual([]);
  });

  it("deletes when the fresh read is the account that is displayed", async () => {
    const { user, client, deleteBodies } = setup("google");
    client.setQueryData(["auth", "me"], camille);
    await confirmAndDelete(user);
    await vi.waitFor(() => expect(deleteBodies).toHaveLength(1));
  });

  it("reads me without the cache just before sending", async () => {
    const { user, client, auth } = setup("google");
    client.setQueryData(["auth", "me"], camille);
    await confirmAndDelete(user);
    await vi.waitFor(() => expect(auth.meCalls).toBe(1));
  });

  it("clears the typed consent when auth updates before submit", async () => {
    const { user, client, deleteBodies } = setup("google");
    await user.type(word(), "SUPPRIMER");
    expect(deleteButton()).toBeEnabled();

    act(() => client.setQueryData(["auth", "me"], dominique));

    expect(await screen.findByText(/dominique\.exemple@example\.org/)).toBeVisible();
    expect(word()).toHaveValue("");
    expect(deleteButton()).toBeDisabled();
    expect(deleteBodies).toEqual([]);
  });

  it("sends the identity accepted in the form even if the cookie changes after me", async () => {
    const { user } = setup("google");
    const received: unknown[] = [];
    server.use(
      http.post(`${API}/account/delete`, async ({ request }) => {
        received.push(await request.json());
        server.use(...authApi({ me: dominique }).handlers);
        return HttpResponse.json(errorBody("account_changed"), { status: 409 });
      }),
    );

    await confirmAndDelete(user);

    expect(await screen.findByTestId("delete-failure")).toHaveTextContent(
      "Le compte connecté a changé dans un autre onglet",
    );
    expect(received).toEqual([{ confirm: "SUPPRIMER", expected_user_id: camille.id }]);
    expect(word()).toHaveValue("");
    expect(deleteButton()).toBeDisabled();
  });
});
