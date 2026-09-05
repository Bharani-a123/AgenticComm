"""
This module provides hash-based integrity verification for AP2 mandate objects.
It does NOT implement cryptographic signing / non-repudiation (no private keys, 
no signature verification against a trusted issuer). This is a deliberate scope 
decision appropriate for a hackathon timeframe — production AP2 would extend 
this with real signature verification.
"""
import hashlib
import json
from uuid import UUID
from pydantic import BaseModel

def compute_mandate_hash(mandate: BaseModel) -> str:
    # Serialize the mandate to canonical JSON (sorted keys, no whitespace)
    canonical_json = mandate.model_dump_json(exclude={"hash"}, exclude_none=True)
    # Ensure consistent ordering for nested dicts by parsing and re-dumping
    parsed = json.loads(canonical_json)
    canonical_str = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

def derive_idempotency_key(cart_mandate_id: UUID) -> str:
    # MUST be pure function of cart_mandate_id
    hash_str = hashlib.sha256(str(cart_mandate_id).encode("utf-8")).hexdigest()
    return f"idem_{hash_str[:24]}"
