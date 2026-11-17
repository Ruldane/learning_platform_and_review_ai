import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { authApi, camille, localMe } from "@/test/authApi";
import { server } from "@/test/server";
import { renderAuth } from "../../authTestkit";

const MESSAGES: [string, string][] = [
  ["access_denied", "Connexion annulée."],
  ["state_invalid", "La connexion a expiré, recommence."],
  ["email_not_allowed", "Ce compte n'est pas autorisé sur cette instance."],
  ["email_unverified", "Adresse Google non vérifiée."],
  ["google_unavailable", "Google ne répond pas, réessaie dans un instant."],
  ["token_invalid", "Réponse de Google refusée."],
  ["claim_expired", "Le choix de la reprise a expiré, reconnecte-toi."],
  ["local_already_claimed", "Les données de cet ordinateur sont déjà reprises par un compte."],
];

describe("LoginPage", () => {
  it.each(MESSAGES)("login error messages by code: %s", async (code, message) => {
    server.use(...authApi({ me: null }).handlers);
    renderAuth(`/connexion?erreur=${code}`);
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
  });

  it("login error messages by code: an unknown code gets the general message, never shown", async () => {
    server.use(...authApi({ me: null }).handlers);
    renderAuth("/connexion?erreur=%3Cb%3Ecode_inventé%3C%2Fb%3E");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("La connexion a échoué, réessaie.");
    expect(alert).not.toHaveTextContent("inventé");
  });

  it("login error messages by code: no code, no message; inherited keys are unknown", async () => {
    server.use(...authApi({ me: null }).handlers);
    renderAuth("/connexion?erreur=constructor");
    expect(await screen.findByRole("alert")).toHaveTextContent("La connexion a échoué");
  });

  it("shows the Google link and no alert without an error code", async () => {
    server.use(...authApi({ me: null }).handlers);
    renderAuth("/connexion");
    const link = await screen.findByRole("link", { name: "Se connecter avec Google" });
    expect(link).toHaveAttribute("href", "http://localhost:8000/api/v1/auth/google/login");
    expect(screen.queryByRole("alert")).toBeNull();
    await waitFor(() =>
      expect(screen.getByRole("heading", { level: 1, name: "Connexion" })).toHaveFocus(),
    );
  });

  it("sends the local mode back to the app", async () => {
    server.use(...authApi({ me: localMe }).handlers);
    renderAuth("/connexion");
    expect(await screen.findByText("Chemin : /")).toBeInTheDocument();
  });

  it("does not bounce a Google account back to the gate: it keeps showing the card", async () => {
    server.use(...authApi({ me: camille }).handlers);
    const { visited } = renderAuth("/connexion");
    expect(
      await screen.findByRole("link", { name: "Se connecter avec Google" }),
    ).toBeInTheDocument();
    expect(visited).toEqual(["/connexion"]);
  });

  it("offers a retry when the server cannot say which mode it runs", async () => {
    server.use(...authApi({ me: camille, meFails: true }).handlers);
    renderAuth("/connexion");
    expect(await screen.findByRole("button", { name: "Réessayer" })).toBeInTheDocument();
  });
});
