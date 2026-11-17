/** Textes de la connexion, de la reprise de l'espace local et du menu du compte. */
export const auth = {
  gate: {
    checking: "Vérification de ta connexion…",
    failed: "Impossible de vérifier ta connexion.",
  },
  login: {
    title: "Connexion",
    intro: "Connecte-toi avec ton compte Google pour ouvrir ton espace Tremplin.",
    google: "Se connecter avec Google",
    privacy: "Tremplin ne reçoit de Google que ton adresse e-mail et ton nom.",
  },
  // Un message par code de `/connexion?erreur=<code>` ; `unknown` sert à tout autre code.
  errors: {
    access_denied: "Connexion annulée.",
    state_invalid: "La connexion a expiré, recommence.",
    email_not_allowed: "Ce compte n'est pas autorisé sur cette instance.",
    email_unverified: "Adresse Google non vérifiée.",
    google_unavailable: "Google ne répond pas, réessaie dans un instant.",
    token_invalid: "Réponse de Google refusée.",
    claim_expired: "Le choix de la reprise a expiré, reconnecte-toi.",
    local_already_claimed: "Les données de cet ordinateur sont déjà reprises par un compte.",
    unknown: "La connexion a échoué, réessaie.",
  },
  claim: {
    title: "Reprendre tes données ?",
    intro:
      "Tremplin a déjà un espace sur cet ordinateur. Tu peux le rattacher à ton compte Google ou commencer un espace vide.",
    take: "Reprendre les données de cet ordinateur",
    takeHint: "Ton espace actuel (profil, programme, mémoire) devient celui de ton compte.",
    fresh: "Commencer un espace vide",
    freshHint: "L'espace de cet ordinateur reste intact, sans être relié à ton compte.",
    pending: "Un instant…",
  },
  account: {
    label: "Compte",
    logout: "Se déconnecter",
    loggingOut: "Déconnexion…",
    logoutFailed: "La déconnexion a échoué.",
  },
} as const;
