import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { noteOut } from "@/test/ideApi";
import { findEditor, renderSession } from "../../ideTestkit";

const proposal = (over: Record<string, unknown> = {}) =>
  noteOut({
    id: "p1",
    kind: "proposal",
    author: "claude",
    author_label: "Claude",
    file_path: "main.py",
    line_start: 1,
    line_end: 1,
    content: "Le texte est à corriger.",
    replacement: "print('corrigé')",
    base_hash: "a".repeat(64),
    ...over,
  });

const card = async () => screen.findByRole("article", { name: "Suggestion from Claude" });

describe("IdeSessionPage, proposals", () => {
  it("shows the passage before and after the proposal", async () => {
    renderSession({ notes: [proposal()] });
    await findEditor();
    const view = await card();
    expect(within(view).getByText("print('bonjour')")).toBeInTheDocument();
    expect(within(view).getByText("print('corrigé')")).toBeInTheDocument();
  });

  it("accepting puts in the editor the text the server returns, and the focus on the list", async () => {
    const { user, calls } = renderSession({
      notes: [proposal()],
      acceptedFiles: { "main.py": "print('texte du serveur')\n" },
    });
    const editor = await findEditor();
    await user.click(within(await card()).getByRole("button", { name: "Accept" }));
    await waitFor(() => expect(calls.accepts).toEqual(["p1"]));
    // Le front n'écrit jamais le fichier lui-même : c'est celui que le serveur a rendu.
    await waitFor(() => expect(editor).toHaveValue("print('texte du serveur')\n"));
    await waitFor(() =>
      expect(screen.getByRole("heading", { level: 2, name: "Professor" })).toHaveFocus(),
    );
    expect(document.body).not.toHaveFocus();
  });

  it("saves the code first, so the server compares with what is on screen", async () => {
    const { user, calls } = renderSession({ notes: [proposal()] });
    const editor = await findEditor();
    await user.type(editor, "x");
    await user.click(within(await card()).getByRole("button", { name: "Accept" }));
    await waitFor(() => expect(calls.accepts).toEqual(["p1"]));
    expect(calls.puts).toHaveLength(1);
  });

  it("a stale refusal is shown and the file stays as it was", async () => {
    const { user } = renderSession({ notes: [proposal()], accept: "stale" });
    const editor = await findEditor();
    await user.click(within(await card()).getByRole("button", { name: "Accept" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Le code a changé depuis.");
    expect(editor).toHaveValue("print('bonjour')\n");
  });

  it("a stale proposal is greyed, says why and cannot be accepted", async () => {
    renderSession({ notes: [proposal({ status: "stale" })] });
    await findEditor();
    const view = await card();
    expect(within(view).getByText("The code has changed since")).toBeInTheDocument();
    expect(within(view).getByRole("button", { name: "Accept" })).toBeDisabled();
  });

  it("rejecting asks the server and leaves the code alone", async () => {
    const { user, calls } = renderSession({ notes: [proposal()] });
    const editor = await findEditor();
    await user.click(within(await card()).getByRole("button", { name: "Reject" }));
    await waitFor(() => expect(calls.rejects).toEqual(["p1"]));
    expect(calls.accepts).toEqual([]);
    expect(editor).toHaveValue("print('bonjour')\n");
  });
});
