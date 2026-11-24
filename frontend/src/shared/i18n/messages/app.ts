/** Textes du squelette : application, navigation, accueil, état des services, erreurs communes. */
export const appMessages = {
  app: {
    name: "Tremplin",
    skipToContent: "Skip to content",
    loading: "Loading…",
    newTab: "(opens in a new tab)",
    notFound: {
      title: "Page not found",
      back: "Back to home",
    },
  },
  nav: {
    label: "Main navigation",
    menu: "Menu",
    here: "You are here",
    crumb: "{section} › {page}",
    panel: "Landmarks and information",
    home: "Home",
    learn: "Learn",
    study: "Study",
    skills: "Skills",
    career: "Career",
    applications: "Applications",
    memory: "Memory",
    settings: "Settings",
  },
  health: {
    label: "Service status",
    loading: "Checking services…",
    allOk: "All services are responding",
    degraded: "Some services aren't responding",
    down: "Database unavailable",
    unreachable: "Server unreachable",
    failing: "{service}: {detail}",
  },
  time: {
    now: "just now",
    minutes: "{count} min ago",
    hours: "{count} h ago",
    days: "{count} d ago",
  },
  errors: {
    generic: "Something went wrong. Try again in a moment.",
    network: "Can't reach the server. Check that Tremplin is running.",
    retry: "Retry",
  },
} as const;
