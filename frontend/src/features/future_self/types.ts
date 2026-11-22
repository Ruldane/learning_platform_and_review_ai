import type { components, paths } from "@/shared/api/schema";

export type Projection = components["schemas"]["FutureSelfOut"];
export type ProjectionQuery = NonNullable<paths["/api/v1/future-self"]["get"]["parameters"]["query"]>;
