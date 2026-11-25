from langchain_core.language_models import BaseChatModel


def with_output_limit(model: BaseChatModel, tokens: int) -> BaseChatModel:
    """Bounds an API model without changing its shared configuration."""
    provider = (model.metadata or {}).get("tremplin_provider")
    if provider == "glm":
        # Z.ai receives max_tokens; ChatOpenAI would rename this field to max_completion_tokens.
        extra_body = getattr(model, "extra_body", None) or {}
        return model.model_copy(update={"extra_body": {**extra_body, "max_tokens": tokens}})
    if provider in {"anthropic", "openai"}:
        return model.model_copy(update={"max_tokens": tokens})
    return model  # played client or scripted provider
