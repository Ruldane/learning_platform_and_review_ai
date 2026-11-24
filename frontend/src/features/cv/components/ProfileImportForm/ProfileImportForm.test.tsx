import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ProfileImportForm } from "./ProfileImportForm";

// `accept` ne retient rien dans un vrai navigateur quand on choisit « tous les fichiers » :
// le composant doit donc refuser lui-même, et le test le contourne comme le ferait January.
const user = () => userEvent.setup({ applyAccept: false });
const pdf = (name = "cv.pdf", size = 1000) => {
  const file = new File(["%PDF-1.4"], name, { type: "application/pdf" });
  Object.defineProperty(file, "size", { value: size });
  return file;
};
const docx = new File(["x"], "cv.docx", {
  type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
});

function setup(props: { pending?: boolean; error?: string | null } = {}) {
  const onSubmit = vi.fn();
  render(
    <ProfileImportForm
      pending={props.pending ?? false}
      error={props.error ?? null}
      onSubmit={onSubmit}
    />,
  );
  return { onSubmit };
}

const cvInput = () => screen.getByLabelText("Your CV (PDF)");
const send = () => screen.getByRole("button", { name: "Create my master profile" });

describe("ProfileImportForm", () => {
  it("says the CV stays private", () => {
    setup();
    expect(
      screen.getByText("Your CV stays private: it's only used for your master profile."),
    ).toBeInTheDocument();
  });

  it("cannot send without a CV", () => {
    setup();
    expect(send()).toBeDisabled();
  });

  it("sends the CV alone", async () => {
    const { onSubmit } = setup();
    const file = pdf();
    await user().upload(cvInput(), file);
    await userEvent.click(send());
    expect(onSubmit).toHaveBeenCalledExactlyOnceWith({ cv: file });
  });

  it("sends the LinkedIn PDF and the trimmed note", async () => {
    const { onSubmit } = setup();
    const cv = pdf();
    const linkedin = pdf("linkedin.pdf");
    const u = user();
    await u.upload(cvInput(), cv);
    await u.upload(screen.getByLabelText("Your LinkedIn profile (PDF, optional)"), linkedin);
    await u.type(
      screen.getByLabelText("Extra details to add (optional)"),
      "  Mission en 2021. ",
    );
    await u.click(send());
    expect(onSubmit).toHaveBeenCalledExactlyOnceWith({ cv, linkedin, note: "Mission en 2021." });
  });

  it("refuses a .docx with a message and keeps the button disabled", async () => {
    const { onSubmit } = setup();
    await user().upload(cvInput(), docx);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Ce fichier n'est pas un PDF : choisis un fichier .pdf.",
    );
    expect(cvInput()).toHaveAttribute("aria-invalid", "true");
    expect(send()).toBeDisabled();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("refuses a file over 10 Mo", async () => {
    setup();
    await user().upload(cvInput(), pdf("gros.pdf", 10 * 1024 * 1024 + 1));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Ce fichier dépasse 10 Mo : choisis un PDF plus léger.",
    );
    expect(send()).toBeDisabled();
  });

  it("accepts a file of exactly 10 Mo", async () => {
    setup();
    await user().upload(cvInput(), pdf("limite.pdf", 10 * 1024 * 1024));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(send()).toBeEnabled();
  });

  it("forgets a good CV when a refused one replaces it", async () => {
    setup();
    const u = user();
    await u.upload(cvInput(), pdf());
    expect(send()).toBeEnabled();
    await u.upload(cvInput(), docx);
    expect(send()).toBeDisabled();
  });

  it("shows the failure message and locks while pending", () => {
    setup({ pending: true, error: "Envoi impossible." });
    expect(screen.getByRole("alert")).toHaveTextContent("Envoi impossible.");
    expect(screen.getByRole("button", { name: "Reading…" })).toBeDisabled();
    expect(cvInput()).toBeDisabled();
  });
});
