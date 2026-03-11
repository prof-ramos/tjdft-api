"""Utilitários para enriquecimento de dados de jurisprudência.

Este módulo fornece funções para calcular métricas e extrair informações
de decisões judiciais, incluindo densidade de precedentes, tipo de instância
e marcadores de relevância.
"""

from enum import Enum
from typing import Any, Dict, Optional


class DensidadeCategoria(str, Enum):
    """Categorias de densidade de precedentes."""

    ESCASSO = "escasso"
    MODERADO = "moderado"
    CONSOLIDADO = "consolidado"
    MASSIVO = "massivo"


class InstanciaTipo(str, Enum):
    """Tipos de instância judicial."""

    JUIZADO_ESPECIAL = "juizado_especial"
    TJDFT_2A_INSTANCIA = "tjdft_2a_instancia"


def calcular_densidade(total: int) -> Dict[str, Any]:
    """Calcula a categoria de densidade baseada no total de precedentes.

    Args:
        total: Número total de precedentes encontrados.

    Returns:
        Dicionário contendo:
            - categoria (DensidadeCategoria): Categoria calculada
            - total (int): Total de precedentes
            - alerta (str): Mensagem de alerta contextual

    Examples:
        >>> calcular_densidade(10)
        {'categoria': 'escasso', 'total': 10, 'alerta': 'Poucos precedentes...'}
        >>> calcular_densidade(1500)
        {'categoria': 'consolidado', 'total': 1500, 'alerta': 'Tema bem consolidado...'}
    """
    if total < 20:
        categoria = DensidadeCategoria.ESCASSO
        alerta = "Poucos precedentes encontrados. Considere ampliar os termos de busca."
    elif 20 <= total < 500:
        categoria = DensidadeCategoria.MODERADO
        alerta = "Quantidade moderada de precedentes."
    elif 500 <= total < 5000:
        categoria = DensidadeCategoria.CONSOLIDADO
        alerta = "Tema bem consolidado nos precedentes."
    else:  # total >= 5000
        categoria = DensidadeCategoria.MASSIVO
        alerta = "Tema com jurisprudência massiva. Considere filtros adicionais."

    return {
        "categoria": categoria.value,
        "total": total,
        "alerta": alerta,
    }


def calcular_instancia(
    turma_recursal: Optional[bool] = None,
    subbase: Optional[str] = None,
) -> Optional[str]:
    """Calcula o tipo de instância baseado em metadados da decisão.

    Args:
        turma_recursal: Indica se a decisão é de Turma Recursal.
        subbase: Subbase da decisão (ex: "acordaos-tr").

    Returns:
        Tipo de instância como string ("juizado_especial" ou "tjdft_2a_instancia"),
        ou None se não for possível determinar.

    Examples:
        >>> calcular_instancia(turma_recursal=True)
        'juizado_especial'
        >>> calcular_instancia(subbase="acordaos-tr")
        'juizado_especial'
        >>> calcular_instancia(turma_recursal=False, subbase="acordaos")
        'tjdft_2a_instancia'
    """
    if turma_recursal is True or subbase == "acordaos-tr":
        return InstanciaTipo.JUIZADO_ESPECIAL.value
    elif turma_recursal is False or subbase is not None:
        return InstanciaTipo.TJDFT_2A_INSTANCIA.value
    else:
        return None


def extrair_marcadores_relevancia(
    marcadores: Optional[Dict[str, Any]],
) -> Dict[str, str]:
    """Extrai marcadores de relevância de uma decisão.

    Args:
        marcadores: Dicionário de marcadores (pode conter listas ou strings).

    Returns:
        Dicionário com os marcadores extraídos como strings.
        Retorna dict vazio se marcadores for None ou vazio.

    Examples:
        >>> extrair_marcadores_relevancia({"trecho": ["texto destacado"]})
        {'trecho': 'texto destacado'}
        >>> extrair_marcadores_relevancia({"palavra": "destaque"})
        {'palavra': 'destaque'}
        >>> extrair_marcadores_relevancia(None)
        {}
    """
    if not marcadores:
        return {}

    resultado: Dict[str, str] = {}

    for chave, valor in marcadores.items():
        if isinstance(valor, list) and valor:
            # Pega o primeiro elemento da lista
            resultado[chave] = str(valor[0])
        elif isinstance(valor, str):
            # Usa a string diretamente
            resultado[chave] = valor
        # Ignora outros tipos ou valores vazios

    return resultado
