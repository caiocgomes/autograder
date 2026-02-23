"""Message variation generator using Anthropic Haiku."""
import json
import logging
import re
from typing import List

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

HAIKU_MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = (
    "Você é um assistente que reescreve mensagens de WhatsApp. "
    "Sua tarefa é gerar variações de uma mensagem mantendo o mesmo significado. "
    "Regras:\n"
    "1. Preserve EXATAMENTE todos os placeholders entre chaves (ex: {nome}, {turma}). "
    "Eles devem aparecer na variação exatamente como no original.\n"
    "2. Varie a estrutura, abertura, tom e ordem das frases.\n"
    "3. Mantenha comprimento aproximado ao original.\n"
    "4. Não adicione informações que não estejam no original.\n"
    "5. Responda APENAS com um JSON array de strings, sem texto adicional."
)


def _extract_placeholders(template: str) -> set:
    """Extract placeholder names from a template string."""
    return set(re.findall(r"\{(\w+)\}", template))


def _call_haiku(template: str, num_variations: int) -> List[str]:
    """Call Anthropic Haiku to generate variations. Returns raw parsed list."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    user_message = (
        f"Gere exatamente {num_variations} variações da seguinte mensagem:\n\n"
        f'"{template}"\n\n'
        f"Responda com um JSON array de {num_variations} strings."
    )

    response = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = response.content[0].text.strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        raise ValueError(
            f"LLM retornou resposta em formato inesperado (não é JSON válido)"
        )

    if not isinstance(parsed, list):
        raise ValueError(
            f"LLM retornou resposta em formato inesperado (esperado array, recebeu {type(parsed).__name__})"
        )

    return [v.strip() for v in parsed if isinstance(v, str)]


def _validate_variations(
    variations: List[str], required_placeholders: set
) -> List[str]:
    """Filter variations that contain all required placeholders."""
    if not required_placeholders:
        return variations

    valid = []
    for v in variations:
        found = _extract_placeholders(v)
        if required_placeholders.issubset(found):
            valid.append(v)
    return valid


def generate_variations(template: str, num_variations: int) -> List[str]:
    """
    Generate message variations using Anthropic Haiku.

    Args:
        template: message template with optional {placeholders}
        num_variations: number of variations to generate (3-10)

    Returns:
        List of variation strings with placeholders preserved.
        May return fewer than requested if LLM can't produce enough valid ones.

    Raises:
        ValueError: if LLM response can't be parsed
        anthropic.APIError: if API call fails
    """
    required_placeholders = _extract_placeholders(template)

    raw = _call_haiku(template, num_variations)
    valid = _validate_variations(raw, required_placeholders)

    # Retry once if we don't have enough valid variations
    if len(valid) < num_variations:
        missing = num_variations - len(valid)
        logger.info(
            "generate_variations: got %d/%d valid, retrying for %d more",
            len(valid), num_variations, missing,
        )
        retry_raw = _call_haiku(template, missing + 2)  # ask for a few extra
        retry_valid = _validate_variations(retry_raw, required_placeholders)
        valid.extend(retry_valid)

    return valid[:num_variations]
