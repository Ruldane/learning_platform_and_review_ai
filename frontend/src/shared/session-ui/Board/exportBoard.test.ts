import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { BoardApi } from "./boardApi";

const exportToBlob = vi.fn();
const exportToSvg = vi.fn();
const serializeAsJSON = vi.fn();
vi.mock("@excalidraw/excalidraw", () => ({ exportToBlob, exportToSvg, serializeAsJSON }));

import { exportBoard, serializeScene } from "./exportBoard";

const api = {
  getSceneElements: () => [{ id: "a" }],
  getAppState: () => ({ viewBackgroundColor: "#fff", scrollX: 3 }),
  getFiles: () => ({}),
} as unknown as BoardApi;

describe("exportBoard", () => {
  const downloads: { name: string; blob: Blob }[] = [];

  beforeEach(() => {
    downloads.length = 0;
    URL.createObjectURL = vi.fn((blob: Blob) => {
      downloads.push({ name: "", blob });
      return "blob:fake";
    });
    URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      const last = downloads[downloads.length - 1];
      if (last) last.name = this.download;
    });
    exportToBlob.mockResolvedValue(new Blob(["png"], { type: "image/png" }));
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    exportToSvg.mockResolvedValue(svg);
    serializeAsJSON.mockReturnValue('{"type":"excalidraw","elements":[]}');
  });

  afterEach(() => vi.restoreAllMocks());

  it("exports a PNG with a background", async () => {
    await exportBoard("png", api, "Carte du domaine");
    expect(exportToBlob).toHaveBeenCalledWith(
      expect.objectContaining({ mimeType: "image/png", elements: [{ id: "a" }] }),
    );
    expect(downloads[0]?.name).toBe("tremplin-carte-du-domaine.png");
  });

  it("exports an SVG file", async () => {
    await exportBoard("svg", api, "Frise du parcours");
    expect(exportToSvg).toHaveBeenCalled();
    expect(downloads[0]?.name).toBe("tremplin-frise-du-parcours.svg");
    expect(downloads[0]?.blob.type).toBe("image/svg+xml");
  });

  it("exports the .excalidraw scene", async () => {
    await exportBoard("scene", api, "Comparaison");
    expect(serializeAsJSON).toHaveBeenCalledWith([{ id: "a" }], expect.any(Object), {}, "local");
    expect(downloads[0]?.name).toBe("tremplin-comparaison.excalidraw");
  });

  it("serializes the scene as a plain object", async () => {
    expect(await serializeScene(api)).toEqual({ type: "excalidraw", elements: [] });
  });
});
