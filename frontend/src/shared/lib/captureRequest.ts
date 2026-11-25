import { create } from "zustand";

interface CaptureRequestState {
  /** Number of capture-open requests since the app started. */
  count: number;
  /** Requests the capture to open; the `capture` feature listens, no other one depends on it. */
  request: () => void;
}

/**
 * The shared "open capture" store: a feature that wants to offer the action (home) calls
 * `request()` without importing `capture`; `CaptureOverlay` opens its dialog when `count` changes
 * (never on mount: a counter already raised is not a request).
 */
export const useCaptureRequest = create<CaptureRequestState>((set) => ({
  count: 0,
  request: () => set((state) => ({ count: state.count + 1 })),
}));
