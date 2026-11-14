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
  return renderCv("/carriere/cv", "/carriere/cv", () => <TemplatesPage pollMs={40} />, api);
}

const pdf = () => new File(["%PDF-1.4"], "cv.pdf", { type: "application/pdf" });

describe("TemplatesPage", () => {
  it("lists the templates and activates a ready one", async () => {
    const { user, state } = setup({
      templates: [
        [
          templateSummary({ id: "t1", name: "Mon CV", active: true }),
          templateSummary({ id: "t2", name: "CV sobre", active: false, score: 80, page_count: 2 }),
        ],
      ],
    });
    const list = await screen.findByRole("list", { name: "Liste des modèles de CV" });
    expect(list).toHaveTextContent("Modèle actif");
    expect(list).toHaveTextContent("Ressemblance : 80 %");
    expect(list).toHaveTextContent("2 pages");
    await user.click(screen.getByRole("button", { name: "Utiliser le modèle CV sobre" }));
    await waitFor(() => expect(state.activated).toEqual(["t2"]));
  });

  it("creates a template from a PDF and opens it", async () => {
    const { user, state } = setup();
    await user.upload(await screen.findByLabelText(/Ton CV \(PDF/), pdf());
    await user.click(screen.getByRole("button", { name: "Créer le modèle" }));
    expect(await screen.findByText("Page du modèle")).toBeInTheDocument();
    expect(state.creates).toHaveLength(1);
  });

  it("creates a template from a PDF that is already imported", async () => {
    const { user, state } = setup({
      documents: [{ id: "d9", name: "cv-camille.pdf", source_kind: "pdf", status: "indexed" }],
    });
    await user.selectOptions(await screen.findByLabelText("Ou utiliser un PDF déjà importé"), "d9");
    await user.click(screen.getByRole("button", { name: "Créer le modèle" }));
    expect(await screen.findByText("Page du modèle")).toBeInTheDocument();
    expect(state.creates).toHaveLength(1);
  });

  it("creates the template from the profile's CV when its document is known", async () => {
    const { user, state } = setup({
      profiles: [{ ...emptyProfile, source_document_id: "d-profil" }],
    });
    await user.click(await screen.findByRole("button", { name: "Utiliser le CV de mon profil" }));
    expect(await screen.findByText("Page du modèle")).toBeInTheDocument();
    expect(state.creates).toHaveLength(1);
    expect(createSpy).toHaveBeenCalledWith({ name: "Mon CV", documentId: "d-profil" });
  });

  it("hides « Utiliser le CV de mon profil » without a source document", async () => {
    setup({ profiles: [{ ...emptyProfile, source_document_id: null }] });
    await screen.findByRole("button", { name: "Créer le modèle" });
    expect(screen.queryByRole("button", { name: "Utiliser le CV de mon profil" })).toBeNull();
  });

  it("asks for a PDF before sending anything", async () => {
    const { user, state } = setup();
    await user.click(await screen.findByRole("button", { name: "Créer le modèle" }));
    expect(screen.getByText("Choisis un PDF, ou un PDF déjà importé.")).toBeInTheDocument();
    expect(state.creates).toHaveLength(0);
  });

  it("links to the settings when vision is unavailable", async () => {
    const { user } = setup({
      createTemplate: () =>
        refusal(409, "vision_unavailable", "La capture du design demande un modèle."),
    });
    await user.upload(await screen.findByLabelText(/Ton CV \(PDF/), pdf());
    await user.click(screen.getByRole("button", { name: "Créer le modèle" }));
    expect(
      await screen.findByText(
        "La capture du design demande un modèle qui lit les images. Active-le dans les réglages.",
      ),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "Ouvrir les réglages des modèles" }));
    expect(await screen.findByText("Réglages des modèles")).toBeInTheDocument();
  });

  it("shows an empty state whose action leads to the file field", async () => {
    const { user } = setup({ templates: [[]] });
    expect(await screen.findByText("Aucun modèle de CV pour l'instant")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Ajouter mon CV en PDF" }));
    expect(screen.getByLabelText(/Ton CV \(PDF/)).toHaveFocus();
  });

  it("shows an error with « Réessayer » and reads again", async () => {
    let failing = true;
    const { user } = setup({
      templateList: () =>
        failing ? HttpResponse.json({}, { status: 500 }) : HttpResponse.json([templateSummary()]),
    });
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    failing = false;
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(
      await screen.findByRole("list", { name: "Liste des modèles de CV" }),
    ).toBeInTheDocument();
  });
});
