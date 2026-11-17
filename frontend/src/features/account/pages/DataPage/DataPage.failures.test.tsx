import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { closedGate } from "@/test/settingsApi";
import { API } from "@/test/councilApi";
import { localMe } from "@/test/authApi";
import { server } from "@/test/server";
import { onLocalReset } from "@/shared/lib/localReset";
import { confirmAndDelete, deleteButton, setup, word } from "./dataPageTestkit";

describe("DataPage, failures and order of calls", () => {
  it("reads the mode first, then deletes", async () => {
    const order: string[] = [];
    const { user } = setup("local", { order });
    server.use(
      http.get(`${API}/auth/me`, () => {
        order.push("me");
        return HttpResponse.json(localMe);
      }),
    );
    await confirmAndDelete(user);
    await screen.findByText("Premier lancement");
    expect(order).toEqual(["me", "delete"]);
  });

  it("sends nothing when the mode cannot be read, and says nothing was deleted", async () => {
    const { user, deleteBodies } = setup("local", {}, { meFails: true });
    await confirmAndDelete(user);
    const message = await screen.findByTestId("delete-failure");
    expect(message).toHaveTextContent("Erreur.");
    expect(message).toHaveTextContent("Rien n'a été supprimé");
    expect(message).not.toHaveTextContent("reprend là où elle s'est arrêtée");
    expect(deleteBodies).toEqual([]);
    expect(word()).toHaveValue("SUPPRIMER");
  });

  it("says nothing was deleted when the memory is unavailable (503, before deleting)", async () => {
    const { user } = setup("local", { delete: "unavailable" });
    await confirmAndDelete(user);
    expect(await screen.findByTestId("delete-failure")).toHaveTextContent("Rien n'a été supprimé");
  });

  it("a network failure keeps the typed word, says it can be replayed, takes focus", async () => {
    const { user, router } = setup("local", { delete: "network" });
    await confirmAndDelete(user);
    const message = await screen.findByTestId("delete-failure");
    expect(message).toHaveTextContent("Impossible de joindre le serveur");
    expect(message).toHaveTextContent("reprend là où elle s'est arrêtée");
    await waitFor(() => expect(message).toHaveFocus());
    expect(word()).toHaveValue("SUPPRIMER");
    expect(router.state.location.pathname).toBe("/reglages/donnees");
  });

  it("a second validation in the same instant sends one deletion only", async () => {
    const held = closedGate();
    const { user, deleteBodies } = setup("local", { gate: held.promise });
    await user.type(word(), "SUPPRIMER");
    const form = word().closest("form")!;
    act(() => {
      fireEvent.submit(form);
      fireEvent.submit(form);
    });
    held.open();
    await screen.findByText("Premier lancement");
    expect(deleteBodies).toHaveLength(1);
  });

  it("announces the wait, and refuses a click while it lasts", async () => {
    const held = closedGate();
    const { user, deleteBodies } = setup("local", { gate: held.promise });
    await confirmAndDelete(user);
    expect(await screen.findByRole("status")).toHaveTextContent("Suppression en cours…");
    expect(deleteButton()).toHaveAttribute("aria-disabled", "true");
    await user.click(deleteButton());
    held.open();
    await screen.findByText("Premier lancement");
    expect(deleteBodies).toHaveLength(1);
  });

  it("drops a shown failure as soon as the word is edited", async () => {
    const { user } = setup("local", { delete: "refused" });
    await confirmAndDelete(user);
    await screen.findByTestId("delete-failure");
    expect(word()).toHaveAttribute("aria-invalid", "true");
    await user.type(word(), "X");
    expect(screen.queryByTestId("delete-failure")).toBeNull();
    expect(word()).not.toHaveAttribute("aria-invalid", "true");
  });

  it("empties what the modules keep outside the query cache, in both modes", async () => {
    const reset = vi.fn();
    onLocalReset(reset);
    const local = setup("local");
    await confirmAndDelete(local.user);
    await screen.findByText("Premier lancement");
    expect(reset).toHaveBeenCalledTimes(1);
  });

  it("empties it also in google mode", async () => {
    const reset = vi.fn();
    onLocalReset(reset);
    const google = setup("google");
    await confirmAndDelete(google.user);
    await waitFor(() => expect(google.client.getQueryData(["auth", "me"])).toBeNull());
    expect(reset).toHaveBeenCalledTimes(1);
  });

  it("tells the first launch the data are gone, through the navigation state", async () => {
    const { user, router } = setup("local");
    await confirmAndDelete(user);
    await screen.findByText("Premier lancement");
    expect(router.state.location.state).toEqual({ deleted: true });
  });
});
