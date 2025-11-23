"""
Service for resolving detected entity names to canonical forms.

Provides a safety net for biography file creation by mapping variations
of entity names to their canonical forms, preventing duplicate files.
"""

import logging
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from daily_insights.services.entity_registry import (
    load_entity_registry,
    get_all_stt_corrections,
    get_all_aliases,
    get_biographical_subjects
)

logger = logging.getLogger(__name__)


def resolve_entity(
    detected_name: str,
    category: Optional[str] = None,
    fuzzy_threshold: float = 0.85
) -> Optional[str]:
    """
    Resolve a detected entity name to its canonical form.

    Resolution order:
    1. Exact match on canonical name (case-insensitive)
    2. Exact match in STT corrections
    3. Exact match in aliases
    4. Fuzzy match against canonical_name (85% threshold by default)

    Parameters
    ----------
    detected_name : str
        The entity name detected in a transcript
    category : Optional[str]
        Entity category hint (person, place, object, pet) - used for filtering
    fuzzy_threshold : float
        Minimum similarity ratio for fuzzy matching (default: 0.85)

    Returns
    -------
    Optional[str]
        Canonical name if resolved, None if this is a new entity

    Example
    -------
    >>> resolve_entity("Joel Gilmet")
    'Joel Guilmet'
    >>> resolve_entity("TV Pal")
    'TV Pow'
    >>> resolve_entity("Some New Person")
    None
    """
    if not detected_name or not detected_name.strip():
        return None

    detected_name = detected_name.strip()
    detected_lower = detected_name.lower()

    registry = load_entity_registry()
    entities = registry.get('entities', {})

    # 1. Exact match on canonical name (case-insensitive)
    for entity_key, entity_data in entities.items():
        canonical = entity_data.get('canonical_name', entity_key)
        if canonical.lower() == detected_lower:
            logger.debug("Exact canonical match: %s -> %s", detected_name, canonical)
            return canonical

    # 2. Exact match in STT corrections
    stt_corrections = get_all_stt_corrections()
    for wrong, right in stt_corrections.items():
        if wrong.lower() == detected_lower:
            # Now find the canonical name for the corrected value
            corrected_canonical = _find_canonical_for_value(right, entities)
            if corrected_canonical:
                logger.debug("STT correction match: %s -> %s -> %s",
                           detected_name, right, corrected_canonical)
                return corrected_canonical

    # 3. Exact match in aliases
    aliases = get_all_aliases()
    for alias, canonical in aliases.items():
        if alias.lower() == detected_lower:
            logger.debug("Alias match: %s -> %s", detected_name, canonical)
            return canonical

    # 4. Fuzzy matching against canonical names
    best_match, best_ratio = fuzzy_match_entity(detected_name, entities, category)
    if best_match and best_ratio >= fuzzy_threshold:
        logger.info("Fuzzy match: %s -> %s (%.1f%% confidence)",
                   detected_name, best_match, best_ratio * 100)
        return best_match

    # No match found - this is a new entity
    logger.debug("No match found for: %s (category: %s)", detected_name, category)
    return None


def _find_canonical_for_value(value: str, entities: Dict) -> Optional[str]:
    """
    Find the canonical name for a given value (which might be a corrected STT value).

    Parameters
    ----------
    value : str
        The value to look up (could be a name or alias)
    entities : Dict
        The entities dictionary from the registry

    Returns
    -------
    Optional[str]
        The canonical name if found
    """
    value_lower = value.lower()

    for entity_key, entity_data in entities.items():
        canonical = entity_data.get('canonical_name', entity_key)

        # Check canonical name
        if canonical.lower() == value_lower:
            return canonical

        # Check aliases
        for alias in entity_data.get('aliases', []):
            if alias.lower() == value_lower:
                return canonical

    return None


def fuzzy_match_entity(
    name: str,
    entities: Dict,
    category: Optional[str] = None
) -> Tuple[Optional[str], float]:
    """
    Find the best fuzzy match for a name among entity canonical names.

    Parameters
    ----------
    name : str
        The name to match
    entities : Dict
        The entities dictionary from the registry
    category : Optional[str]
        If provided, only match entities of this type

    Returns
    -------
    Tuple[Optional[str], float]
        Best matching canonical name and similarity ratio (0.0-1.0)

    Example
    -------
    >>> match, ratio = fuzzy_match_entity("Joel Guilmet", entities)
    >>> match
    'Joel Guilmet'
    >>> ratio
    1.0
    """
    best_match = None
    best_ratio = 0.0

    for entity_key, entity_data in entities.items():
        # Filter by category if specified
        if category and entity_data.get('entity_type') != category:
            continue

        # Only consider biographical subjects
        if not entity_data.get('is_biographical_subject', False):
            continue

        canonical = entity_data.get('canonical_name', entity_key)

        # Compare against canonical name
        ratio = SequenceMatcher(None, name.lower(), canonical.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = canonical

        # Also compare against aliases
        for alias in entity_data.get('aliases', []):
            ratio = SequenceMatcher(None, name.lower(), alias.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = canonical

    return best_match, best_ratio


def get_entity_category(name: str) -> Optional[str]:
    """
    Get the entity type/category for a resolved name.

    Parameters
    ----------
    name : str
        The entity name (should be canonical)

    Returns
    -------
    Optional[str]
        Entity type (person, place, object, pet, device) or None if not found

    Example
    -------
    >>> get_entity_category("Joel Guilmet")
    'person'
    >>> get_entity_category("TV Pow")
    'object'
    """
    registry = load_entity_registry()
    entities = registry.get('entities', {})

    # Direct key lookup
    if name in entities:
        return entities[name].get('entity_type')

    # Search by canonical name
    for entity_data in entities.values():
        if entity_data.get('canonical_name') == name:
            return entity_data.get('entity_type')

    return None


def resolve_and_categorize(
    detected_name: str,
    detected_category: Optional[str] = None
) -> Tuple[str, str]:
    """
    Resolve entity name and determine its category.

    Combines resolution with category lookup/inference.

    Parameters
    ----------
    detected_name : str
        The entity name detected in a transcript
    detected_category : Optional[str]
        Category hint from detection (may be overridden by registry)

    Returns
    -------
    Tuple[str, str]
        (canonical_name_or_detected, category)
        - canonical_name if resolved, detected_name if new entity
        - category from registry if resolved, detected_category otherwise

    Example
    -------
    >>> name, cat = resolve_and_categorize("Joel Gilmet", "person")
    >>> name
    'Joel Guilmet'
    >>> cat
    'person'
    """
    canonical = resolve_entity(detected_name, detected_category)

    if canonical:
        # Use resolved name and get category from registry
        category = get_entity_category(canonical) or detected_category or "person"
        return canonical, category
    else:
        # New entity - use detected values
        return detected_name, detected_category or "person"


def suggest_new_entity(
    name: str,
    category: str,
    context: Optional[str] = None
) -> Dict:
    """
    Generate a suggestion for adding a new entity to the registry.

    Parameters
    ----------
    name : str
        The new entity name
    category : str
        Entity category (person, place, object, pet)
    context : Optional[str]
        Optional context about the entity

    Returns
    -------
    Dict
        Suggested entity data structure for adding to registry

    Example
    -------
    >>> suggestion = suggest_new_entity("New Friend", "person", "Met at conference")
    >>> suggestion['canonical_name']
    'New Friend'
    """
    return {
        "canonical_name": name,
        "entity_type": category,
        "is_speaker": category == "person",
        "is_biographical_subject": True,
        "aliases": [],
        "stt_corrections": {},
        "relationship": "unknown",
        "biographical_context": context or f"New {category} detected in transcripts"
    }


def report_resolution_statistics(
    resolutions: List[Tuple[str, Optional[str]]]
) -> Dict:
    """
    Generate statistics about entity resolution results.

    Parameters
    ----------
    resolutions : List[Tuple[str, Optional[str]]]
        List of (detected_name, resolved_canonical) tuples

    Returns
    -------
    Dict
        Statistics including:
        - total: Total entities processed
        - resolved: Successfully resolved count
        - new: New entities (not in registry) count
        - resolution_rate: Percentage resolved

    Example
    -------
    >>> stats = report_resolution_statistics([("Joel", "Joel Guilmet"), ("New", None)])
    >>> stats['resolution_rate']
    50.0
    """
    total = len(resolutions)
    resolved = sum(1 for _, r in resolutions if r is not None)
    new = total - resolved

    return {
        "total": total,
        "resolved": resolved,
        "new": new,
        "resolution_rate": (resolved / total * 100) if total > 0 else 0.0
    }
