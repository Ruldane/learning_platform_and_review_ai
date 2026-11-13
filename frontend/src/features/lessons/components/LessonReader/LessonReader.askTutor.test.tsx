import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { LessonView } from "../viewTypes";
import { LessonReader } from "./LessonReader";

vi.mock("mermaid", () => ({ default: { initialize: vi.fn(), render: vi.fn() } }));

const LESSON: LessonView = {
  title: "Les API REST",
  markdown: "## Verbes\n\nGET lit une ressource.\n\nPUT remplace une ressource.",
  wordCount: 20,
  pdfUrl: null,
};

/** Sélectionne tout le texte d'un élément, comme le ferait la souris. */
function select(element: Element) {
  const range = document.createRange();
  range.selectNodeContents(element);
  const selection = window.getSelection()!;
  selection.removeAllRanges();
  selection.addRange(range);
  act(() => {
    document.dispatchEvent(new Event("selectionchange"));
  });
}

function clearSelection() {
  window.getSelection()!.removeAllRanges();
  act(() => {
    document.dispatchEvent(new Event("selectionchange"));
  });
}

const paragraph = (text: string) => within(screen.getByTestId("lesson-body")).getByText(text);

afterEach(() => window.getSelection()?.removeAllRanges());

describe("LessonReader: Demander au tuteur", () => {
  it("offers nothing until a passage is selected", () => {
    render(<LessonReader lesson={LESSON} onAskTutor={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "Demander au tuteur" })).not.toBeInTheDocument();
  });

  it("asks the tutor about a selected passage", async () => {
    const onAskTutor = vi.fn();
    render(<LessonReader lesson={LESSON} onAskTutor={onAskTutor} />);
    select(paragraph("GET lit une ressource."));
    const bar = screen.getByRole("region", { name: "Question au tuteur" });
    expect(bar).toHaveTextContent("GET lit une ressource.");
    await userEvent.click(within(bar).getByRole("button", { name: "Demander au tuteur" }));
    expect(onAskTutor).toHaveBeenCalledExactlyOnceWith("GET lit une ressource.");
  });

  it("does not take the selection away when the button is pressed", () => {
    render(<LessonReader lesson={LESSON} onAskTutor={vi.fn()} />);
    select(paragraph("GET lit une ressource."));
    const button = screen.getByRole("button", { name: "Demander au tuteur" });
    const press = new MouseEvent("mousedown", { bubbles: true, cancelable: true });
    button.dispatchEvent(press);
    expect(press.defaultPrevented).toBe(true);
  });

  it("goes away with the selection", () => {
    render(<LessonReader lesson={LESSON} onAskTutor={vi.fn()} />);
    select(paragraph("PUT remplace une ressource."));
    expect(screen.getByRole("button", { name: "Demander au tuteur" })).toBeInTheDocument();
    clearSelection();
    expect(screen.queryByRole("button", { name: "Demander au tuteur" })).not.toBeInTheDocument();
  });

  it("ignores a selection outside the text of the lesson", () => {
    render(<LessonReader lesson={LESSON} onAskTutor={vi.fn()} />);
    select(screen.getByRole("heading", { name: "Les API REST", level: 1 }));
    expect(screen.queryByRole("button", { name: "Demander au tuteur" })).not.toBeInTheDocument();
  });

  it("is not offered when the page gives no way to ask", () => {
    render(<LessonReader lesson={LESSON} />);
    select(paragraph("GET lit une ressource."));
    expect(screen.queryByRole("button", { name: "Demander au tuteur" })).not.toBeInTheDocument();
  });

  it("recalls only the start of a long passage in the bar, and sends it whole", async () => {
    const long = "mot ".repeat(60).trim();
    const onAskTutor = vi.fn();
    render(
      <LessonReader
        lesson={{ ...LESSON, markdown: `## Verbes\n\n${long}` }}
        onAskTutor={onAskTutor}
      />,
    );
    select(paragraph(long));
    expect(screen.getByRole("region", { name: "Question au tuteur" }).textContent).toContain("…");
    await userEvent.click(screen.getByRole("button", { name: "Demander au tuteur" }));
    expect(onAskTutor).toHaveBeenCalledWith(long);
  });
});
