from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.services.ai_service as ai_module
from app.config import Settings
from app.services.ai_service import AIService, AIServiceError, AIServiceNotAvailableError
from app.utils.cache import CacheManager

pytestmark = pytest.mark.unit


@pytest.fixture
def cache_manager() -> CacheManager:
    cache = CacheManager()
    cache._redis_client = None
    return cache


@pytest.fixture
def settings() -> Settings:
    return Settings(openai_api_key="test-key")


@pytest.fixture
def ai_service(settings: Settings, cache_manager: CacheManager) -> AIService:
    return AIService(settings, cache_manager)


class TestInitialize:
    @pytest.mark.asyncio
    async def test_initialize_disables_service_when_package_unavailable(
        self, ai_service: AIService, monkeypatch
    ):
        monkeypatch.setattr(ai_module, "OPENAI_AVAILABLE", False)

        await ai_service.initialize()

        assert ai_service.is_available is False
        assert ai_service.client is None

    @pytest.mark.asyncio
    async def test_initialize_disables_service_without_api_key(
        self, cache_manager: CacheManager, monkeypatch
    ):
        service = AIService(Settings(openai_api_key=None), cache_manager)
        monkeypatch.setattr(ai_module, "OPENAI_AVAILABLE", True)

        await service.initialize()

        assert service.is_available is False
        assert service.client is None

    @pytest.mark.asyncio
    async def test_initialize_sets_async_client_on_success(
        self, ai_service: AIService, monkeypatch
    ):
        fake_client = MagicMock()
        async_openai = MagicMock(return_value=fake_client)
        monkeypatch.setattr(ai_module, "OPENAI_AVAILABLE", True)
        monkeypatch.setattr(ai_module, "AsyncOpenAI", async_openai)

        await ai_service.initialize()

        async_openai.assert_called_once_with(api_key="test-key")
        assert ai_service.client is fake_client
        assert ai_service.is_available is True

    @pytest.mark.asyncio
    async def test_initialize_handles_client_creation_failure(
        self, ai_service: AIService, monkeypatch
    ):
        monkeypatch.setattr(ai_module, "OPENAI_AVAILABLE", True)
        monkeypatch.setattr(
            ai_module,
            "AsyncOpenAI",
            MagicMock(side_effect=RuntimeError("boom")),
        )

        await ai_service.initialize()

        assert ai_service.client is None
        assert ai_service.is_available is False


class TestPublicMethods:
    @pytest.mark.asyncio
    async def test_resumir_ementa_requires_non_empty_input(self, ai_service: AIService):
        with pytest.raises(ValueError, match="Ementa cannot be empty"):
            await ai_service.resumir_ementa("   ")

    @pytest.mark.asyncio
    async def test_resumir_ementa_returns_none_when_service_unavailable(
        self, ai_service: AIService
    ):
        ai_service.is_available = False

        assert await ai_service.resumir_ementa("ementa válida") is None

    @pytest.mark.asyncio
    async def test_resumir_ementa_parses_json_response(self, ai_service: AIService, monkeypatch):
        ai_service.is_available = True
        ai_service._call_llm = AsyncMock(
            return_value='{"resumo":"ok","pontos_chave":["a","b"]}'
        )

        resultado = await ai_service.resumir_ementa("ementa válida")

        assert resultado == {"resumo": "ok", "pontos_chave": ["a", "b"]}
        called_prompt = ai_service._call_llm.await_args.args[0]
        assert "ementa válida" in called_prompt

    @pytest.mark.asyncio
    async def test_resumir_ementa_returns_none_for_invalid_json(
        self, ai_service: AIService
    ):
        ai_service.is_available = True
        ai_service._call_llm = AsyncMock(return_value="not-json")

        assert await ai_service.resumir_ementa("ementa válida") is None

    @pytest.mark.asyncio
    async def test_extrair_teses_uses_inteiro_teor_and_parses_list(self, ai_service: AIService):
        ai_service.is_available = True
        ai_service._call_llm = AsyncMock(
            return_value='{"teses":[{"tese":"t1","contexto":"c1","tipo":"civil"}]}'
        )

        resultado = await ai_service.extrair_teses("ementa", inteiro_teor="inteiro teor")

        assert resultado == [{"tese": "t1", "contexto": "c1", "tipo": "civil"}]
        called_prompt = ai_service._call_llm.await_args.args[0]
        assert "Inteiro Teor" in called_prompt

    @pytest.mark.asyncio
    async def test_comparar_decisoes_requires_non_empty_list(self, ai_service: AIService):
        with pytest.raises(ValueError, match="ementas list cannot be empty"):
            await ai_service.comparar_decisoes([])

    @pytest.mark.asyncio
    async def test_comparar_decisoes_limits_input_size(self, ai_service: AIService):
        ai_service.is_available = True
        ai_service._call_llm = AsyncMock(
            return_value='{"similaridades":["s"],"diferencas":["d"],"posicao_majoritaria":"p"}'
        )

        resultado = await ai_service.comparar_decisoes(
            ["e1", "e2", "e3"],
            max_decisoes=2,
        )

        assert resultado["posicao_majoritaria"] == "p"
        called_prompt = ai_service._call_llm.await_args.args[0]
        assert "Decisão 1" in called_prompt
        assert "Decisão 2" in called_prompt
        assert "Decisão 3" not in called_prompt

    @pytest.mark.asyncio
    async def test_sugerir_argumentos_returns_none_for_invalid_json(
        self, ai_service: AIService
    ):
        ai_service.is_available = True
        ai_service._call_llm = AsyncMock(return_value="invalid")

        assert await ai_service.sugerir_argumentos("ementa") is None

    @pytest.mark.asyncio
    async def test_explicar_conceito_requires_non_empty_input(self, ai_service: AIService):
        with pytest.raises(ValueError, match="Conceito cannot be empty"):
            await ai_service.explicar_conceito("")

    @pytest.mark.asyncio
    async def test_explicar_conceito_returns_llm_response(self, ai_service: AIService):
        ai_service.is_available = True
        ai_service._call_llm = AsyncMock(return_value="explicação pronta")

        resultado = await ai_service.explicar_conceito("coisa julgada", contexto="civil")

        assert resultado == "explicação pronta"


class TestHelpers:
    def test_build_prompt_formats_template(self, ai_service: AIService):
        prompt = ai_service._build_prompt("Olá {nome}", nome="TJDFT")

        assert prompt == "Olá TJDFT"

    def test_build_prompt_raises_for_missing_key(self, ai_service: AIService):
        with pytest.raises(KeyError):
            ai_service._build_prompt("Olá {nome}")

    def test_generate_cache_key_is_deterministic(self, ai_service: AIService):
        key1 = ai_service._generate_cache_key("prompt", 100, 0.3)
        key2 = ai_service._generate_cache_key("prompt", 100, 0.3)
        key3 = ai_service._generate_cache_key("prompt-alterado", 100, 0.3)

        assert key1 == key2
        assert key1 != key3
        assert key1.startswith("ai:llm:gpt-4o-mini:")

    @pytest.mark.asyncio
    async def test_call_llm_requires_available_client(self, ai_service: AIService):
        ai_service.is_available = False
        ai_service.client = None

        with pytest.raises(AIServiceNotAvailableError):
            await ai_service._call_llm("prompt")

    @pytest.mark.asyncio
    async def test_call_llm_returns_cached_response(self, ai_service: AIService):
        ai_service.is_available = True
        ai_service.client = MagicMock()
        key = ai_service._generate_cache_key("prompt", 1000, 0.3)
        ai_service.cache.set(key, "cache-hit", ttl=10)

        resultado = await ai_service._call_llm("prompt")

        assert resultado == "cache-hit"

    @pytest.mark.asyncio
    async def test_call_llm_calls_api_and_caches_result(self, ai_service: AIService):
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="resultado"))],
            usage=usage,
        )
        create = AsyncMock(return_value=response)
        ai_service.client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create),
            )
        )
        ai_service.is_available = True

        resultado = await ai_service._call_llm("prompt", max_tokens=50, temperature=0.4)

        assert resultado == "resultado"
        create.assert_awaited_once()
        cache_key = ai_service._generate_cache_key("prompt", 50, 0.4)
        assert ai_service.cache.get(cache_key) == "resultado"

    @pytest.mark.asyncio
    async def test_call_llm_wraps_client_errors(self, ai_service: AIService):
        create = AsyncMock(side_effect=RuntimeError("api-down"))
        ai_service.client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create),
            )
        )
        ai_service.is_available = True

        with pytest.raises(AIServiceError, match="Failed to call LLM"):
            await ai_service._call_llm("prompt")

    @pytest.mark.asyncio
    async def test_close_resets_client_and_availability(self, ai_service: AIService):
        client = SimpleNamespace(close=AsyncMock())
        ai_service.client = client
        ai_service.is_available = True

        await ai_service.close()

        client.close.assert_awaited_once()
        assert ai_service.client is None
        assert ai_service.is_available is False

    @pytest.mark.asyncio
    async def test_close_handles_client_close_failure(self, ai_service: AIService):
        client = SimpleNamespace(close=AsyncMock(side_effect=RuntimeError("boom")))
        ai_service.client = client
        ai_service.is_available = True

        await ai_service.close()

        assert ai_service.client is None
        assert ai_service.is_available is False
