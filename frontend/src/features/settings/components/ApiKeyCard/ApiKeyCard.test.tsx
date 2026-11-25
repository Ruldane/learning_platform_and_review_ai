import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ApiKeyEntry } from "../viewTypes";
import { ApiKeyCard } from "./ApiKeyCard";

const entry: ApiKeyEntry = {
  provider: "anthropic",
  label: "Anthropic",
  source: "ui",
  last4: "1234",
  readable: true,
  last_test_ok: null,
};

const noop = () => undefined;
const KEY_FIELD = "Anthropic API key";

describe("ApiKeyCard", () => {
  it("keeps the key hidden and clears the field after saving", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(
      <ApiKeyCard entry={entry} pending={false} onSave={onSave} onDelete={noop} onTest={noop} />,
    );
    await user.type(screen.getByLabelText(KEY_FIELD), "sk-ant-secret-1234");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalledWith("sk-ant-secret-1234");
    expect(screen.getByLabelText(KEY_FIELD)).toHaveValue("");
    expect(screen.getByText("•••• 1234")).toBeInTheDocument();
    expect(screen.queryByText(/sk-ant/)).not.toBeInTheDocument();
    expect(document.body.innerHTML).not.toContain("sk-ant-secret");
  });

  it("keeps the value if saving fails and clears it after a successful retry", async () => {
    const user = userEvent.setup();
    const onSave = vi
      .fn()
      .mockRejectedValueOnce(new Error("refus"))
      .mockResolvedValueOnce(undefined);
    render(
      <ApiKeyCard entry={entry} pending={false} onSave={onSave} onDelete={noop} onTest={noop} />,
    );
    await user.type(screen.getByLabelText(KEY_FIELD), "sk-ant-secret-1234");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByLabelText(KEY_FIELD)).toHaveValue("sk-ant-secret-1234");
    expect(document.body.innerHTML).not.toContain("sk-ant-secret");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByLabelText(KEY_FIELD)).toHaveValue("");
  });

  it("uses an empty password field with no autofill", () => {
    render(
      <ApiKeyCard entry={entry} pending={false} onSave={noop} onDelete={noop} onTest={noop} />,
    );
    const input = screen.getByLabelText(KEY_FIELD);
    expect(input).toHaveAttribute("type", "password");
    expect(input).toHaveAttribute("autocomplete", "new-password");
    expect(input).toHaveValue("");
  });

  it("disables Save while the field is empty", () => {
    render(
      <ApiKeyCard entry={entry} pending={false} onSave={noop} onDelete={noop} onTest={noop} />,
    );
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });

  it("reports an unreadable key", () => {
    render(
      <ApiKeyCard
        entry={{ ...entry, readable: false }}
        pending={false}
        onSave={noop}
        onDelete={noop}
        onTest={noop}
      />,
    );
    expect(screen.getByText("Unreadable key, enter it again")).toBeInTheDocument();
  });

  it("shows where a key was entered and offers to delete it", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    render(
      <ApiKeyCard entry={entry} pending={false} onSave={noop} onDelete={onDelete} onTest={noop} />,
    );
    expect(screen.getByText("entered here")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(onDelete).toHaveBeenCalledTimes(1);
  });

  it("identifies a key from the .env file and hides Delete", () => {
    render(
      <ApiKeyCard
        entry={{ ...entry, source: "env" }}
        pending={false}
        onSave={noop}
        onDelete={noop}
        onTest={noop}
      />,
    );
    expect(screen.getByText(".env file")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
    expect(screen.getByText(/remove it from that file/)).toBeInTheDocument();
  });

  it("reports a missing key and disables Test", () => {
    render(
      <ApiKeyCard
        entry={{ ...entry, source: null, last4: null }}
        pending={false}
        onSave={noop}
        onDelete={noop}
        onTest={noop}
      />,
    );
    expect(screen.getByText("No key saved")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Test" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });

  it("starts the test and announces the result in a status region", async () => {
    const user = userEvent.setup();
    const onTest = vi.fn();
    const { rerender } = render(
      <ApiKeyCard entry={entry} pending={false} onSave={noop} onDelete={noop} onTest={onTest} />,
    );
    await user.click(screen.getByRole("button", { name: "Test" }));
    expect(onTest).toHaveBeenCalledTimes(1);
    rerender(
      <ApiKeyCard
        entry={entry}
        testResult={{ ok: true, message: "Clé valide." }}
        pending={false}
        onSave={noop}
        onDelete={noop}
        onTest={onTest}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Clé valide.");
  });

  it("disables the buttons while an operation is pending", () => {
    render(<ApiKeyCard entry={entry} pending onSave={noop} onDelete={noop} onTest={noop} />);
    expect(screen.getByRole("button", { name: "Test" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Delete" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });

  it("shows the last test result saved by the server", () => {
    render(
      <ApiKeyCard
        entry={{ ...entry, last_test_ok: false }}
        pending={false}
        onSave={noop}
        onDelete={noop}
        onTest={noop}
      />,
    );
    expect(screen.getByText("Last test: failed")).toBeInTheDocument();
  });
});
