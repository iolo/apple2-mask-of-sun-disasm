#!/usr/bin/env python3
"""Build a clean tracked tree with supplied inputs/reference-only regions absent."""
import argparse
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='new generated audit directory')
    parser.add_argument('--revision', default='HEAD', help='committed revision to archive')
    args = parser.parse_args()
    revision = subprocess.check_output(['git', 'rev-parse', args.revision], cwd=ROOT, text=True).strip()
    archive = subprocess.check_output(['git', 'archive', revision], cwd=ROOT)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    checkout = out / 'checkout'
    checkout.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive)) as files:
        classification = json.load(files.extractfile('assets/classification.json'))
        inputs = json.load(files.extractfile('docs/inputs.json'))
        supplied = {entry['path'] for entry in inputs['inputs']}
        references = {entry['path'] for entry in classification['regions'] if entry.get('reference_only')}
        omitted = supplied | references
        members = [entry for entry in files.getmembers() if entry.name not in omitted]
        files.extractall(checkout, members=members, filter='data')
    commands = [
        [sys.executable, 'tools/check_tools.py', '--build-only'],
        [sys.executable, 'tools/build.py'],
        [sys.executable, 'tools/verify_build.py', '--output', 'build/read-audit'],
    ]
    for number, command in enumerate(commands, 1):
        with (out / f'command-{number}.log').open('w') as log:
            subprocess.run(command, cwd=checkout, stdout=log, stderr=subprocess.STDOUT, check=True)
    audit = json.loads((checkout / 'build/read-audit/report.json').read_text())
    build = json.loads((checkout / 'build/disks/build.json').read_text())
    checks = {
        'supplied_inputs_absent': all(not (checkout / path).exists() for path in supplied),
        'reference_regions_absent': all(not (checkout / path).exists() for path in references),
        'read_and_repeatability_audit': audit['pass'],
        'documented_default_build_matches_audit': all(
            disk['sha256'] == next(entry['sha256'] for entry in build['disk_images']
                                  if Path(entry['path']).name == f"mask-of-sun-{disk['side']}.dsk")
            for disk in audit['disks']),
    }
    report = {'revision': revision, 'checkout': str(checkout), 'commands': commands,
        'method': 'git archive of committed tracked tree; exclude inputs/reference-only assets before any build',
        'omitted_supplied_count': len(supplied), 'omitted_reference_count': len(references),
        'omitted_paths': sorted(omitted), 'checks': checks, 'pass': all(checks.values()), 'build_audit': audit,
        'boot_scope': 'Separate MAME session and verify_boot report required; this tool verifies builds only.'}
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'pass': report['pass'], 'checks': checks, 'checkout': str(checkout)}, indent=2))
    return not report['pass']


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
