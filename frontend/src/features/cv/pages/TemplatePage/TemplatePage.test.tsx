import { screen, waitFor } from "@testing-library/react";
import { HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { sessionOut } from "@/test/councilApi";
import { councilEvents } from "@/test/councilEvents";
import { recordPosts } from "@/test/councilHarness";
import { refusal, templateOut } from "@/test/cvApi";
import { openStream, renderCv } from "@/test/cvHarness";
import { TemplatePage } from "./TemplatePage";

const ROUTE = "/carriere/cv/modeles/:templateId";

function setup(api: Parameters<typeof renderCv>[3] = {}) {
  return renderCv(
    ROUTE,
    "/carriere/cv/modeles/t1",
    (createSocket) => <TemplatePage pollMs={40} createSocket={createSocket} />,
    api,
  );
}

const OPTIONS = [
  { value: "validate", label: "Valider" },
  { value: "adjust", label: "Ajuster" },
  { value: "restart", label: "Recommencer la capture" },
];
const INSTRUCTION = {
  id: "instruction",
  label: "Ce qu'il faut changer",
  max_length: 500,
  required: false,
};

/** La question du Maquettiste, posée dans le flux de la capture `d1`. */
async function askQuestion(sockets: Parameters<typeof openStream>[0]) {
  const stream = await openStream(sockets, "d1");
  const e = councilEvents("d1");
  stream.push(
    e.message("m1", "Voici ma passe 2.", "designer"),
    e.interrupt("cv_template", "i1", {
      question: "Ressemblance : 91 %. Tu valides ?",
      options: OPTIONS,
      fields: [INSTRUCTION],
    }),
  );
  expect(await screen.findByText("Ressemblance : 91 %. Tu valides ?")).toBeInTheDocument();
}

describe("TemplatePage", () => {
  beforeEach(() => useSessionStore.getState().reset("d1"));

  it("compares the original with the model and says which fonts were replaced", async () => {
    setup();
    expect(await screen.findByRole("heading", { level: 1, name: "Mon CV" })).toBeInTheDocument();
    expect(await screen.findByAltText("Page 1 de ton CV d'origine")).toBeInTheDocument();
    const render = screen.getByAltText("Page 1 du modèle recréé");
    expect(render).toHaveAttribute("src", expect.stringContaining("/pages/render/1?pass=2"));
    expect(screen.getByText("Ressemblance : 91 %")).toBeInTheDocument();
    expect(screen.getByText(/La police des titres n'est pas libre/)).toBeInTheDocument();
    expect(screen.getByText("C'est ton modèle actif.")).toBeInTheDocument();
  });

  it("sends the instruction when asked to adjust", async () => {
    const { sockets, user } = setup({ template: [templateOut({ status: "review" })] });
    const resumes = recordPosts("/sessions/d1/resume", 200, sessionOut("d1", "running"));
    await askQuestion(sockets);
    await user.type(screen.getByLabelText("Ce qu'il faut changer"), "Titres plus grands");
    await user.click(screen.getByRole("button", { name: "Ajuster" }));
    await waitFor(() => expect(resumes).toHaveLength(1));
    expect(resumes[0]).toEqual({
      interrupt_id: "i1",
      value: { answers: { instruction: "Titres plus grands" } },
    });
  });

  it("does not send a bare « Ajuster » and says what to write", async () => {
    const { sockets, user } = setup({ template: [templateOut({ status: "review" })] });
    const resumes = recordPosts("/sessions/d1/resume", 200, sessionOut("d1", "running"));
    await askQuestion(sockets);
    await user.click(screen.getByRole("button", { name: "Ajuster" }));
    expect(
      await screen.findByText("Écris d'abord ce qu'il faut changer, puis demande l'ajustement."),
    ).toBeInTheDocument();
    expect(resumes).toHaveLength(0);
  });

  it("validates with « Valider » even when an instruction was typed", async () => {
    const { sockets, user } = setup({ template: [templateOut({ status: "review" })] });
    const resumes = recordPosts("/sessions/d1/resume", 200, sessionOut("d1", "running"));
    await askQuestion(sockets);
    await user.type(screen.getByLabelText("Ce qu'il faut changer"), "Oublie");
    await user.click(screen.getByRole("button", { name: "Valider" }));
    await waitFor(() => expect(resumes).toHaveLength(1));
    expect(resumes[0]).toEqual({ interrupt_id: "i1", value: "validate" });
  });

  it("shows the reason when the capture failed", async () => {
    setup({
      template: [templateOut({ status: "failed", active: false, session_id: null, passes: 0 })],
    });
    expect(await screen.findByText("La capture a échoué.")).toBeInTheDocument();
    expect(
      screen.getByText("La capture s'est arrêtée avant la fin : crée un nouveau modèle."),
    ).toBeInTheDocument();
  });

  it("activates a ready model that is not the active one", async () => {
    const { user, state } = setup({ template: [templateOut({ active: false })] });
    await user.click(await screen.findByRole("button", { name: "Utiliser ce modèle pour mes CV" }));
    await waitFor(() => expect(state.activated).toEqual(["t1"]));
  });

  it("says the model is unknown on a 404", async () => {
    setup({ templateRead: () => refusal(404, "template_not_found", "Introuvable.") });
    expect(await screen.findByText("Modèle introuvable")).toBeInTheDocument();
  });

  it("shows an error with « Réessayer » on a failure", async () => {
    let failing = true;
    const { user } = setup({
      templateRead: () =>
        failing ? HttpResponse.json({}, { status: 500 }) : HttpResponse.json(templateOut()),
    });
    // Une panne est retentée une fois (1 s) avant d'être montrée.
    expect(await screen.findByRole("alert", {}, { timeout: 3000 })).toBeInTheDocument();
    failing = false;
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Mon CV" })).toBeInTheDocument();
  });
});
