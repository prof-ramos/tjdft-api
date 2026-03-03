"""
Validation filters for TJDFT API.

This module provides validation functions for reference data
including relatores (judges), classes (case types), and órgãos julgadores (court divisions).
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

# Configure logging
logger = logging.getLogger(__name__)

# Cache for reference data
_referencia_cache: Optional[Dict[str, Any]] = None


def load_referencia() -> Dict[str, Any]:
    """
    Load reference data from JSON file.

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
    global _referencia_cache

    if _referencia_cache is not None:
        return _referencia_cache

    try:
        referencia_path = Path(__file__).parent.parent.parent / "data" / "referencia.json"

        if not referencia_path.exists():
            raise FileNotFoundError(
                f"Reference file not found: {referencia_path}"
            )

        with open(referencia_path, "r", encoding="utf-8") as f:
            _referencia_cache = json.load(f)

        logger.debug(f"Reference data loaded from {referencia_path}")
        return _referencia_cache

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
        return referencia.get("relatores", [])
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
        return referencia.get("classes", [])
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
        return referencia.get("orgaos_julgadores", [])
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
        return referencia.get("assuntos", [])
    except Exception as e:
        logger.error(f"Error getting assuntos: {e}")
        return []


def clear_referencia_cache() -> None:
    """
    Clear the reference data cache.

    This forces the next load_referencia() call to reload from disk.
    """
    global _referencia_cache
    _referencia_cache = None
    logger.debug("Reference data cache cleared")
