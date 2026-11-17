import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { hashesOf } from "@/test/ideApi";
import { AUTOSAVE_MS } from "../../hooks/useFilesDraft";
import { findEditor, renderSession } from "../../ideTestkit";

const slow = { timeout: AUTOSAVE_MS + 3000 };
const sessionFiles = (files: Record<string, string>) => ({ files });
type Options = NonNullable<Parameters<typeof renderSession>[0]>;
const filesOf = (options: Options) => (options.session as { files: Record<string, string> }).files;

describe("IdeSessionPage, a save never overwrites what Claude wrote", () => {
  it("sends the hash of the version each file was read at", async () => {
    const files = { "main.py": "a = 1\n", "util.py": "b = 1\n" };
    const { user, calls } = renderSession({ session: sessionFiles(files) });
    await user.type(await findEditor(), "x");
    await waitFor(() => expect(calls.puts).toHaveLength(1), slow);
    expect(calls.puts[0]).toMatchObject({ base_hashes: hashesOf(files) });
  });

  it("a save refused because Claude wrote meanwhile offers the choice and loses nothing", async () => {
    const options: Options = { session: sessionFiles({ "main.py": "a = 1\n" }) };
    const { user, calls } = renderSession(options);
    const editor = await findEditor();
    await user.type(editor, "b");
    options.session = sessionFiles({ "main.py": "a = 2\n" }); // Claude écrit, la page ne l'a pas relu
    const card = await screen.findByRole(
      "alert",
      { name: "Claude a modifié main.py pendant que tu écrivais" },
      slow,
    );
    expect(calls.puts.length).toBeGreaterThanOrEqual(1);
    expect(filesOf(options)).toEqual({ "main.py": "a = 2\n" }); // rien d'écrit par le refus
    expect(editor).toHaveValue("a = 1\nb"); // ta frappe est restée
    const refused = calls.puts.length;
    // « Garder la mienne » renvoie avec les empreintes à jour : cette fois le serveur accepte.
    await user.click(within(card).getByRole("button", { name: "Garder la mienne" }));
    await waitFor(() => expect(calls.puts.length).toBe(refused + 1), slow);
    expect(calls.puts[refused]).toMatchObject({ base_hashes: hashesOf({ "main.py": "a = 2\n" }) });
    await waitFor(() => expect(filesOf(options)).toEqual({ "main.py": "a = 1\nb" }));
    expect(screen.queryByRole("alert", { name: /pendant que tu écrivais/ })).toBeNull();
  });

  it("a file you did not touch keeps Claude's version when you save another one", async () => {
    const files = { "main.py": "a = 1\n", "util.py": "b = 1\n" };
    const options: Options = { session: sessionFiles(files) };
    const { user, calls } = renderSession(options);
    await user.type(await findEditor(), "x");
    options.session = sessionFiles({ ...files, "util.py": "b = 2\n" }); // Claude, pas encore relu
    await waitFor(() => expect(calls.puts.length).toBeGreaterThanOrEqual(2), slow);
    // le premier envoi était refusé ; le second repart de la version relue, et la garde
    expect(filesOf(options)).toEqual({ "main.py": "a = 1\nx", "util.py": "b = 2\n" });
    const tabs = screen.getByRole("navigation", { name: "Fichiers de la séance" });
    expect(
      within(tabs).getByRole("button", { name: "util.py (modifié par Claude)" }),
    ).toBeInTheDocument();
  });

  it("does not show a save error for the refusal itself", async () => {
    const options: Options = { session: sessionFiles({ "main.py": "a = 1\n" }) };
    const { user, calls } = renderSession(options);
    await user.type(await findEditor(), "b");
    options.session = sessionFiles({ "main.py": "a = 2\n" });
    await waitFor(() => expect(calls.puts.length).toBeGreaterThanOrEqual(1), slow);
    await screen.findByRole("alert", { name: /pendant que tu écrivais/ }, slow);
    expect(screen.queryByText(/L'enregistrement a échoué/)).toBeNull();
  });
});
