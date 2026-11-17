/**
 * Événement « connexion requise » : le client API l'émet quand n'importe quel appel reçoit un 401
 * `auth_required` ; la porte de la coquille l'écoute (une seule fois montée) et mène à `/connexion`.
 * `shared/` n'importe aucune feature : le lien entre les deux passe par cet événement.
 */
type Listener = () => void;

const listeners = new Set<Listener>();

/** S'abonne à l'événement ; renvoie la fonction qui se désabonne. */
export function onAuthRequired(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Prévient les écouteurs qu'une réponse a dit « connexion requise ». */
export function emitAuthRequired(): void {
  for (const listener of [...listeners]) listener();
}
