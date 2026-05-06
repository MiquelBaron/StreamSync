"""
Compatibilitat enrere: la implementació viu a ``ss.sync``.

Sincronitza el catàleg des de ``ss.catalog_api`` (OpenAPI Movies API v1).

Alineació amb l'esquema publicat:
- ``Genre``: ``id``, ``description`` (sense ``name``); el nom local es deriva de ``description``.
- ``AgeRating``: ``id``, ``title`` (sense ``minimum_age`` obligatori); es mapa ``title`` →
  ``AgeRating.description`` i s'intenta extreure l'edat mínima del text si cal.
- ``Movie.rating``: pot ser objecte (classificació) o número (valoració de contingut);
  objecte → ``AgeRating``; número → ``Content.rating``.
- ``Movie``: ``duration_minutes`` es persisteix a ``Film.duration_minutes``.
- ``Serie``: només ``id`` i ``title`` al schema; la resta de FKs es resolen amb placeholders
  o mapes dels endpoints quan hi hagi ``*_id``.
- ``Serie`` es deduplica entre plataformes com ``Film``: una instància i ``platforms`` many-to-many.
- Gènere, edat, país, idioma i director (dades de referència per ``external_id``) es desen a
  ``CATALOG_REF_SOURCE`` — una sola fila per id, compartida per totes les plataformes.
  Al iniciar cada sync s'uneixen duplicats vells (``merge_legacy_reference_tables``).

Flux per plataforma: endpoints de referència → ``movies``/``series`` → mirall suau ``is_active``.
"""
from ss.sync import CATALOG_REF_SOURCE, sync_catalog_from_apis

__all__ = ["CATALOG_REF_SOURCE", "sync_catalog_from_apis"]
