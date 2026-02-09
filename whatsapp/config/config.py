import os
import groq
from dotenv import load_dotenv
from langchain_groq import ChatGroq


def load_environment():
    """Load and validate environment variables."""
    load_dotenv()
    required_vars = {"GROQ_API_KEY": os.getenv("GROQ_API_KEY")}
    missing = [k for k, v in required_vars.items() if not v]
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")
    return required_vars


def setup_model(llm_config):
    """Initialize the language model."""
    _ = load_environment()
    if llm_config["provider"] == "groq":
        return ChatGroq(model=llm_config["model"], temperature=llm_config["temperature"])


def setup_groq_client():
    """Initialize the Groq client for audio transcription."""
    env = load_environment()
    return groq.Groq(api_key=env["GROQ_API_KEY"])
