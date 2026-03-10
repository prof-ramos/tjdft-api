import json
from pathlib import Path

import pytest

import app.utils.filtros as filtros

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clear_cache_between_tests():
    filtros.clear_referencia_cache()
    yield
    filtros.clear_referencia_cache()


@pytest.fixture
def referencia_fixture_root(tmp_path: Path) -> Path:
    fake_module = tmp_path / "app" / "utils" / "filtros.py"
    fake_module.parent.mkdir(parents=True, exist_ok=True)
    fake_module.write_text("# fake filtros module\n", encoding="utf-8")
    return fake_module


def write_referencia_json(root: Path, content: str) -> Path:
    data_dir = root.parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / "referencia.json"
    target.write_text(content, encoding="utf-8")
    return target


def test_load_referencia_reads_file_and_uses_cache(
    monkeypatch, referencia_fixture_root: Path
):
    sample = {
        "relatores": [{"id": "rel-1", "nome": "Relator 1", "orgao": "1CC"}],
        "classes": [{"codigo": "APC", "nome": "Apelação Cível"}],
        "orgaos_julgadores": [{"codigo": "1CC", "nome": "1ª Câmara Cível"}],
        "assuntos": [{"codigo": "TRIB", "nome": "Tributário"}],
    }
    write_referencia_json(referencia_fixture_root, json.dumps(sample))
    monkeypatch.setattr(filtros, "__file__", str(referencia_fixture_root))

    loaded_first = filtros.load_referencia()
    loaded_second = filtros.load_referencia()

    assert loaded_first == sample
    assert loaded_second is loaded_first


def test_load_referencia_raises_file_not_found(
    monkeypatch, referencia_fixture_root: Path
):
    monkeypatch.setattr(filtros, "__file__", str(referencia_fixture_root))

    with pytest.raises(FileNotFoundError):
        filtros.load_referencia()


def test_load_referencia_raises_json_decode_error(
    monkeypatch, referencia_fixture_root: Path
):
    write_referencia_json(referencia_fixture_root, "{invalid json")
    monkeypatch.setattr(filtros, "__file__", str(referencia_fixture_root))

    with pytest.raises(json.JSONDecodeError):
        filtros.load_referencia()


def test_validate_functions_and_getters_use_reference_data(monkeypatch):
    referencia = {
        "relatores": [{"id": "desembargador-faustolo", "nome": "Faustolo"}],
        "classes": [{"codigo": "APC", "nome": "Apelação Cível"}],
        "orgaos_julgadores": [{"codigo": "6CC", "nome": "6ª Câmara Cível"}],
        "assuntos": [{"codigo": "TRIB", "nome": "Tributário"}],
    }
    monkeypatch.setattr(filtros, "load_referencia", lambda: referencia)

    assert filtros.validate_relator("desembargador-faustolo") is True
    assert filtros.validate_relator("inexistente") is False
    assert filtros.validate_classe("APC") is True
    assert filtros.validate_classe("XXX") is False
    assert filtros.validate_orgao("6CC") is True
    assert filtros.validate_orgao("YYY") is False
    assert filtros.get_relatores() == referencia["relatores"]
    assert filtros.get_classes() == referencia["classes"]
    assert filtros.get_orgaos() == referencia["orgaos_julgadores"]
    assert filtros.get_assuntos() == referencia["assuntos"]


@pytest.mark.parametrize(
    ("getter_name", "expected"),
    [
        ("validate_relator", False),
        ("validate_classe", False),
        ("validate_orgao", False),
        ("get_relatores", []),
        ("get_classes", []),
        ("get_orgaos", []),
        ("get_assuntos", []),
    ],
)
def test_validation_and_getters_handle_load_errors(monkeypatch, getter_name, expected):
    monkeypatch.setattr(
        filtros, "load_referencia", lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    target = getattr(filtros, getter_name)

    if getter_name.startswith("validate_"):
        result = target("any")
    else:
        result = target()

    assert result == expected


def test_filtrar_por_instancia_returns_same_list_when_flag_is_false():
    registros = [{"uuid_tjdft": "1"}, {"uuid_tjdft": "2"}]

    resultado = filtros.filtrar_por_instancia(registros, False)

    assert resultado is registros


def test_filtrar_por_instancia_excludes_turmas_recursais():
    registros = [
        {"uuid_tjdft": "1", "turmaRecursal": True, "subbase": "acordaos"},
        {"uuid_tjdft": "2", "turmaRecursal": False, "subbase": "acordaos"},
        {"uuid_tjdft": "3", "subbase": "acordaos-tr"},
        {"uuid_tjdft": "4"},
    ]

    resultado = filtros.filtrar_por_instancia(registros, True)

    assert [item["uuid_tjdft"] for item in resultado] == ["2", "4"]


def test_filtrar_relatores_ativos_returns_same_list_when_flag_is_false():
    registros = [{"uuid_tjdft": "1"}, {"uuid_tjdft": "2"}]

    resultado = filtros.filtrar_relatores_ativos(registros, False)

    assert resultado is registros


def test_filtrar_relatores_ativos_keeps_only_explicit_true():
    registros = [
        {"uuid_tjdft": "1", "relatorAtivo": True},
        {"uuid_tjdft": "2", "relatorAtivo": False},
        {"uuid_tjdft": "3"},
        {"uuid_tjdft": "4", "relatorAtivo": None},
    ]

    resultado = filtros.filtrar_relatores_ativos(registros, True)

    assert [item["uuid_tjdft"] for item in resultado] == ["1"]
