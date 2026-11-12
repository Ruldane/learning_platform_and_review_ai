import type { SensorContext } from "@dnd-kit/core";
import { describe, expect, it, vi } from "vitest";
import { columnKeyboardCoordinates } from "./keyboardCoordinates";

function rect(left: number) {
  return { left, top: 0, width: 100, height: 400, right: left + 100, bottom: 400 };
}

function makeContext(ids: Record<string, number>, collisionLeft: number): SensorContext {
  const rects = new Map(Object.entries(ids).map(([id, left]) => [id, rect(left)]));
  return {
    collisionRect: {
      left: collisionLeft,
      top: 40,
      width: 80,
      height: 50,
      right: collisionLeft + 80,
      bottom: 90,
    },
    droppableRects: rects,
    droppableContainers: { getEnabled: () => [...rects.keys()].map((id) => ({ id })) },
  } as unknown as SensorContext;
}

function press(code: string, context: SensorContext) {
  const event = { code, preventDefault: vi.fn() } as unknown as KeyboardEvent;
  const result = columnKeyboardCoordinates(event, {
    active: "t1",
    currentCoordinates: { x: context.collisionRect?.left ?? 0, y: 40 },
    context,
  });
  return { event, result };
}

const COLUMNS = { a: 0, b: 110, c: 220 };

describe("columnKeyboardCoordinates", () => {
  it("moves to the centre of the next column on the right", () => {
    const { event, result } = press("ArrowRight", makeContext(COLUMNS, 120));
    expect(result).toEqual({ x: 230, y: 40 });
    expect(event.preventDefault).toHaveBeenCalled();
  });

  it("moves to the column on the left", () => {
    expect(press("ArrowLeft", makeContext(COLUMNS, 120)).result).toEqual({ x: 10, y: 40 });
  });

  it("stays put at the last column", () => {
    expect(press("ArrowRight", makeContext(COLUMNS, 230)).result).toBeUndefined();
  });

  it("ignores other keys", () => {
    expect(press("ArrowUp", makeContext(COLUMNS, 120)).result).toBeUndefined();
  });
});
