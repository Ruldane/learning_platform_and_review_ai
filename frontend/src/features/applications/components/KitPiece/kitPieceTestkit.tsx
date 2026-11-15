import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import type { KitPieceView, KitSaveResult } from "../viewTypes";
import { KitPiece } from "./KitPiece";

export const piece = (over: Partial<KitPieceView> = {}): KitPieceView => ({
  kind: "letter",
  status: "ready",
  content: "Bonjour,\n\nCordialement",
  flags: [],
  salaryFields: 0,
  words: 120,
  sources: [],
  edited: false,
  error: null,
  updatedAt: "2026-11-15T10:00:00Z",
  ...over,
});

export function setup(
  view: KitPieceView,
  extra: { running?: boolean; save?: KitSaveResult; copy?: () => Promise<void> } = {},
) {
  const onSave = vi.fn(() =>
    Promise.resolve(extra.save ?? { ok: true as const, status: "ready" as const }),
  );
  const onCopy = vi.fn(extra.copy ?? (() => Promise.resolve()));
  const user = userEvent.setup();
  const ui = (next: KitPieceView) => (
    <KitPiece piece={next} running={extra.running ?? false} onSave={onSave} onCopy={onCopy} />
  );
  const view_ = render(ui(view));
  return { user, onSave, onCopy, rerender: (next: KitPieceView) => view_.rerender(ui(next)) };
}
