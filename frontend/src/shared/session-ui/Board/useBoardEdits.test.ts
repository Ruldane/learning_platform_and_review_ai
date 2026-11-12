import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { SceneElementLike } from "../boardTypes";
import { useBoardEdits } from "./useBoardEdits";

const el = (id: string, x = 0, y = 0): SceneElementLike => ({ id, type: "rectangle", x, y });

describe("useBoardEdits", () => {
  it("is clean when only the order of elements changes", () => {
    const initial = [el("a"), el("b", 10, 10)];
    const { result } = renderHook(() => useBoardEdits(initial));
    act(() => result.current.onSceneChange([initial[1]!, initial[0]!]));
    expect(result.current.dirty).toBe(false);
  });

  it("notices a move even when Excalidraw mutates the element it already received", () => {
    const initial = [el("a"), el("b", 10, 10)];
    const { result } = renderHook(() => useBoardEdits(initial));
    const live = initial; // Excalidraw garde et modifie ces mêmes objets
    live[1]!.x = 90;
    act(() => result.current.onSceneChange(live));
    expect(result.current.dirty).toBe(true);
    expect(result.current.snapshot().before[1]?.x).toBe(10);
  });

  it("takes the sent scene as the new reference", () => {
    const initial = [el("a")];
    const { result } = renderHook(() => useBoardEdits(initial));
    act(() => result.current.onSceneChange([el("a", 50, 0)]));
    expect(result.current.dirty).toBe(true);
    act(() => result.current.markSent());
    expect(result.current.dirty).toBe(false);
    act(() => result.current.onSceneChange([el("a", 50, 0)]));
    expect(result.current.dirty).toBe(false);
    act(() => result.current.onSceneChange([el("a", 80, 0)]));
    expect(result.current.dirty).toBe(true);
  });

  it("takes the scene adjusted by Excalidraw (read-only canvas) as the reference", () => {
    const initial = [el("a"), el("arrow", 100, 20)];
    const { result } = renderHook(() => useBoardEdits(initial));
    const adjusted = [el("a", 3, 2), el("arrow", 104, 23)];
    act(() => result.current.onSceneChange(adjusted, true));
    act(() => result.current.onSceneChange([el("a", 3, 2), el("arrow", 104, 23)]));
    expect(result.current.dirty).toBe(false);
    expect(result.current.snapshot().before[1]?.x).toBe(104);
    act(() => result.current.onSceneChange([el("a", 60, 2), el("arrow", 104, 23)]));
    expect(result.current.dirty).toBe(true);
  });

  it("never reports changes before a scene is displayed", () => {
    const { result } = renderHook(() => useBoardEdits(null));
    act(() => result.current.onSceneChange([el("a")]));
    expect(result.current.dirty).toBe(false);
  });
});
