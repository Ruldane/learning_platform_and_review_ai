import { useRef, useState } from "react";
import type { ModelChoice, SettingsOut } from "../types";
import { withAgentOverrides } from "../userSettings";
import { useUpdateSettings } from "./useUpdateSettings";

/** Requested choices not yet written: `null` removes the agent's override. */
type Wanted = Record<string, ModelChoice | null>;

/**
 * Choose an agent's model, or return it to its level (`null`): one full `PUT /settings`,
 * one at a time. A choice made during a send (one more arrow in a list, another agent) is never
 * dropped: it waits, and each agent's last choice is replayed at the end of the send, from the
 * settings the server has just returned. The lists show the requested choice without
 * going back (`overrides`); if a send fails, they fall back to what the server saved and the
 * pending choices are abandoned.
 */
export function useAgentOverrideActions(settings: SettingsOut) {
  const update = useUpdateSettings();
  const [wanted, setWanted] = useState<Wanted>({});
  const [saved, setSaved] = useState(false);
  const queue = useRef<Wanted>({});
  const running = useRef(false);

  async function flush(start: SettingsOut) {
    running.current = true;
    update.reset();
    try {
      let current = start;
      while (Object.keys(queue.current).length > 0) {
        const batch = queue.current;
        queue.current = {};
        current = await update.mutateAsync(withAgentOverrides(current, batch));
      }
      setSaved(true);
    } catch {
      queue.current = {}; // the error is shown from the mutation
    } finally {
      running.current = false;
      setWanted({});
    }
  }

  return {
    pending: update.isPending,
    error: update.error,
    /** A save has just finished (the requested choices are written). */
    saved,
    /** Overrides as the server has them, plus the requested choices it does not have yet. */
    overrides: (): Record<string, ModelChoice | undefined> => {
      const shown: Record<string, ModelChoice | undefined> = { ...settings.agent_overrides };
      for (const [agent, choice] of Object.entries(wanted)) {
        if (choice) shown[agent] = choice;
        else delete shown[agent];
      }
      return shown;
    },
    setOverride: (agent: string, choice: ModelChoice | null) => {
      queue.current[agent] = choice;
      setWanted((current) => ({ ...current, [agent]: choice }));
      setSaved(false);
      if (!running.current) void flush(settings);
    },
  };
}
