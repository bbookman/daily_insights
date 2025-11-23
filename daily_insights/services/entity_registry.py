"""
Service for managing the unified entity registry.

Provides functionality for:
- Loading and saving entity profiles
- Querying entities by type, speaker status, biographical status
- Managing STT corrections
- Adding new entities
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Config file path - relative to this file's location
_CONFIG_DIR = Path(__file__).parent.parent / "config"
ENTITY_PROFILES_FILE = _CONFIG_DIR / "entity_profiles.json"

# Legacy file for backward compatibility check
SPEAKER_PROFILES_FILE = _CONFIG_DIR / "speaker_profiles.json"


# ============================================================================
# Core Load/Save Functions
# ============================================================================

def load_entity_registry() -> Dict:
    """
    Load entity profiles from configuration file.

    Returns
    -------
    Dict
        Dictionary containing version and entities data

    Example
    -------
    >>> registry = load_entity_registry()
    >>> 'Matt Bookman' in registry['entities']
    True
    """
    if not ENTITY_PROFILES_FILE.exists():
        logger.warning("Entity profiles file not found: %s", ENTITY_PROFILES_FILE)
        return {"version": "2.0", "entities": {}}

    try:
        with open(ENTITY_PROFILES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error("Error loading entity profiles: %s", e)
        return {"version": "2.0", "entities": {}}


def save_entity_registry(data: Dict) -> bool:
    """
    Save entity profiles to configuration file.

    Parameters
    ----------
    data : Dict
        Entity registry data to save

    Returns
    -------
    bool
        True if save succeeded, False otherwise

    Example
    -------
    >>> registry = load_entity_registry()
    >>> save_entity_registry(registry)
    True
    """
    try:
        # Ensure config directory exists
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        with open(ENTITY_PROFILES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("Saved entity registry with %d entities", len(data.get('entities', {})))
        return True
    except Exception as e:
        logger.error("Error saving entity profiles: %s", e)
        return False


# ============================================================================
# Query Functions
# ============================================================================

def get_entity(name: str) -> Optional[Dict]:
    """
    Get a single entity by name.

    Searches both canonical names and aliases.

    Parameters
    ----------
    name : str
        Entity name to look up

    Returns
    -------
    Optional[Dict]
        Entity data if found, None otherwise

    Example
    -------
    >>> entity = get_entity("Matt")
    >>> entity['canonical_name']
    'Matt Bookman'
    """
    registry = load_entity_registry()
    entities = registry.get('entities', {})

    # First check for exact match on key
    if name in entities:
        return entities[name]

    # Then check aliases
    for entity_key, entity_data in entities.items():
        if name in entity_data.get('aliases', []):
            return entity_data
        if name == entity_data.get('canonical_name'):
            return entity_data

    return None


def get_entity_by_canonical_name(canonical_name: str) -> Optional[Dict]:
    """
    Get entity by its canonical name.

    Parameters
    ----------
    canonical_name : str
        Canonical name to look up

    Returns
    -------
    Optional[Dict]
        Entity data if found, None otherwise
    """
    registry = load_entity_registry()
    entities = registry.get('entities', {})

    for entity_data in entities.values():
        if entity_data.get('canonical_name') == canonical_name:
            return entity_data

    return None


def get_speakers() -> Dict[str, Dict]:
    """
    Get all entities that are speakers (is_speaker=True).

    Returns
    -------
    Dict[str, Dict]
        Dictionary of speaker entities

    Example
    -------
    >>> speakers = get_speakers()
    >>> 'Bruce' in speakers
    True
    >>> 'Peach' in speakers  # Pet, not a speaker
    False
    """
    registry = load_entity_registry()
    entities = registry.get('entities', {})

    return {
        key: entity
        for key, entity in entities.items()
        if entity.get('is_speaker', False)
    }


def get_biographical_subjects() -> Dict[str, Dict]:
    """
    Get all entities that are biographical subjects (is_biographical_subject=True).

    Returns
    -------
    Dict[str, Dict]
        Dictionary of biographical subject entities

    Example
    -------
    >>> subjects = get_biographical_subjects()
    >>> 'Peach' in subjects or any(e.get('canonical_name') == 'Peach' for e in subjects.values())
    True
    """
    registry = load_entity_registry()
    entities = registry.get('entities', {})

    return {
        key: entity
        for key, entity in entities.items()
        if entity.get('is_biographical_subject', False)
    }


def get_entities_by_type(entity_type: str) -> Dict[str, Dict]:
    """
    Get all entities of a specific type.

    Parameters
    ----------
    entity_type : str
        Type to filter by (person, place, object, pet, device)

    Returns
    -------
    Dict[str, Dict]
        Dictionary of matching entities

    Example
    -------
    >>> pets = get_entities_by_type('pet')
    >>> len(pets)
    2
    """
    registry = load_entity_registry()
    entities = registry.get('entities', {})

    return {
        key: entity
        for key, entity in entities.items()
        if entity.get('entity_type') == entity_type
    }


def get_all_stt_corrections() -> Dict[str, str]:
    """
    Get aggregated STT corrections from all entities.

    Returns
    -------
    Dict[str, str]
        Map of wrong -> correct spellings

    Example
    -------
    >>> corrections = get_all_stt_corrections()
    >>> corrections.get('Crape')
    'Grape'
    """
    registry = load_entity_registry()
    entities = registry.get('entities', {})

    corrections = {}
    for entity_data in entities.values():
        entity_corrections = entity_data.get('stt_corrections', {})
        corrections.update(entity_corrections)

    return corrections


def get_all_aliases() -> Dict[str, str]:
    """
    Get map of all aliases to their canonical names.

    Returns
    -------
    Dict[str, str]
        Map of alias -> canonical_name

    Example
    -------
    >>> aliases = get_all_aliases()
    >>> aliases.get('Matt')
    'Matt Bookman'
    """
    registry = load_entity_registry()
    entities = registry.get('entities', {})

    alias_map = {}
    for entity_data in entities.values():
        canonical = entity_data.get('canonical_name')
        for alias in entity_data.get('aliases', []):
            alias_map[alias] = canonical

    return alias_map


# ============================================================================
# Entity Management Functions
# ============================================================================

def add_entity(
    name: str,
    entity_type: str,
    is_speaker: bool = False,
    is_biographical_subject: bool = True,
    aliases: Optional[List[str]] = None,
    stt_corrections: Optional[Dict[str, str]] = None,
    relationship: Optional[str] = None,
    biographical_context: Optional[str] = None,
    **kwargs
) -> bool:
    """
    Add a new entity to the registry.

    Parameters
    ----------
    name : str
        Entity name (will also be canonical_name)
    entity_type : str
        Type: person, place, object, pet, device
    is_speaker : bool
        Can appear as speaker in transcripts
    is_biographical_subject : bool
        Should have biography file
    aliases : Optional[List[str]]
        Known alternate names
    stt_corrections : Optional[Dict[str, str]]
        Map of STT errors to correct spellings
    relationship : Optional[str]
        Relationship to primary user
    biographical_context : Optional[str]
        Brief description
    **kwargs : dict
        Additional fields (relationships, languages, speech_patterns)

    Returns
    -------
    bool
        True if entity was added successfully

    Example
    -------
    >>> add_entity("New Person", "person", relationship="friend")
    True
    """
    registry = load_entity_registry()

    if name in registry.get('entities', {}):
        logger.warning("Entity '%s' already exists", name)
        return False

    entity_data = {
        "canonical_name": name,
        "entity_type": entity_type,
        "is_speaker": is_speaker,
        "is_biographical_subject": is_biographical_subject,
        "aliases": aliases or [],
        "stt_corrections": stt_corrections or {},
        "added_date": datetime.now().strftime("%Y-%m-%d")
    }

    if relationship:
        entity_data["relationship"] = relationship
    if biographical_context:
        entity_data["biographical_context"] = biographical_context

    # Add any additional fields
    for key, value in kwargs.items():
        if value is not None:
            entity_data[key] = value

    registry.setdefault('entities', {})[name] = entity_data

    if save_entity_registry(registry):
        logger.info("Added entity: %s (%s)", name, entity_type)
        return True

    return False


def add_stt_correction(wrong: str, right: str, entity_name: Optional[str] = None) -> bool:
    """
    Add an STT correction to an entity.

    If entity_name is not provided, attempts to find the entity
    that the 'right' value belongs to.

    Parameters
    ----------
    wrong : str
        Incorrect STT spelling
    right : str
        Correct spelling
    entity_name : Optional[str]
        Entity to add correction to (auto-detected if not provided)

    Returns
    -------
    bool
        True if correction was added successfully

    Example
    -------
    >>> add_stt_correction("Crape", "Grape")
    True
    """
    registry = load_entity_registry()
    entities = registry.get('entities', {})

    # Find target entity
    target_key = None

    if entity_name:
        # Use provided entity name
        if entity_name in entities:
            target_key = entity_name
        else:
            # Check canonical names
            for key, entity in entities.items():
                if entity.get('canonical_name') == entity_name:
                    target_key = key
                    break
    else:
        # Auto-detect: find entity where 'right' matches canonical_name or alias
        for key, entity in entities.items():
            if entity.get('canonical_name') == right:
                target_key = key
                break
            if right in entity.get('aliases', []):
                target_key = key
                break

    if not target_key:
        logger.error("Could not find entity for correction: %s -> %s", wrong, right)
        return False

    # Add correction
    if 'stt_corrections' not in entities[target_key]:
        entities[target_key]['stt_corrections'] = {}

    entities[target_key]['stt_corrections'][wrong] = right

    if save_entity_registry(registry):
        logger.info("Added STT correction to '%s': %s -> %s", target_key, wrong, right)
        return True

    return False


def update_entity(name: str, updates: Dict) -> bool:
    """
    Update an existing entity's data.

    Parameters
    ----------
    name : str
        Entity name (key or canonical_name)
    updates : Dict
        Fields to update

    Returns
    -------
    bool
        True if update succeeded

    Example
    -------
    >>> update_entity("Matt Bookman", {"biographical_context": "Updated context"})
    True
    """
    registry = load_entity_registry()
    entities = registry.get('entities', {})

    # Find entity
    target_key = None
    if name in entities:
        target_key = name
    else:
        for key, entity in entities.items():
            if entity.get('canonical_name') == name:
                target_key = key
                break

    if not target_key:
        logger.error("Entity not found: %s", name)
        return False

    # Apply updates
    entities[target_key].update(updates)

    if save_entity_registry(registry):
        logger.info("Updated entity: %s", name)
        return True

    return False


# ============================================================================
# Backward Compatibility
# ============================================================================

def get_speaker_profiles_legacy_format() -> Dict:
    """
    Get speaker profiles in legacy format for backward compatibility.

    Converts entity registry to the format expected by speaker_service.py.

    Returns
    -------
    Dict
        Speaker profiles in legacy format with 'version' and 'speakers' keys

    Example
    -------
    >>> profiles = get_speaker_profiles_legacy_format()
    >>> 'speakers' in profiles
    True
    """
    speakers = get_speakers()

    legacy_profiles = {
        "version": "1.0",
        "speakers": {}
    }

    for key, entity in speakers.items():
        # Convert to legacy format (drop entity-specific fields)
        legacy_speaker = {
            "relationship": entity.get("relationship", "unknown"),
            "relationships": entity.get("relationships", {}),
            "languages": entity.get("languages", {"English": "fluent"}),
            "added_date": entity.get("added_date", "")
        }

        if "speech_patterns" in entity:
            legacy_speaker["speech_patterns"] = entity["speech_patterns"]

        legacy_profiles["speakers"][key] = legacy_speaker

    return legacy_profiles
