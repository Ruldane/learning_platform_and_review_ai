import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { makeDebrief, makeInterview } from "../fixtures";
import { InterviewList } from "./InterviewList";

describe("InterviewList", () => {
  it("lists each interview with its settings, its state in words and its average score", () => {
    render(
      <InterviewList
        interviews={[
          makeInterview({ id: "i2", mode: "technical", durationMin: 30, language: "en" }),
          makeInterview({ id: "i1", status: "stopped", exchanges: [], debrief: null }),
        ]}
        onOpen={vi.fn()}
      />,
    );
    const list = screen.getByRole("list", { name: "Past interviews" });
    const [first, second] = list.querySelectorAll("li");
    expect(first).toHaveTextContent("Technical, 30 minutes, in English");
    expect(first).toHaveTextContent("Debrief written");
    expect(first).toHaveTextContent("Average: 3.5 out of 5");
    expect(second).toHaveTextContent("Stopped before the first answer");
    expect(second).not.toHaveTextContent("Average");
  });

  it("says in words what happened to an interview without debrief", () => {
    render(
      <InterviewList
        interviews={[
          makeInterview({ id: "i1", status: "debrief_failed", debrief: null }),
          makeInterview({ id: "i2", status: "failed", debrief: null, exchanges: [] }),
        ]}
        onOpen={vi.fn()}
      />,
    );
    expect(screen.getByText("Debrief not written")).toBeVisible();
    expect(screen.getByText("No result")).toBeVisible();
  });

  it("opens an interview by its button", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(
      <InterviewList
        interviews={[makeInterview({ id: "i7", debrief: makeDebrief() })]}
        onOpen={onOpen}
      />,
    );
    await user.click(screen.getByRole("button", { name: /Mixed, 15 minutes/ }));
    expect(onOpen).toHaveBeenCalledWith("i7");
  });

  it("shows the role of a free interview", () => {
    render(
      <InterviewList
        interviews={[makeInterview({ applicationId: null, role: "Data engineer" })]}
        onOpen={vi.fn()}
      />,
    );
    expect(screen.getByText("Role: Data engineer")).toBeVisible();
  });
});
