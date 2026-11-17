import { beforeEach, describe, expect, it, vi } from "vitest";
import { useCaptureDialog } from "@/features/capture/captureDialog";
import { timerKey } from "@/features/study/components/StudyTimer";
import { onLocalReset, resetLocalState } from "@/shared/lib/localReset";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { started } from "@/shared/realtime/testEvents";

describe("resetLocalState", () => {
  beforeEach(() => window.sessionStorage.clear());

  it("runs every registration, once each", () => {
    const reset = vi.fn();
    onLocalReset(reset);
    onLocalReset(reset);
    resetLocalState();
    expect(reset).toHaveBeenCalledTimes(1);
  });

  it("empties what the modules keep outside the query cache", () => {
    useSessionStore.getState().ingest("s1", [started(1, "demo_critic")]);
    useCaptureDialog.setState({ draft: "https://example.org/offre", textDraft: "Texte collé" });
    window.sessionStorage.setItem(timerKey("study-1"), '{"phase":"work"}');
    window.sessionStorage.setItem("autre-cle", "reste");
    expect(Object.keys(useSessionStore.getState().sessions)).toEqual(["s1"]);

    resetLocalState();

    expect(useSessionStore.getState().sessions).toEqual({});
    expect(useSessionStore.getState().events).toEqual({});
    expect(useCaptureDialog.getState()).toMatchObject({
      draft: "",
      textDraft: "",
      sessionId: null,
    });
    expect(window.sessionStorage.getItem(timerKey("study-1"))).toBeNull();
    // Seul le stockage du minuteur est vidé.
    expect(window.sessionStorage.getItem("autre-cle")).toBe("reste");
  });
});
