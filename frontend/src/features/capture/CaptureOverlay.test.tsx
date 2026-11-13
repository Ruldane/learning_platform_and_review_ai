import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { openCaptureStream, renderCapture } from "@/test/captureApi";
import { councilEvents } from "@/test/councilEvents";
import { API } from "@/test/councilApi";
import { apiError, recordPosts } from "@/test/councilHarness";
import { server } from "@/test/server";
import { CaptureOverlay } from "./CaptureOverlay";
import { CaptureTopbarButton } from "./CaptureTopbarButton";
import { useCaptureDialog } from "./captureDialog";

const setup = () =>
  renderCapture((createSocket) => (
    <>
      <CaptureTopbarButton />
      <CaptureOverlay createSocket={createSocket} />
      <input aria-label="Un champ de la page" />
    </>
  ));

const reset = () => {
  useCaptureDialog.setState({ open: false, sessionId: null, draft: "", textDraft: "" });
  useSessionStore.getState().reset("s5");
};

const resumedSession = {
  id: "s5",
  graph: "capture",
  status: "running",
  last_seq: 0,
  pending_interrupt: null,
};

describe("capture dialog", () => {
  beforeEach(reset);
  afterEach(reset);

  it("opens capture with Ctrl+K and Cmd+K", async () => {
    const { user } = setup();
    expect(screen.queryByRole("dialog")).toBeNull();
    await user.keyboard("{Control>}k{/Control}");
    expect(await screen.findByRole("dialog", { name: "Capture rapide" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await user.keyboard("{Meta>}k{/Meta}");
    expect(await screen.findByRole("dialog", { name: "Capture rapide" })).toBeInTheDocument();
  });

  it("opens capture with Ctrl+K even from a text field", async () => {
    const { user } = setup();
    await user.click(screen.getByLabelText("Un champ de la page"));
    await user.keyboard("{Control>}k{/Control}");
    expect(await screen.findByRole("dialog", { name: "Capture rapide" })).toBeInTheDocument();
  });

  it("opens from the top bar button, focuses the field and closes with Escape", async () => {
    const { user } = setup();
    await user.click(screen.getByRole("button", { name: /Capture rapide/ }));
    const field = await screen.findByLabelText("Un lien ou une note");
    expect(field).toHaveFocus();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("keeps the focus inside the dialog", async () => {
    const { user } = setup();
    await user.keyboard("{Control>}k{/Control}");
    const dialog = await screen.findByRole("dialog");
    for (let i = 0; i < 8; i += 1) {
      await user.tab();
      expect(dialog).toContainElement(document.activeElement as HTMLElement);
    }
  });

  it("captures a link and shows the summary", async () => {
    const posts = recordPosts("/capture", 202, { session_id: "s5" });
    const { user, fake } = setup();
    await user.keyboard("{Control>}k{/Control}");
    await user.type(
      await screen.findByLabelText("Un lien ou une note"),
      "https://exemple.fr/article",
    );
    expect(screen.getByText("Lien détecté : l'Archiviste va le lire.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Capturer" }));
    await waitFor(() => expect(posts).toEqual([{ url: "https://exemple.fr/article" }]));
    const e = councilEvents("s5");
    const socket = await openCaptureStream(fake);
    socket.push(e.message("m1", "Résumé en trois lignes.", "archivist"));
    expect(await screen.findByText("Résumé en trois lignes.")).toBeInTheDocument();
  });

  it("captures a note typed in the same field", async () => {
    const posts = recordPosts("/capture", 202, { session_id: "s5" });
    const { user } = setup();
    await user.keyboard("{Control>}k{/Control}");
    await user.type(
      await screen.findByLabelText("Un lien ou une note"),
      "Idée : lire https://x.fr plus tard",
    );
    expect(screen.getByText(/Note : elle sera résumée/)).toBeInTheDocument();
    await user.keyboard("{Control>}{Enter}{/Control}");
    await waitFor(() => expect(posts).toEqual([{ text: "Idée : lire https://x.fr plus tard" }]));
  });

  it("answers yes to the task and cards questions", async () => {
    const resumes = recordPosts("/sessions/s5/resume", 202, resumedSession);
    recordPosts("/capture", 202, { session_id: "s5" });
    const { user, fake } = setup();
    await user.keyboard("{Control>}k{/Control}");
    await user.type(await screen.findByLabelText("Un lien ou une note"), "https://exemple.fr/a");
    await user.click(screen.getByRole("button", { name: "Capturer" }));
    const e = councilEvents("s5");
    const socket = await openCaptureStream(fake);
    socket.push(
      e.interrupt("capture_task", "i1", {
        question: "Cocher la tâche « Lire le chapitre 2 » ?",
        options: [
          { value: "yes", label: "Oui" },
          { value: "no", label: "Non" },
        ],
      }),
    );
    await user.click(await screen.findByRole("button", { name: "Oui" }));
    await waitFor(() => expect(resumes).toEqual([{ interrupt_id: "i1", value: "yes" }]));
  });

  it("asks for text when the link is unreadable", async () => {
    const resumes = recordPosts("/sessions/s5/resume", 202, resumedSession);
    recordPosts("/capture", 202, { session_id: "s5" });
    const { user, fake } = setup();
    await user.keyboard("{Control>}k{/Control}");
    await user.type(await screen.findByLabelText("Un lien ou une note"), "https://ferme.fr/page");
    await user.click(screen.getByRole("button", { name: "Capturer" }));
    const e = councilEvents("s5");
    const socket = await openCaptureStream(fake);
    socket.push(
      e.interrupt("capture_text", "i1", {
        question: "Je n'arrive pas à lire ce lien. Colle son texte ci-dessous.",
        options: [{ value: "cancel", label: "Abandonner" }],
        fields: [{ id: "text", label: "Le texte de la page", max_length: 20000, required: true }],
      }),
    );
    const area = await screen.findByLabelText("Le texte de la page");
    expect(area).toHaveAttribute("maxlength", "20000");
    expect(screen.getByRole("button", { name: "Envoyer le texte" })).toBeDisabled();
    await user.type(area, "Le contenu collé.");
    await user.click(screen.getByRole("button", { name: "Envoyer le texte" }));
    await waitFor(() =>
      expect(resumes).toEqual([
        { interrupt_id: "i1", value: { answers: { text: "Le contenu collé." } } },
      ]),
    );
  });

  it("cancels the text question without sending the typed text", async () => {
    const resumes = recordPosts("/sessions/s5/resume", 202, resumedSession);
    recordPosts("/capture", 202, { session_id: "s5" });
    const { user, fake } = setup();
    await user.keyboard("{Control>}k{/Control}");
    await user.type(await screen.findByLabelText("Un lien ou une note"), "https://ferme.fr/page");
    await user.click(screen.getByRole("button", { name: "Capturer" }));
    (await openCaptureStream(fake)).push(
      councilEvents("s5").interrupt("capture_text", "i1", {
        question: "Colle le texte.",
        options: [{ value: "cancel", label: "Abandonner" }],
        fields: [{ id: "text", label: "Le texte de la page", max_length: 20000, required: true }],
      }),
    );
    await user.type(await screen.findByLabelText("Le texte de la page"), "Brouillon");
    await user.click(screen.getByRole("button", { name: "Abandonner" }));
    await waitFor(() => expect(resumes).toEqual([{ interrupt_id: "i1", value: "cancel" }]));
  });

  it("uploads a file then captures it", async () => {
    const posts = recordPosts("/capture", 202, { session_id: "s5" });
    let contentType = "";
    server.use(
      http.post(`${API}/documents`, ({ request }) => {
        contentType = request.headers.get("content-type") ?? "";
        return HttpResponse.json(
          { document: { id: "d1", name: "cours.pdf", status: "queued" }, duplicate: false },
          { status: 202 },
        );
      }),
    );
    const { user } = setup();
    await user.keyboard("{Control>}k{/Control}");
    const file = new File(["%PDF"], "cours.pdf", { type: "application/pdf" });
    await user.upload(await screen.findByLabelText("Choisir un fichier"), file);
    await waitFor(() => expect(posts).toEqual([{ document_id: "d1" }]));
    expect(contentType).toMatch(/^multipart\/form-data; boundary=/);
  });

  it("refuses a file of an unsupported type without any call", async () => {
    const posts = recordPosts("/capture", 202, { session_id: "s5" });
    const { user } = setup();
    await user.keyboard("{Control>}k{/Control}");
    const file = new File(["MZ"], "setup.exe", { type: "application/octet-stream" });
    // Un glisser-déposer ne passerait pas par le filtre `accept` du sélecteur natif.
    await userEvent
      .setup({ applyAccept: false })
      .upload(await screen.findByLabelText("Choisir un fichier"), file);
    expect(await screen.findByText(/Type de fichier non pris en charge/)).toBeInTheDocument();
    expect(posts).toEqual([]);
  });

  it("says clearly when the imported document failed (409 document_failed)", async () => {
    recordPosts("/capture", 409, apiError("document_failed", "Import en échec."));
    server.use(
      http.post(`${API}/documents`, () =>
        HttpResponse.json(
          { document: { id: "d1", name: "cours.pdf", status: "error" }, duplicate: true },
          { status: 200 },
        ),
      ),
    );
    const { user } = setup();
    await user.keyboard("{Control>}k{/Control}");
    const file = new File(["%PDF"], "cours.pdf", { type: "application/pdf" });
    await user.upload(await screen.findByLabelText("Choisir un fichier"), file);
    expect(await screen.findByText(/L'import de ce fichier a échoué/)).toBeInTheDocument();
  });

  it("shows a refused link inline and keeps the field", async () => {
    recordPosts("/capture", 422, apiError("url_forbidden", "Adresse refusée."));
    const { user } = setup();
    await user.keyboard("{Control>}k{/Control}");
    await user.type(
      await screen.findByLabelText("Un lien ou une note"),
      "https://moi:mdp@site.fr/a",
    );
    await user.click(screen.getByRole("button", { name: "Capturer" }));
    expect(await screen.findByText(/identifiants/)).toBeInTheDocument();
    expect(screen.getByLabelText("Un lien ou une note")).toHaveValue("https://moi:mdp@site.fr/a");
  });

  it("shows the end of a capture and goes to the journal", async () => {
    recordPosts("/capture", 202, { session_id: "s5" });
    const { user, fake, router } = setup();
    await user.keyboard("{Control>}k{/Control}");
    await user.type(await screen.findByLabelText("Un lien ou une note"), "https://exemple.fr/a");
    await user.click(screen.getByRole("button", { name: "Capturer" }));
    const e = councilEvents("s5");
    const socket = await openCaptureStream(fake);
    socket.push(e.message("m1", "Résumé.", "archivist"), e.completed());
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText("Capture terminée.")).toBeInTheDocument();
    await user.click(within(dialog).getByRole("link", { name: "Voir le journal" }));
    expect(router.state.location.pathname).toBe("/etudier/journal");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });
});
