import os
from pathlib import Path


class DeepAnalyzeAPI:
    """
    DeepAnalyzeAPI provides functionality to interact with external LLM APIs
    for text generation and analysis.
    """

    def __init__(
        self,
        api_base: str = None,
        model_name: str = None,
        api_key: str = None,
    ):
        self.api_base = api_base or os.environ.get("LLM_API_BASE", "https://api.deepseek.com/v1")
        self.model_name = model_name or os.environ.get("LLM_MODEL", "deepseek-chat")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", os.environ.get("DEEPSEEK_API_KEY"))

        if not self.api_key:
            raise ValueError("API key is required. Set OPENAI_API_KEY or DEEPSEEK_API_KEY environment variable.")

    def get_config(self) -> dict:
        """
        Returns the current configuration.
        """
        return {
            "api_base": self.api_base,
            "model_name": self.model_name,
            "api_key": "***" if self.api_key else None
        }
