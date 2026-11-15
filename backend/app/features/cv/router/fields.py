"""Erreurs de saisie des routes du CV : une 422 nomme les champs par leur chemin
(`details.fields`, « experiences.2.role »), sans valeur ni message de pydantic. Le code vit dans
`app.core.field_paths` (partagé avec les candidatures) ; réexporté ici."""

from app.core.field_paths import FieldPathsRoute as FieldPathsRoute
from app.core.field_paths import field_paths as field_paths
from app.core.field_paths import invalid_fields as invalid_fields
