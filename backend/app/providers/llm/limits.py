from langchain_core.language_models import BaseChatModel


def with_output_limit(model: BaseChatModel, tokens: int) -> BaseChatModel:
    """Borne un modèle d'API sans changer sa configuration partagée."""
    provider = (model.metadata or {}).get("tremplin_provider")
    if provider == "glm":
        # Z.ai reçoit max_tokens ; ChatOpenAI renommerait ce champ en max_completion_tokens.
        extra_body = getattr(model, "extra_body", None) or {}
        return model.model_copy(update={"extra_body": {**extra_body, "max_tokens": tokens}})
    if provider in {"anthropic", "openai"}:
        return model.model_copy(update={"max_tokens": tokens})
    return model  # client joué ou fournisseur scripté
