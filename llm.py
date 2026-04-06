"""Cerebras LLM client with retry logic and structured output support."""

import time
import json
import logging
from typing import Optional
from cerebras.cloud.sdk import Cerebras

import config

logger = logging.getLogger(__name__)


class CerebrasLLM:
    """Wrapper around the Cerebras Cloud SDK with retry + structured output."""

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = config.LLM_TEMPERATURE,
        max_tokens: int = config.LLM_MAX_TOKENS,
    ):
        if not config.CEREBRAS_API_KEY:
            raise ValueError("CEREBRAS_API_KEY not set. Check your .env file.")

        self.client = Cerebras(api_key=config.CEREBRAS_API_KEY)
        self.model = model or config.MODEL_FAST
        self.temperature = temperature
        self.max_tokens = max_tokens
        logger.info(f"CerebrasLLM initialised — model={self.model}, temp={self.temperature}")

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        model_override: Optional[str] = None,
        temperature_override: Optional[float] = None,
        max_tokens_override: Optional[int] = None,
    ) -> str:
        """Send a chat completion request with automatic retry on transient failures."""
        model = model_override or self.model
        temperature = temperature_override if temperature_override is not None else self.temperature
        max_tokens = max_tokens_override or self.max_tokens

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        last_error = None
        for attempt in range(1, config.LLM_MAX_RETRIES + 1):
            try:
                logger.debug(f"Attempt {attempt}/{config.LLM_MAX_RETRIES} → {model}")
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content
                logger.debug(f"Response received — {len(content)} chars")
                return content.strip()

            except Exception as e:
                last_error = e
                delay = config.LLM_RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(f"Attempt {attempt} failed: {e} — retrying in {delay:.1f}s")
                time.sleep(delay)

        raise RuntimeError(
            f"Cerebras API failed after {config.LLM_MAX_RETRIES} retries: {last_error}"
        )

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs,
    ) -> dict:
        """Chat expecting a JSON response. Parses and returns dict."""
        system_prompt_json = (
            system_prompt
            + "\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown fences, no explanation."
        )
        raw = self.chat(system_prompt_json, user_prompt, **kwargs)

        # Strip markdown fences if the model wraps anyway
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed: {e}\nRaw response:\n{raw[:500]}")
            raise ValueError(f"Model returned invalid JSON: {e}")


# ── Convenience singleton ───────────────────────────────────────────────
_default_llm: Optional[CerebrasLLM] = None


def get_llm(model: Optional[str] = None) -> CerebrasLLM:
    """Return (or create) the default LLM client."""
    global _default_llm
    if _default_llm is None or (model and model != _default_llm.model):
        _default_llm = CerebrasLLM(model=model)
    return _default_llm
