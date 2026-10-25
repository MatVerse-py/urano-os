#!/usr/bin/env python3
"""Offline, non-authoritative validator for the Prancha demo profile.

Only the schema keywords used by the bundled profile are supported. Unknown
keywords fail closed. This is not a general JSON Schema engine or a Gate.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / 'docs/schemas/prancha-scene-demo.v1.schema.json'
MAX_BYTES = 65536
KEYWORDS = {'$schema', '$id', 'title', 'description', 'type', 'const', 'enum',
            'required', 'properties', 'additionalProperties', 'items',
            'minItems', 'maxItems', 'minLength', 'maxLength', 'pattern'}
TYPES = {'object': dict, 'array': list, 'string': str, 'boolean': bool,
         'null': type(None)}


class InvalidDemo(ValueError):
    pass


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidDemo('duplicate JSON key: ' + key)
        result[key] = value
    return result


def _constant(value):
    raise InvalidDemo('non-JSON number: ' + value)


def read_json(path):
    # Read at most one byte beyond the budget, including untrusted CLI files.
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise InvalidDemo('manifest exceeds 65536 bytes')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                           parse_constant=_constant)
        stack = [(value, 0)]
        while stack:
            node, depth = stack.pop()
            if depth > 16:
                raise InvalidDemo('manifest exceeds nesting depth 16')
            if type(node) is dict:
                stack.extend((child, depth + 1) for child in node.values())
            elif type(node) is list:
                stack.extend((child, depth + 1) for child in node)
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise InvalidDemo('invalid UTF-8 JSON') from exc


def check_schema(schema):
    unknown = set(schema) - KEYWORDS
    if unknown:
        raise InvalidDemo('unsupported schema keywords: ' + ', '.join(sorted(unknown)))
    if schema.get('type') not in TYPES:
        raise InvalidDemo('unsupported or missing schema type')
    if schema['type'] == 'object' and schema.get('additionalProperties') is not False:
        raise InvalidDemo('demo object must reject unknown fields')
    if 'pattern' in schema:
        re.compile(schema['pattern'])
    for child in schema.get('properties', {}).values():
        check_schema(child)
    if 'items' in schema:
        check_schema(schema['items'])


def _check(value, schema, path='$'):
    if type(value) is not TYPES[schema['type']]:
        raise InvalidDemo(path + ': wrong type')
    if 'const' in schema and (type(value) is not type(schema['const']) or value != schema['const']):
        raise InvalidDemo(path + ': forbidden value')
    if 'enum' in schema and value not in schema['enum']:
        raise InvalidDemo(path + ': unknown state')
    if type(value) is dict:
        properties = schema.get('properties', {})
        missing = set(schema.get('required', [])) - set(value)
        unknown = set(value) - set(properties)
        if missing or unknown:
            raise InvalidDemo(path + ': missing or unknown fields')
        for key, item in value.items():
            _check(item, properties[key], path + '.' + key)
    elif type(value) is list:
        if not schema.get('minItems', 0) <= len(value) <= schema.get('maxItems', MAX_BYTES):
            raise InvalidDemo(path + ': invalid item count')
        for i, item in enumerate(value):
            _check(item, schema['items'], f'{path}[{i}]')
    elif type(value) is str:
        if not schema.get('minLength', 0) <= len(value) <= schema.get('maxLength', MAX_BYTES):
            raise InvalidDemo(path + ': invalid string length')
        if 'pattern' in schema and re.fullmatch(schema['pattern'], value) is None:
            raise InvalidDemo(path + ': invalid identifier')


def validate_scene(scene, schema=None):
    schema = read_json(SCHEMA) if schema is None else schema
    check_schema(schema)
    _check(scene, schema)
    identifiers = [c['id'] for c in scene['claims']]
    if len(set(identifiers)) != len(identifiers):
        raise InvalidDemo('duplicate claim identifier')
    return scene


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    try:
        scene = validate_scene(read_json(args.manifest))
    except (InvalidDemo, OSError) as exc:
        print(json.dumps({'result': 'FAIL', 'reason': str(exc)}))
        return 1
    print(json.dumps({'result': 'PASS_DEMO_PROFILE', 'scene_id': scene['scene_id'],
                      'status': 'DEMO_ONLY', 'may_execute': False,
                      'operational_validation': 'HOLD', 'publication': 'HOLD'}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
