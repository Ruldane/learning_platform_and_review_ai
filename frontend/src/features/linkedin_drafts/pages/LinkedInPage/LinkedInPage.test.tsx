import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, expect, it, vi } from "vitest";
import { API } from "@/test/councilApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import type { DraftView } from "../../api";
import { LinkedInPage } from "./LinkedInPage";

const initial: DraftView = {
  id: "brouillon-fictif",
  revision: 2,
  session_id: "session-fictive",
  profile_version: 3,
  state: "ready",
  text: {
    headline: "Ingénieure données",
    about: "Je développe des scripts Python.",
    skills: ["Python"],
  },
  claims: [],
};

class ClipboardItemDouble {
  readonly text: Promise<Blob>;

  constructor(items: Record<string, Promise<Blob>>) {
    this.text = items["text/plain"]!;
  }

  getType() {
    return this.text;
  }
}

afterEach(() => vi.unstubAllGlobals());

function blobText(blob: Blob): Promise<string> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.readAsText(blob);
  });
}

it.each([false, true])(
  "revalidates the draft before delivering its text (stale: %s)",
  async (stale) => {
    let complete!: (draft: DraftView) => void;
    const response = new Promise<DraftView>((resolve) => {
      complete = resolve;
    });
    const reads = vi.fn();
    server.use(
      http.get(`${API}/postings`, () => HttpResponse.json([])),
      http.get(`${API}/linkedin-drafts/latest`, async () => {
        reads();
        return HttpResponse.json(reads.mock.calls.length === 1 ? initial : await response);
      }),
    );
    const fetches = vi.spyOn(globalThis, "fetch");
    vi.stubGlobal("ClipboardItem", ClipboardItemDouble);
    const path = "/career/linkedin";
    const { user } = renderRoutes([{ path, Component: LinkedInPage }], path);
    const written = vi.fn();
    const writeText = vi
      .spyOn(navigator.clipboard, "writeText")
      .mockImplementation(async (text) => {
        written(text);
      });
    const write = vi.spyOn(navigator.clipboard, "write").mockImplementation(async ([item]) => {
      if (item) written(await blobText(await item.getType("text/plain")));
    });

    const copy = await screen.findByRole("button", { name: "Copy about section" });
    await user.click(copy);
    expect(write).toHaveBeenCalledOnce();
    await waitFor(() => expect(reads).toHaveBeenCalledTimes(2));
    expect(fetches.mock.lastCall?.[0]).toMatchObject({ cache: "no-store" });
    expect(written).not.toHaveBeenCalled();
    expect(writeText).not.toHaveBeenCalled();
    complete(stale ? { ...initial, state: "stale", text: null } : initial);

    if (stale) {
      expect(
        await screen.findByText("The master profile has changed. Prepare a new suggestion."),
      ).toBeVisible();
      expect(written).not.toHaveBeenCalled();
      expect(screen.queryByText("Text copied.")).not.toBeInTheDocument();
    } else {
      expect(await screen.findByText("Text copied.")).toBeVisible();
      expect(written).toHaveBeenCalledWith(initial.text?.about);
    }
  },
);
