import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { councilEvents } from "@/test/councilEvents";
import { noteOut } from "@/test/ideApi";
import { findEditor, refresh, renderSession } from "../../ideTestkit";

const THREAD = { name: "Conversation with the professor" };
const ask = (content: string, id = "q1", at = "2026-11-17T10:05:00Z") =>
  noteOut({ id, kind: "question", author: "user", author_label: null, content, created_at: at });
const answer = (content: string, id = "a1", at = "2026-11-17T10:06:00Z") =>
  noteOut({ id, kind: "explanation", content, created_at: at });

/** Un conteneur qui défile : jsdom ne mesure rien, la hauteur et la position sont posées ici. */
function scrollable(el: HTMLElement, top: number) {
  let scrollTop = top;
  Object.defineProperty(el, "clientHeight", { value: 100, configurable: true });
  Object.defineProperty(el, "scrollHeight", { value: 500, configurable: true });
  Object.defineProperty(el, "scrollTop", {
    get: () => scrollTop,
    set: (value: number) => {
      scrollTop = value;
    },
    configurable: true,
  });
  return { top: () => scrollTop };
}

describe("IdeSessionPage, the teacher chat", () => {
  it("orders the thread, her messages on the right and the teacher's on the left", async () => {
    renderSession({ notes: [answer("Une boucle répète."), ask("C'est quoi une boucle ?")] });
    await findEditor();
    const thread = await screen.findByRole("log", THREAD);
    const messages = await within(thread).findAllByRole("article");
    expect(messages.map((m) => m.textContent)).toEqual([
      expect.stringContaining("C'est quoi une boucle ?"),
      expect.stringContaining("Une boucle répète."),
    ]);
    expect(messages[0]).toHaveAttribute("data-author", "user");
    expect(messages[0]?.closest("li")?.className).toContain("justify-end");
    expect(within(messages[0] as HTMLElement).getByText("You")).toBeVisible();
    expect(messages[1]?.closest("li")?.className).toContain("justify-start");
    expect(within(messages[1] as HTMLElement).getByText("The professor")).toBeVisible();
  });

  it("tags a note nobody asked for, not an answer", async () => {
    renderSession({
      notes: [
        answer("Bravo.", "c1", "2026-11-17T10:01:00Z"),
        ask("Et ça ?", "q1", "2026-11-17T10:02:00Z"),
        answer("Ça marche ainsi.", "a1", "2026-11-17T10:03:00Z"),
      ],
    });
    await findEditor();
    const thread = await screen.findByRole("log", THREAD);
    const [first, , reply] = await within(thread).findAllByRole("article");
    expect(first).toHaveAccessibleName("The professor · after a run");
    expect(reply).toHaveAccessibleName("The professor");
  });

  it("Enter sends the question, Shift+Enter makes a new line", async () => {
    const { user, calls } = renderSession();
    await findEditor();
    const field = screen.getByRole("textbox", { name: "Your question" });
    await user.type(field, "ligne un{Shift>}{Enter}{/Shift}ligne deux");
    expect(field).toHaveValue("ligne un\nligne deux");
    expect(calls.teach).toHaveLength(0);
    await user.type(field, "{Enter}");
    await waitFor(() => expect(calls.teach).toHaveLength(1));
    expect(calls.teach[0]).toMatchObject({
      trigger: "question",
      question: "ligne un\nligne deux",
    });
    await waitFor(() => expect(field).toHaveValue(""));
  });

  it("shows her question at once, the teacher writing, and holds Envoyer meanwhile", async () => {
    const { user, sockets } = renderSession({ teach: { session_id: "t1" } });
    await findEditor();
    const field = screen.getByRole("textbox", { name: "Your question" });
    await user.type(field, "Pourquoi ?{Enter}");
    const thread = await screen.findByRole("log", THREAD);
    expect(await within(thread).findByText("Pourquoi ?")).toBeVisible();
    expect(await screen.findByText("The professor is writing…")).toBeVisible();
    await user.type(field, "encore");
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
    await waitFor(() => expect(sockets.sockets.length).toBeGreaterThan(0));
    const stream = sockets.sockets.find((s) => s.url.includes("/sessions/t1/stream"));
    act(() => {
      stream?.open().push(councilEvents("t1").completed());
    });
    await waitFor(() => expect(screen.queryByText("The professor is writing…")).toBeNull());
    expect(screen.getByRole("button", { name: "Send" })).toBeEnabled();
  });

  it("keeps the typed text and says why when the teacher cannot take the question", async () => {
    const { user } = renderSession({ teach: { skipped: "busy" } });
    await findEditor();
    const field = screen.getByRole("textbox", { name: "Your question" });
    await user.type(field, "Ma question{Enter}");
    expect(await screen.findByText(/The professor is already working/)).toBeVisible();
    expect(field).toHaveValue("Ma question");
    expect(within(screen.getByRole("log", THREAD)).queryByText("Ma question")).toBeNull();
  });

  it("scrolls inside the thread and offers « Nouveaux messages » when she scrolled up", async () => {
    const options: Parameters<typeof renderSession>[0] = { notes: [ask("Première ?")] };
    const { user } = renderSession(options);
    await findEditor();
    const thread = await screen.findByRole("log", THREAD);
    expect(thread.className).toContain("overflow-y-auto");
    const geometry = scrollable(thread, 0);
    fireEvent.scroll(thread);
    options.notes = [ask("Première ?"), answer("Voici.")];
    await refresh();
    await within(thread).findByText("Voici.");
    const more = await screen.findByRole("button", { name: "New messages ↓" });
    expect(geometry.top()).toBe(0);
    await user.click(more);
    expect(geometry.top()).toBe(500);
    expect(screen.queryByRole("button", { name: "New messages ↓" })).toBeNull();
  });

  it("follows the last message when she is at the bottom", async () => {
    const options: Parameters<typeof renderSession>[0] = { notes: [ask("Première ?")] };
    renderSession(options);
    await findEditor();
    const thread = await screen.findByRole("log", THREAD);
    const geometry = scrollable(thread, 400);
    fireEvent.scroll(thread);
    options.notes = [ask("Première ?"), answer("Voici.")];
    await refresh();
    await within(thread).findByText("Voici.");
    expect(geometry.top()).toBe(500);
    expect(screen.queryByRole("button", { name: "New messages ↓" })).toBeNull();
  });

  it("renders the teacher's Markdown and never raw HTML", async () => {
    const hostile = [
      "Voici **gras**, `x = 1` et une liste :",
      "",
      "- un",
      "- deux",
      "",
      "```python",
      "print('ok')",
      "```",
      "",
      "<script>window.__pwn = 1</script><img src=x onerror=alert(1)>",
      "[piège](javascript:alert(1)) et [doc](https://docs.python.org)",
    ].join("\n");
    renderSession({ notes: [answer(hostile)] });
    await findEditor();
    const thread = await screen.findByRole("log", THREAD);
    await within(thread).findByText("gras");
    expect(within(thread).getByText("gras").tagName).toBe("STRONG");
    expect(within(thread).getByText("x = 1").tagName).toBe("CODE");
    expect(within(thread).getAllByRole("listitem").length).toBeGreaterThanOrEqual(2);
    expect(thread.querySelector("pre code")?.textContent).toContain("print('ok')");
    expect(thread.querySelector("script, img, iframe")).toBeNull();
    expect(thread.querySelector('a[href^="javascript"]')).toBeNull();
    expect(within(thread).getByRole("link", { name: "doc" })).toHaveAttribute(
      "href",
      "https://docs.python.org",
    );
    expect((window as unknown as { __pwn?: number }).__pwn).toBeUndefined();
  });

  it("accepts a proposal from the thread", async () => {
    const { user, calls } = renderSession({
      notes: [
        ask("Corrige-moi."),
        noteOut({
          id: "p1",
          kind: "proposal",
          author: "professor",
          file_path: "main.py",
          line_start: 1,
          line_end: 1,
          content: "Je remplace cette ligne.",
          replacement: "print('corrigé')",
          base_hash: "a".repeat(64),
          created_at: "2026-11-17T10:06:00Z",
        }),
      ],
    });
    await findEditor();
    const thread = await screen.findByRole("log", THREAD);
    const card = await within(thread).findByRole("article", { name: /^Suggestion from/ });
    await user.click(within(card).getByRole("button", { name: "Accept" }));
    await waitFor(() => expect(calls.accepts).toEqual(["p1"]));
  });
});
