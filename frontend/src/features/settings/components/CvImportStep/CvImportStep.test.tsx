import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { useState } from "react";
import type { PdfChoice } from "../viewTypes";
import { CvImportStep } from "./CvImportStep";

// `accept` ne retient rien quand on choisit « tous les fichiers » : le composant refuse lui-même.
const user = () => userEvent.setup({ applyAccept: false });
const pdf = (name = "cv.pdf", size = 1000) => {
  const file = new File(["%PDF-1.4"], name, { type: "application/pdf" });
  Object.defineProperty(file, "size", { value: size });
  return file;
};

interface Props {
  pending: boolean;
  error: string | null;
  imported: boolean;
  hasKey: boolean;
}

function setup(props: Partial<Props> = {}) {
  const onImport = vi.fn();
  const onGoToKey = vi.fn();
  function Step(over: Partial<Props>) {
    // La page garde les deux PDF (voir `useCvDocuments`) : la même forme, ici avec `useState`.
    const [cv, setCv] = useState<PdfChoice>({ file: null, problem: null });
    const [linkedin, setLinkedin] = useState<PdfChoice>({ file: null, problem: null });
    const documents = { cv, linkedin, setCv, setLinkedin };
    return (
      <CvImportStep
        documents={documents}
        hasKey={over.hasKey ?? props.hasKey ?? true}
        pending={over.pending ?? props.pending ?? false}
        error={props.error ?? null}
        imported={props.imported ?? false}
        onImport={onImport}
        onGoToKey={onGoToKey}
      />
    );
  }
  const view = render(<Step />);
  return {
    onImport,
    onGoToKey,
    user: user(),
    pendingNow: () => view.rerender(<Step pending />),
  };
}

const cvInput = () => screen.getByLabelText("Ton CV (PDF, 10 Mo au plus)");
const linkedinInput = () => screen.getByLabelText("Ton profil LinkedIn (PDF, facultatif)");
const send = () => screen.getByRole("button", { name: "Importer mes documents" });

describe("CvImportStep", () => {
  it("cannot send without a CV, and says why", async () => {
    const { onImport, user: u } = setup();
    expect(send()).toHaveAttribute("aria-disabled", "true");
    expect(send()).toHaveAccessibleDescription("Choisis d'abord ton CV.");
    await u.click(send());
    expect(onImport).not.toHaveBeenCalled();
    await u.upload(cvInput(), pdf());
    expect(send()).toHaveAttribute("aria-disabled", "false");
    expect(send()).not.toHaveAccessibleDescription("Choisis d'abord ton CV.");
  });

  it("sends the CV alone, then the CV and the LinkedIn PDF", async () => {
    const { onImport, user: u } = setup();
    const cv = pdf();
    await u.upload(cvInput(), cv);
    await u.click(send());
    expect(onImport).toHaveBeenLastCalledWith({ cv });

    const linkedin = pdf("linkedin.pdf");
    await u.upload(linkedinInput(), linkedin);
    await u.click(send());
    expect(onImport).toHaveBeenLastCalledWith({ cv, linkedin });
  });

  it("refuses a file that is not a PDF, or is over 10 Mo, and never sends it", async () => {
    const { onImport, user: u } = setup();
    await u.upload(cvInput(), new File(["x"], "cv.docx", { type: "application/msword" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Ce fichier n'est pas un PDF");
    expect(cvInput()).toHaveAttribute("aria-invalid", "true");
    await u.click(send());
    expect(onImport).not.toHaveBeenCalled();

    await u.upload(cvInput(), pdf("cv.pdf", 11 * 1024 * 1024));
    expect(screen.getByRole("alert")).toHaveTextContent("dépasse 10 Mo");
    await u.upload(cvInput(), pdf());
    expect(screen.queryByRole("alert")).toBeNull();
    expect(cvInput()).toHaveAttribute("aria-invalid", "false");
  });

  it("says a refused LinkedIn file is left out, and still sends the CV", async () => {
    const { onImport, user: u } = setup();
    const cv = pdf();
    await u.upload(cvInput(), cv);
    expect(screen.queryByText(/Ton profil LinkedIn n'a pas été retenu/)).toBeNull();
    await u.upload(linkedinInput(), new File(["x"], "profil.docx", { type: "application/msword" }));
    expect(screen.getByText(/Ton profil LinkedIn n'a pas été retenu/)).toBeInTheDocument();
    expect(send()).toHaveAccessibleDescription(/Ton profil LinkedIn n'a pas été retenu/);
    await u.click(send());
    expect(onImport).toHaveBeenLastCalledWith({ cv });
  });

  it("without a key, sends nothing and says a key comes first", async () => {
    const { onImport, onGoToKey, user: u } = setup({ hasKey: false });
    await u.upload(cvInput(), pdf());
    expect(send()).toHaveAttribute("aria-disabled", "true");
    expect(send()).toHaveAccessibleDescription(/Sans clé d'API, Tremplin ne peut pas lire/);
    await u.click(send());
    expect(onImport).not.toHaveBeenCalled();
    await u.click(screen.getByRole("button", { name: "Aller à l'étape de la clé" }));
    expect(onGoToKey).toHaveBeenCalledTimes(1);
  });

  it("does not offer the way to the key when there is one", () => {
    setup();
    expect(screen.queryByRole("button", { name: "Aller à l'étape de la clé" })).toBeNull();
  });

  it("reminds that nothing leaves until « Importer » is clicked, once a CV is chosen", async () => {
    const { user: u } = setup();
    expect(screen.queryByText(/Rien n'est envoyé/)).toBeNull();
    await u.upload(cvInput(), pdf());
    expect(screen.getByText(/Rien n'est envoyé tant que/)).toBeInTheDocument();
  });

  it("ignores a second click while the import goes on", async () => {
    const { onImport, user: u, pendingNow } = setup();
    await u.upload(cvInput(), pdf());
    pendingNow();
    expect(screen.getByRole("button", { name: "Envoi en cours…" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    await u.click(screen.getByRole("button", { name: "Envoi en cours…" }));
    expect(onImport).not.toHaveBeenCalled();
  });

  it("shows the refusal of the server and keeps the chosen files", () => {
    setup({ error: "Une lecture est déjà en cours." });
    expect(screen.getByRole("alert")).toHaveTextContent("Une lecture est déjà en cours.");
  });

  it("says the documents are sent, and drops the reminder", () => {
    setup({ imported: true });
    expect(screen.getByRole("status")).toHaveTextContent("Tes documents sont envoyés");
    expect(screen.queryByText(/Rien n'est envoyé/)).toBeNull();
  });
});
