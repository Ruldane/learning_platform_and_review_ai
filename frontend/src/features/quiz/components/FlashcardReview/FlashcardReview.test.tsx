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
    expect(screen.getByText("Compétence : SQL")).toBeInTheDocument();
    expect(screen.queryByText(CARD.back)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Raté/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Voir la réponse/ })).toBeInTheDocument();
  });

  it("reveals the back with the button, then answers with the buttons", async () => {
    const { onResult } = setup();
    await userEvent.click(screen.getByRole("button", { name: /Voir la réponse/ }));
    expect(screen.getByText(CARD.back)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Voir la réponse/ })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Raté/ }));
    expect(onResult).toHaveBeenLastCalledWith("fail");
    await userEvent.click(screen.getByRole("button", { name: /Su/ }));
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
    expect(screen.getByRole("button", { name: /Voir la réponse/ })).toBeInTheDocument();
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
    await userEvent.click(screen.getByRole("button", { name: /Voir la réponse/ }));
    const fail = screen.getByRole("button", { name: /Raté/ });
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
    expect(screen.getByRole("button", { name: /Voir la réponse/ })).toBeDisabled();
    expect(onResult).not.toHaveBeenCalled();
  });

  it("disables the answers while busy once flipped", async () => {
    const { onResult, rerender } = setup();
    await userEvent.keyboard(" ");
    rerender(<FlashcardReview card={CARD} onResult={onResult} busy />);
    expect(screen.getByRole("button", { name: /Raté/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Su/ })).toBeDisabled();
    await userEvent.keyboard("1");
    expect(onResult).not.toHaveBeenCalled();
  });

  it("announces the shortcuts", () => {
    setup();
    expect(screen.getByRole("button", { name: /Voir la réponse/ })).toHaveAttribute(
      "aria-keyshortcuts",
      "Space",
    );
    expect(screen.getByText(/Raccourcis/)).toBeInTheDocument();
  });

  it("moves focus to the back once it is shown", async () => {
    setup();
    await userEvent.click(screen.getByRole("button", { name: /Voir la réponse/ }));
    expect(screen.getByRole("group", { name: "Réponse" })).toHaveFocus();
  });
});
