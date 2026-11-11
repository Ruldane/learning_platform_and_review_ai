import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { documentRow } from "../viewFixtures";
import { DocumentList } from "./DocumentList";

const none: string[] = [];
const rowOf = (name: string) => screen.getByText(name).closest("li")!;

describe("DocumentList", () => {
  it("offers Déjà appris only for indexed documents not learned yet", () => {
    render(
      <DocumentList
        documents={[
          documentRow({ id: "a", name: "indexe.pdf" }),
          documentRow({ id: "b", name: "file.pdf", status: "queued" }),
          documentRow({ id: "c", name: "cours.pdf", status: "processing" }),
          documentRow({ id: "d", name: "casse.pdf", status: "error" }),
          documentRow({ id: "e", name: "appris.pdf", learned: true }),
        ]}
        learningIds={none}
        onMarkLearned={vi.fn()}
      />,
    );
    expect(screen.getAllByRole("button", { name: "Déjà appris" })).toHaveLength(1);
    expect(within(rowOf("indexe.pdf")).getByRole("button", { name: "Déjà appris" })).toBeVisible();
    expect(within(rowOf("appris.pdf")).getByText("Marqué déjà appris")).toBeInTheDocument();
    expect(within(rowOf("indexe.pdf")).queryByText("Marqué déjà appris")).not.toBeInTheDocument();
  });

  it("calls back with the document id", async () => {
    const onMarkLearned = vi.fn();
    const user = userEvent.setup();
    render(
      <DocumentList
        documents={[documentRow({ id: "a" })]}
        learningIds={none}
        onMarkLearned={onMarkLearned}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Déjà appris" }));
    expect(onMarkLearned).toHaveBeenCalledWith("a");
  });

  it("disables Déjà appris while that document is being marked", () => {
    render(
      <DocumentList
        documents={[documentRow({ id: "a" }), documentRow({ id: "b", name: "autre.pdf" })]}
        learningIds={["a"]}
        onMarkLearned={vi.fn()}
      />,
    );
    const [first, second] = screen.getAllByRole("button", { name: "Déjà appris" });
    expect(first).toBeDisabled();
    expect(second).toBeEnabled();
  });

  it("shows the status of each document", () => {
    render(
      <DocumentList
        documents={[
          documentRow({ id: "a", name: "a.pdf", status: "queued" }),
          documentRow({ id: "b", name: "b.pdf", status: "processing" }),
          documentRow({ id: "c", name: "c.pdf", status: "indexed" }),
          documentRow({ id: "d", name: "d.pdf", status: "error" }),
        ]}
        learningIds={none}
        onMarkLearned={vi.fn()}
      />,
    );
    expect(within(rowOf("a.pdf")).getByText("En file")).toBeInTheDocument();
    expect(within(rowOf("b.pdf")).getByText("En cours")).toBeInTheDocument();
    expect(within(rowOf("c.pdf")).getByText("Indexé")).toBeInTheDocument();
    expect(within(rowOf("d.pdf")).getByText("Erreur")).toBeInTheDocument();
  });

  it("shows the server error message", () => {
    render(
      <DocumentList
        documents={[
          documentRow({
            status: "error",
            error: { code: "pdf_unreadable", message: "Ce PDF ne contient aucun texte lisible." },
          }),
        ]}
        learningIds={none}
        onMarkLearned={vi.fn()}
      />,
    );
    expect(screen.getByText("Ce PDF ne contient aucun texte lisible.")).toBeInTheDocument();
  });

  it("labels every source kind the back end sends (paste included)", () => {
    const kinds = ["pdf", "docx", "markdown", "text", "url", "youtube", "paste"];
    render(
      <DocumentList
        documents={kinds.map((kind) =>
          documentRow({ id: kind, name: `n-${kind}`, source_kind: kind }),
        )}
        learningIds={none}
        onMarkLearned={vi.fn()}
      />,
    );
    for (const label of ["PDF", "DOCX", "Markdown", "Texte", "Lien", "YouTube", "Texte collé"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("names the source kind, and falls back to the raw value", () => {
    render(
      <DocumentList
        documents={[
          documentRow({ id: "a", name: "a", source_kind: "youtube" }),
          documentRow({ id: "b", name: "b", source_kind: "inconnu" }),
        ]}
        learningIds={none}
        onMarkLearned={vi.fn()}
      />,
    );
    expect(screen.getByText("YouTube")).toBeInTheDocument();
    expect(screen.getByText("inconnu")).toBeInTheDocument();
  });

  it("shows an empty state without documents", () => {
    render(<DocumentList documents={[]} learningIds={none} onMarkLearned={vi.fn()} />);
    expect(screen.getByText("Aucun document importé")).toBeInTheDocument();
  });
});
