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

const cvInput = () => screen.getByLabelText("Your CV (PDF, 10 MB max)");
const linkedinInput = () => screen.getByLabelText("Your LinkedIn profile (PDF, optional)");
const send = () => screen.getByRole("button", { name: "Import my documents" });
const KEY_STEP = "Go to the key step";
const LINKEDIN_LEFT_OUT = /Your LinkedIn profile was not kept/;

describe("CvImportStep", () => {
  it("cannot send without a CV, and says why", async () => {
    const { onImport, user: u } = setup();
    expect(send()).toHaveAttribute("aria-disabled", "true");
    expect(send()).toHaveAccessibleDescription("Choose your CV first.");
    await u.click(send());
    expect(onImport).not.toHaveBeenCalled();
    await u.upload(cvInput(), pdf());
    expect(send()).toHaveAttribute("aria-disabled", "false");
    expect(send()).not.toHaveAccessibleDescription("Choose your CV first.");
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
    expect(screen.getByRole("alert")).toHaveTextContent("This file is not a PDF");
    expect(cvInput()).toHaveAttribute("aria-invalid", "true");
    await u.click(send());
    expect(onImport).not.toHaveBeenCalled();

    await u.upload(cvInput(), pdf("cv.pdf", 11 * 1024 * 1024));
    expect(screen.getByRole("alert")).toHaveTextContent("This file is over 10 MB");
    await u.upload(cvInput(), pdf());
    expect(screen.queryByRole("alert")).toBeNull();
    expect(cvInput()).toHaveAttribute("aria-invalid", "false");
  });

  it("says a refused LinkedIn file is left out, and still sends the CV", async () => {
    const { onImport, user: u } = setup();
    const cv = pdf();
    await u.upload(cvInput(), cv);
    expect(screen.queryByText(LINKEDIN_LEFT_OUT)).toBeNull();
    await u.upload(linkedinInput(), new File(["x"], "profil.docx", { type: "application/msword" }));
    expect(screen.getByText(LINKEDIN_LEFT_OUT)).toBeInTheDocument();
    expect(send()).toHaveAccessibleDescription(LINKEDIN_LEFT_OUT);
    await u.click(send());
    expect(onImport).toHaveBeenLastCalledWith({ cv });
  });

  it("without a key, sends nothing and says a key comes first", async () => {
    const { onImport, onGoToKey, user: u } = setup({ hasKey: false });
    await u.upload(cvInput(), pdf());
    expect(send()).toHaveAttribute("aria-disabled", "true");
    expect(send()).toHaveAccessibleDescription(/Without an API key, Tremplin cannot read/);
    await u.click(send());
    expect(onImport).not.toHaveBeenCalled();
    await u.click(screen.getByRole("button", { name: KEY_STEP }));
    expect(onGoToKey).toHaveBeenCalledTimes(1);
  });

  it("does not offer the way to the key when there is one", () => {
    setup();
    expect(screen.queryByRole("button", { name: KEY_STEP })).toBeNull();
  });

  it("reminds that nothing leaves until « Importer » is clicked, once a CV is chosen", async () => {
    const { user: u } = setup();
    expect(screen.queryByText(/Nothing is sent until/)).toBeNull();
    await u.upload(cvInput(), pdf());
    expect(screen.getByText(/Nothing is sent until/)).toBeInTheDocument();
  });

  it("ignores a second click while the import goes on", async () => {
    const { onImport, user: u, pendingNow } = setup();
    await u.upload(cvInput(), pdf());
    pendingNow();
    expect(screen.getByRole("button", { name: "Sending…" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    await u.click(screen.getByRole("button", { name: "Sending…" }));
    expect(onImport).not.toHaveBeenCalled();
  });

  it("shows the refusal of the server and keeps the chosen files", () => {
    setup({ error: "Une lecture est déjà en cours." });
    expect(screen.getByRole("alert")).toHaveTextContent("Une lecture est déjà en cours.");
  });

  it("says the documents are sent, and drops the reminder", () => {
    setup({ imported: true });
    expect(screen.getByRole("status")).toHaveTextContent("Your documents have been sent");
    expect(screen.queryByText(/Nothing is sent until/)).toBeNull();
  });
});
