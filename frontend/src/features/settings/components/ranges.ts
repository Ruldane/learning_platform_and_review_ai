/** Bornes du contrat, en un seul endroit : les champs (`components`) et la validation les partagent. */
export const MINUTES_RANGE = { min: 0, max: 1440 } as const;
export const DELAY_RANGE = { min: 1, max: 90 } as const;
