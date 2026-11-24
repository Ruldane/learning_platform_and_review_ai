import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { CardView } from "../viewTypes";
import { FlashcardReview } from "./FlashcardReview";

const CARD: CardView = {
  id: "c1",
  front: "Que fait EXPLAIN ?",
  back: "Il montre le plan d'exécution d'une requête.",
  skill: "SQL",
};

function setup(props: Partial<Parameters<typeof FlashcardReview>[0]> = {}) {
  const onResult = vi.fn();
  const view = render(<FlashcardReview card={CARD} onResult={onResult} busy={false} {...props} />);
  return { onResult, ...view };
}

describe("FlashcardReview", () => {
  it("shows the front and hides the back", () => {
    setup();
    expect(screen.getByText("Que fait EXPLAIN ?")).toBeInTheDocument();
    expect(screen.getByText("Skill: SQL")).toBeInTheDocument();
    expect(screen.queryByText(CARD.back)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Missed/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Show the answer/ })).toBeInTheDocument();
  });

  it("reveals the back with the button, then answers with the buttons", async () => {
    const { onResult } = setup();
    await userEvent.click(screen.getByRole("button", { name: /Show the answer/ }));
    expect(screen.getByText(CARD.back)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Show the answer/ })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Missed/ }));
    expect(onResult).toHaveBeenLastCalledWith("fail");
    await userEvent.click(screen.getByRole("button", { name: /Knew it/ }));
    expect(onResult).toHaveBeenLastCalledWith("ok");
  });

  it("flips with space and answers with 1 and 2", async () => {
    const { onResult } = setup();
    await userEvent.keyboard("1");
    await userEvent.keyboard("2");
    expect(onResult).not.toHaveBeenCalled();
    await userEvent.keyboard(" ");
    expect(screen.getByText(CARD.back)).toBeInTheDocument();
    await userEvent.keyboard("1");
    expect(onResult).toHaveBeenLastCalledWith("fail");
    await userEvent.keyboard("2");
    expect(onResult).toHaveBeenLastCalledWith("ok");
    expect(onResult).toHaveBeenCalledTimes(2);
  });

  it("ignores space once the back is shown", async () => {
    const { onResult } = setup();
    await userEvent.keyboard(" ");
    await userEvent.keyboard(" ");
    expect(onResult).not.toHaveBeenCalled();
  });

  it("starts again on the front for the next card", async () => {
    const { rerender, onResult } = setup();
    await userEvent.keyboard(" ");
    rerender(
      <FlashcardReview
        card={{ ...CARD, id: "c2", front: "Autre question", back: "Autre réponse" }}
        onResult={onResult}
        busy={false}
      />,
    );
    expect(screen.getByText("Autre question")).toBeInTheDocument();
    expect(screen.queryByText("Autre réponse")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Show the answer/ })).toBeInTheDocument();
  });

  it("leaves the keys alone while typing in a field", async () => {
    const { onResult } = setup();
    render(<input aria-label="Note" />);
    await userEvent.click(screen.getByRole("textbox", { name: "Note" }));
    await userEvent.keyboard(" 12");
    expect(screen.queryByText(CARD.back)).not.toBeInTheDocument();
    expect(onResult).not.toHaveBeenCalled();
  });

  it("leaves space to the focused button", async () => {
    const { onResult } = setup();
    await userEvent.click(screen.getByRole("button", { name: /Show the answer/ }));
    const fail = screen.getByRole("button", { name: /Missed/ });
    fail.focus();
    fireEvent.keyDown(fail, { key: " " });
    expect(onResult).not.toHaveBeenCalled();
  });

  it("ignores shortcuts with a modifier key", async () => {
    const { onResult } = setup();
    await userEvent.keyboard("{Control>} {/Control}");
    expect(screen.queryByText(CARD.back)).not.toBeInTheDocument();
    await userEvent.keyboard(" ");
    await userEvent.keyboard("{Control>}1{/Control}");
    expect(onResult).not.toHaveBeenCalled();
  });

  it("does nothing while an answer is on its way", async () => {
    const { onResult } = setup({ busy: true });
    await userEvent.keyboard(" ");
    expect(screen.queryByText(CARD.back)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Show the answer/ })).toBeDisabled();
    expect(onResult).not.toHaveBeenCalled();
  });

  it("disables the answers while busy once flipped", async () => {
    const { onResult, rerender } = setup();
    await userEvent.keyboard(" ");
    rerender(<FlashcardReview card={CARD} onResult={onResult} busy />);
    expect(screen.getByRole("button", { name: /Missed/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Knew it/ })).toBeDisabled();
    await userEvent.keyboard("1");
    expect(onResult).not.toHaveBeenCalled();
  });

  it("announces the shortcuts", () => {
    setup();
    expect(screen.getByRole("button", { name: /Show the answer/ })).toHaveAttribute(
      "aria-keyshortcuts",
      "Space",
    );
    expect(screen.getByText(/Shortcuts/)).toBeInTheDocument();
  });

  it("moves focus to the back once it is shown", async () => {
    setup();
    await userEvent.click(screen.getByRole("button", { name: /Show the answer/ }));
    expect(screen.getByRole("group", { name: "Answer" })).toHaveFocus();
  });
});
