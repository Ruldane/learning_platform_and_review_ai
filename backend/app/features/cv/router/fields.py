"""Input errors of the CV routes: a 422 names the fields by their path
(`details.fields`, "experiences.2.role"), without any value or pydantic message. The code lives in
`app.core.field_paths` (shared with applications); re-exported here."""

from app.core.field_paths import FieldPathsRoute as FieldPathsRoute
from app.core.field_paths import field_paths as field_paths
from app.core.field_paths import invalid_fields as invalid_fields
