#!/usr/bin/env python3
"""Static checks of the original standalone HTML; never executes its JavaScript.

The report does not certify browser behavior, licensing, privacy or release.
The separate scene validator does not validate this legacy presentation format.
"""
import argparse
import base64
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

ORIGINAL_SHA256 = '9bae870fefb63c079a5afa632e1a64d5d0b0d6c2a25c61f8f31efb68fc67ba1e'
ORIGINAL_BYTES = 4668964


class Structure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.script = None
        self.ids = []
        self.automatic_remote_resources = []
        self.tabs = []
        self.transcript = False
        self.lang = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'html':
            self.lang = attrs.get('lang')
        if attrs.get('id') == 'transcript':
            self.transcript = True
        if attrs.get('role') == 'tab':
            self.tabs.append(attrs)
        if tag == 'script':
            self.script = []
        if tag != 'a':
            for key in ['src', 'href', 'action', 'data', 'poster', 'srcset']:
                value = attrs.get(key, '')
                if re.search(r'(?:https?:)?//', value):
                    self.automatic_remote_resources.append({'tag': tag, 'attribute': key})

    def handle_data(self, data):
        if self.script is not None:
            self.script.append(data)

    def handle_endtag(self, tag):
        if tag == 'script' and self.script is not None:
            self.scripts.append(''.join(self.script))
            self.script = None


def embedded_json(script, name):
    found = re.search(r'\bconst\s+' + re.escape(name) + r'\s*=\s*', script)
    if not found:
        raise ValueError('missing JSON constant ' + name)
    value, end = json.JSONDecoder().raw_decode(script[found.end():])
    if not script[found.end() + end:].lstrip().startswith(';'):
        raise ValueError('constant is not a literal JSON assignment: ' + name)
    return value


def audit(path):
    raw = Path(path).read_bytes()
    html = raw.decode('utf-8')
    parser = Structure()
    parser.feed(html)
    script = '\n'.join(parser.scripts)
    slides = embedded_json(script, 'SLIDES')
    manifest = embedded_json(script, 'MANIFEST')
    claims = embedded_json(script, 'CLAIMS')
    modules = embedded_json(script, 'MODULES')
    media = []
    for index, slide in enumerate(slides, 1):
        for field, prefix in [('audio_data', 'data:audio/mpeg;base64,'),
                              ('slide_data', 'data:image/png;base64,')]:
            uri = slide[field]
            if not uri.startswith(prefix):
                raise ValueError(f'unsupported media type: slide {index} {field}')
            payload = base64.b64decode(uri[len(prefix):], validate=True)
            valid_header = (payload.startswith(b'\x89PNG\r\n\x1a\n') if field == 'slide_data'
                            else payload.startswith(b'ID3') or
                            (len(payload) > 1 and payload[0] == 255 and payload[1] & 224 == 224))
            if not valid_header:
                raise ValueError(f'invalid media signature: slide {index} {field}')
            media.append({'slide': index, 'kind': field, 'bytes': len(payload),
                          'sha256': hashlib.sha256(payload).hexdigest()})
    node = shutil.which('node')
    syntax = 'HOLD_NODE_UNAVAILABLE'
    if node:
        with tempfile.TemporaryDirectory() as directory:
            js = Path(directory) / 'inline.js'
            js.write_text(script, encoding='utf-8')
            outcome = subprocess.run([node, '--check', str(js)], capture_output=True, timeout=30)
            syntax = 'PASS' if outcome.returncode == 0 else 'FAIL'
    # Indicators aid the accompanying source review; absence is not a proof of isolation.
    network_indicators = sorted(set(re.findall(
        r'\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon|importScripts)\b', script)))
    checks = {
        'original_hash_matches': hashlib.sha256(raw).hexdigest() == ORIGINAL_SHA256,
        'original_size_matches': len(raw) == ORIGINAL_BYTES,
        'js_syntax_pass': syntax == 'PASS',
        'six_slides': len(slides) == 6,
        'twelve_embedded_media_headers': len(media) == 12,
        'unique_html_ids': len(parser.ids) == len(set(parser.ids)),
        'no_declared_automatic_remote_resources': not parser.automatic_remote_resources,
        'no_network_api_indicators': not network_indicators,
        'transcript_element_and_pt_br': parser.transcript and parser.lang == 'pt-BR',
        'legacy_export_is_demo_only': manifest.get('epistemic_status') == 'DEMO_ONLY',
        'legacy_export_claims_match_ui': manifest.get('claims') == claims,
        'legacy_export_modules_match_ui': manifest.get('modules') == modules,
    }
    return {
        'report_version': 1,
        'scope': 'STATIC_ORIGINAL_ARTIFACT_ONLY',
        'result': 'PASS_STATIC_CHECKS' if all(checks.values()) else 'FAIL_STATIC_CHECKS',
        'artifact': {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
                     'presentation_schema': manifest.get('schema')},
        'checks': checks, 'media': media,
        'network_api_indicators': network_indicators,
        'findings': {
            'tabs_without_aria_controls': sum('aria-controls' not in tab for tab in parser.tabs),
            'tabs_without_explicit_tabindex': sum('tabindex' not in tab for tab in parser.tabs),
            'legacy_claim_states': sorted({claim['status'] for claim in claims}),
            'visible_demo_stamp_hidden_below_720': '@media(max-width:720px)' in html and 'header .stamp{display:none}' in html,
        },
        'holds': ['real_browser', 'physical_devices', 'full_accessibility', 'media_rights',
                  'publication_privacy_review', 'deployment', 'operational_integration'],
        'release_authorized': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('html', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.html)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(json.dumps({'result': 'FAIL_STATIC_CHECKS', 'reason': str(exc)}))
        return 1
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(rendered, encoding='utf-8')
    print(rendered)
    return 0 if report['result'] == 'PASS_STATIC_CHECKS' else 1


if __name__ == '__main__':
    sys.exit(main())
