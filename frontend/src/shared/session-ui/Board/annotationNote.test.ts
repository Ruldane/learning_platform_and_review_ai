import { describe, expect, it } from "vitest";
import type { SceneElementLike } from "../boardTypes";
import { annotationNote } from "./annotationNote";

const box = (id: string, x = 0, y = 0): SceneElementLike => ({ id, type: "rectangle", x, y });
const text = (id: string, value: string, containerId: string | null = null): SceneElementLike => ({
  id,
  type: "text",
  x: 0,
  y: 0,
  text: value,
  containerId,
});

describe("annotationNote", () => {
  const before = [box("a"), text("a-t", "MLOps", "a"), box("b", 10, 10)];

  it("lists added texts and moved elements", () => {
    const after = [box("a"), text("a-t", "MLOps", "a"), box("b", 60, 10), text("t1", "Docker")];
    expect(annotationNote(before, after)).toBe("Ajouté : « Docker » ; 1 élément(s) déplacé(s)");
  });

  it("lists changed and removed texts", () => {
    const after = [
      box("a"),
      text("a-t", "MLOps avancé", "a"),
      { ...box("b", 10, 10), isDeleted: true },
    ];
    expect(annotationNote(before, after)).toBe("Modifié : « MLOps avancé »");
    const gone = [box("a"), box("b", 10, 10)];
    expect(annotationNote(before, gone)).toBe("Supprimé : « MLOps »");
  });

  it("returns an empty string when nothing changed", () => {
    expect(annotationNote(before, before)).toBe("");
  });

  it("does not count bound labels or arrows that follow their shape", () => {
    const arrow: SceneElementLike = { id: "e", type: "arrow", x: 0, y: 0 };
    const after = [
      box("a", 100, 100),
      text("a-t", "MLOps", "a"),
      box("b", 10, 10),
      { ...arrow, x: 5 },
    ];
    expect(annotationNote([...before, arrow], after)).toBe("1 élément(s) déplacé(s)");
  });

  it("flattens line breaks and caps long lists", () => {
    const added = Array.from({ length: 7 }, (_, i) => text(`n${i}`, `Idée\n${i}`));
    const note = annotationNote(before, [...before, ...added]);
    expect(note).toBe("Ajouté : « Idée 0 », « Idée 1 », « Idée 2 », « Idée 3 », « Idée 4 », …");
  });
});
