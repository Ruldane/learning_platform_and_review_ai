import { focusManager } from "@tanstack/react-query";
import { screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { noteOut } from "@/test/ideApi";
import { AUTOSAVE_MS } from "../../hooks/useFilesDraft";
import { findEditor, refresh, renderSession, settle } from "../../ideTestkit";

afterEach(() => focusManager.setFocused(undefined));

describe("IdeSessionPage, files changed by Claude", () => {
  const sessionFiles = (files: Record<string, string>) => ({ files });

  it("loads Claude's version and says so when there are no unsaved edits", async () => {
    const options: Parameters<typeof renderSession>[0] = {
      session: sessionFiles({ "main.py": "a = 1\n" }),
    };
    const { calls } = renderSession(options);
    const editor = await findEditor();
    options.session = sessionFiles({ "main.py": "a = 2\n" });
    await refresh();
    await waitFor(() => expect(editor).toHaveValue("a = 2\n"));
    expect(await screen.findByText("Claude changed this file.")).toBeInTheDocument();
    await settle(AUTOSAVE_MS + 300);
    expect(calls.puts).toHaveLength(0); // rien n'est renvoyé au serveur
    await screen.findByText("Saved");
  });

  it("the message goes away on its own button and when you type in the file", async () => {
    const options: Parameters<typeof renderSession>[0] = {
      session: sessionFiles({ "main.py": "a = 1\n" }),
    };
    const { user } = renderSession(options);
    const editor = await findEditor();
    options.session = sessionFiles({ "main.py": "a = 2\n" });
    await refresh();
    await user.click(await screen.findByRole("button", { name: "Got it" }));
    expect(screen.queryByText("Claude changed this file.")).toBeNull();
    options.session = sessionFiles({ "main.py": "a = 3\n" });
    await refresh();
    await screen.findByText("Claude changed this file.");
    await user.type(editor, "!");
    expect(screen.queryByText("Claude changed this file.")).toBeNull();
  });

  it("flags in the tabs the other files Claude changed", async () => {
    const options: Parameters<typeof renderSession>[0] = {
      session: sessionFiles({ "main.py": "a = 1\n", "util.py": "b = 1\n" }),
    };
    renderSession(options);
    await findEditor();
    options.session = sessionFiles({ "main.py": "a = 1\n", "util.py": "b = 2\n" });
    await refresh();
    const files = screen.getByRole("navigation", { name: "Session files" });
    expect(
      await within(files).findByRole("button", { name: "util.py (changed by Claude)" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Claude changed this file.")).toBeNull(); // pas le fichier ouvert
  });

  describe("with unsaved edits in the same file", () => {
    async function conflict() {
      const options: Parameters<typeof renderSession>[0] = {
        session: sessionFiles({ "main.py": "a = 1\n" }),
      };
      const view = renderSession(options);
      const editor = await findEditor();
      await view.user.type(editor, "b");
      options.session = sessionFiles({ "main.py": "a = 2\n" });
      await refresh();
      const card = await screen.findByRole("alert", {
        name: "Claude changed main.py while you were typing",
      });
      return { ...view, editor, card, options };
    }

    it("keeps your text, sends nothing, and offers both choices", async () => {
      const { calls, editor, card } = await conflict();
      expect(editor).toHaveValue("a = 1\nb");
      expect(within(card).getByRole("button", { name: "View Claude's version" })).toBeVisible();
      expect(within(card).getByRole("button", { name: "Keep mine" })).toBeVisible();
      await settle(AUTOSAVE_MS + 300);
      expect(calls.puts).toHaveLength(0); // jamais d'écrasement de la version de Claude
      expect(editor).toHaveValue("a = 1\nb");
    });

    it("shows Claude's version without touching yours", async () => {
      const { user, card, editor } = await conflict();
      await user.click(within(card).getByRole("button", { name: "View Claude's version" }));
      expect(within(card).getByLabelText("Claude's version of main.py")).toHaveTextContent(
        "a = 2",
      );
      expect(editor).toHaveValue("a = 1\nb");
      await user.click(within(card).getByRole("button", { name: "Hide Claude's version" }));
      expect(within(card).queryByLabelText("Claude's version of main.py")).toBeNull();
    });

    it("does not run while the conflict is open: the code on screen is not saved", async () => {
      const { user, calls } = await conflict();
      await user.click(screen.getByRole("button", { name: /^Run code/ }));
      expect(
        await screen.findByText("The code could not be saved, so it was not run."),
      ).toBeInTheDocument();
      expect(calls.runs).toHaveLength(0);
      expect(calls.puts).toHaveLength(0);
    });

    it("« Garder la mienne » keeps your text and saves it", async () => {
      const { user, calls, card, editor } = await conflict();
      await user.click(within(card).getByRole("button", { name: "Keep mine" }));
      expect(screen.queryByRole("alert", { name: /while you were typing/ })).toBeNull();
      await waitFor(() => expect(calls.puts).toHaveLength(1), { timeout: AUTOSAVE_MS + 2000 });
      expect(calls.puts[0]).toMatchObject({ files: { "main.py": "a = 1\nb" }, entry: "main.py" });
      expect(editor).toHaveValue("a = 1\nb");
      await refresh();
      await settle(300);
      expect(screen.queryByRole("alert", { name: /while you were typing/ })).toBeNull();
    });

    it("« Prendre celle de Claude » drops your edits for that file, and sends nothing", async () => {
      const { user, calls, card, editor } = await conflict();
      await user.click(within(card).getByRole("button", { name: "View Claude's version" }));
      await user.click(within(card).getByRole("button", { name: "Take Claude's" }));
      await user.click(within(card).getByRole("button", { name: "Discard my edits" }));
      await waitFor(() => expect(editor).toHaveValue("a = 2\n"));
      expect(await screen.findByText("Claude changed this file.")).toBeInTheDocument();
      expect(screen.queryByRole("alert", { name: /while you were typing/ })).toBeNull();
      await settle(AUTOSAVE_MS + 300);
      expect(calls.puts).toHaveLength(0);
    });

    it("a second change by Claude updates the version offered", async () => {
      const { user, card, options } = await conflict();
      options.session = sessionFiles({ "main.py": "a = 3\n" });
      await refresh();
      await user.click(within(card).getByRole("button", { name: "View Claude's version" }));
      await waitFor(() =>
        expect(within(card).getByLabelText("Claude's version of main.py")).toHaveTextContent(
          "a = 3",
        ),
      );
    });

    it("saves the edits of the other files meanwhile, and keeps the conflicted one aside", async () => {
      const options: Parameters<typeof renderSession>[0] = {
        session: sessionFiles({ "main.py": "a = 1\n", "util.py": "b = 1\n" }),
      };
      const { user, calls } = renderSession(options);
      const editor = await findEditor();
      await user.type(editor, "x");
      const files = screen.getByRole("navigation", { name: "Session files" });
      await user.click(within(files).getByRole("button", { name: "util.py" }));
      await user.type(editor, "y");
      options.session = sessionFiles({ "main.py": "a = 2\n", "util.py": "b = 1\n" });
      await refresh();
      await screen.findByRole("alert", { name: /Claude changed main\.py/ });
      await waitFor(() => expect(calls.puts).toHaveLength(1), { timeout: AUTOSAVE_MS + 2000 });
      // util.py part ; main.py garde la version de Claude côté serveur, la tienne reste à l'écran
      expect(calls.puts[0]).toMatchObject({
        files: { "main.py": "a = 2\n", "util.py": "b = 1\ny" },
        entry: "main.py",
      });
      expect(screen.getByRole("alert", { name: /Claude changed main\.py/ })).toBeInTheDocument();
      await user.click(within(files).getByRole("button", { name: "main.py (run file)" }));
      expect(editor).toHaveValue("a = 1\nx");
    });
  });

  it("your own save is never taken for a change by Claude", async () => {
    const { user, calls } = renderSession();
    const editor = await findEditor();
    await user.type(editor, "y");
    await waitFor(() => expect(calls.puts).toHaveLength(1), { timeout: AUTOSAVE_MS + 2000 });
    await screen.findByText("Saved");
    await refresh();
    await settle(300);
    expect(screen.queryByText("Claude changed this file.")).toBeNull();
    expect(screen.queryByRole("alert", { name: /while you were typing/ })).toBeNull();
  });

  it("an accepted proposal is not taken for a change by Claude", async () => {
    const { user } = renderSession({
      notes: [
        noteOut({
          id: "p1",
          kind: "proposal",
          author: "claude",
          author_label: "Claude",
          origin: "mcp",
          file_path: "main.py",
          line_start: 1,
          line_end: 1,
          replacement: "print('corrigé')",
          base_hash: "a".repeat(64),
        }),
      ],
      acceptedFiles: { "main.py": "print('corrigé')\n" },
    });
    const editor = await findEditor();
    await user.click(await screen.findByRole("button", { name: "Accept" }));
    await waitFor(() => expect(editor).toHaveValue("print('corrigé')\n"));
    await refresh();
    await settle(300);
    expect(screen.queryByText("Claude changed this file.")).toBeNull();
  });
});
