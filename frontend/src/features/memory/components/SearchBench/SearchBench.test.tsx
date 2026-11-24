import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { hit } from "../viewFixtures";
import { SearchBench } from "./SearchBench";

const base = { result: null, pending: false, onRun: vi.fn() };

async function run(onRun: () => void, k?: string) {
  const user = userEvent.setup();
  render(<SearchBench {...base} onRun={onRun} />);
  await user.type(screen.getByLabelText("Query"), "attention");
  if (k !== undefined)
    fireEvent.change(screen.getByLabelText("Number of results"), { target: { value: k } });
  await user.click(screen.getByRole("button", { name: "Run" }));
}

describe("SearchBench", () => {
  it("shows the agent text verbatim with k = 8 by default", async () => {
    const onRun = vi.fn();
    await run(onRun);
    expect(onRun).toHaveBeenCalledWith("attention", [], 8);
  });

  it("renders the agent text untouched in a pre", () => {
    const agentText = '<<<CONTENU_NON_FIABLE source="memory">>>\n  ligne  indentée\n<<<FIN>>>';
    const { container } = render(<SearchBench {...base} result={{ hits: [hit()], agentText }} />);
    const pre = container.querySelector("pre");
    expect(pre?.textContent).toBe(agentText);
  });

  it("shows the retrieved fragments with their scores", () => {
    render(<SearchBench {...base} result={{ hits: [hit()], agentText: "texte" }} />);
    expect(screen.getByText("0.83")).toBeInTheDocument();
    expect(screen.getByText("Cours NLP")).toBeInTheDocument();
  });

  it("clamps k between 1 and 50", async () => {
    const onRun = vi.fn();
    await run(onRun, "500");
    expect(onRun).toHaveBeenLastCalledWith("attention", [], 50);
    fireEvent.change(screen.getByLabelText("Number of results"), { target: { value: "0" } });
    await userEvent.setup().click(screen.getByRole("button", { name: "Run" }));
    expect(onRun).toHaveBeenLastCalledWith("attention", [], 1);
  });

  it("falls back to 8 when k is emptied", async () => {
    const onRun = vi.fn();
    await run(onRun, "");
    expect(onRun).toHaveBeenCalledWith("attention", [], 8);
  });

  it("forwards the checked kinds", async () => {
    const onRun = vi.fn();
    const user = userEvent.setup();
    render(<SearchBench {...base} onRun={onRun} />);
    await user.type(screen.getByLabelText("Query"), "cv");
    await user.click(screen.getByRole("checkbox", { name: "Posting" }));
    await user.click(screen.getByRole("button", { name: "Run" }));
    expect(onRun).toHaveBeenCalledWith("cv", ["posting"], 8);
  });

  it("needs a query and locks while pending", () => {
    const { rerender } = render(<SearchBench {...base} />);
    expect(screen.getByRole("button", { name: "Run" })).toBeDisabled();
    rerender(<SearchBench {...base} pending />);
    expect(screen.getByRole("button", { name: "Running…" })).toBeDisabled();
  });
});
