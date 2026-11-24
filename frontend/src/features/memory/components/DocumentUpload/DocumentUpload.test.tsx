import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DocumentUpload } from "./DocumentUpload";

function setup(overrides: Partial<Parameters<typeof DocumentUpload>[0]> = {}) {
  const props = {
    busy: false,
    error: null,
    onUploadFile: vi.fn(),
    onSubmitUrl: vi.fn(),
    onSubmitText: vi.fn(),
    ...overrides,
  };
  render(<DocumentUpload {...props} />);
  return { props, user: userEvent.setup() };
}

const fileInput = () => screen.getByLabelText("Choose a file");
const bigFile = () =>
  new File([new Uint8Array(20 * 1024 * 1024 + 1)], "gros.pdf", { type: "application/pdf" });

describe("DocumentUpload", () => {
  it("offers three tabs, the file tab first", () => {
    setup();
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual([
      "File",
      "Link",
      "Pasted text",
    ]);
    expect(screen.getByRole("tab", { name: "File", selected: true })).toBeInTheDocument();
  });

  it("restricts the file picker to the supported types", () => {
    setup();
    expect(fileInput()).toHaveAttribute("accept", ".pdf,.docx,.md,.markdown,.txt");
  });

  it("uploads an accepted file", async () => {
    const { props, user } = setup();
    const file = new File(["# Titre"], "notes.md", { type: "text/markdown" });
    await user.upload(fileInput(), file);
    expect(props.onUploadFile).toHaveBeenCalledWith(file);
  });

  it("refuses a file over 20 MB without calling back", async () => {
    const { props, user } = setup();
    await user.upload(fileInput(), bigFile());
    expect(screen.getByText("File too large: 20 MB max.")).toBeInTheDocument();
    expect(props.onUploadFile).not.toHaveBeenCalled();
  });

  it("accepts a file of exactly 20 MB", async () => {
    const { props, user } = setup();
    await user.upload(
      fileInput(),
      new File([new Uint8Array(20 * 1024 * 1024)], "limite.pdf", { type: "application/pdf" }),
    );
    expect(props.onUploadFile).toHaveBeenCalledOnce();
  });

  it("refuses an unsupported extension without calling back", async () => {
    const { props } = setup();
    // Un glisser-déposer ne passerait pas par le filtre `accept` du sélecteur natif.
    await userEvent
      .setup({ applyAccept: false })
      .upload(fileInput(), new File(["x"], "image.png", { type: "image/png" }));
    expect(
      screen.getByText("Unsupported file type: use PDF, DOCX, Markdown or text."),
    ).toBeInTheDocument();
    expect(props.onUploadFile).not.toHaveBeenCalled();
  });

  it("shows the error given by the parent", () => {
    setup({ error: "Le serveur a refusé ce fichier." });
    expect(screen.getByRole("alert")).toHaveTextContent("Le serveur a refusé ce fichier.");
  });

  it("disables the inputs while busy", async () => {
    const { user } = setup({ busy: true });
    expect(fileInput()).toBeDisabled();
    await user.click(screen.getByRole("tab", { name: "Link" }));
    expect(screen.getByLabelText("Link URL")).toBeDisabled();
  });

  it("submits a link, trimmed", async () => {
    const { props, user } = setup();
    await user.click(screen.getByRole("tab", { name: "Link" }));
    const input = screen.getByLabelText("Link URL");
    expect(input).toHaveAttribute("type", "url");
    expect(screen.getByRole("button", { name: "Import link" })).toBeDisabled();
    await user.type(input, "  https://exemple.fr/cours  ");
    await user.click(screen.getByRole("button", { name: "Import link" }));
    expect(props.onSubmitUrl).toHaveBeenCalledWith("https://exemple.fr/cours");
  });

  it("submits pasted text with an optional title, and requires the text", async () => {
    const { props, user } = setup();
    await user.click(screen.getByRole("tab", { name: "Pasted text" }));
    const submit = screen.getByRole("button", { name: "Import text" });
    expect(submit).toBeDisabled();
    await user.type(screen.getByLabelText("Text"), "Le contenu à retenir");
    expect(submit).toBeEnabled();
    await user.click(submit);
    expect(props.onSubmitText).toHaveBeenCalledWith("", "Le contenu à retenir");
    await user.type(screen.getByLabelText("Title (optional)"), "Mes notes");
    await user.click(submit);
    expect(props.onSubmitText).toHaveBeenLastCalledWith("Mes notes", "Le contenu à retenir");
  });

  it("switches tabs with the arrow keys", async () => {
    const { user } = setup();
    screen.getByRole("tab", { name: "File" }).focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Link", selected: true })).toHaveFocus();
    await user.keyboard("{ArrowLeft}");
    expect(screen.getByRole("tab", { name: "File", selected: true })).toHaveFocus();
  });

  it("clears the size error when another tab is opened", async () => {
    const { user } = setup();
    await user.upload(fileInput(), bigFile());
    await user.click(screen.getByRole("tab", { name: "Link" }));
    expect(screen.queryByText(/too large/)).not.toBeInTheDocument();
  });

  it("empties the link and pasted-text forms when resetKey changes, on the same tab", async () => {
    const props = {
      busy: false,
      error: null,
      onUploadFile: vi.fn(),
      onSubmitUrl: vi.fn(),
      onSubmitText: vi.fn(),
    };
    const user = userEvent.setup();
    const { rerender } = render(<DocumentUpload {...props} resetKey={0} />);
    await user.click(screen.getByRole("tab", { name: "Pasted text" }));
    await user.type(screen.getByLabelText("Text"), "À garder");
    rerender(<DocumentUpload {...props} resetKey={0} />);
    expect(screen.getByLabelText("Text")).toHaveValue("À garder");
    rerender(<DocumentUpload {...props} resetKey={1} />);
    expect(screen.getByRole("tab", { name: "Pasted text", selected: true })).toBeInTheDocument();
    expect(screen.getByLabelText("Text")).toHaveValue("");
    await user.click(screen.getByRole("tab", { name: "Link" }));
    await user.type(screen.getByLabelText("Link URL"), "https://exemple.fr");
    rerender(<DocumentUpload {...props} resetKey={2} />);
    expect(screen.getByLabelText("Link URL")).toHaveValue("");
  });
});
