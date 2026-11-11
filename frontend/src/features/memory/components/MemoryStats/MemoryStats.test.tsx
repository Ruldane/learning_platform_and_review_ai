import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { stats } from "../viewFixtures";
import { MemoryStats } from "./MemoryStats";

const base = { stats: stats(), exportUrl: "/api/memory/export", reindexPending: false };

describe("MemoryStats", () => {
  it("shows the Vectorize share and the reindex progress", () => {
    render(
      <MemoryStats
        {...base}
        stats={stats({ reindex: { status: "running", done: 3, total: 10, error: null } })}
        onReindex={vi.fn()}
      />,
    );
    expect(screen.getByText(/25,0 %/)).toBeInTheDocument();
    expect(screen.getByText(/du quota gratuit Vectorize \(5 M dimensions\)/)).toBeInTheDocument();
    expect(screen.getByText("Réindexation : 3 / 10")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Réindexer" })).toBeDisabled();
  });

  it("counts items per kind, in total and in chunks", () => {
    render(<MemoryStats {...base} onReindex={vi.fn()} />);
    const byKind = screen.getByRole("list", { name: "Éléments par type" });
    expect(within(byKind).getByText("Acquis").closest("li")).toHaveTextContent("5");
    expect(within(byKind).getAllByRole("listitem")).toHaveLength(6);
    expect(screen.getByText("Éléments").parentElement).toHaveTextContent("12");
    expect(screen.getByText("Fragments").parentElement).toHaveTextContent("48");
    expect(screen.getByText("À confirmer").parentElement).toHaveTextContent("1");
  });

  it("shows the last write with its author and date", () => {
    render(<MemoryStats {...base} onReindex={vi.fn()} />);
    expect(screen.getByText(/Dernière écriture : .+ · 11 nov\. 2026/)).toBeInTheDocument();
  });

  it("says nothing was written yet", () => {
    render(<MemoryStats {...base} stats={stats({ last_write: null })} onReindex={vi.fn()} />);
    expect(screen.getByText("Aucune écriture pour l'instant.")).toBeInTheDocument();
  });

  it("warns about items not indexed yet, in the singular and the plural", () => {
    const { rerender } = render(
      <MemoryStats {...base} stats={stats({ unindexed_items: 1 })} onReindex={vi.fn()} />,
    );
    expect(screen.getByText("1 élément pas encore indexé")).toBeInTheDocument();
    rerender(<MemoryStats {...base} stats={stats({ unindexed_items: 3 })} onReindex={vi.fn()} />);
    expect(screen.getByText("3 éléments pas encore indexés")).toBeInTheDocument();
  });

  it("does not warn when everything is indexed", () => {
    render(<MemoryStats {...base} onReindex={vi.fn()} />);
    expect(screen.queryByText(/pas encore indexé/)).not.toBeInTheDocument();
  });

  it("reindexes on click, and is disabled while the request is pending", async () => {
    const onReindex = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(<MemoryStats {...base} onReindex={onReindex} />);
    await user.click(screen.getByRole("button", { name: "Réindexer" }));
    expect(onReindex).toHaveBeenCalledOnce();
    rerender(<MemoryStats {...base} reindexPending onReindex={onReindex} />);
    expect(screen.getByRole("button", { name: "Réindexer" })).toBeDisabled();
  });

  it("shows the reindex failure and lets the user retry", () => {
    render(
      <MemoryStats
        {...base}
        stats={stats({
          reindex: { status: "failed", done: 2, total: 10, error: "Qdrant injoignable" },
        })}
        onReindex={vi.fn()}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Qdrant injoignable");
    expect(screen.getByRole("button", { name: "Réindexer" })).toBeEnabled();
  });

  it("links to the JSON export and the Qdrant dashboard", () => {
    render(<MemoryStats {...base} onReindex={vi.fn()} />);
    const exportLink = screen.getByRole("link", { name: "Exporter en JSON" });
    expect(exportLink).toHaveAttribute("href", "/api/memory/export");
    expect(exportLink).toHaveAttribute("download");
    const dashboard = screen.getByRole("link", { name: "Tableau de bord Qdrant" });
    expect(dashboard).toHaveAttribute("href", "http://localhost:6333/dashboard");
    expect(dashboard).toHaveAttribute("target", "_blank");
    expect(dashboard).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("does not link a dashboard address that is not http(s)", () => {
    render(
      <MemoryStats
        {...base}
        stats={stats({ dashboard_url: "javascript:alert(1)" })}
        onReindex={vi.fn()}
      />,
    );
    expect(screen.queryByRole("link", { name: "Tableau de bord Qdrant" })).not.toBeInTheDocument();
  });
});
