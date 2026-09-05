def compute_delta(user_constraints: dict, schema: dict) -> list[str]:
    """Pure function. Returns list of required_attributes keys from schema that are
    missing or None in user_constraints. No LLM, no I/O. O(1)-ish, just dict diffing."""
    required = schema.get("required_attributes", [])
    missing = []
    for req in required:
        if req not in user_constraints or user_constraints[req] is None:
            missing.append(req)
    return missing
