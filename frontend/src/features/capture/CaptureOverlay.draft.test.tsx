import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { openCaptureStream, renderCapture } from "@/test/captureApi";
import { councilEvents } from "@/test/councilEvents";
import { recordPosts } from "@/test/councilHarness";
import { CaptureOverlay } from "./CaptureOverlay";
import { CaptureTopbarButton } from "./CaptureTopbarButton";
import { useCaptureDialog } from "./captureDialog";

const setup = () =>
  renderCapture((createSocket) => (
    <>
      <CaptureTopbarButton />
      <CaptureOverlay createSocket={createSocket} />
    </>
  ));

const reset = () => {
  useCaptureDialog.setState({ open: false, sessionId: null, draft: "", textDraft: "" });
  useSessionStore.getState().reset("s5");
};

const FIELD = "Un lien ou une note";

/** Revue finale 5 : brouillons gardés (C-m1) et limites visibles du champ (C-m6). */
describe("capture dialog: drafts and limits", () => {
  beforeEach(reset);
  afterEach(reset);

  it("keeps the typed note when the dialog closes (Escape, Fermer)", async () => {
    const { user } = setup();
    await user.keyboard("{Control>}k{/Control}");
    await user.type(await screen.findByLabelText(FIELD), "Une note de dix lignes");
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await user.keyboard("{Control>}k{/Control}");
    expect(await screen.findByLabelText(FIELD)).toHaveValue("Une note de dix lignes");
    // Toute fermeture (Échap, clic à côté, « Fermer ») passe par `closeDialog` : la saisie reste.
    await user.click(screen.getByRole("button", { name: "Fermer" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await user.keyboard("{Control>}k{/Control}");
    expect(await screen.findByLabelText(FIELD)).toHaveValue("Une note de dix lignes");
  });

  it("empties the field once the capture is sent, and after a new capture", async () => {
    recordPosts("/capture", 202, { session_id: "s5" });
    const { user, fake } = setup();
    await user.keyboard("{Control>}k{/Control}");
    await user.type(await screen.findByLabelText(FIELD), "https://exemple.fr/a");
    await user.click(screen.getByRole("button", { name: "Capturer" }));
    (await openCaptureStream(fake)).push(councilEvents("s5").completed());
    await user.click(await screen.findByRole("button", { name: "Nouvelle capture" }));
    expect(await screen.findByLabelText(FIELD)).toHaveValue("");
  });

  it("keeps the pasted text of an unreadable link when the dialog closes", async () => {
    recordPosts("/capture", 202, { session_id: "s5" });
    const { user, fake } = setup();
    await user.keyboard("{Control>}k{/Control}");
    await user.type(await screen.findByLabelText(FIELD), "https://ferme.fr/page");
    await user.click(screen.getByRole("button", { name: "Capturer" }));
    (await openCaptureStream(fake)).push(
      councilEvents("s5").interrupt("capture_text", "i1", {
        question: "Colle le texte.",
        options: [{ value: "cancel", label: "Abandonner" }],
        fields: [{ id: "text", label: "Le texte de la page", max_length: 20000, required: true }],
      }),
    );
    await user.type(await screen.findByLabelText("Le texte de la page"), "Le contenu collé.");
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await user.keyboard("{Control>}k{/Control}");
    expect(await screen.findByLabelText("Le texte de la page")).toHaveValue("Le contenu collé.");
  });

  it("shows the 20 000 character limit as a counter", async () => {
    const { user } = setup();
    await user.keyboard("{Control>}k{/Control}");
    const field = await screen.findByLabelText(FIELD);
    expect(field).toHaveAccessibleDescription(/0 \/ 20\s000 caractères/);
    await user.type(field, "Bonjour");
    expect(screen.getByText(/^7 \/ 20\s000 caractères$/)).toBeInTheDocument();
  });

  it("says that a link is limited to 2 048 characters", async () => {
    const { user } = setup();
    await user.keyboard("{Control>}k{/Control}");
    const field = await screen.findByLabelText(FIELD);
    await user.click(field);
    await user.paste(`https://exemple.fr/${"a".repeat(2100)}`);
    expect(screen.getByText("2 048 caractères au plus pour un lien.")).toBeInTheDocument();
    expect(screen.queryByText(/^20 000 caractères au plus/)).toBeNull();
    expect(screen.getByRole("button", { name: "Capturer" })).toBeDisabled();
  });
});
