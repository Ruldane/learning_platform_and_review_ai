import { describe, expect, it } from "vitest";
import { detectSource, fileProblem } from "./source";

describe("detectSource", () => {
  it("reads an http or https address alone as a link", () => {
    expect(detectSource("  https://exemple.fr/a?b=1 ")).toEqual({
      kind: "url",
      url: "https://exemple.fr/a?b=1",
    });
    expect(detectSource("HTTP://exemple.fr")).toEqual({ kind: "url", url: "HTTP://exemple.fr" });
  });

  it("reads anything else as a note, a link inside a sentence included", () => {
    expect(detectSource("Lire https://exemple.fr demain")).toEqual({
      kind: "text",
      text: "Lire https://exemple.fr demain",
    });
    expect(detectSource("ftp://exemple.fr")).toEqual({ kind: "text", text: "ftp://exemple.fr" });
  });

  it("returns null for an empty field", () => {
    expect(detectSource("   \n ")).toBeNull();
  });
});

describe("fileProblem", () => {
  it("accepts the supported types and refuses the others and big files", () => {
    expect(fileProblem(new File(["x"], "cours.PDF"))).toBeNull();
    expect(fileProblem(new File(["x"], "image.png"))).toBe("badType");
    expect(fileProblem(new File([new Uint8Array(20 * 1024 * 1024 + 1)], "gros.pdf"))).toBe(
      "tooBig",
    );
  });
});
