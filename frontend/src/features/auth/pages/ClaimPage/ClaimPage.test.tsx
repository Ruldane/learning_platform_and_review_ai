import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { authApi, camille } from "@/test/authApi";
import { server } from "@/test/server";
import { renderAuth } from "../../authTestkit";

const TAKE = "Reprendre les données de cet ordinateur";

describe("ClaimPage", () => {
  it("claim take_local then home", async () => {
    const api = authApi({ me: null, claim: camille });
    server.use(...api.handlers);
    const { user, visited } = renderAuth("/connexion/reprise");
    expect(screen.getByRole("heading", { name: "Reprendre tes données ?" })).toHaveFocus();
    await user.click(screen.getByRole("button", { name: TAKE }));
    expect(await screen.findByText("Chemin : /")).toBeInTheDocument();
    expect(api.claimBodies).toEqual([{ choice: "take_local" }]);
    // `me` vient de la réponse du choix : la porte s'ouvre sans une relecture qui échouerait.
    expect(visited).toEqual(["/connexion/reprise", "/"]);
    expect(api.meCalls).toBe(0);
  });

  it("claim fresh sends the other choice", async () => {
    const api = authApi({ me: null, claim: camille });
    server.use(...api.handlers);
    const { user } = renderAuth("/connexion/reprise");
    await user.click(screen.getByRole("button", { name: "Commencer un espace vide" }));
    expect(await screen.findByText("Chemin : /")).toBeInTheDocument();
    expect(api.claimBodies).toEqual([{ choice: "fresh" }]);
  });

  it("claim expired returns to login", async () => {
    server.use(...authApi({ me: null, claim: { conflict: "claim_expired" } }).handlers);
    const { user, router } = renderAuth("/connexion/reprise");
    await user.click(screen.getByRole("button", { name: TAKE }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Le choix de la reprise a expiré, reconnecte-toi.",
    );
    expect(router.state.location.pathname).toBe("/connexion");
    await waitFor(() => expect(screen.getByRole("heading", { name: "Connexion" })).toHaveFocus());
  });

  it("claim already taken returns to login with its own message", async () => {
    server.use(...authApi({ me: null, claim: { conflict: "local_already_claimed" } }).handlers);
    const { user } = renderAuth("/connexion/reprise");
    await user.click(screen.getByRole("button", { name: TAKE }));
    expect(await screen.findByRole("alert")).toHaveTextContent("déjà reprises par un compte");
  });

  it("claim replayed by the person who just took the space lets them in", async () => {
    // Deuxième envoi (double clic, deuxième onglet) : la session est déjà ouverte.
    const api = authApi({ me: camille, claim: { conflict: "local_already_claimed" } });
    server.use(...api.handlers);
    const { user, visited } = renderAuth("/connexion/reprise");
    await user.click(screen.getByRole("button", { name: TAKE }));
    expect(await screen.findByText("Chemin : /")).toBeInTheDocument();
    expect(visited).toEqual(["/connexion/reprise", "/"]);
    expect(api.meCalls).toBe(1);
  });

  it("claim keeps the page and says why on another error", async () => {
    server.use(...authApi({ me: null, claim: { conflict: "other_conflict" } }).handlers);
    const { user, router } = renderAuth("/connexion/reprise");
    await user.click(screen.getByRole("button", { name: TAKE }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Reprise impossible.");
    expect(router.state.location.pathname).toBe("/connexion/reprise");
    // Le focus est resté sur le bouton pressé : on peut réessayer au clavier.
    expect(screen.getByRole("button", { name: TAKE })).toHaveFocus();
  });
});
