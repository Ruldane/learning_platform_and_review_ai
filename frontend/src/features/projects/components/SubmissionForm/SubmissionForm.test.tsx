import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { SubmissionRefusalView } from "../viewTypes";
import { SubmissionForm } from "./SubmissionForm";

const png = (name: string, bytes = 100) =>
  new File([new Uint8Array(bytes)], name, { type: "image/png" });

function setup(busy = false, initial?: { repoUrl: string | null; description: string | null }) {
  const onSubmit = vi.fn();
  render(<SubmissionForm onSubmit={onSubmit} busy={busy} initial={initial} />);
  return { onSubmit, user: userEvent.setup() };
}

const repo = () => screen.getByLabelText("Repository link");
const description = () => screen.getByLabelText("Description");
const pickerInput = () => screen.getByLabelText("Screenshots");

describe("SubmissionForm", () => {
  it("attaches the issued GitHub claim to the selected commit and repository", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    const url = "https://github.com/orga-fictive/bibliotheque";
    const sha = "a".repeat(40);
    render(
      <SubmissionForm
        onSubmit={onSubmit}
        busy={false}
        initial={{ repoUrl: url, description: null }}
        github={{
          pending: false,
          error: null,
          request: vi.fn(),
          claim: {
            repoUrl: url,
            sha,
            id: "defi",
            code: "tremplin:exemple",
            profileUrl: "https://github.com/camille-fictive",
          },
        }}
      />,
    );
    await user.click(screen.getByText("Get a GitHub commit verified"));
    await user.type(screen.getByRole("textbox", { name: "Full commit SHA" }), sha);
    expect(screen.getByText("tremplin:exemple")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Submit the project" }));
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ githubClaimId: "defi" }));
    await user.clear(repo());
    await user.type(repo(), "https://github.com/orga-fictive/autre");
    expect(screen.queryByText("tremplin:exemple")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Submit the project" }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("starts from initial: both fields are prefilled, editable and sent as they are", async () => {
    const { onSubmit, user } = setup(false, {
      repoUrl: "https://example.org/camille/ventes",
      description: "Un pipeline SQL.",
    });
    expect(repo()).toHaveValue("https://example.org/camille/ventes");
    expect(description()).toHaveValue("Un pipeline SQL.");
    await user.click(screen.getByRole("button", { name: "Submit the project" }));
    expect(onSubmit).toHaveBeenCalledWith({
      repoUrl: "https://example.org/camille/ventes",
      description: "Un pipeline SQL.",
      screenshots: [],
    });
    await user.clear(description());
    await user.type(description(), "Corrigé.");
    expect(description()).toHaveValue("Corrigé.");
  });

  it("leaves a null initial field empty, and the other one prefilled", () => {
    setup(false, { repoUrl: null, description: "Une requête." });
    expect(repo()).toHaveValue("");
    expect(description()).toHaveValue("Une requête.");
  });

  it("sends the trimmed link, description and screenshots", async () => {
    const { onSubmit, user } = setup();
    const shot = png("a.png");
    await user.type(repo(), "  https://example.org/repo ");
    await user.type(description(), " Un pipeline SQL. ");
    await user.upload(pickerInput(), shot);
    await user.click(screen.getByRole("button", { name: "Submit the project" }));
    expect(onSubmit).toHaveBeenCalledWith({
      repoUrl: "https://example.org/repo",
      description: "Un pipeline SQL.",
      screenshots: [shot],
    });
  });

  it("accepts a description alone, or a link alone", async () => {
    const { onSubmit, user } = setup();
    await user.type(description(), "Seulement une description.");
    await user.click(screen.getByRole("button", { name: "Submit the project" }));
    expect(onSubmit).toHaveBeenCalledWith({
      repoUrl: null,
      description: "Seulement une description.",
      screenshots: [],
    });
  });

  it("asks for a link or a description and sends nothing without them", async () => {
    const { onSubmit, user } = setup();
    await user.click(screen.getByRole("button", { name: "Submit the project" }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Add a repository link or a description.",
    );
  });

  it.each(["ftp://example.org/repo", "javascript:alert(1)", "pas une adresse"])(
    "refuses the link %s with a field error",
    async (value) => {
      const { onSubmit, user } = setup();
      await user.type(repo(), value);
      await user.click(screen.getByRole("button", { name: "Submit the project" }));
      expect(onSubmit).not.toHaveBeenCalled();
      expect(repo()).toBeInvalid();
      expect(screen.getByRole("alert")).toHaveTextContent("http or https address");
    },
  );

  it("refuses a link longer than 2 048 characters", async () => {
    const { onSubmit, user } = setup();
    fireEvent.change(repo(), { target: { value: `https://example.org/${"a".repeat(2040)}` } });
    await user.click(screen.getByRole("button", { name: "Submit the project" }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(repo()).toBeInvalid();
  });

  it("counts the description and flags it as soon as it passes 4 000 characters", () => {
    setup();
    expect(screen.getByText("0 / 4,000 characters")).toBeInTheDocument();
    fireEvent.change(description(), { target: { value: "a".repeat(120) } });
    expect(screen.getByText("120 / 4,000 characters")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
    fireEvent.change(description(), { target: { value: "a".repeat(4001) } });
    expect(screen.getByText(/4,001 \/ 4,000 characters/)).toBeInTheDocument();
    expect(description()).toBeInvalid();
    expect(screen.getByRole("alert")).toHaveTextContent("4,000 characters at most");
  });

  it("blocks the submission of a description that is too long", async () => {
    const { onSubmit, user } = setup();
    fireEvent.change(description(), { target: { value: "a".repeat(4001) } });
    await user.click(screen.getByRole("button", { name: "Submit the project" }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("previews each screenshot and removes one on request", async () => {
    const { user } = setup();
    await user.upload(pickerInput(), [png("a.png"), png("b.png")]);
    expect(await screen.findByRole("img", { name: "Preview of a.png" })).toBeInTheDocument();
    expect(await screen.findByRole("img", { name: "Preview of b.png" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Remove screenshot a.png" }));
    expect(screen.queryByRole("img", { name: "Preview of a.png" })).toBeNull();
    expect(screen.getByRole("img", { name: "Preview of b.png" })).toBeInTheDocument();
  });

  it("keeps five screenshots at most and says the others were not kept", async () => {
    const { user } = setup();
    const six = ["1", "2", "3", "4", "5", "6"].map((n) => png(`${n}.png`));
    await user.upload(pickerInput(), six);
    await waitFor(() => expect(screen.getAllByRole("img")).toHaveLength(5));
    expect(screen.queryByRole("img", { name: "Preview of 6.png" })).toBeNull();
    expect(screen.getByRole("alert")).toHaveTextContent("5 screenshots at most");
    await user.upload(pickerInput(), png("7.png"));
    expect(screen.getAllByRole("img")).toHaveLength(5);
    expect(screen.getAllByRole("button", { name: /Remove screenshot/ })).toHaveLength(5);
  });

  it("refuses a screenshot that is not PNG, JPEG or WebP, or is over 5 Mo", async () => {
    const { user } = setup();
    const gif = new File([new Uint8Array(10)], "anim.gif", { type: "image/gif" });
    const huge = png("grosse.png", 5 * 1024 * 1024 + 1);
    fireEvent.change(pickerInput(), { target: { files: [gif, huge] } });
    expect(screen.queryAllByRole("img")).toHaveLength(0);
    const alerts = screen.getAllByRole("alert").map((a) => a.textContent);
    expect(alerts).toContain("Screenshot rejected (anim.gif): PNG, JPEG or WebP only.");
    expect(alerts).toContain("Screenshot rejected (grosse.png): 5 MB at most.");
    await user.upload(
      pickerInput(),
      new File([new Uint8Array(10)], "ok.webp", { type: "image/webp" }),
    );
    expect(await screen.findByRole("img", { name: "Preview of ok.webp" })).toBeInTheDocument();
  });

  it("disables everything and says it is sending while busy", () => {
    setup(true);
    expect(repo()).toBeDisabled();
    expect(description()).toBeDisabled();
    expect(pickerInput()).toBeDisabled();
    expect(screen.getByRole("button", { name: "Sending…" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(screen.getByRole("form", { name: "Submit your project" })).toHaveAttribute(
      "aria-busy",
      "true",
    );
  });

  it("counts the description in code points, like the server", () => {
    setup();
    // 4 000 émojis = 8 000 unités UTF-16 : le serveur en compte 4 000, c'est accepté.
    fireEvent.change(description(), { target: { value: "😀".repeat(4000) } });
    expect(screen.getByText("4,000 / 4,000 characters")).toBeInTheDocument();
    expect(description()).toBeValid();
    fireEvent.change(description(), { target: { value: "😀".repeat(4001) } });
    expect(screen.getByText(/4,001 \/ 4,000 characters/)).toBeInTheDocument();
    expect(description()).toBeInvalid();
  });

  it("does not remount the other previews when one is removed", async () => {
    const { user } = setup();
    await user.upload(pickerInput(), [png("a.png"), png("b.png"), png("c.png")]);
    const second = await screen.findByRole("img", { name: "Preview of b.png" });
    const third = await screen.findByRole("img", { name: "Preview of c.png" });
    await user.click(screen.getByRole("button", { name: "Remove screenshot a.png" }));
    expect(screen.queryByRole("img", { name: "Preview of a.png" })).toBeNull();
    expect(screen.getByRole("img", { name: "Preview of b.png" })).toBe(second);
    expect(screen.getByRole("img", { name: "Preview of c.png" })).toBe(third);
  });

  it("keeps two identical files apart and removes only the one asked", async () => {
    const { user } = setup();
    await user.upload(pickerInput(), png("a.png"));
    await user.upload(pickerInput(), png("a.png"));
    expect(await screen.findAllByRole("button", { name: "Remove screenshot a.png" })).toHaveLength(
      2,
    );
    await user.click(screen.getAllByRole("button", { name: "Remove screenshot a.png" })[0]!);
    expect(screen.getAllByRole("button", { name: "Remove screenshot a.png" })).toHaveLength(1);
  });

  describe("server refusal", () => {
    function withRefusal(refusal: SubmissionRefusalView) {
      const onSubmit = vi.fn();
      const view = render(<SubmissionForm onSubmit={onSubmit} busy={false} refusal={refusal} />);
      return { ...view, user: userEvent.setup(), onSubmit };
    }

    it("puts each refused field's message on that field and clears it when the field changes", async () => {
      const { user } = withRefusal({
        repoUrl: "Le serveur refuse ce lien.",
        screenshots: "Une capture n'est pas acceptée.",
      });
      expect(repo()).toBeInvalid();
      expect(repo()).toHaveAccessibleDescription(/Le serveur refuse ce lien./);
      expect(screen.getByText("Une capture n'est pas acceptée.")).toBeVisible();
      expect(description()).toBeValid();
      await user.type(repo(), "x");
      expect(repo()).toBeValid();
      expect(screen.getByText("Une capture n'est pas acceptée.")).toBeVisible();
      await user.upload(pickerInput(), png("a.png"));
      expect(screen.queryByText("Une capture n'est pas acceptée.")).toBeNull();
    });

    it("shows a refusal for « neither a link nor a description » and clears it on typing", async () => {
      const { user } = withRefusal({ missing: "Add a repository link or a description." });
      expect(screen.getByRole("alert")).toHaveTextContent("Add a repository link");
      await user.type(description(), "a");
      expect(screen.queryByRole("alert")).toBeNull();
    });
  });
});
