/**
 * "Sign-in required" event: the API client emits it when any call gets a 401
 * `auth_required`; the shell gate listens (mounted once) and leads to
 * `/login`. `shared/` imports no feature: the link between the two goes through this
 * event.
 */
type Listener = () => void;

const listeners = new Set<Listener>();

/** Subscribes to the event; returns the function that unsubscribes. */
export function onAuthRequired(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Notifies listeners that a response said "sign-in required". */
export function emitAuthRequired(): void {
  for (const listener of [...listeners]) {
    // A listener that throws does not stop the next ones (the plan expects several gates);
    // we only log the fact, never the error.
    try {
      listener();
    } catch {
      console.error("auth_listener_failed");
    }
  }
}
