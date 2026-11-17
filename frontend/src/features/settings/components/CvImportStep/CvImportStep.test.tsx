import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CvImportStep } from "./CvImportStep";

// `accept` ne retient rien quand on choisit « tous les fichiers » : le composant refuse lui-même.
const user = () => userEvent.setup({ applyAccept: false });
const pdf = (name = "cv.pdf", size = 1000) => {
  const file = new File(["%PDF-1.4"], name, { type: "application/pdf" });
  Object.defineProperty(file, "size", { value: size });
  return file;
};

function setup(props: { pending?: boolean; error?: string | null; imported?: boolean } = {}) {
  const onImport = vi.fn();
  const ui = (over: { pending?: boolean } = {}) => (
    <CvImportStep
      pending={over.pending ?? props.pending ?? false}
      error={props.error ?? null}
      imported={props.imported ?? false}
      onImport={onImport}
    />
  );
  const view = render(ui());
  return { onImport, user: user(), pendingNow: () => view.rerender(ui({ pending: true })) };
}

const cvInput = () => screen.getByLabelText("Ton CV (PDF, 10 Mo au plus)");
const linkedinInput = () => screen.getByLabelText("Ton profil LinkedIn (PDF, facultatif)");
const send = () => screen.getByRole("button", { name: "Importer mes documents" });

describe("CvImportStep", () => {
  it("cannot send without a CV", async () => {
    const { onImport, user: u } = setup();
    expect(send()).toHaveAttribute("aria-disabled", "true");
    await u.click(send());
    expect(onImport).not.toHaveBeenCalled();
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

  it("says the documents are sent", () => {
    setup({ imported: true });
    expect(screen.getByRole("status")).toHaveTextContent("Tes documents sont envoyés");
  });
});
