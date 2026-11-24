import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiKeyForm } from "./ApiKeyForm";

const KEY_FIELD = "Anthropic API key";

describe("ApiKeyForm", () => {
  it("labels the password field with the provider name", () => {
    render(<ApiKeyForm providerLabel="Anthropic" pending={false} onSave={vi.fn()} />);
    const input = screen.getByLabelText(KEY_FIELD);
    expect(input).toHaveAttribute("type", "password");
    expect(input).toHaveAttribute("autocomplete", "new-password");
    expect(input).toHaveValue("");
  });

  it("trims and saves the key on Enter, then clears the field", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<ApiKeyForm providerLabel="Anthropic" pending={false} onSave={onSave} />);
    await user.type(screen.getByLabelText(KEY_FIELD), "  sk-ant-1234  {Enter}");
    expect(onSave).toHaveBeenCalledWith("sk-ant-1234");
    expect(screen.getByLabelText(KEY_FIELD)).toHaveValue("");
  });

  it("keeps Save disabled for an empty field", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<ApiKeyForm providerLabel="Anthropic" pending={false} onSave={onSave} />);
    await user.type(screen.getByLabelText(KEY_FIELD), "   {Enter}");
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });

  it("disables saving while an operation is pending", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<ApiKeyForm providerLabel="Anthropic" pending onSave={onSave} />);
    await user.type(screen.getByLabelText(KEY_FIELD), "sk-ant-1234{Enter}");
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });

  it("keeps the key out of the DOM markup during input and after a failed save", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockRejectedValue(new Error("refus"));
    const { container } = render(
      <ApiKeyForm providerLabel="Anthropic" pending={false} onSave={onSave} />,
    );
    const input = screen.getByLabelText(KEY_FIELD);
    await user.type(input, "sk-ant-secret-1234");
    expect(input.getAttribute("value") ?? "").not.toContain("sk-ant-secret");
    expect(container.innerHTML).not.toContain("sk-ant-secret");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalledWith("sk-ant-secret-1234");
    // Après l'échec, la saisie est gardée pour réessayer, mais seulement dans la valeur du champ.
    expect(input).toHaveValue("sk-ant-secret-1234");
    expect(input.getAttribute("value") ?? "").not.toContain("sk-ant-secret");
    expect(container.innerHTML).not.toContain("sk-ant-secret");
  });

  it("enables Save when the field has text and disables it when cleared", async () => {
    const user = userEvent.setup();
    render(<ApiKeyForm providerLabel="Anthropic" pending={false} onSave={vi.fn()} />);
    const button = screen.getByRole("button", { name: "Save" });
    await user.type(screen.getByLabelText(KEY_FIELD), "a");
    expect(button).toBeEnabled();
    await user.clear(screen.getByLabelText(KEY_FIELD));
    expect(button).toBeDisabled();
  });
});
