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
    expect(screen.getByText(/25\.0%/)).toBeInTheDocument();
    expect(screen.getByText(/of the free Vectorize quota \(5M dimensions\)/)).toBeInTheDocument();
    expect(screen.getByText("Reindexing: 3 / 10")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reindex" })).toBeDisabled();
  });

  it("counts items per kind, in total and in chunks", () => {
    render(<MemoryStats {...base} onReindex={vi.fn()} />);
    const byKind = screen.getByRole("list", { name: "Items by type" });
    expect(within(byKind).getByText("Acquired skill").closest("li")).toHaveTextContent("5");
    expect(within(byKind).getAllByRole("listitem")).toHaveLength(6);
    expect(screen.getByText("Items").parentElement).toHaveTextContent("12");
    expect(screen.getByText("Chunks").parentElement).toHaveTextContent("48");
    expect(screen.getByText("To confirm").parentElement).toHaveTextContent("1");
  });

  it("shows the last write with its author and date", () => {
    render(<MemoryStats {...base} onReindex={vi.fn()} />);
    expect(screen.getByText(/Last write: .+ · 11 Nov 2026/)).toBeInTheDocument();
  });

  it("says nothing was written yet", () => {
    render(<MemoryStats {...base} stats={stats({ last_write: null })} onReindex={vi.fn()} />);
    expect(screen.getByText("No writes yet.")).toBeInTheDocument();
  });

  it("warns about items not indexed yet, in the singular and the plural", () => {
    const { rerender } = render(
      <MemoryStats {...base} stats={stats({ unindexed_items: 1 })} onReindex={vi.fn()} />,
    );
    expect(screen.getByText("1 item not indexed yet")).toBeInTheDocument();
    rerender(<MemoryStats {...base} stats={stats({ unindexed_items: 3 })} onReindex={vi.fn()} />);
    expect(screen.getByText("3 items not indexed yet")).toBeInTheDocument();
  });

  it("does not warn when everything is indexed", () => {
    render(<MemoryStats {...base} onReindex={vi.fn()} />);
    expect(screen.queryByText(/not indexed yet/)).not.toBeInTheDocument();
  });

  it("reindexes on click, and is disabled while the request is pending", async () => {
    const onReindex = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(<MemoryStats {...base} onReindex={onReindex} />);
    await user.click(screen.getByRole("button", { name: "Reindex" }));
    expect(onReindex).toHaveBeenCalledOnce();
    rerender(<MemoryStats {...base} reindexPending onReindex={onReindex} />);
    expect(screen.getByRole("button", { name: "Reindex" })).toBeDisabled();
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
    expect(screen.getByRole("button", { name: "Reindex" })).toBeEnabled();
  });

  it("links to the JSON export and the Qdrant dashboard", () => {
    render(<MemoryStats {...base} onReindex={vi.fn()} />);
    const exportLink = screen.getByRole("link", { name: "Export as JSON" });
    expect(exportLink).toHaveAttribute("href", "/api/memory/export");
    expect(exportLink).toHaveAttribute("download");
    const dashboard = screen.getByRole("link", { name: "Qdrant dashboard" });
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
    expect(screen.queryByRole("link", { name: "Qdrant dashboard" })).not.toBeInTheDocument();
  });
});
