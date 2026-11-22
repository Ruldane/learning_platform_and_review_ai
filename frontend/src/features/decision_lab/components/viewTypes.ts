export interface ArchitectureFieldsValue {
  replicas: number;
  capacityPerReplica: number;
  hourlyCents: number;
}

export interface AssumptionFields {
  rate: number;
  duration: number;
  outage: number;
  first: ArchitectureFieldsValue;
  second: ArchitectureFieldsValue;
}

export interface ArchitectureMeasures {
  served: number;
  missed: number;
  servedFraction: number | null;
  costEuros: number;
}

export interface ComparisonView {
  attempted: number;
  first: ArchitectureMeasures;
  second: ArchitectureMeasures;
}

export interface ScenarioLink {
  id: string;
  title: string;
  createdAt: string;
}
