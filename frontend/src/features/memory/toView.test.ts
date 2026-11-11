import { describe, expect, it } from "vitest";
import { itemDetail, itemOut, statsOut } from "./fixtures";
import { toDocumentRow, toItemDetail, toItemRow, toStats } from "./toView";

describe("toStats", () => {
  it("keeps the six kinds, defaulting the missing ones to 0", () => {
    const view = toStats(statsOut({ by_kind: { acquis: 4, document: 2 } }));
    expect(view.by_kind).toEqual({
      document: 2,
      acquis: 4,
      lecon: 0,
      source: 0,
      offre: 0,
      decision: 0,
    });
  });

  it("ignores kinds the front does not know and rejects non-numeric counts", () => {
    const view = toStats(statsOut({ by_kind: { acquis: 1, mystere: 9, lecon: Number.NaN } }));
    expect(Object.keys(view.by_kind)).toHaveLength(6);
    expect(view.by_kind.lecon).toBe(0);
    expect("mystere" in view.by_kind).toBe(false);
  });

  it("carries the totals, the last write and the reindex state", () => {
    const view = toStats(statsOut());
    expect(view.total_items).toBe(12);
    expect(view.last_write?.author).toBe("archivist");
    expect(view.reindex.status).toBe("idle");
    expect(view.dashboard_url).toBe("http://localhost:6333/dashboard");
  });
});

describe("toItemRow / toItemDetail", () => {
  it("drops the text from a list row", () => {
    const row = toItemRow(itemOut({ text: "secret" }));
    expect(row).not.toHaveProperty("text");
    expect(row.status).toBe("active");
  });

  it("maps the detail with its journal", () => {
    const detail = toItemDetail(itemDetail());
    expect(detail.writes[0]).toEqual(
      expect.objectContaining({ author: "archivist", action: "create" }),
    );
    expect(detail.neighbors[0]?.score).toBe(0.71);
    expect(detail.chunks[0]?.token_count).toBe(120);
  });
});

describe("toDocumentRow", () => {
  it("keeps the source kind sent by the back end", () => {
    const row = toDocumentRow({
      id: "d1",
      name: "Notes",
      source_kind: "paste",
      status: "error",
      error: { code: "no_text", message: "Aucun texte exploitable." },
      learned: false,
      item_id: null,
      size_bytes: null,
      url: null,
      created_at: "2026-11-11T10:00:00Z",
      updated_at: "2026-11-11T10:00:00Z",
    });
    expect(row.source_kind).toBe("paste");
    expect(row.error).toEqual({ code: "no_text", message: "Aucun texte exploitable." });
    expect(row).not.toHaveProperty("url");
  });
});
