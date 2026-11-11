import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MessageComposer } from "./MessageComposer";

describe("MessageComposer", () => {
  it("sends on Enter and keeps newline on Shift+Enter", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<MessageComposer disabled={false} onSend={onSend} />);
    const field = screen.getByRole("textbox", { name: "Ton message" });
    await user.type(field, "ligne 1{Shift>}{Enter}{/Shift}ligne 2");
    expect(onSend).not.toHaveBeenCalled();
    expect(field).toHaveValue("ligne 1\nligne 2");
    await user.keyboard("{Enter}");
    expect(onSend).toHaveBeenCalledWith("ligne 1\nligne 2");
    expect(field).toHaveValue("");
  });

  it("sends with the button and ignores blank messages", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<MessageComposer disabled={false} onSend={onSend} />);
    await user.type(screen.getByRole("textbox"), "   {Enter}");
    expect(onSend).not.toHaveBeenCalled();
    await user.clear(screen.getByRole("textbox"));
    await user.type(screen.getByRole("textbox"), "Salut");
    await user.click(screen.getByRole("button", { name: "Envoyer" }));
    expect(onSend).toHaveBeenCalledWith("Salut");
  });

  it("is fully disabled when asked to", () => {
    render(<MessageComposer disabled onSend={vi.fn()} />);
    expect(screen.getByRole("textbox")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Envoyer" })).toBeDisabled();
  });
});
