from fastapi import APIRouter

# Chaque feature ajoute ici son routeur ; `create_app` les monte sous `/api/v1`.
FEATURE_ROUTERS: list[APIRouter] = []
