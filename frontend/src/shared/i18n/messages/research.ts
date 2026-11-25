/** Texts for web research (the Scout trial). */
export const research = {
  nav: { bench: "Research test" },
  page: {
    title: "Research test",
    intro:
      "Run the Scout on a query and watch live the queries sent and the sources kept, discarded or unreadable.",
    settingsLink: "Research settings",
    loading: "Opening the test…",
    reconnecting: "Reconnecting to the feed…",
    again: "New test",
    failed: "The test failed.",
  },
  bench: {
    query: "Query",
    queryHint: "From 2 to 300 characters.",
    urls: "Extra addresses",
    urlsHint: "One address per line, 5 at most: the Scout reads them in addition to its search.",
    submit: "Run the test",
    busy: "Test in progress…",
    errors: {
      query: "The query must be from 2 to 300 characters.",
      urlScheme: "This address must start with http:// or https://: {url}",
      tooManyUrls: "{max} extra addresses at most.",
    },
  },
} as const;
