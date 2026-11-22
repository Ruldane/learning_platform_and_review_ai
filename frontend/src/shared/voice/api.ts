import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";

export async function transcribe(recording: Blob, signal: AbortSignal): Promise<string> {
  const result = await api.POST("/voice/transcriptions", {
    headers: { "Content-Type": "audio/wav" },
    body: "",
    bodySerializer: () => recording,
    signal,
  });
  return unwrap(result).text;
}

export async function speak(text: string, signal: AbortSignal): Promise<Blob> {
  return unwrap(await api.POST("/voice/speech", { body: { text }, parseAs: "blob", signal }));
}
