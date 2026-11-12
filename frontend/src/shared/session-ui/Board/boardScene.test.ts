import { beforeEach, describe, expect, it, vi } from "vitest";

const parse = vi.fn();
const convert = vi.fn();
vi.mock("@excalidraw/mermaid-to-excalidraw", () => ({ parseMermaidToExcalidraw: parse }));
vi.mock("@excalidraw/excalidraw", () => ({ convertToExcalidrawElements: convert }));

import { mermaidToScene } from "./boardScene";

describe("mermaidToScene", () => {
  beforeEach(() => {
    parse.mockReset();
    convert.mockReset();
  });

  it("parses the flowchart then converts the skeletons, keeping files", async () => {
    parse.mockResolvedValue({ elements: [{ type: "rectangle" }], files: { f1: {} } });
    convert.mockReturnValue([{ id: "a", type: "rectangle" }]);
    const result = await mermaidToScene("flowchart TD\n A-->B");
    expect(parse).toHaveBeenCalledWith(
      "flowchart TD\n A-->B",
      expect.objectContaining({ maxEdges: expect.any(Number) }),
    );
    expect(convert).toHaveBeenCalledWith([{ type: "rectangle" }], { regenerateIds: false });
    expect(result).toEqual({
      ok: true,
      elements: [{ id: "a", type: "rectangle" }],
      files: { f1: {} },
    });
  });

  it("points Excalidraw at the locally served fonts before loading it", async () => {
    parse.mockResolvedValue({ elements: [{ type: "rectangle" }], files: {} });
    convert.mockReturnValue([{ id: "a", type: "rectangle" }]);
    await mermaidToScene("flowchart TD");
    expect(window.EXCALIDRAW_ASSET_PATH).toBe("/excalidraw-assets/");
  });

  it("fails without leaking the diagram when the parser throws", async () => {
    parse.mockRejectedValue(new Error("Parse error on line 2: A-->secret"));
    const result = await mermaidToScene("flowchart TD\n A-->secret");
    expect(result).toEqual({ ok: false, error: "conversion_failed" });
  });

  it("fails when the diagram draws nothing", async () => {
    parse.mockResolvedValue({ elements: [], files: undefined });
    convert.mockReturnValue([]);
    expect(await mermaidToScene("flowchart TD")).toEqual({ ok: false, error: "empty_scene" });
  });
});
