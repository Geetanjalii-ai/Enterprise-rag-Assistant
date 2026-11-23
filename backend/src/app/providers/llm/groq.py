from langchain_groq import ChatGroq

from app.core.config import get_settings


def get_chat_model(temperature: float = 0.0, model_name: str = "") -> ChatGroq:
    """Instantiate a LangChain ChatGroq model using app configuration."""
    settings = get_settings()
    return ChatGroq(  # type: ignore[call-arg]
        api_key=settings.GROQ_API_KEY,  # type: ignore[arg-type]
        model=model_name or settings.GROQ_MODEL,
        temperature=temperature,
    )
