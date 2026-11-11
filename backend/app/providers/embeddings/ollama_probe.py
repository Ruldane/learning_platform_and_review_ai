"""Sonde d'Ollama : `GET /api/tags` liste les modèles présents ; le modèle d'embeddings doit y
figurer. Le pourcentage de téléchargement n'est pas exposé ici (écran de premier lancement, D28)."""

import httpx

from app.providers.health import HealthStatus, available, unexpected_status


class OllamaProbe:
    name = "ollama"

    def __init__(self, url: str, model: str, http: httpx.AsyncClient) -> None:
        self._url = url.rstrip("/")
        self._model = model
        self._http = http

    def _has_model(self, payload: object) -> bool:
        models = payload.get("models") if isinstance(payload, dict) else None
        if not isinstance(models, list):
            return False
        names = [m.get("name") for m in models if isinstance(m, dict)]
        # « bge-m3 » correspond à « bge-m3 » et « bge-m3:latest », pas à « bge-m3-large ».
        return any(isinstance(n, str) and self._model in (n, n.split(":", 1)[0]) for n in names)

    async def check(self) -> HealthStatus:
        response = await self._http.get(f"{self._url}/api/tags")
        if response.status_code != 200:
            return unexpected_status(response)
        if not self._has_model(response.json()):
            return HealthStatus(
                ok=False, detail=f"Le modèle {self._model} est en cours de téléchargement."
            )
        return available()
