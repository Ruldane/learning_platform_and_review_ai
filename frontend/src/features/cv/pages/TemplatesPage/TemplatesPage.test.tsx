import { screen, waitFor } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { emptyProfile, refusal, templateSummary } from "@/test/cvApi";
import { renderCv } from "@/test/cvHarness";
import * as cvApiModule from "../../api";
import { TemplatesPage } from "./TemplatesPage";

// Le corps multipart n'est pas relisible sous jsdom : on observe la source passée à l'appel.
const createSpy = vi.spyOn(cvApiModule, "createTemplate");

function setup(api: Parameters<typeof renderCv>[3] = {}) {
  return renderCv("/career/cv", "/career/cv", () => <TemplatesPage pollMs={40} />, api);
}

const pdf = () => new File(["%PDF-1.4"], "cv.pdf", { type: "application/pdf" });

describe("TemplatesPage", () => {
  it("lists the templates and activates a ready one", async () => {
    const { user, state } = setup({
      templates: [
        [
          templateSummary({ id: "t1", name: "My CV", active: true }),
          templateSummary({ id: "t2", name: "CV sobre", active: false, score: 80, page_count: 2 }),
        ],
      ],
    });
    const list = await screen.findByRole("list", { name: "CV template list" });
    expect(list).toHaveTextContent("Active template");
    expect(list).toHaveTextContent("Similarity: 80%");
    expect(list).toHaveTextContent("2 pages");
    await user.click(screen.getByRole("button", { name: "Use template CV sobre" }));
    await waitFor(() => expect(state.activated).toEqual(["t2"]));
  });

  it("creates a template from a PDF and opens it", async () => {
    const { user, state } = setup();
    await user.upload(await screen.findByLabelText(/Your CV \(PDF/), pdf());
    await user.click(screen.getByRole("button", { name: "Create template" }));
    expect(await screen.findByText("Page du modèle")).toBeInTheDocument();
    expect(state.creates).toHaveLength(1);
  });

  it("creates a template from a PDF that is already imported", async () => {
    const { user, state } = setup({
      documents: [{ id: "d9", name: "cv-camille.pdf", source_kind: "pdf", status: "indexed" }],
    });
    const existing = await screen.findByLabelText("Or use a PDF you've already imported");
    await user.selectOptions(existing, "d9");
    await user.click(screen.getByRole("button", { name: "Create template" }));
    expect(await screen.findByText("Page du modèle")).toBeInTheDocument();
    expect(state.creates).toHaveLength(1);
  });

  it("creates the template from the profile's CV when its document is known", async () => {
    const { user, state } = setup({
      profiles: [{ ...emptyProfile, source_document_id: "d-profil" }],
      templates: [[]],
    });
    await user.selectOptions(
      await screen.findByRole("combobox", { name: "Who runs the agents for this launch" }),
      "codex",
    );
    await user.click(await screen.findByRole("button", { name: "Use my profile's CV" }));
    expect(await screen.findByText("Page du modèle")).toBeInTheDocument();
    expect(state.creates).toHaveLength(1);
    expect(createSpy).toHaveBeenCalledWith({ name: "My CV", documentId: "d-profil" }, "codex");
  });

  it("hides « Use my profile's CV » without a source document", async () => {
    setup({ profiles: [{ ...emptyProfile, source_document_id: null }] });
    await screen.findByRole("button", { name: "Create template" });
    expect(screen.queryByRole("button", { name: "Use my profile's CV" })).toBeNull();
  });

  it("asks for a PDF before sending anything", async () => {
    const { user, state } = setup();
    await user.click(await screen.findByRole("button", { name: "Create template" }));
    expect(screen.getByText("Choose a PDF, or one you've already imported.")).toBeInTheDocument();
    expect(state.creates).toHaveLength(0);
  });

  it("links to the settings when vision is unavailable", async () => {
    const { user } = setup({
      createTemplate: () =>
        refusal(409, "vision_unavailable", "La capture du design demande un modèle."),
    });
    await user.upload(await screen.findByLabelText(/Your CV \(PDF/), pdf());
    await user.click(screen.getByRole("button", { name: "Create template" }));
    expect(
      await screen.findByText(
        "Capturing the design needs a model that can read images. Turn it on in settings.",
      ),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "Open template settings" }));
    expect(await screen.findByText("Réglages des modèles")).toBeInTheDocument();
  });

  it("shows the back's message when a template capture is already running (409)", async () => {
    const { user } = setup({
      createTemplate: () =>
        refusal(409, "capture_in_progress", "Une capture de modèle de CV est déjà en cours."),
    });
    await user.upload(await screen.findByLabelText(/Your CV \(PDF/), pdf());
    await user.click(screen.getByRole("button", { name: "Create template" }));
    expect(
      await screen.findByText("Une capture de modèle de CV est déjà en cours."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/lecture de documents/)).toBeNull();
  });

  it("shows an empty state whose action leads to the file field", async () => {
    const { user } = setup({ templates: [[]] });
    expect(await screen.findByText("No CV templates yet")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Add my CV as a PDF" }));
    expect(screen.getByLabelText(/Your CV \(PDF/)).toHaveFocus();
  });

  it("shows an error with « Retry » and reads again", async () => {
    let failing = true;
    const { user } = setup({
      templateList: () =>
        failing ? HttpResponse.json({}, { status: 500 }) : HttpResponse.json([templateSummary()]),
    });
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    failing = false;
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(
      await screen.findByRole("list", { name: "CV template list" }),
    ).toBeInTheDocument();
  });
});
