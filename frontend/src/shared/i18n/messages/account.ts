/** Texts for the « Mes données » page: export and deletion of the whole account (SPEC 17.3). */
export const account = {
  nav: { data: "My data" },
  title: "My data",
  intro: "What Tremplin keeps in your space: you can take it with you, or erase it all.",
  export: {
    title: "Export",
    description:
      "A zip archive with everything your space holds: your settings, your profile and " +
      "résumé, your goals and program, your lessons and reviews, your memory, your " +
      "applications and the log of model calls, plus the files you imported. " +
      "It never contains your API keys, nor the memory vectors, which Tremplin " +
      "recomputes.",
    link: "Export all my data",
    help: "The download opens in a new tab; if your session has expired, sign in again and retry.",
  },
  delete: {
    title: "Delete everything",
    identity: "Account to erase: {account}",
    localIdentity: "local space on this computer",
    warning: "This cannot be undone.",
    scope:
      "It erases everything Tremplin keeps for you: settings, keys entered in " +
      "the interface, profile, résumé, program, lessons, memory, applications, call log and " +
      "imported files. Export first if you want to keep a copy.",
    keep: "API keys written in the .env file are not affected.",
    after:
      "With a Google account, your Tremplin account is removed too and you return to the " +
      "sign-in page. Purging the vectors may finish in the background. In local mode, you " +
      "return to the first launch.",
    word: "SUPPRIMER",
    label: "Type SUPPRIMER to confirm",
    submit: "Delete everything",
    pending: "Deleting…",
    confirmationRequired: "The confirmation word is wrong: type SUPPRIMER, in capitals.",
    retry: "You can retry: deletion resumes where it stopped.",
    accountChanged:
      "The signed-in account changed in another tab. Nothing was deleted. " +
      "Check the account shown before trying again.",
    notStarted: "Nothing was deleted: you can safely retry.",
    rowsUntouched:
      "The vector memory isn't responding. Nothing was deleted from the database. You can retry.",
    waiting: "Deleting… don't close this page.",
  },
} as const;
