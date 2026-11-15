import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { applicationOut } from "@/test/applicationsApi";
import { openStream, renderApplications } from "@/test/applicationsHarness";
import { sessionOut } from "@/test/councilApi";
import { councilEvents } from "@/test/councilEvents";
import { apiError, recordPosts } from "@/test/councilHarness";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { applicationsManifest } from "../../manifest";
import { NewApplicationPage } from "./NewApplicationPage";

function setup(api: Parameters<typeof renderApplications>[2] = {}) {
  const sockets = createFakeSocketServer();
  const routes = applicationsManifest.routes.map((route) =>
    route.path === "candidatures/nouvelle"
      ? { path: route.path, element: <NewApplicationPage createSocket={sockets.factory} /> }
      : route,
  );
  const view = renderApplications(routes, "/candidatures/nouvelle", {
    applications: [applicationOut({ id: "a1" }), applicationOut({ id: "a9", title: "Autre" })],
    ...api,
  });
  return { ...view, sockets };
}

const field = (id: string, label: string, value: string, required = false) => ({
  id,
  label,
  required,
  max_length: 200,
  value,
});

const CONFIRM_FIELDS = [
  field("company", "Entreprise", "Acme", true),
  field("title", "Poste", "Data engineer", true),
  field("status", "Statut", "applied", true),
  field("applied_on", "Date de candidature (AAAA-MM-JJ)", ""),
  field("channel", "Canal", "linkedin"),
  field("contact_name", "Contact", ""),
  field("contact_role", "Rôle du contact", ""),
  field("notes", "Notes", ""),
];

/** La carte de confirmation de l'Assistant de suivi (la page a aussi le formulaire à la main). */
const confirmation = () => screen.findByRole("region", { name: /Je crée cette fiche/ });

describe("NewApplicationPage, en une phrase", () => {
  beforeEach(() => useSessionStore.getState().reset("i1"));

  async function askConfirmation(over: Record<string, unknown> = {}) {
    const view = setup();
    await view.user.type(
      screen.getByLabelText("Ta phrase"),
      "J'ai postulé hier chez Acme pour un poste de data engineer",
    );
    await view.user.click(screen.getByRole("button", { name: "Préparer la fiche" }));
    const stream = await openStream(view.sockets, "i1");
    const e = councilEvents("i1");
    stream.push(
      e.message("m1", "J'ai lu : Acme, Data engineer.", "tracker"),
      e.interrupt("application_confirm", "q1", {
        question: "Je crée cette fiche ?",
        options: [
          { value: "create", label: "Créer la fiche" },
          { value: "cancel", label: "Annuler" },
        ],
        fields: CONFIRM_FIELDS,
        ...over,
      }),
    );
    return { ...view, stream, e };
  }

  it("starts the session with the sentence and shows the confirmation with the read values", async () => {
    const { state } = await askConfirmation();
    expect(state.intakes).toEqual([
      { text: "J'ai postulé hier chez Acme pour un poste de data engineer" },
    ]);
    const card = within(await confirmation());
    expect(card.getByLabelText("Entreprise")).toHaveValue("Acme");
    expect(card.getByLabelText("Statut")).toHaveDisplayValue("Postulée");
    expect(card.getByLabelText("Date de candidature (AAAA-MM-JJ)")).toHaveAccessibleDescription(
      "Sans date, la fiche prend la date d'aujourd'hui.",
    );
  });

  it("answers with the choice and the fields, then opens the application the session announces", async () => {
    const resumes = recordPosts("/sessions/i1/resume", 200, sessionOut("i1", "running"));
    const { user, stream, e, router } = await askConfirmation();
    const card = within(await confirmation());
    const company = card.getByLabelText("Entreprise");
    await user.clear(company);
    await user.type(company, "Acme Corp");
    await user.click(card.getByRole("button", { name: "Créer la fiche" }));
    await waitFor(() => expect(resumes).toHaveLength(1));
    expect(resumes[0]).toEqual({
      interrupt_id: "q1",
      value: {
        choice: "create",
        fields: expect.objectContaining({ company: "Acme Corp", status: "applied" }),
      },
    });
    stream.push(e.artifactReady("application", "a1", "/candidatures/a1"));
    await waitFor(() => expect(router.state.location.pathname).toBe("/candidatures/a1"));
  });

  it("offers « autre poste », « Ouvrir » and « Annuler » when the assistant found a duplicate, never « Créer »", async () => {
    const resumes = recordPosts("/sessions/i1/resume", 200, sessionOut("i1", "running"));
    const { user } = await askConfirmation({
      question: "Je crée cette fiche ? Attention, tu as déjà une fiche chez Acme.",
      options: [
        { value: "distinct", label: "C'est un autre poste" },
        { value: "open", label: "Ouvrir la fiche existante" },
        { value: "cancel", label: "Annuler" },
      ],
    });
    const card = within(await confirmation());
    expect(card.getByRole("button", { name: "C'est un autre poste" })).toBeVisible();
    expect(card.queryByRole("button", { name: "Créer la fiche" })).toBeNull();
    await user.click(card.getByRole("button", { name: "Ouvrir la fiche existante" }));
    await waitFor(() => expect(resumes).toEqual([{ interrupt_id: "q1", value: "open" }]));
  });

  it("opens the existing fiche the session announces after « Ouvrir »", async () => {
    const { stream, e, router } = await askConfirmation();
    stream.push(e.artifactReady("application", "a9", "/candidatures/a9"));
    await waitFor(() => expect(router.state.location.pathname).toBe("/candidatures/a9"));
  });

  it("lets January fix her sentence once the session is over without a fiche", async () => {
    const { user, stream, e } = await askConfirmation();
    stream.push(e.failed("Je n'ai pas trouvé l'entreprise ou le poste dans ta phrase."));
    expect(
      await screen.findByText("Je n'ai pas trouvé l'entreprise ou le poste dans ta phrase."),
    ).toBeVisible();
    await user.click(await screen.findByRole("button", { name: "Écrire une autre phrase" }));
    expect(screen.getByLabelText("Ta phrase")).toHaveValue(
      "J'ai postulé hier chez Acme pour un poste de data engineer",
    );
  });

  it("offers to resume or cancel a sentence session that is already open", async () => {
    let first = true;
    const { user, state } = setup({
      intake: () => {
        if (!first) return HttpResponse.json({ session_id: "i2" }, { status: 202 });
        first = false;
        return HttpResponse.json(
          apiError("intake_in_progress", "Une saisie est déjà ouverte.", { session_id: "s9" }),
          { status: 409 },
        );
      },
    });
    await user.type(screen.getByLabelText("Ta phrase"), "Une phrase");
    await user.click(screen.getByRole("button", { name: "Préparer la fiche" }));
    expect(await screen.findByText(/Une saisie en une phrase est déjà ouverte/)).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Annuler cette saisie" }));
    await waitFor(() => expect(state.cancels).toEqual(["s9"]));
    await waitFor(() => expect(screen.queryByText(/déjà ouverte/)).toBeNull());
    await user.click(screen.getByRole("button", { name: "Préparer la fiche" }));
    await waitFor(() => expect(state.intakes).toHaveLength(2));
  });

  it("resumes the open session when asked", async () => {
    const { user, sockets } = setup({
      intake: () =>
        HttpResponse.json(
          apiError("intake_in_progress", "Une saisie est déjà ouverte.", { session_id: "s9" }),
          { status: 409 },
        ),
    });
    await user.type(screen.getByLabelText("Ta phrase"), "Une phrase");
    await user.click(screen.getByRole("button", { name: "Préparer la fiche" }));
    await user.click(await screen.findByRole("button", { name: "Reprendre cette saisie" }));
    await openStream(sockets, "s9");
  });

  it("does not send an empty sentence", async () => {
    const { state } = setup();
    expect(screen.getByRole("button", { name: "Préparer la fiche" })).toBeDisabled();
    expect(state.intakes).toHaveLength(0);
  });
});
