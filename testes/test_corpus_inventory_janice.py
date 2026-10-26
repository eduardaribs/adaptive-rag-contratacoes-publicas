from src.corpus_inventory import diff, inventory

def test_diff_quatro_categorias():
    old={'version':'v1','arquivos':[{'path':'raw/v1/a','sha256':'1'},{'path':'raw/v1/b','sha256':'2'},{'path':'raw/v1/c','sha256':'3'}]}
    new={'version':'v2','arquivos':[{'path':'raw/v2/a','sha256':'1'},{'path':'raw/v2/b','sha256':'X'},{'path':'raw/v2/d','sha256':'4'}]}
    _, groups=diff(old,new)
    assert groups=={'adicionados':['d'],'removidos':['c'],'alterados':['b'],'identicos':['a']}

def test_inventario_detecta_hash_incorreto(tmp_path):
    import yaml
    p=tmp_path/'data/raw/v1/teste/a.txt';p.parent.mkdir(parents=True);p.write_text('abc')
    m=tmp_path/'corpus_manifest.yaml';m.write_text(yaml.safe_dump({'scenario_id':'x','bases':[{'base_id':'teste','natureza':'normativa','arquivos':[{'path':'teste/a.txt','sha256':'invalido'}]}]}))
    result=inventory(tmp_path,'v1',m)
    assert result['totais']['falhas']==1 and result['totais']['arquivos']==0
