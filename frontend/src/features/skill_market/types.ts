import type { paths } from "@/shared/api/schema";

export type MarketFilters = NonNullable<paths["/api/v1/skill-market"]["get"]["parameters"]["query"]>;
