import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChatComposer } from "../ChatComposer";
import { ChatMessage } from "../ChatMessage";
import { ChatThread } from "./ChatThread";

describe("chat components", () => {
  it("shows the role, Markdown response and document link in the conversation", () => {
    render(
      <ChatThread label="Conversation avec le bibliothécaire" emptyText="Écris un message">
        <ChatMessage author="assistant" label="Le bibliothécaire" content="Un **retriever**.">
          <a href="/memoire?document=note-1">Note sur la recherche</a>
        </ChatMessage>
      </ChatThread>,
    );
    const thread = screen.getByRole("log", { name: "Conversation avec le bibliothécaire" });
    const message = within(thread).getByRole("article", { name: "Le bibliothécaire" });
    expect(within(message).getByText("retriever").tagName).toBe("STRONG");
    expect(within(message).getByRole("link", { name: "Note sur la recherche" })).toHaveAttribute(
      "href",
      "/memoire?document=note-1",
    );
  });

  it("keeps rejected text and accepts a different prompt label", async () => {
    const user = userEvent.setup();
    const send = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    render(
      <ChatComposer busy={false} label="Sujet du training" placeholder="Exercice" onSend={send} />,
    );
    const input = screen.getByRole("textbox", { name: "Sujet du training" });
    await user.type(input, "Revoir les boucles{Enter}");
    expect(send).toHaveBeenNthCalledWith(1, "Revoir les boucles");
    expect(input).toHaveValue("Revoir les boucles");
    await user.keyboard("{Enter}");
    expect(send).toHaveBeenNthCalledWith(2, "Revoir les boucles");
    expect(input).toHaveValue("");
  });
});
