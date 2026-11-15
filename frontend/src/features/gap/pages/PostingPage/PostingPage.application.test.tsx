import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { apiError } from "@/test/councilHarness";
import { postingsApi } from "@/test/postingsApi";
import { renderPosting } from "@/test/postingsHarness";
import { PostingPage } from "./PostingPage";

function setup(api: Parameters<typeof postingsApi>[0] = {}) {
  return renderPosting((createSocket) => <PostingPage createSocket={createSocket} />, api);
}

const alert = (over: Record<string, unknown> = {}) => ({
  application_id: "ap9",
  level: "probable",
  message: "Attention, tu as déjà une fiche chez Société Fictive pour ce poste.",
  company: "Société Fictive",
  title: "Ingénieure données (H/F)",
  status: "applied",
  applied_on: "2026-11-03",
  created_on: "2026-11-03",
  ...over,
});

const check =
  (over: Record<string, unknown> = {}) =>
  () =>
    HttpResponse.json({ own: null, alerts: [], info: [], ...over });

const block = () => screen.findByRole("region", { name: "Candidature pour cette offre" });

describe("PostingPage, candidature", () => {
  beforeEach(() => useSessionStore.getState().reset("a1"));

  it("checks the posting and offers to create the application when there is none", async () => {
    const { user, state, router } = setup();
    const section = within(await block());
    expect(state.checks).toEqual(["?posting_id=p1"]);
    expect(section.queryByRole("alert")).toBeNull();
    await user.click(section.getByRole("button", { name: "Créer la candidature" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/candidatures/ap1"));
    expect(state.applications).toEqual([{ posting_id: "p1", status: "to_apply" }]);
  });

  it("shows the application the posting already has and opens it", async () => {
    const { user, router } = setup({
      check: check({
        own: {
          id: "ap2",
          company: "Société Fictive",
          title: "Ingénieure données",
          status: "applied",
          applied_on: "2026-11-03",
        },
      }),
    });
    const section = within(await block());
    expect(
      section.getByText(
        "Tu as déjà une candidature pour cette offre : Société Fictive, Ingénieure données (Postulée).",
      ),
    ).toBeVisible();
    expect(section.queryByRole("button", { name: "Créer la candidature" })).toBeNull();
    await user.click(section.getByRole("button", { name: "Ouvrir la candidature" }));
    expect(router.state.location.pathname).toBe("/candidatures/ap2");
  });

  it("shows the duplicate alert of the check, with its three choices and no create button", async () => {
    const { user, router } = setup({ check: check({ alerts: [alert()] }) });
    const section = within(await block());
    expect(section.getByRole("alert")).toHaveTextContent("Doublon probable");
    expect(section.getByText(/tu as déjà une fiche chez Société Fictive/)).toBeVisible();
    expect(section.queryByRole("button", { name: "Créer la candidature" })).toBeNull();
    await user.click(section.getByRole("button", { name: "Ouvrir la fiche existante" }));
    expect(router.state.location.pathname).toBe("/candidatures/ap9");
  });

  it("creates the application with « C'est un autre poste » and the confirmed ones", async () => {
    const { user, state, router } = setup({ check: check({ alerts: [alert()] }) });
    await user.click(await screen.findByRole("button", { name: "C'est un autre poste" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/candidatures/ap1"));
    expect(state.applications).toEqual([
      { posting_id: "p1", status: "to_apply", distinct_from: ["ap9"] },
    ]);
  });

  it("brings back the create button when the alert is cancelled, and the alert again if the server insists", async () => {
    const { user, state } = setup({
      check: check({ alerts: [alert()] }),
      application: () =>
        HttpResponse.json(
          apiError("application_duplicate", "Existe déjà.", { alerts: [alert()] }),
          { status: 409 },
        ),
    });
    await user.click(await screen.findByRole("button", { name: "Annuler" }));
    expect(screen.queryByRole("alert")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Créer la candidature" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Doublon probable");
    expect(state.applications).toHaveLength(1);
  });

  it("only notes a same-company info and still offers to create", async () => {
    setup({
      check: check({
        info: [
          alert({
            level: "info",
            message: "Pour info : tu as postulé chez Société Fictive il y a 12 jours.",
          }),
        ],
      }),
    });
    const section = within(await block());
    expect(section.getByRole("note")).toHaveTextContent("Pour info : tu as postulé chez");
    expect(section.queryByRole("alert")).toBeNull();
    expect(section.getByRole("button", { name: "Créer la candidature" })).toBeEnabled();
  });

  it("opens the application the posting already has when the server says it exists (409)", async () => {
    const { user, router } = setup({
      application: () =>
        HttpResponse.json(
          apiError("application_exists", "Cette offre a déjà une candidature.", {
            application_id: "ap5",
          }),
          { status: 409 },
        ),
    });
    await user.click(await screen.findByRole("button", { name: "Créer la candidature" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/candidatures/ap5"));
  });

  it("says why the creation failed and keeps the button", async () => {
    const { user } = setup({
      application: () =>
        HttpResponse.json(apiError("internal_error", "Le serveur ne répond pas."), { status: 500 }),
    });
    await user.click(await screen.findByRole("button", { name: "Créer la candidature" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Le serveur ne répond pas.");
    expect(screen.getByRole("button", { name: "Créer la candidature" })).toBeEnabled();
  });

  it("says when the check fails, with a retry", async () => {
    let calls = 0;
    const { user } = setup({
      check: () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json(apiError("internal_error", "Panne."), { status: 500 })
          : HttpResponse.json({ own: null, alerts: [], info: [] });
      },
    });
    expect(
      await screen.findByText("La recherche d'une candidature existante a échoué. Panne."),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByRole("button", { name: "Créer la candidature" })).toBeVisible();
  });
});
