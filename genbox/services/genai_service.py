import json
import csv
import io
import logging
import asyncio
import google.generativeai as genai
from openai import OpenAI, AuthenticationError, APIStatusError, APIError
from typing import Any
from genbox.core.config import settings
from jsonschema import validate, ValidationError

logger = logging.getLogger(__name__)

MAX_CONTEXT_SIZE = 108_000

class GenAIService:
    def __init__(self):
        # Configure Google
        if settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
        
    def _get_provider_config(self, model_name: str) -> tuple[str, str | None, str | None]:
        """Returns (provider, api_key, base_url)"""
        m = model_name.lower()
        if "gemini" in m:
            return "google", settings.GOOGLE_API_KEY, None
        if "gpt" in m:
            return "openai", settings.OPENAI_API_KEY, None
        if "deepseek" in m:
            return "openai", settings.DEEPSEEK_API_KEY, settings.DEEPSEEK_BASE_URL
        if "glm" in m:
            return "openai", settings.GLM_API_KEY, settings.GLM_BASE_URL
        if "kimi" in m:
            return "openai", settings.KIMI_API_KEY, settings.KIMI_BASE_URL
        
        return "google", settings.GOOGLE_API_KEY, None

    async def _call_google_with_retry(self, model_name: str, prompt: str) -> str:
        model = genai.GenerativeModel(model_name)
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                err_msg = str(e).lower()
                # Check for common authentication failure markers
                if "api_key_invalid" in err_msg or "unauthorized" in err_msg or "401" in err_msg:
                    logger.error(f"Google API Authentication failed: {str(e)}")
                    raise e
                
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"Google API temporary error (attempt {attempt+1}), retrying in {wait_time}s: {str(e)}")
                    await asyncio.sleep(wait_time)
                else:
                    raise e

    async def _call_openai_with_retry(self, model_name: str, prompt: str, api_key: str, base_url: str | None = None) -> str:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=60.0)
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content
            except AuthenticationError as e:
                logger.error(f"OpenAI-compatible provider Authentication failed for {model_name}: {str(e)}")
                raise e
            except (APIStatusError, APIError) as e:
                # Retry for 5xx errors or specific temporary ones
                is_temporary = e.status_code >= 500 if hasattr(e, 'status_code') else True
                if is_temporary and attempt < max_retries:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"OpenAI-compatible provider temporary error (attempt {attempt+1}), retrying in {wait_time}s: {str(e)}")
                    await asyncio.sleep(wait_time)
                else:
                    raise e
            except Exception as e:
                if attempt < max_retries:
                    await asyncio.sleep(2)
                    continue
                raise e

    async def generate_text(self, prompt: str, model_name: str | None = None) -> str:
        # 1. Boundary Check: Empty Prompt
        if not prompt or not prompt.strip():
            logger.info("Empty prompt received, ignoring and returning empty.")
            return ""

        # 2. Boundary Check: Max Context Size
        if len(prompt) > MAX_CONTEXT_SIZE:
            logger.warning(f"Prompt exceeds max size ({len(prompt)} > {MAX_CONTEXT_SIZE}). Truncating.")
            prompt = prompt[:MAX_CONTEXT_SIZE]

        model_name = model_name or settings.DEFAULT_MODEL
        provider, api_key, base_url = self._get_provider_config(model_name)
        
        if not api_key:
            logger.error(f"API Key for {model_name} family is missing.")
            raise ValueError(f"API Key for model family of '{model_name}' is not configured.")

        if provider == "google":
            return await self._call_google_with_retry(model_name, prompt)
        else:
            return await self._call_openai_with_retry(model_name, prompt, api_key, base_url)

    async def generate_dict(self, prompt: str, model_name: str | None = None, json_schema: dict[str, Any] | None = None, retry_count: int = 0) -> dict[str, Any]:
        if not prompt or not prompt.strip():
            return {}

        model_name = model_name or settings.DEFAULT_MODEL
        schema_instruction = f"\n\nPlease return a valid JSON object matching this schema: {json.dumps(json_schema)}" if json_schema else "\n\nPlease return a valid JSON object ONLY."
        full_prompt = f"{prompt}{schema_instruction}\nNo other text, just the JSON."
        
        try:
            raw_text = await self.generate_text(full_prompt, model_name)
            if not raw_text:
                return {}
            clean_text = self._clean_markdown(raw_text, "json")
            data = json.loads(clean_text)
            
            if json_schema:
                validate(instance=data, schema=json_schema)
            
            return data
        except (json.JSONDecodeError, ValidationError, Exception) as e:
            # If it's an Auth error, don't trigger the structural retry
            if "authentication" in str(e).lower() or "unauthorized" in str(e).lower() or "401" in str(e).lower():
                raise e

            if retry_count < 1:
                error_type = "JSON formatting" if isinstance(e, json.JSONDecodeError) else "schema validation"
                logger.warning(f"Retrying dict generation for {model_name} due to {error_type} error: {str(e)}")
                retry_prompt = f"The previous response failed {error_type}. Error: {str(e)}. Please try again and return ONLY a valid JSON object matching the requested schema."
                return await self.generate_dict(f"{prompt}\n\n{retry_prompt}", model_name, json_schema, retry_count + 1)
            
            logger.error(f"Failed to generate dict for {model_name} after retry: {str(e)}")
            return {}

    async def generate_csv(self, prompt: str, model_name: str | None = None, retry_count: int = 0) -> list[dict[str, Any]]:
        if not prompt or not prompt.strip():
            return []

        model_name = model_name or settings.DEFAULT_MODEL
        full_prompt = f"{prompt}\n\nPlease return a valid CSV data ONLY. No other text."
        
        try:
            raw_text = await self.generate_text(full_prompt, model_name)
            if not raw_text:
                return []
            clean_text = self._clean_markdown(raw_text, "csv")
            
            f = io.StringIO(clean_text)
            reader = csv.DictReader(f)
            data = list(reader)
            if not data:
                raise ValueError("Empty CSV or invalid format")
            return data
        except Exception as e:
            if "authentication" in str(e).lower() or "unauthorized" in str(e).lower() or "401" in str(e).lower():
                raise e

            if retry_count < 1:
                logger.warning(f"Retrying CSV generation for {model_name} due to error: {str(e)}")
                retry_prompt = f"The previous response was not a valid CSV format. Error: {str(e)}. Please try again and return ONLY valid CSV data."
                return await self.generate_csv(f"{prompt}\n\n{retry_prompt}", model_name, retry_count + 1)
            
            logger.error(f"Failed to generate CSV for {model_name} after retry: {str(e)}")
            return []

    def _clean_markdown(self, text: str, format_type: str) -> str:
        text = text.strip()
        if text.startswith(f"```{format_type}"):
            text = text[len(f"```{format_type}"):]
        elif text.startswith("```"):
            text = text[3:]
        
        if text.endswith("```"):
            text = text[:-3]
        
        if format_type == "json":
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                text = text[start:end+1]
        
        return text.strip()

genai_service = GenAIService()
