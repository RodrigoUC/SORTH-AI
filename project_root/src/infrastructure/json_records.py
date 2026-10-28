"""Strict JSON decoding shared by local identities and remote metadata readers."""
import json


def decode_record(raw):
    """Reject duplicate keys and non-finite numbers; callers own size/schema limits."""
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate key')
            result[key] = value
        return result

    def reject_constant(_):
        raise ValueError('non-finite JSON value')

    return json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
