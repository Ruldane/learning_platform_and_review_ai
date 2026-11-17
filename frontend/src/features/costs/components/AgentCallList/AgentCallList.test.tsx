import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import type { CallView } from "../viewTypes";
import { AgentCallList } from "./AgentCallList";

const call = (id: string, over: Partial<CallView> = {}): CallView => ({
  id,
  at: "2026-11-16T09:30:00Z",
  agentLabel: "Stratège",
  graphLabel: "Quiz",
  model: "glm:glm-5.3-flash",
  tokensIn: 100,
  tokensOut: 20,
  latencyMs: 340,
  costUsd: 0.004,
  estimated: false,
  sessionId: null,
  screenPath: null,
  ...over,
});

const base = { filtered: false, hasMore: false, loadingMore: false, onLoadMore: () => undefined };
const renderList = (props: Partial<Parameters<typeof AgentCallList>[0]> & { calls: CallView[] }) =>
  render(
    <MemoryRouter>
      <AgentCallList {...base} {...props} />
    </MemoryRouter>,
  );

describe("AgentCallList", () => {
  it("shows duration under a second in milliseconds and a small cost with three decimals", () => {
    renderList({ calls: [call("a")] });
    expect(screen.getByText("340 ms")).toBeInTheDocument();
    expect(screen.getByText("0,004 $")).toBeInTheDocument();
    expect(screen.getByText("1 appel affiché")).toBeInTheDocument();
  });

  it("keeps the load button pressable by keyboard but inert while loading", async () => {
    const onLoadMore = vi.fn();
    renderList({ calls: [call("a")], hasMore: true, loadingMore: true, onLoadMore });
    const button = screen.getByRole("button", { name: "Chargement…" });
    expect(button).toHaveAttribute("aria-disabled", "true");
    button.focus();
    await userEvent.keyboard("{Enter}");
    expect(onLoadMore).not.toHaveBeenCalled();
  });

  it("asks for the next page", async () => {
    const onLoadMore = vi.fn();
    renderList({ calls: [call("a")], hasMore: true, onLoadMore });
    await userEvent.click(screen.getByRole("button", { name: "Voir plus" }));
    expect(onLoadMore).toHaveBeenCalledTimes(1);
  });

  it("does not take the focus when the whole journal fits in one page", () => {
    renderList({ calls: [call("a")] });
    expect(screen.getByText("C'est tout : le journal est affiché en entier.")).not.toHaveFocus();
  });
});
