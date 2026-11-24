import { afterEach, describe, expect, it, vi } from "vitest";
import { copyText } from "./clipboard";

const original = Object.getOwnPropertyDescriptor(navigator, "clipboard");

afterEach(() => {
  if (original) Object.defineProperty(navigator, "clipboard", original);
  else Reflect.deleteProperty(navigator, "clipboard");
});

describe("copyText", () => {
  it("writes the text to the clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    await copyText("Un brouillon.");
    expect(writeText).toHaveBeenCalledWith("Un brouillon.");
  });

  it("rejects when there is no clipboard", async () => {
    Object.defineProperty(navigator, "clipboard", { value: undefined, configurable: true });
    await expect(copyText("x")).rejects.toThrow("The clipboard isn’t available.");
  });

  it("rejects when the browser refuses", async () => {
    const writeText = vi.fn().mockRejectedValue(new Error("denied"));
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    await expect(copyText("x")).rejects.toThrow("denied");
  });
});
