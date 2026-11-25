import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { OutputView } from "../viewTypes";
import { OutputPanel } from "./OutputPanel";

const view = (over: Partial<OutputView> = {}): OutputView => ({
  runId: null,
  kind: null,
  origin: "app",
  status: "idle",
  output: "",
  exitCode: null,
  durationMs: null,
  truncated: false,
  error: null,
  ...over,
});

describe("OutputPanel", () => {
  it("is read-only: no field, no keyboard entry for the program", () => {
    render(<OutputPanel view={view()} />);
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.getByText(/does not read keyboard input/)).toBeInTheDocument();
    expect(screen.getByText("Nothing has run yet. Press Ctrl+Enter.")).toBeInTheDocument();
  });

  it("writes the state of each end in words", () => {
    const { rerender } = render(
      <OutputPanel
        view={view({ runId: "r1", kind: "run", status: "done", exitCode: 0, durationMs: 120 })}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Finished (code 0, 120 ms).");
    rerender(<OutputPanel view={view({ runId: "r1", kind: "run", status: "timeout" })} />);
    expect(screen.getByRole("status")).toHaveTextContent("Stopped: the time limit was exceeded.");
    rerender(
      <OutputPanel view={view({ runId: "r1", kind: "check", status: "done", exitCode: 1 })} />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Check failed.");
    rerender(
      <OutputPanel view={view({ runId: "r1", kind: "check", status: "done", exitCode: 0 })} />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Check passed");
  });

  it("shows the output, the truncation notice and an error", () => {
    render(
      <OutputPanel
        view={view({
          runId: "r1",
          kind: "run",
          status: "done",
          exitCode: 0,
          output: "Bonjour\n",
          truncated: true,
          error: "The output could not be reloaded.",
        })}
      />,
    );
    expect(screen.getByRole("log", { name: "Program output" }).textContent).toBe("Bonjour\n");
    expect(screen.getByText(/The output is truncated/)).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("The output could not be reloaded.");
  });

  it("takes the focus when a run starts, and only then", () => {
    const { rerender } = render(<OutputPanel view={view()} />);
    const region = screen.getByRole("region", { name: "Output" });
    expect(region).not.toHaveFocus();
    rerender(<OutputPanel view={view({ runId: "r1", kind: "run", status: "running" })} />);
    expect(region).toHaveFocus();
  });
});
