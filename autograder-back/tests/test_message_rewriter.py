"""Tests for message_rewriter service — LLM-powered message variation generation."""
import pytest
import json
from unittest.mock import patch, Mock, MagicMock


# ── generate_variations ─────────────────────────────────────────────────


@patch("app.services.message_rewriter.anthropic")
def test_generate_variations_returns_list(mock_anthropic):
    """GIVEN valid template, WHEN generate_variations called, THEN returns list of strings."""
    from app.services.message_rewriter import generate_variations

    variations = [
        "Oi {nome}! Aula amanhã sobre regressão linear.",
        "E aí {nome}! Amanhã tem aula de regressão linear.",
        "{nome}, lembrete: amanhã a aula é sobre regressão linear.",
    ]
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_response = Mock()
    mock_response.content = [Mock(text=json.dumps(variations))]
    mock_client.messages.create.return_value = mock_response

    result = generate_variations("Olá {nome}! Aula amanhã sobre regressão linear.", 3)

    assert isinstance(result, list)
    assert len(result) == 3
    for v in result:
        assert isinstance(v, str)
        assert "{nome}" in v


@patch("app.services.message_rewriter.anthropic")
def test_generate_variations_exact_count(mock_anthropic):
    """GIVEN num_variations=6, WHEN called, THEN returns exactly 6 variations."""
    from app.services.message_rewriter import generate_variations

    variations = [f"Variação {i} {{nome}}" for i in range(6)]
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_response = Mock()
    mock_response.content = [Mock(text=json.dumps(variations))]
    mock_client.messages.create.return_value = mock_response

    result = generate_variations("Olá {nome}!", 6)
    assert len(result) == 6


@patch("app.services.message_rewriter.anthropic")
def test_generate_variations_preserves_all_placeholders(mock_anthropic):
    """GIVEN template with {nome}, {turma}, WHEN called, THEN each variation has both."""
    from app.services.message_rewriter import generate_variations

    variations = [
        "Oi {nome}! Sua turma {turma} começa amanhã.",
        "{nome}, a turma {turma} tem aula amanhã.",
        "Fala {nome}! Turma {turma} amanhã!",
    ]
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_response = Mock()
    mock_response.content = [Mock(text=json.dumps(variations))]
    mock_client.messages.create.return_value = mock_response

    result = generate_variations("Olá {nome}! Turma {turma} começa amanhã.", 3)

    for v in result:
        assert "{nome}" in v
        assert "{turma}" in v


@patch("app.services.message_rewriter.anthropic")
def test_generate_variations_discards_missing_placeholders(mock_anthropic):
    """GIVEN LLM returns variations where some lost placeholders, WHEN validated, THEN invalid ones discarded."""
    from app.services.message_rewriter import generate_variations

    # First call: 2 of 4 are valid (have {nome}), 2 are invalid
    first_response = [
        "Oi {nome}! Aula amanhã.",
        "Aula amanhã pessoal!",  # missing {nome}
        "E aí {nome}! Não falte!",
        "Lembrete de aula amanhã.",  # missing {nome}
    ]
    # Retry call: 2 more valid
    retry_response = [
        "Fala {nome}! Amanhã tem aula.",
        "{nome}, amanhã é dia de aula!",
    ]

    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    resp1 = Mock()
    resp1.content = [Mock(text=json.dumps(first_response))]
    resp2 = Mock()
    resp2.content = [Mock(text=json.dumps(retry_response))]
    mock_client.messages.create.side_effect = [resp1, resp2]

    result = generate_variations("Olá {nome}! Aula amanhã.", 4)

    assert len(result) == 4
    for v in result:
        assert "{nome}" in v


@patch("app.services.message_rewriter.anthropic")
def test_generate_variations_returns_partial_if_retry_insufficient(mock_anthropic):
    """GIVEN LLM can't produce enough valid variations after retry, THEN returns what's available."""
    from app.services.message_rewriter import generate_variations

    # Both calls produce only 1 valid each
    first_response = [
        "Oi {nome}!",
        "Aula amanhã!",  # missing {nome}
        "Vem pra aula!",  # missing {nome}
    ]
    retry_response = [
        "{nome}, amanhã!",
        "Aula!",  # missing {nome}
    ]

    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    resp1 = Mock()
    resp1.content = [Mock(text=json.dumps(first_response))]
    resp2 = Mock()
    resp2.content = [Mock(text=json.dumps(retry_response))]
    mock_client.messages.create.side_effect = [resp1, resp2]

    result = generate_variations("Olá {nome}! Aula amanhã.", 3)

    # Should return whatever valid ones we got (2 in this case)
    assert len(result) == 2
    for v in result:
        assert "{nome}" in v


@patch("app.services.message_rewriter.anthropic")
def test_generate_variations_prompt_includes_template(mock_anthropic):
    """GIVEN template, WHEN called, THEN prompt sent to Haiku includes the template text."""
    from app.services.message_rewriter import generate_variations

    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_response = Mock()
    mock_response.content = [Mock(text='["Oi {nome}!", "E aí {nome}!"]')]
    mock_client.messages.create.return_value = mock_response

    generate_variations("Olá {nome}! Mensagem especial.", 2)

    call_args = mock_client.messages.create.call_args
    messages = call_args[1]["messages"]
    user_message = messages[0]["content"]
    assert "Olá {nome}! Mensagem especial." in user_message


@patch("app.services.message_rewriter.anthropic")
def test_generate_variations_uses_haiku_model(mock_anthropic):
    """GIVEN call to generate_variations, WHEN LLM is called, THEN uses Haiku model."""
    from app.services.message_rewriter import generate_variations

    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_response = Mock()
    mock_response.content = [Mock(text='["Oi {nome}!"]')]
    mock_client.messages.create.return_value = mock_response

    generate_variations("Olá {nome}!", 1)

    call_args = mock_client.messages.create.call_args
    assert "haiku" in call_args[1]["model"]


@patch("app.services.message_rewriter.anthropic")
def test_generate_variations_strips_whitespace(mock_anthropic):
    """GIVEN LLM returns variations with extra whitespace, WHEN parsed, THEN stripped."""
    from app.services.message_rewriter import generate_variations

    variations = ["  Oi {nome}!  ", "\nE aí {nome}!\n"]
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_response = Mock()
    mock_response.content = [Mock(text=json.dumps(variations))]
    mock_client.messages.create.return_value = mock_response

    result = generate_variations("Olá {nome}!", 2)

    assert result[0] == "Oi {nome}!"
    assert result[1] == "E aí {nome}!"


@patch("app.services.message_rewriter.anthropic")
def test_generate_variations_api_error_raises(mock_anthropic):
    """GIVEN Anthropic API fails, WHEN called, THEN raises exception."""
    from app.services.message_rewriter import generate_variations

    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_anthropic.APIError = type("APIError", (Exception,), {})
    mock_client.messages.create.side_effect = mock_anthropic.APIError("rate limit")

    with pytest.raises(Exception):
        generate_variations("Olá {nome}!", 3)


@patch("app.services.message_rewriter.anthropic")
def test_generate_variations_invalid_json_raises(mock_anthropic):
    """GIVEN LLM returns non-JSON response, WHEN parsed, THEN raises ValueError."""
    from app.services.message_rewriter import generate_variations

    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_response = Mock()
    mock_response.content = [Mock(text="This is not JSON at all")]
    mock_client.messages.create.return_value = mock_response

    with pytest.raises(ValueError, match="formato inesperado"):
        generate_variations("Olá {nome}!", 3)


@patch("app.services.message_rewriter.anthropic")
def test_generate_variations_json_not_list_raises(mock_anthropic):
    """GIVEN LLM returns valid JSON but not a list, WHEN parsed, THEN raises ValueError."""
    from app.services.message_rewriter import generate_variations

    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_response = Mock()
    mock_response.content = [Mock(text='{"variation": "Oi {nome}!"}')]
    mock_client.messages.create.return_value = mock_response

    with pytest.raises(ValueError, match="formato inesperado"):
        generate_variations("Olá {nome}!", 3)


@patch("app.services.message_rewriter.anthropic")
def test_generate_variations_template_without_placeholders(mock_anthropic):
    """GIVEN template with no placeholders, WHEN called, THEN variations also have no placeholders."""
    from app.services.message_rewriter import generate_variations

    variations = [
        "Aula amanhã, não faltem!",
        "Lembrete: aula amanhã!",
        "Amanhã tem aula pessoal!",
    ]
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_response = Mock()
    mock_response.content = [Mock(text=json.dumps(variations))]
    mock_client.messages.create.return_value = mock_response

    result = generate_variations("Aula amanhã, não faltem!", 3)
    assert len(result) == 3
