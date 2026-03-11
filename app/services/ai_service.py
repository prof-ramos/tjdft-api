"""
AI Service - Legal analysis service using LLM (OpenAI).

This module provides intelligent legal analysis features using OpenAI's API
with optional configuration, intelligent caching, and graceful degradation.
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, cast

# Try to import OpenAI, but make it optional
try:
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None  # type: ignore

from app.config import Settings
from app.utils.cache import CacheManager

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Base exception for AI service errors."""

    pass


class AIServiceNotAvailableError(AIServiceError):
    """Exception raised when OpenAI is not configured."""

    pass


class AIService:
    """
    Serviço de análise jurídica usando LLM (OpenAI).

    This service provides intelligent legal analysis features including:
    - Summarizing legal decisions (ementas)
    - Extracting legal theses
    - Comparing multiple decisions
    - Suggesting legal arguments
    - Explaining legal concepts

    The service gracefully degrades when OpenAI is not configured,
    returning None or placeholder responses.

    Example:
        >>> cache = CacheManager()
        >>> settings = Settings()
        >>> ai_service = AIService(settings, cache)
        >>> await ai_service.initialize()
        >>> summary = await ai_service.resumir_ementa(ementa_text)
    """

    # Model configuration
    DEFAULT_MODEL = "gpt-4o-mini"
    DEFAULT_MAX_TOKENS = 1000
    DEFAULT_TEMPERATURE = 0.3

    # Cache TTL (24 hours for AI responses)
    CACHE_TTL = 86400

    def __init__(self, settings: Settings, cache_manager: CacheManager):
        """
        Initialize AI service.

        Args:
            settings: Application settings
            cache_manager: CacheManager instance for caching responses
        """
        self.settings = settings
        self.cache = cache_manager
        self.client: Optional[AsyncOpenAI] = None
        self.is_available = False

        logger.info("AIService initialized")

    async def initialize(self):
        """
        Inicializa o cliente OpenAI se API key estiver configurada.

        This method attempts to initialize the OpenAI client if an API key
        is available. If not, the service remains in degraded mode.
        """
        if not OPENAI_AVAILABLE:
            logger.warning(
                "OpenAI package not installed. AI features will be disabled. "
                "Install with: pip install openai"
            )
            self.is_available = False
            return

        if not self.settings.openai_api_key:
            logger.info(
                "OpenAI API key not configured. AI features will be disabled. "
                "Set OPENAI_API_KEY environment variable to enable."
            )
            self.is_available = False
            return

        try:
            self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)
            self.is_available = True
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.is_available = False

    async def resumir_ementa(
        self, ementa: str, max_tokens: int = 300
    ) -> Optional[Dict[str, Any]]:
        """
        Gera resumo de ementa com pontos-chave.

        Args:
            ementa: Texto da ementa judicial
            max_tokens: Máximo de tokens para o resumo (default: 300)

        Returns:
            Dict com:
                - resumo: Resumo da ementa em 2-3 parágrafos
                - pontos_chave: Lista de pontos-chave da decisão
            Ou None se serviço não disponível

        Raises:
            ValueError: Se ementa estiver vazia
        """
        if not ementa or not ementa.strip():
            raise ValueError("Ementa cannot be empty")

        if not self.is_available:
            logger.debug("AI service not available for summarization")
            return None

        prompt = self._build_prompt(
            """Resuma a seguinte ementa judicial em 2-3 parágrafos,
destacando os pontos-chave da decisão.

Após o resumo, liste os principais pontos-chave da decisão em formato de tópicos.

Ementa:
{ementa}

Responda em português no seguinte formato JSON:
{{
    "resumo": "resumo em 2-3 parágrafos",
    "pontos_chave": ["ponto 1", "ponto 2", "ponto 3"]
}}""",
            ementa=ementa[:4000],  # Limit input size
        )

        try:
            response = await self._call_llm(
                prompt, max_tokens=max_tokens, temperature=0.3
            )

            # Parse JSON response
            return cast(Dict[str, Any], json.loads(response))

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error summarizing ementa: {e}")
            return None

    async def extrair_teses(
        self, ementa: str, inteiro_teor: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Extrai teses jurídicas de uma decisão.

        Args:
            ementa: Texto da ementa judicial
            inteiro_teor: Texto completo do inteiro teor (opcional)

        Returns:
            Lista de dict com:
                - tese: Texto da tese jurídica
                - contexto: Contexto da tese
                - tipo: Tipo da tese (constitucional, infraconstitucional, etc.)
            Ou None se serviço não disponível

        Raises:
            ValueError: Se ementa estiver vazia
        """
        if not ementa or not ementa.strip():
            raise ValueError("Ementa cannot be empty")

        if not self.is_available:
            logger.debug("AI service not available for thesis extraction")
            return None

        # Build input text
        input_text = f"Ementa:\n{ementa[:4000]}"
        if inteiro_teor:
            input_text += f"\n\nInteiro Teor:\n{inteiro_teor[:6000]}"

        prompt = self._build_prompt(
            """Identifique as teses jurídicas centrais nesta decisão,
classificando-as por tipo.

Para cada tese, extraia:
1. O texto da tese jurídica
2. O contexto em que foi aplicada
3. O tipo de tese
(constitucional, infraconstitucional, administrativa, civil, penal, etc.)

{input_text}

Responda em português no seguinte formato JSON:
{{
    "teses": [
        {{
            "tese": "texto da tese",
            "contexto": "contexto da tese",
            "tipo": "tipo da tese"
        }}
    ]
}}""",
            input_text=input_text,
        )

        try:
            response = await self._call_llm(prompt, max_tokens=800, temperature=0.3)

            # Parse JSON response
            parsed = cast(Dict[str, Any], json.loads(response))
            return cast(List[Dict[str, Any]], parsed.get("teses", []))

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extracting theses: {e}")
            return None

    async def comparar_decisoes(
        self, ementas: List[str], max_decisoes: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Compara múltiplas decisões e identifica similaridades/diferenças.

        Args:
            ementas: Lista de ementas para comparar
            max_decisoes: Número máximo de decisões a comparar (default: 5)

        Returns:
            Dict com:
                - similaridades: Lista de similaridades encontradas
                - diferencas: Lista de diferenças identificadas
                - posicao_majoritaria: Posição majoritária entre as decisões
            Ou None se serviço não disponível

        Raises:
            ValueError: Se lista de ementas estiver vazia
        """
        if not ementas or len(ementas) == 0:
            raise ValueError("ementas list cannot be empty")

        if len(ementas) > max_decisoes:
            logger.warning(f"Limiting comparison to {max_decisoes} decisions")
            ementas = ementas[:max_decisoes]

        if not self.is_available:
            logger.debug("AI service not available for decision comparison")
            return None

        # Build ementas text
        ementas_text = "\n\n---\n\n".join(
            [f"Decisão {i+1}:\n{e[:2000]}" for i, e in enumerate(ementas)]
        )

        prompt = self._build_prompt(
            """Compare as seguintes decisões judiciais, identificando:

1. Similaridades: Pontos em comum entre as decisões
2. Diferenças: Pontos divergentes entre as decisões
3. Posição majoritária: A posição predominante no conjunto das decisões

{ementas_text}

Responda em português no seguinte formato JSON:
{{
    "similaridades": ["similaridade 1", "similaridade 2"],
    "diferencas": ["diferença 1", "diferença 2"],
    "posicao_majoritaria": "descrição da posição majoritária"
}}""",
            ementas_text=ementas_text,
        )

        try:
            response = await self._call_llm(prompt, max_tokens=1000, temperature=0.3)

            # Parse JSON response
            return cast(Dict[str, Any], json.loads(response))

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error comparing decisions: {e}")
            return None

    async def sugerir_argumentos(
        self, ementa: str, contexto: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Sugere argumentos com base em decisão precedente.

        Args:
            ementa: Texto da ementa judicial precedente
            contexto: Contexto adicional do caso (opcional)

        Returns:
            Dict com:
                - argumentos_favoraveis: Lista de argumentos favoráveis
                - riscos: Lista de riscos e contra-argumentos
                - jurisprudencia_recomendada: Lista de jurisprudência relacionada
            Ou None se serviço não disponível

        Raises:
            ValueError: Se ementa estiver vazia
        """
        if not ementa or not ementa.strip():
            raise ValueError("Ementa cannot be empty")

        if not self.is_available:
            logger.debug("AI service not available for argument suggestion")
            return None

        # Build input text
        input_text = f"Ementa Precedente:\n{ementa[:4000]}"
        if contexto:
            input_text += f"\n\nContexto do Caso:\n{contexto[:2000]}"

        prompt = self._build_prompt(
            """Com base na seguinte decisão precedente,
sugira argumentos para um caso jurídico.

Analise e forneça:
1. Argumentos favoráveis:
   Argumentos que podem ser utilizados com base no precedente
2. Riscos:
   Possíveis contra-argumentos e riscos da tese
3. Jurisprudência recomendada:
   Sugestões de jurisprudência relacionada

{input_text}

Responda em português no seguinte formato JSON:
{{
    "argumentos_favoraveis": ["argumento 1", "argumento 2"],
    "riscos": ["risco 1", "risco 2"],
    "jurisprudencia_recomendada": ["sugestão 1", "sugestão 2"]
}}""",
            input_text=input_text,
        )

        try:
            response = await self._call_llm(prompt, max_tokens=1000, temperature=0.4)

            # Parse JSON response
            return cast(Dict[str, Any], json.loads(response))

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error suggesting arguments: {e}")
            return None

    async def explicar_conceito(
        self, conceito: str, contexto: Optional[str] = None
    ) -> Optional[str]:
        """
        Explica conceito jurídico.

        Args:
            conceito: Conceito jurídico a explicar
            contexto: Contexto adicional para a explicação (opcional)

        Returns:
            Explicação do conceito em português
            Ou None se serviço não disponível

        Raises:
            ValueError: Se conceito estiver vazio
        """
        if not conceito or not conceito.strip():
            raise ValueError("Conceito cannot be empty")

        if not self.is_available:
            logger.debug("AI service not available for concept explanation")
            return None

        # Build input text
        input_text = f"Conceito: {conceito}"
        if contexto:
            input_text += f"\nContexto: {contexto[:2000]}"

        prompt = self._build_prompt(
            """Explique o seguinte conceito jurídico de forma clara e didática.

Forneça:
1. Definição do conceito
2. Contexto de aplicação
3. Exemplos práticos
4. Referências jurisprudenciais relevantes (se aplicável)

{input_text}

Responda em português de forma clara e estruturada.""",
            input_text=input_text,
        )

        try:
            response = await self._call_llm(prompt, max_tokens=800, temperature=0.3)

            return response

        except Exception as e:
            logger.error(f"Error explaining concept: {e}")
            return None

    def _build_prompt(self, template: str, **kwargs) -> str:
        """
        Constrói prompt com template.

        Args:
            template: Template string com placeholders {key}
            **kwargs: Valores para substituir no template

        Returns:
            Prompt formatado
        """
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing key in prompt template: {e}")
            raise

    async def _call_llm(
        self, prompt: str, max_tokens: int = 1000, temperature: float = 0.3
    ) -> str:
        """
        Chama LLM com cache.

        Args:
            prompt: Prompt para enviar ao LLM
            max_tokens: Máximo de tokens na resposta (default: 1000)
            temperature: Temperatura para geração (default: 0.3)

        Returns:
            Resposta do LLM como string

        Raises:
            AIServiceNotAvailableError: Se serviço não disponível
            AIServiceError: Se erro na chamada à API
        """
        if not self.is_available or not self.client:
            raise AIServiceNotAvailableError("AI service is not available")

        # Generate cache key from prompt
        cache_key = self._generate_cache_key(prompt, max_tokens, temperature)

        # Try cache first
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"AI cache hit for key: {cache_key[:20]}...")
            return str(cached)

        try:
            logger.debug(
                f"Calling OpenAI API (max_tokens={max_tokens}, temp={temperature})"
            )

            response = await self.client.chat.completions.create(
                model=self.DEFAULT_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Você é um assistente jurídico especializado em "
                            "direito brasileiro. Responda sempre em português "
                            "de forma clara, precisa e profissional."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=30.0,
            )

            result = response.choices[0].message.content or ""

            # Log token usage if available
            if hasattr(response, "usage") and response.usage:
                logger.info(
                    f"OpenAI API call completed - "
                    f"prompt_tokens: {response.usage.prompt_tokens}, "
                    f"completion_tokens: {response.usage.completion_tokens}, "
                    f"total_tokens: {response.usage.total_tokens}"
                )

            # Cache the result
            self.cache.set(cache_key, result, ttl=self.CACHE_TTL)

            return result

        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            raise AIServiceError(f"Failed to call LLM: {e}") from e

    def _generate_cache_key(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> str:
        """
        Gera chave de cache para chamada LLM.

        Args:
            prompt: Prompt usado
            max_tokens: Máximo de tokens
            temperature: Temperatura usada

        Returns:
            Chave de cache única
        """
        # Create a deterministic string from parameters
        key_data = f"{prompt}:{max_tokens}:{temperature}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:12]

        return f"ai:llm:{self.DEFAULT_MODEL}:{key_hash}"

    async def close(self):
        """
        Close the AI service and release resources.
        """
        if self.client:
            try:
                await self.client.close()
                logger.info("OpenAI client closed")
            except Exception as e:
                logger.error(f"Error closing OpenAI client: {e}")
            finally:
                self.client = None
                self.is_available = False
