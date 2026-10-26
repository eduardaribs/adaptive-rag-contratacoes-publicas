"""Inventário verificável de snapshots locais, sem acesso à rede."""
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def inventory(root, version, manifest_path):
    manifest = yaml.safe_load(manifest_path.read_text(encoding='utf-8'))
    bases = manifest['bases']
    if len({b['base_id'] for b in bases}) != len(bases):
        raise ValueError('base_id duplicado')
    base_by_id = {b['base_id']: b for b in bases}
    raw = root / 'data' / 'raw' / version
    if not raw.is_dir():
        raise FileNotFoundError(raw)
    entries, failures, summaries = [], [], []
    for base in bases:
        base_id = base['base_id']
        declared = base.get('arquivos', [])
        current = []
        for entry in declared:
            rel = Path(entry['path'])
            if rel.is_absolute() or '..' in rel.parts:
                raise ValueError(f'caminho inseguro: {rel}')
            path = raw / rel
            if not path.is_file():
                failures.append({'base_id': base_id, 'origem': entry.get('origem', ''), 'path': str(rel), 'erro': 'arquivo ausente'})
                continue
            digest = sha(path)
            if entry.get('sha256') and digest != entry['sha256']:
                failures.append({'base_id': base_id, 'origem': entry.get('origem', ''), 'path': str(rel), 'erro': 'sha256 diferente do manifesto'})
                continue
            item = {'path': f'raw/{version}/{rel.as_posix()}', 'base_id': base_id,
                    'tipo': path.suffix.lstrip('.').lower(), 'bytes': path.stat().st_size,
                    'sha256': digest, 'origem': entry.get('origem', ''),
                    'coletado_em': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(), 'status': 'ok'}
            entries.append(item)
            current.append(item)
        target = base.get('volume_alvo', len(declared))
        summaries.append({'base_id': base_id, 'natureza': base['natureza'], 'arquivos': len(current),
                          'formatos': dict(Counter(e['tipo'] for e in current)),
                          'bytes': sum(e['bytes'] for e in current), 'volume_alvo': target,
                          'divergencia_alvo': len(current) - target})
    known = {'raw/' + version + '/' + item['path'] for base in bases for item in base.get('arquivos', [])}
    for path in sorted(raw.rglob('*')):
        if path.is_file() and '_progresso_fetch' not in path.parts:
            rel = 'raw/' + version + '/' + path.relative_to(raw).as_posix()
            if rel not in known:
                failures.append({'path': rel, 'erro': 'arquivo não declarado no manifesto'})
    result = {'scenario_id': manifest['scenario_id'], 'version': version,
              'coletado_em': datetime.now(timezone.utc).isoformat(),
              'manifest_hash': 'sha256:' + sha(manifest_path),
              'totais': {'arquivos': len(entries), 'bytes': sum(e['bytes'] for e in entries), 'falhas': len(failures)},
              'por_base': summaries, 'arquivos': entries, 'falhas': failures}
    return result


def diff(old, new):
    def keyed(doc):
        return {e['path'].split('/', 2)[-1]: e['sha256'] for e in doc['arquivos']}
    a, b = keyed(old), keyed(new)
    groups = {'adicionados': sorted(b.keys() - a.keys()), 'removidos': sorted(a.keys() - b.keys()),
              'alterados': sorted(k for k in a.keys() & b.keys() if a[k] != b[k]),
              'identicos': sorted(k for k in a.keys() & b.keys() if a[k] == b[k])}
    lines = [f"# DIFF {old['version']} → {new['version']}", '', 'Comparação por SHA-256; caminhos relativos à raiz da versão.', '']
    for name, paths in groups.items():
        lines.extend([f'## {name.capitalize()} ({len(paths)})', *('- ' + p for p in paths), ''])
    return '\n'.join(lines), groups


def save(root, result):
    target = root / 'data' / 'inventory' / (result['version'] + '.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    md = ['# Inventário do corpus', '', f"Versão: {result['version']}",
          f"Coleta/inventário: {result['coletado_em']}", f"Arquivos: {result['totais']['arquivos']}",
          f"Bytes: {result['totais']['bytes']}", f"Falhas: {result['totais']['falhas']}", '',
          '| Base | Natureza | Arquivos | Formatos | Bytes | Alvo | Divergência |',
          '|---|---|---:|---|---:|---:|---:|']
    for b in result['por_base']:
        md.append(f"| {b['base_id']} | {b['natureza']} | {b['arquivos']} | {b['formatos']} | {b['bytes']} | {b['volume_alvo']} | {b['divergencia_alvo']} |")
    md.extend(['', '## Falhas', *('- ' + json.dumps(f, ensure_ascii=False) for f in result['falhas'])])
    (root / 'CORPUS_INVENTORY.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    return target
