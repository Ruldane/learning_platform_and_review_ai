import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { useState } from "react";
import { VoiceDraftControls } from "./VoiceDraftControls";

const doubles = vi.hoisted(() => ({
  openCapture: vi.fn(),
  transcribe: vi.fn(),
}));

vi.mock("../capture", () => ({ ...doubles, canRecord: () => true }));
vi.mock("../api", () => ({ transcribe: doubles.transcribe }));

beforeEach(() => {
  vi.resetAllMocks();
  const clip = new Blob(["fictif"], { type: "audio/wav" });
  doubles.openCapture.mockImplementationOnce(async (_signal, onData: () => void) => {
    queueMicrotask(onData);
    return { finish: () => clip, cancel: vi.fn() };
  });
});

async function record(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Start recording" }));
  await user.click(await screen.findByRole("button", { name: "Stop recording" }));
}

it("asks on demand and only proposes a draft after the explicit transcription", async () => {
  const user = userEvent.setup();
  const onDraft = vi.fn();
  doubles.transcribe.mockResolvedValueOnce("Je relis cette réponse.");
  render(<VoiceDraftControls onDraft={onDraft} />);
  expect(doubles.openCapture).not.toHaveBeenCalled();
  await record(user);
  expect(doubles.transcribe).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Transcribe the recording" }));
  await waitFor(() => expect(onDraft).toHaveBeenCalledWith("Je relis cette réponse."));
});

it("aborts a pending transcription and discards its late result", async () => {
  const user = userEvent.setup();
  const onDraft = vi.fn();
  let resolve!: (text: string) => void;
  doubles.transcribe.mockImplementationOnce(
    () =>
      new Promise<string>((done) => {
        resolve = done;
      }),
  );
  render(<VoiceDraftControls onDraft={onDraft} />);
  await record(user);
  await user.click(screen.getByRole("button", { name: "Transcribe the recording" }));
  await user.click(screen.getByRole("button", { name: "Discard audio" }));
  const signal: AbortSignal = doubles.transcribe.mock.calls[0]?.[1];
  expect(signal.aborted).toBe(true);
  await act(async () => resolve("Texte arrivé après l’annulation."));
  expect(onDraft).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Start recording" })).toHaveFocus();
});

function TypedDraft() {
  const [draft, setDraft] = useState("Début de réponse.");
  return (
    <>
      <textarea aria-label="Draft" value={draft} onChange={(e) => setDraft(e.target.value)} />
      <VoiceDraftControls onDraft={setDraft} />
    </>
  );
}

it("preserves typed text and permits editing after a transcription error", async () => {
  const user = userEvent.setup();
  doubles.transcribe.mockRejectedValueOnce(new Error("Échec simulé"));
  render(<TypedDraft />);
  await record(user);
  await user.click(screen.getByRole("button", { name: "Transcribe the recording" }));
  await screen.findByRole("alert");
  const draft = screen.getByRole("textbox", { name: "Draft" });
  expect(draft).toHaveValue("Début de réponse.");
  await user.type(draft, " Suite au clavier.");
  expect(draft).toHaveValue("Début de réponse. Suite au clavier.");
});
