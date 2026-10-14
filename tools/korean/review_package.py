#!/usr/bin/env python3
"""Snapshot checked draft review material; never approve or build game disks."""
import argparse
import json
from pathlib import Path
import shutil
import zipfile

from audit_outputs import audit as audit_outputs
from catalog import DEFAULT, ROOT, check_sources, digest, export_exclusions, export_review, review_hash, validate, write_json


def read(path):
    return json.loads(path.read_text())


def build(output, baseline):
    if output.exists() or output.with_suffix('.zip').exists():
        raise ValueError('review snapshot destination already exists')
    catalog = read(DEFAULT)
    validate(catalog)
    check_sources(catalog, baseline)
    active = [m for m in catalog['messages'] if m['status'] != 'excluded']
    if catalog.get('orphaned') or any(m['ko'] is None for m in active):
        raise ValueError('unresolved source entries or missing translations')
    catalog_hash = digest(json.dumps(catalog, ensure_ascii=False, sort_keys=True).encode())
    evidence = ROOT/'docs/evidence/korean'
    policy = read(ROOT/'assets/korean/output-policy.json')
    fresh, _ = audit_outputs(catalog, baseline, policy)
    if fresh != read(evidence/'output-audit.json'):
        raise ValueError('stale source output audit')
    for name in ['draft-encoding.json', 'layout-preview.json', 'input-audit.json',
                 'composed-layout.json', 'output-audit-capacity.json',
                 'output-audit-media-equivalence.json']:
        if read(evidence/name)['catalog_sha256'] != catalog_hash:
            raise ValueError('stale catalog evidence: '+name)
    inputs = read(evidence/'input-audit.json')
    if inputs['glossary_sha256'] != digest((ROOT/'assets/korean/glossary.json').read_bytes()):
        raise ValueError('stale glossary input audit')
    if inputs['tool_sha256'] != digest((ROOT/'tools/korean/audit_inputs.py').read_bytes()):
        raise ValueError('stale input audit tool')
    for name, report in [('layout-preview', 'layout.json'), ('composed-layout', 'composed-layout.json')]:
        if read(ROOT/'build/korean'/name/report)['catalog_sha256'] != catalog_hash:
            raise ValueError('stale preview: '+name)
    equivalence = read(evidence/'output-audit-media-equivalence.json')
    for name, artifact in equivalence['identical_artifacts'].items():
        if digest((ROOT/equivalence['current_build']/name).read_bytes()) != artifact['sha256']:
            raise ValueError('changed synthetic media: '+name)
    for name, expected in equivalence['prior_execution_reports'].items():
        if digest((evidence/name).read_bytes()) != expected:
            raise ValueError('changed execution report: '+name)

    output.mkdir(parents=True)
    for name in ['PLAN-korean.md', 'PRD-korean.md', 'assets/korean/messages.json',
                 'assets/korean/glossary.json', 'assets/korean/output-policy.json',
                 'assets/korean/font/OFL.md', 'assets/korean/font/source.json']:
        target = output/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    for name in ['docs/korean', 'docs/evidence/korean', 'build/korean/layout-preview',
                 'build/korean/composed-layout']:
        shutil.copytree(ROOT/name, output/name)
    # Export from the checked catalog instead of trusting a stale review table.
    export_review(catalog, output/'docs/korean/review.md')
    export_exclusions(catalog, output/'docs/korean/exclusions.md')
    (output/'README.md').write_text(
        '# 한국어 번역 검수 묶음\n\n'
        '미승인 초안입니다. [검수 안내](docs/korean/review-package.md)부터 읽어 주세요.\n\n'
        '- [7×8 화면 검색·미리보기](build/korean/layout-preview/index.html)\n'
        '- [원문·번역·문맥 검수표](docs/korean/review.md)\n'
        '- [용어집](assets/korean/glossary.json)\n'
        '- [영문 입력 안내](docs/korean/input-guide.md)\n'
        '- [검수자용 수수께끼 자료 — 정답 포함](docs/korean/input-review.md)\n'
        '- [번역 제외 목록](docs/korean/exclusions.md)\n\n'
        f'카탈로그 SHA-256: `{catalog_hash}`\n\n'
        '이 묶음의 상태는 검수 요청이며 번역 적용 승인이 아닙니다. '
        '항목별 카탈로그 상태는 draft로 유지합니다. 수정안 또는 명시적 승인 범위를 '
        '알려 주세요. 응답이 없다는 이유로 승인하지 않습니다.\n\n'
        '화면 HTML은 images 폴더와 함께 열어야 합니다. 미리보기는 가정된 배치이며 '
        '실제 게임 화면이 아닙니다. 기술 문서의 소스·원본·빌드 링크는 원래 저장소 '
        '체크아웃이 필요할 수 있습니다. 원본 게임 디스크는 포함하지 않습니다.\n')
    manifest = dict(kind='human translation review snapshot; no approval',
        review_status='in_review', catalog_sha256=catalog_hash,
        translated_entries=len(active), excluded_entries=len(catalog['messages'])-len(active),
        approved_entries=sum(m['status']=='approved' for m in active),
        builder_sha256=digest(Path(__file__).read_bytes()),
        message_review_hashes={m['id']:review_hash(m) for m in active},
        files={str(p.relative_to(output)):digest(p.read_bytes())
               for p in sorted(output.rglob('*')) if p.is_file()})
    write_json(output/'manifest.json', manifest)
    archive = output.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(output.rglob('*')):
            if path.is_file():
                info = zipfile.ZipInfo(str(path.relative_to(output)), date_time=(2026,10,14,0,0,0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                bundle.writestr(info, path.read_bytes())
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise ValueError('review archive checksum failure')
        for name, expected in manifest['files'].items():
            if digest(bundle.read(name)) != expected:
                raise ValueError('review archive manifest mismatch: '+name)
    return dict(output=str(output), archive=str(archive), archive_sha256=digest(archive.read_bytes()),
                catalog_sha256=catalog_hash, translated_entries=len(active), files=len(manifest['files']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, default=ROOT/'build/korean/english-baseline')
    args = parser.parse_args()
    print(json.dumps(build(args.output.resolve(), args.baseline), ensure_ascii=False, indent=2))
