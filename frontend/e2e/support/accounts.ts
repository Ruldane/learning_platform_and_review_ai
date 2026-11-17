/**
 * Les deux comptes du parcours n° 5 (`account.spec.ts`), connus du faux fournisseur
 * `backend/scripts/fake_oidc.py` : l'adresse vient de `login_hint`, sans mot de passe. Camille est
 * l'adresse par défaut du faux fournisseur (le lien « Se connecter avec Google » sans `login_hint`).
 * Les deux sont **nommées** dans `ALLOWED_EMAILS` : la reprise de l'espace local n'est proposée
 * qu'à une adresse d'une liste explicite (jamais avec `*`).
 */
export const CAMILLE = "camille.exemple@example.org";
export const DOMINIQUE = "dominique.exemple@example.org";

/** La ligne du journal de l'espace `local`, posée par `tests.e2e.server --seed-local`. */
export const LOCAL_NOTE =
  "Note prise sur cet ordinateur avant la connexion : relire les jointures SQL.";

/** `ALLOWED_EMAILS` du serveur du parcours n° 5. */
export const ALLOWED_EMAILS = `${CAMILLE},${DOMINIQUE}`;
