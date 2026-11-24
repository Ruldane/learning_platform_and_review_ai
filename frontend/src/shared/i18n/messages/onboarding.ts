/** Textes du premier lancement (`/welcome`, SPEC 15.5 et 17.3). */
export const onboarding = {
  gate: {
    checking: "Preparing your space…",
    failed: "Could not read your settings.",
  },
  page: {
    label: "First launch",
    loading: "Loading your space…",
    deleted: "Your data has been deleted: Tremplin is starting from scratch.",
  },
  steps: {
    counter: "Step {step} of {total}",
    previous: "Previous",
    next: "Next",
    later: "Later",
    skipStep: "Skip",
    finish: "Finish",
    finishing: "Saving…",
    skipAll: "Skip the welcome",
    blocked: "Fix the flagged fields before finishing.",
    titles: {
      health: "Tremplin's services",
      privacy: "What leaves your machine",
      key: "Your API key",
      cv: "Your CV",
      availability: "Your available time",
    },
  },
  health: {
    intro:
      "Tremplin relies on a few local services. Their status updates on its own, there is " +
      "nothing for you to do here.",
    list: "Service status",
    checking: "Checking services…",
    unreachable: "Could not read the service status: retrying automatically.",
    ok: "responding",
    down: "not responding",
    services: {
      db: "Database",
      llm: "Language model key",
      qdrant: "Vector memory (Qdrant)",
      ollama: "Embedding model (Ollama)",
      searxng: "Web search (SearXNG)",
    },
    keyLater: "to set up in step 3",
    recovered: "{services}: responding again.",
  },
  embedding: {
    label: "Embedding model",
    percent: "{model}: {percent}%",
    ready: "{model}: ready",
    waiting: "{model}: download pending",
    unreadable: "Could not read the model's progress: retrying automatically.",
    hint: "The model downloads only once; Tremplin needs it only for memory.",
  },
  privacy: {
    intro:
      "Here, in plain terms, is what leaves your computer. You can review it later in Settings.",
    table: "What leaves your machine",
    data: "Data",
    destination: "Destination",
    rows: {
      prompts: {
        data: "Prompts, which may contain your CV and your profile",
        destination: "The model provider you choose",
      },
      searches: {
        data: "Search queries",
        destination: "The engines queried by SearXNG",
      },
      rest: {
        data: "Everything else (database, vectors, files, embeddings)",
        destination: "Stays on your machine",
      },
    },
    safeguards: "What Tremplin does to limit what leaves",
    search: "Search removes your name, email and phone number from queries before sending them.",
    contacts: "The contacts you save are limited to a name, a role and a public link.",
    control: "At any time, Settings > My data lets you export or delete everything.",
  },
  key: {
    intro:
      "A provider's key sends your prompts to that provider (previous step). One key is enough, " +
      "but it must belong to your models' provider: if you give another one, " +
      "Tremplin switches your models to that provider.",
    provider: "Provider",
    fromEnv: "A key is already provided by the .env file ({providers}): you can move on.",
    fromUi: "A key is already saved ({providers}): you can move on.",
    moveTo:
      "Your models will switch to {provider}, this key's provider, when you go to the next " +
      "step. You can change them in Settings > Models and keys.",
    noPreset:
      "The {provider} key has no model preset: once the welcome is done, choose its " +
      "models in Settings > Models and keys. Until then, CV import stays closed.",
    none: "No key yet: you can enter one, or do it later in Settings.",
    loading: "Loading providers…",
  },
  cv: {
    intro:
      "Your CV and your LinkedIn profile (as PDF) are used to write your master profile. You can " +
      "skip this step and do it later in Career.",
    privacy: "Their text is sent to the model provider to be read.",
    cvLabel: "Your CV (PDF, 10 MB max)",
    linkedinLabel: "Your LinkedIn profile (PDF, optional)",
    submit: "Import my documents",
    pending: "Sending…",
    done:
      "Your documents have been sent: Tremplin reads them in the background, " +
      "and you will find your profile in Career.",
    notPdf: "This file is not a PDF: choose a .pdf file.",
    tooBig: "This file is over 10 MB: choose a smaller PDF.",
    needCv: "Choose your CV first.",
    needKey:
      "Without an API key, Tremplin cannot read your documents: " + "add a key in step 3 first.",
    goToKey: "Go to the key step",
    chosen: "Selected file: {name}",
    notSent: "Nothing is sent until you click “Import my documents”.",
    linkedinLeftOut: "Your LinkedIn profile was not kept: only your CV will be sent.",
  },
  availability: {
    intro:
      "Say how much time you can devote to learning. You can adjust it at any " +
      "time in Settings > Availability and pace.",
  },
} as const;
