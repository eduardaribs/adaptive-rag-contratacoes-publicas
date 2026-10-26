from copy import deepcopy

from src.technology_classifier import classificar_registro


def classificar(objeto):
    return classificar_registro({
        "id_pncp": "teste",
        "objeto": objeto,
        "fonte_original": "teste.json",
    })


def test_servico_tic_contextual():
    resultado = classificar("Contratação de serviços de informática.")
    assert resultado["status"] == "tic_proposto"
    assert resultado["tipo"] == "servico_proposto"


def test_material_nao_e_contado_como_servico():
    resultado = classificar("Aquisição de material de informática.")
    assert resultado["status"] == "tic_proposto"
    assert resultado["tipo"] == "bem_proposto"


def test_instituicao_de_informatica_nao_basta():
    resultado = classificar(
        "Recrutamento de jovem aprendiz para a Empresa Municipal "
        "de Informática."
    )
    assert resultado["status"] == "revisao"
    assert resultado["tipo"] == "indeterminado"


def test_rede_generica_exige_revisao():
    resultado = classificar("Manutenção da rede de águas pluviais.")
    assert resultado["status"] == "revisao"


def test_palavra_ambigua_nao_classifica():
    resultado = classificar("Aquisição de sistema eletrônico.")
    assert resultado["status"] == "revisao"


def test_preserva_evidencia_fonte_e_registro():
    registro = {
        "id_pncp": "1",
        "objeto": "Contratação de serviços de segurança da informação.",
        "fonte_original": "corpus.json",
    }
    original = deepcopy(registro)
    resultado = classificar_registro(registro)

    assert resultado["evidencia"] == registro["objeto"]
    assert resultado["campo_evidencia"] == "objeto"
    assert resultado["fonte"] == "corpus.json"
    assert resultado["id_pncp"] == "1"
    assert registro == original


def test_sem_indicio_nao_significa_exclusao_confirmada():
    resultado = classificar("Aquisição de cadeiras.")
    assert resultado["status"] == "sem_indicio"


def test_objeto_ausente_exige_revisao():
    assert classificar("")["status"] == "revisao"
