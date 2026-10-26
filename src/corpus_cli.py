"""CLI de inventário e atualização offline a partir de fontes locais verificadas."""
import argparse
import json
import shutil
from pathlib import Path
from .corpus_inventory import inventory, save, diff, sha


def main():
    p=argparse.ArgumentParser()
    p.add_argument('command', choices=['inventory','update','fetch'])
    p.add_argument('--manifest', default='corpus_manifest.yaml')
    p.add_argument('--version', default='v1')
    p.add_argument('--sources', help='Pasta contendo caminhos relativos à versão (update)')
    args=p.parse_args()
    manifest=Path(args.manifest).resolve(); root=manifest.parent
    if args.command=='inventory':
        result=inventory(root,args.version,manifest)
        target=save(root,result)
        print(target, result['totais'])
        if result['falhas']: raise SystemExit(2)
        return
    if not args.sources: p.error(f'{args.command} requer --sources com todos os arquivos do manifesto')
    import yaml
    m=yaml.safe_load(manifest.read_text(encoding='utf-8'))
    source=Path(args.sources).resolve()
    existing=sorted(int(x.name[1:]) for x in (root/'data/raw').glob('v[0-9]*') if x.name[1:].isdigit())
    if args.command == 'update' and not existing: p.error('nenhuma versão anterior encontrada')
    if args.command == 'fetch' and existing:
        if existing != [1]: p.error('fetch não altera versões existentes; use update')
        result=inventory(root,'v1',manifest)
        if result['falhas']: p.error('v1 existente inválida: '+str(result['falhas']))
        for base in m['bases']:
            for item in base['arquivos']:
                path=source/item['path']
                if not path.is_file() or sha(path)!=sha(root/'data/raw/v1'/item['path']):
                    p.error(f'fonte difere da v1 imutável: {path}')
        print('v1 já existe e confere com as fontes; nenhum arquivo alterado')
        return
    previous=f'v{existing[-1]}' if existing else None
    version=f'v{existing[-1]+1}' if existing else 'v1'
    target=root/'data/raw'/version
    if target.exists(): p.error('destino já existe; não será sobrescrito')
    # Pré-validação de TODAS as fontes antes de criar a nova versão.
    for base in m['bases']:
        for item in base['arquivos']:
            rel=Path(item['path'])
            if rel.is_absolute() or '..' in rel.parts: p.error('caminho inseguro')
            path=source/rel
            if not path.is_file(): p.error(f'fonte ausente: {path}')
            if item.get('sha256') and sha(path)!=item['sha256']:
                p.error(f'hash da fonte diverge do manifesto: {path}')
    target.mkdir(parents=True)
    try:
        for base in m['bases']:
            for item in base['arquivos']:
                rel=Path(item['path']); dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(source/rel,dest)
        current=inventory(root,version,manifest)
        if current['falhas']: raise RuntimeError(str(current['falhas']))
        if previous:
            old_path=root/'data/inventory'/f'{previous}.json'
            old=json.loads(old_path.read_text(encoding='utf-8')) if old_path.exists() else inventory(root,previous,manifest)
            text,_=diff(old,current)
        save(root,current)
        if previous:
            (root/'data/inventory'/f'DIFF_{previous}_{version}.md').write_text(text,encoding='utf-8')
        print(f'Versão imutável criada: {version}; {current["totais"]["arquivos"]} arquivos; {current["totais"]["falhas"]} falhas')
    except Exception:
        shutil.rmtree(target)
        raise

if __name__=='__main__':main()
