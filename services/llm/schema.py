"""Convert the existing prompt examples into a closed JSON Schema."""
def schema_from_example(value):
    if isinstance(value, dict):
        return {'type': 'object', 'properties': {k: schema_from_example(v) for k, v in value.items()},
                'required': list(value), 'additionalProperties': False}
    if isinstance(value, list):
        return {'type': 'array', 'items': schema_from_example(value[0]), 'maxItems': 8}
    if type(value) is int:
        return {'type': 'integer', 'minimum': 1}
    return {'type': 'string', 'maxLength': 600}
