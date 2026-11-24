import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { camille, localMe } from "@/test/authApi";
import { confirmAndDelete, setup } from "./dataPageTestkit";

describe("DataPage", () => {
  it("shows the export link and the delete card under one heading", () => {
    setup("local");
    expect(screen.getByRole("heading", { level: 1, name: "My data" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Export all my data" })).toHaveAttribute(
      "href",
      `${apiBaseUrl}/api/v1/account/export`,
    );
  });

  it("delete sends confirm and goes to welcome in local mode", async () => {
    const { user, deleteBodies, router, client } = setup("local");
    await confirmAndDelete(user);
    await screen.findByText("Premier lancement");
    expect(deleteBodies).toEqual([{ confirm: "SUPPRIMER", expected_user_id: localMe.id }]);
    expect(router.state.location.pathname).toBe("/welcome");
    // Les réglages et le reste seront relus à neuf ; l'identité locale reste.
    expect(client.getQueryData(["settings"])).toBeUndefined();
    expect(client.getQueryData(["goals"])).toBeUndefined();
    expect(client.getQueryData(["auth", "me"])).toEqual(localMe);
  });

  it("delete goes to login in google mode", async () => {
    const { user, deleteBodies, client, router } = setup("google");
    await confirmAndDelete(user);
    await waitFor(() => expect(client.getQueryData(["auth", "me"])).toBeNull());
    expect(deleteBodies).toEqual([{ confirm: "SUPPRIMER", expected_user_id: camille.id }]);
    expect(client.getQueryData(["settings"])).toBeUndefined();
    // La porte de la coquille mène à /login dès que `me` est vide ; ici, aucune porte :
    // la page n'ordonne aucune navigation elle-même.
    expect(router.state.location.pathname).toBe("/settings/data");
  });

  it("closes the Google session when only the final vector purge remains", async () => {
    const { user, client } = setup("google", { delete: "pending" });
    await confirmAndDelete(user);
    await waitFor(() => expect(client.getQueryData(["auth", "me"])).toBeNull());
    expect(client.getQueryData(["settings"])).toBeUndefined();
  });

  it("422 shows field error", async () => {
    const { user, router } = setup("local", { delete: "refused" });
    await confirmAndDelete(user);
    const message = await screen.findByTestId("delete-failure");
    expect(message).toHaveTextContent("The confirmation word is wrong: type SUPPRIMER");
    expect(screen.getByLabelText("Type SUPPRIMER to confirm")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(router.state.location.pathname).toBe("/settings/data");
  });

  it("shows its own wording for a refused confirmation, never the server text", async () => {
    const { user } = setup("local", { delete: "refused" });
    await confirmAndDelete(user);
    const message = await screen.findByTestId("delete-failure");
    expect(message.textContent).not.toContain("La confirmation n'est pas exacte.");
  });

  it("focus moves to result message", async () => {
    const { user } = setup("local", { delete: "down" });
    await confirmAndDelete(user);
    const message = await screen.findByTestId("delete-failure");
    expect(message).toHaveTextContent("La mémoire ne répond pas.");
    expect(message).toHaveTextContent("You can retry");
    await waitFor(() => expect(message).toHaveFocus());
    expect(screen.getByLabelText("Type SUPPRIMER to confirm")).not.toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });

  it("another 422 code is a plain error, not a field error", async () => {
    const { user } = setup("local", { delete: "wrong-code" });
    await confirmAndDelete(user);
    const message = await screen.findByTestId("delete-failure");
    expect(message).toHaveTextContent("Requête refusée.");
    expect(screen.getByLabelText("Type SUPPRIMER to confirm")).not.toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });
});
