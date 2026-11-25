/** Texts for sign-in, resuming the local space, and the account menu. */
export const auth = {
  gate: {
    checking: "Checking your sign-in…",
    failed: "Couldn't check your sign-in.",
  },
  login: {
    title: "Sign in",
    intro: "Sign in with your Google account to open your Tremplin space.",
    google: "Sign in with Google",
    privacy: "Tremplin only receives your email address and name from Google.",
  },
  // One message per `/login?error=<code>` code; `unknown` covers any other code.
  errors: {
    access_denied: "Sign-in cancelled.",
    state_invalid: "The sign-in expired, start again.",
    email_not_allowed: "This account isn't allowed on this instance.",
    email_unverified: "Google address not verified.",
    google_unavailable: "Google isn't responding, try again in a moment.",
    token_invalid: "Google's response was rejected.",
    claim_expired: "The takeover choice expired, sign in again.",
    local_already_claimed: "This computer's data has already been taken over by an account.",
    unknown: "Sign-in failed, try again.",
  },
  claim: {
    title: "Take over your data?",
    intro:
      "Tremplin already has a space on this computer. You can link it to your Google account or start with an empty space.",
    take: "Take over this computer's data",
    takeHint: "Your current space (profile, program, memory) becomes your account's space.",
    fresh: "Start with an empty space",
    freshHint: "This computer's space stays intact, without being linked to your account.",
    pending: "One moment…",
  },
  account: {
    label: "Account",
    logout: "Sign out",
    loggingOut: "Signing out…",
    logoutFailed: "Sign-out failed.",
  },
} as const;
