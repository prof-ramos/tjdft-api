"""
Validation filters for TJDFT API.

This module provides validation functions for reference data including relatores
(judges), classes (case types), and órgãos julgadores (court divisions).
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, cast

from app.utils.cache import get_cache

# Configure logging
logger = logging.getLogger(__name__)

# Cache key for reference data
REFERENCIA_DATA_CACHE_KEY = "referencia:data"

# Cache TTL for reference data (24 hours = 86400 seconds)
REFERENCIA_TTL = 86400


def load_referencia() -> Dict[str, Any]:
    """
    Load reference data from JSON file with 24h cache.

    Uses CacheManager singleton for efficient caching with TTL.

    Returns:
        Dict containing reference data with keys:
        - relatores: List of judge information
        - classes: List of case type classes
        - orgaos_julgadores: List of court divisions
        - assuntos: List of legal subjects

    Raises:
        FileNotFoundError: If reference file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    # Try to get from cache first (24h TTL = 86400 seconds)
    cache = get_cache()
    cache_key = REFERENCIA_DATA_CACHE_KEY

    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.debug("Reference data loaded from cache")
        return cast(Dict[str, Any], cached_data)

    # Load from file if not in cache
    try:
        referencia_path = (
            Path(__file__).parent.parent.parent / "data" / "referencia.json"
        )

        if not referencia_path.exists():
            raise FileNotFoundError(f"Reference file not found: {referencia_path}")

        with open(referencia_path, "r", encoding="utf-8") as f:
            data = cast(Dict[str, Any], json.load(f))

        # Cache for 24 hours
        cache.set(cache_key, data, ttl=REFERENCIA_TTL)

        logger.debug(f"Reference data loaded from {referencia_path} and cached")
        return data

    except json.JSONDecodeError as e:
        logger.error(f"Error decoding reference JSON: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading reference data: {e}")
        raise


def validate_relator(relator_id: str) -> bool:
    """
    Validate if a relator (judge) exists in reference data.

    Args:
        relator_id: The ID of the relator to validate

    Returns:
        True if relator exists, False otherwise
    """
    try:
        referencia = load_referencia()
        relatores = referencia.get("relatores", [])

        for relator in relatores:
            if relator.get("id") == relator_id:
                return True

        return False

    except Exception as e:
        logger.error(f"Error validating relator {relator_id}: {e}")
        return False


def validate_classe(classe_codigo: str) -> bool:
    """
    Validate if a class (case type) exists in reference data.

    Args:
        classe_codigo: The code of the class to validate

    Returns:
        True if class exists, False otherwise
    """
    try:
        referencia = load_referencia()
        classes = referencia.get("classes", [])

        for classe in classes:
            if classe.get("codigo") == classe_codigo:
                return True

        return False

    except Exception as e:
        logger.error(f"Error validating class {classe_codigo}: {e}")
        return False


def validate_orgao(orgao_codigo: str) -> bool:
    """
    Validate if an órgão julgador (court division) exists in reference data.

    Args:
        orgao_codigo: The code of the órgão to validate

    Returns:
        True if órgão exists, False otherwise
    """
    try:
        referencia = load_referencia()
        orgaos = referencia.get("orgaos_julgadores", [])

        for orgao in orgaos:
            if orgao.get("codigo") == orgao_codigo:
                return True

        return False

    except Exception as e:
        logger.error(f"Error validating órgão {orgao_codigo}: {e}")
        return False


def get_relatores() -> List[Dict[str, str]]:
    """
    Get list of all relatores (judges).

    Returns:
        List of dictionaries containing relator information (id, nome, orgao)
    """
    try:
        referencia = load_referencia()
        return cast(List[Dict[str, str]], referencia.get("relatores", []))
    except Exception as e:
        logger.error(f"Error getting relatores: {e}")
        return []


def get_classes() -> List[Dict[str, str]]:
    """
    Get list of all classes (case types).

    Returns:
        List of dictionaries containing class information (codigo, nome)
    """
    try:
        referencia = load_referencia()
        return cast(List[Dict[str, str]], referencia.get("classes", []))
    except Exception as e:
        logger.error(f"Error getting classes: {e}")
        return []


def get_orgaos() -> List[Dict[str, str]]:
    """
    Get list of all órgãos julgadores (court divisions).

    Returns:
        List of dictionaries containing órgão information (codigo, nome)
    """
    try:
        referencia = load_referencia()
        return cast(List[Dict[str, str]], referencia.get("orgaos_julgadores", []))
    except Exception as e:
        logger.error(f"Error getting órgãos: {e}")
        return []


def get_assuntos() -> List[Dict[str, str]]:
    """
    Get list of all assuntos (legal subjects).

    Returns:
        List of dictionaries containing assunto information (codigo, nome)
    """
    try:
        referencia = load_referencia()
        return cast(List[Dict[str, str]], referencia.get("assuntos", []))
    except Exception as e:
        logger.error(f"Error getting assuntos: {e}")
        return []


def clear_referencia_cache() -> None:
    """
    Clear the reference data cache.

    This forces the next load_referencia() call to reload from disk.
    """
    cache = get_cache()
    cache.delete(REFERENCIA_DATA_CACHE_KEY)
    logger.debug("Reference data cache cleared")


def filtrar_por_instancia(
    registros: List[Dict[str, Any]], excluir_turmas_recursais: bool
) -> List[Dict[str, Any]]:
    """
    Filter records by instancia, excluding turmas recursais when requested.

    Args:
        registros: List of decision records to filter
        excluir_turmas_recursais: If False, return registros unchanged.
            If True, filter out turma recursal records.

    Returns:
        NEW list of filtered records (original list is not modified).

    Note:
        - Turmas recursais are identified by turmaRecursal=True
          OR subbase=="acordaos-tr"
        - Missing turmaRecursal field is treated as False (record is kept)
        - Monocratic decisions may have different field structures
    """
    if not excluir_turmas_recursais:
        return registros

    filtrados = []
    for registro in registros:
        turma_recursal = registro.get("turmaRecursal", False)
        subbase = registro.get("subbase", "")

        # Keep record if it's not a turma recursal
        if not turma_recursal and subbase != "acordaos-tr":
            filtrados.append(registro)

    return filtrados


def filtrar_relatores_ativos(
    registros: List[Dict[str, Any]], apenas_ativos: bool
) -> List[Dict[str, Any]]:
    """
    Filter records to only include active relatores (judges).

    Args:
        registros: List of decision records to filter
        apenas_ativos: If False, return registros unchanged.
            If True, keep only records with active relatores.

    Returns:
        NEW list of filtered records (original list is not modified).

    Note:
        - Active relatores are identified by relatorAtivo=True
        - Missing relatorAtivo field results in exclusion (conservative approach)
        - Monocratic decisions may not have this field and will be excluded
    """
    if not apenas_ativos:
        return registros

    filtrados = []
    for registro in registros:
        # Use .get() with default None to detect missing field
        relator_ativo = registro.get("relatorAtivo")

        # Keep only records where relatorAtivo is explicitly True
        if relator_ativo is True:
            filtrados.append(registro)

    return filtrados
