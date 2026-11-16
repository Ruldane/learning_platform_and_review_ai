import { describe, expect, it } from "vitest";
import { submissionForm } from "./api";

const png = (name: string) => new File([new Uint8Array(4)], name, { type: "image/png" });

describe("submissionForm", () => {
  it("carries the link, the description and one `screenshots` part per capture", () => {
    const form = submissionForm({
      repoUrl: "https://example.org/camille/ventes",
      description: "Une requête SQL.",
      screenshots: [png("a.png"), png("b.png")],
    });
    expect(form.get("repo_url")).toBe("https://example.org/camille/ventes");
    expect(form.get("description")).toBe("Une requête SQL.");
    expect(form.getAll("screenshots").map((file) => (file as File).name)).toEqual([
      "a.png",
      "b.png",
    ]);
  });

  it("leaves out the link and the description that are not given", () => {
    const form = submissionForm({
      repoUrl: null,
      description: "Seulement un texte.",
      screenshots: [],
    });
    expect(form.has("repo_url")).toBe(false);
    expect(form.get("description")).toBe("Seulement un texte.");
    expect(form.has("screenshots")).toBe(false);
  });
});
