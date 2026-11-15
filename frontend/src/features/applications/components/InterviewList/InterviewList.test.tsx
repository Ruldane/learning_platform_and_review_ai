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
    const list = screen.getByRole("list", { name: "Entretiens passés" });
    const [first, second] = list.querySelectorAll("li");
    expect(first).toHaveTextContent("Technique, 30 minutes, en anglais");
    expect(first).toHaveTextContent("Débrief écrit");
    expect(first).toHaveTextContent("Moyenne : 3,5 sur 5");
    expect(second).toHaveTextContent("Arrêté avant la première réponse");
    expect(second).not.toHaveTextContent("Moyenne");
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
    expect(screen.getByText("Débrief non écrit")).toBeVisible();
    expect(screen.getByText("Sans résultat")).toBeVisible();
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
    await user.click(screen.getByRole("button", { name: /Mixte, 15 minutes/ }));
    expect(onOpen).toHaveBeenCalledWith("i7");
  });

  it("shows the role of a free interview", () => {
    render(
      <InterviewList
        interviews={[makeInterview({ applicationId: null, role: "Data engineer" })]}
        onOpen={vi.fn()}
      />,
    );
    expect(screen.getByText("Poste : Data engineer")).toBeVisible();
  });
});
