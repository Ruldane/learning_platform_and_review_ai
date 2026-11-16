import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SubmissionForm } from "./SubmissionForm";

const png = (name: string, bytes = 100) =>
  new File([new Uint8Array(bytes)], name, { type: "image/png" });

function setup(busy = false) {
  const onSubmit = vi.fn();
  render(<SubmissionForm onSubmit={onSubmit} busy={busy} />);
  return { onSubmit, user: userEvent.setup() };
}

const repo = () => screen.getByLabelText("Lien du dépôt");
const description = () => screen.getByLabelText("Description");
const pickerInput = () => screen.getByLabelText("Captures d'écran");

describe("SubmissionForm", () => {
  it("sends the trimmed link, description and screenshots", async () => {
    const { onSubmit, user } = setup();
    const shot = png("a.png");
    await user.type(repo(), "  https://example.org/repo ");
    await user.type(description(), " Un pipeline SQL. ");
    await user.upload(pickerInput(), shot);
    await user.click(screen.getByRole("button", { name: "Rendre le projet" }));
    expect(onSubmit).toHaveBeenCalledWith({
      repoUrl: "https://example.org/repo",
      description: "Un pipeline SQL.",
      screenshots: [shot],
    });
  });

  it("accepts a description alone, or a link alone", async () => {
    const { onSubmit, user } = setup();
    await user.type(description(), "Seulement une description.");
    await user.click(screen.getByRole("button", { name: "Rendre le projet" }));
    expect(onSubmit).toHaveBeenCalledWith({
      repoUrl: null,
      description: "Seulement une description.",
      screenshots: [],
    });
  });

  it("asks for a link or a description and sends nothing without them", async () => {
    const { onSubmit, user } = setup();
    await user.click(screen.getByRole("button", { name: "Rendre le projet" }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Ajoute un lien de dépôt ou une description.",
    );
  });

  it.each(["ftp://example.org/repo", "javascript:alert(1)", "pas une adresse"])(
    "refuses the link %s with a field error",
    async (value) => {
      const { onSubmit, user } = setup();
      await user.type(repo(), value);
      await user.click(screen.getByRole("button", { name: "Rendre le projet" }));
      expect(onSubmit).not.toHaveBeenCalled();
      expect(repo()).toBeInvalid();
      expect(screen.getByRole("alert")).toHaveTextContent("adresse http ou https");
    },
  );

  it("refuses a link longer than 2 048 characters", async () => {
    const { onSubmit, user } = setup();
    fireEvent.change(repo(), { target: { value: `https://example.org/${"a".repeat(2040)}` } });
    await user.click(screen.getByRole("button", { name: "Rendre le projet" }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(repo()).toBeInvalid();
  });

  it("counts the description and flags it as soon as it passes 4 000 characters", () => {
    setup();
    expect(screen.getByText("0 / 4 000 caractères")).toBeInTheDocument();
    fireEvent.change(description(), { target: { value: "a".repeat(120) } });
    expect(screen.getByText("120 / 4 000 caractères")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
    fireEvent.change(description(), { target: { value: "a".repeat(4001) } });
    expect(screen.getByText(/4 001 \/ 4 000 caractères/)).toBeInTheDocument();
    expect(description()).toBeInvalid();
    expect(screen.getByRole("alert")).toHaveTextContent("4 000 caractères au plus");
  });

  it("blocks the submission of a description that is too long", async () => {
    const { onSubmit, user } = setup();
    fireEvent.change(description(), { target: { value: "a".repeat(4001) } });
    await user.click(screen.getByRole("button", { name: "Rendre le projet" }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("previews each screenshot and removes one on request", async () => {
    const { user } = setup();
    await user.upload(pickerInput(), [png("a.png"), png("b.png")]);
    expect(await screen.findByRole("img", { name: "Aperçu de a.png" })).toBeInTheDocument();
    expect(await screen.findByRole("img", { name: "Aperçu de b.png" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retirer la capture a.png" }));
    expect(screen.queryByRole("img", { name: "Aperçu de a.png" })).toBeNull();
    expect(screen.getByRole("img", { name: "Aperçu de b.png" })).toBeInTheDocument();
  });

  it("keeps five screenshots at most and says the others were not kept", async () => {
    const { user } = setup();
    const six = ["1", "2", "3", "4", "5", "6"].map((n) => png(`${n}.png`));
    await user.upload(pickerInput(), six);
    await waitFor(() => expect(screen.getAllByRole("img")).toHaveLength(5));
    expect(screen.queryByRole("img", { name: "Aperçu de 6.png" })).toBeNull();
    expect(screen.getByRole("alert")).toHaveTextContent("5 captures au plus");
    await user.upload(pickerInput(), png("7.png"));
    expect(screen.getAllByRole("img")).toHaveLength(5);
    expect(screen.getAllByRole("button", { name: /Retirer la capture/ })).toHaveLength(5);
  });

  it("refuses a screenshot that is not PNG, JPEG or WebP, or is over 5 Mo", async () => {
    const { user } = setup();
    const gif = new File([new Uint8Array(10)], "anim.gif", { type: "image/gif" });
    const huge = png("grosse.png", 5 * 1024 * 1024 + 1);
    fireEvent.change(pickerInput(), { target: { files: [gif, huge] } });
    expect(screen.queryAllByRole("img")).toHaveLength(0);
    const alerts = screen.getAllByRole("alert").map((a) => a.textContent);
    expect(alerts).toContain("Capture refusée (anim.gif) : PNG, JPEG ou WebP seulement.");
    expect(alerts).toContain("Capture refusée (grosse.png) : 5 Mo au plus.");
    await user.upload(
      pickerInput(),
      new File([new Uint8Array(10)], "ok.webp", { type: "image/webp" }),
    );
    expect(await screen.findByRole("img", { name: "Aperçu de ok.webp" })).toBeInTheDocument();
  });

  it("disables everything and says it is sending while busy", () => {
    setup(true);
    expect(repo()).toBeDisabled();
    expect(description()).toBeDisabled();
    expect(pickerInput()).toBeDisabled();
    expect(screen.getByRole("button", { name: "Envoi en cours…" })).toBeDisabled();
    expect(screen.getByRole("form", { name: "Rendre ton projet" })).toHaveAttribute(
      "aria-busy",
      "true",
    );
  });
});
