export interface OfferFactsView {
  heading: string;
  company: string | null;
  score: string;
  facts: { label: string; value: string }[];
  missing: string;
  source: string;
}

export interface WeightSensitivityView {
  criterion: string;
  lower: string;
  higher: string;
}

export interface ComparisonView {
  rank: string;
  criteria: string;
  first: OfferFactsView;
  second: OfferFactsView;
  sensitivity: WeightSensitivityView[];
}
