import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { expectCoherentOutline } from "@/test/headingOutline";
import type { NoteView } from "../viewTypes";
import { TeacherPanel } from "./TeacherPanel";

const note = (over: Partial<NoteView> = {}): NoteView => ({
  id: "n1",
  kind: "hint",
  author: "professor",
  authorLabel: "Le professeur",
  origin: "app",
  status: "open",
  filePath: null,
  lineStart: null,
  lineEnd: null,
  content: "Relis la ligne du retour.",
  replacement: null,
  before: null,
  hintLevel: 1,
  ...over,
});

const props = { busy: false, onAccept: vi.fn(), onReject: vi.fn() };

describe("TeacherPanel", () => {
  it("groups notes by kind and shows level of hint", () => {
    render(
      <>
        <h1>Séance</h1>
        <TeacherPanel
          {...props}
          notes={[
            note({ id: "n1", hintLevel: 1, content: "Regarde le signe." }),
            note({ id: "n2", hintLevel: 2, content: "Le signe est faux." }),
            note({
              id: "n3",
              kind: "explanation",
              hintLevel: null,
              content: "Un moins soustrait.",
            }),
            note({
              id: "n4",
              kind: "annotation",
              hintLevel: null,
              filePath: "main.py",
              lineStart: 2,
              content: "Ici.",
            }),
          ]}
        />
      </>,
    );
    const hints = screen.getByRole("region", { name: "Indices" });
    expect(within(hints).getByText(/Indice 1/)).toBeInTheDocument();
    expect(within(hints).getByText(/Indice 2/)).toBeInTheDocument();
    expect(within(hints).getByText("Regarde le signe.")).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Explications" })).getByText("Un moins soustrait."),
    ).toBeInTheDocument();
    const margin = screen.getByRole("region", { name: "Dans la marge" });
    expect(within(margin).getByText("main.py, ligne 2")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Propositions" })).toBeNull();
    expectCoherentOutline();
  });

  it("says when the teacher has not spoken yet", () => {
    render(<TeacherPanel {...props} notes={[]} />);
    expect(screen.getByText("Le professeur n'a encore rien dit.")).toBeInTheDocument();
  });

  it("greys a stale note and says why", () => {
    render(<TeacherPanel {...props} notes={[note({ status: "stale" })]} />);
    expect(screen.getByText("Le code a changé depuis")).toBeInTheDocument();
  });

  it("routes accept and reject of a proposal to the right note", async () => {
    const onAccept = vi.fn();
    const onReject = vi.fn();
    const proposal = note({
      id: "p1",
      kind: "proposal",
      hintLevel: null,
      filePath: "main.py",
      lineStart: 2,
      lineEnd: 2,
      before: "return a - b",
      replacement: "return a + b",
    });
    render(<TeacherPanel {...props} notes={[proposal]} onAccept={onAccept} onReject={onReject} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Accepter" }));
    await user.click(screen.getByRole("button", { name: "Refuser" }));
    expect(onAccept).toHaveBeenCalledWith("p1");
    expect(onReject).toHaveBeenCalledWith("p1");
  });
});
