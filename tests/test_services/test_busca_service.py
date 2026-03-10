from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

import app.services.busca_service as busca_module
from app.models.decisao import Decisao
from app.schemas.consulta import BuscaRequest
from app.services.busca_service import BuscaService, BuscaServiceError, FiltroInvalidoError
from app.utils.cache import CacheManager

pytestmark = pytest.mark.unit


@pytest.fixture
def cache_manager() -> CacheManager:
    cache = CacheManager()
    cache._redis_client = None
    return cache


@pytest.fixture
def service(db_session, cache_manager: CacheManager) -> BuscaService:
    return BuscaService(session=db_session, cache_manager=cache_manager)


@pytest.fixture
def consulta_stub():
    return SimpleNamespace(
        id=str(uuid4()),
        query="tributário",
        filtros={"classe": "APC"},
        resultados_encontrados=2,
        pagina=1,
        tamanho=20,
        criado_em=datetime(2024, 1, 15, 10, 30, 0),
        usuario_id=str(uuid4()),
    )


class DummyTJDFTClient:
    response = {}
    all_results = []

    def __init__(self, cache):
        self.cache = cache
        self.buscar_simples = AsyncMock(return_value=self.response)
        self.buscar_com_filtros = AsyncMock(return_value=self.response)
        self.buscar_todas_paginas = AsyncMock(return_value=self.all_results)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


class TestBuscar:
    @pytest.mark.asyncio
    async def test_buscar_uses_registros_contract_regression(
        self, service: BuscaService, monkeypatch, consulta_stub
    ):
        # Regressão do contrato com o cliente: o serviço deve aceitar payloads
        # no formato legado/normalizado com `registros`, não apenas `dados`.
        request = BuscaRequest(query="tributário", pagina=1, tamanho=20)
        DummyTJDFTClient.response = {
            "registros": [
                {
                    "uuid": "uuid-1",
                    "numeroProcesso": "0700001",
                    "ementa": "Ementa 1",
                    "nomeRelator": "Relator 1",
                    "dataJulgamento": "2024-01-10",
                    "descricaoOrgaoJulgador": "1ª Câmara Cível",
                    "descricaoClasseCnj": "Apelação",
                    "marcadores": {"trecho": ["destaque"]},
                    "turmaRecursal": False,
                    "subbase": "acordaos",
                }
            ],
            "total": 1,
        }
        monkeypatch.setattr(busca_module, "TJDFTClient", DummyTJDFTClient)
        service.consulta_repo.create = AsyncMock(return_value=consulta_stub)
        service._salvar_decisoes_cache = AsyncMock()

        resultado = await service.buscar(request)

        assert resultado["total"] == 1
        assert resultado["total_filtrado"] == 1
        assert len(resultado["resultados"]) == 1
        assert resultado["resultados"][0]["uuid_tjdft"] == "uuid-1"
        service._salvar_decisoes_cache.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_buscar_with_filtros_calls_filtered_client(
        self, service: BuscaService, monkeypatch, consulta_stub
    ):
        request = BuscaRequest(
            query="tributário",
            filtros={"relator": "desembargador-faustolo", "classe": "APC"},
            pagina=1,
            tamanho=20,
        )
        dummy_client = DummyTJDFTClient(None)
        dummy_client.buscar_com_filtros = AsyncMock(return_value={"dados": [], "total": 0})
        client_factory = MagicMock(return_value=dummy_client)
        monkeypatch.setattr(busca_module, "TJDFTClient", client_factory)
        monkeypatch.setattr(busca_module, "validate_relator", lambda value: True)
        monkeypatch.setattr(busca_module, "validate_classe", lambda value: True)
        service.consulta_repo.create = AsyncMock(return_value=consulta_stub)
        service._salvar_decisoes_cache = AsyncMock()

        resultado = await service.buscar(request)

        dummy_client.buscar_com_filtros.assert_awaited_once()
        dummy_client.buscar_simples.assert_not_awaited()
        assert resultado["consulta_id"] == str(consulta_stub.id)

    @pytest.mark.asyncio
    async def test_buscar_applies_runtime_filters_and_caches_results(
        self, service: BuscaService, monkeypatch, consulta_stub
    ):
        request = BuscaRequest(
            query="tributário",
            pagina=1,
            tamanho=20,
            excluir_turmas_recursais=True,
            apenas_ativos=True,
        )
        DummyTJDFTClient.response = {
            "dados": [
                {
                    "uuid": "uuid-1",
                    "numeroProcesso": "0700001",
                    "ementa": "Ementa 1",
                    "nomeRelator": "Relator 1",
                    "dataJulgamento": "2024-01-10",
                    "descricaoOrgaoJulgador": "1ª Câmara Cível",
                    "descricaoClasseCnj": "Apelação",
                    "marcadores": {"trecho": ["destaque"]},
                    "turmaRecursal": False,
                    "subbase": "acordaos",
                    "relatorAtivo": True,
                },
                {
                    "uuid": "uuid-2",
                    "numeroProcesso": "0700002",
                    "ementa": "Ementa 2",
                    "nomeRelator": "Relator 2",
                    "dataJulgamento": "2024-02-10",
                    "descricaoOrgaoJulgador": "1ª Câmara Cível",
                    "descricaoClasseCnj": "Apelação",
                    "turmaRecursal": True,
                    "subbase": "acordaos-tr",
                    "relatorAtivo": False,
                },
            ],
            "total": 2,
        }
        monkeypatch.setattr(busca_module, "TJDFTClient", DummyTJDFTClient)
        service.consulta_repo.create = AsyncMock(return_value=consulta_stub)
        service._salvar_decisoes_cache = AsyncMock()

        resultado = await service.buscar(request)

        assert resultado["total"] == 2
        assert resultado["total_filtrado"] == 1
        assert len(resultado["resultados"]) == 1
        assert resultado["resultados"][0]["instancia"] == "tjdft_2a_instancia"
        assert resultado["resultados"][0]["resumo_relevancia"] == {"trecho": "destaque"}
        service._salvar_decisoes_cache.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_buscar_raises_filtro_invalido_error_for_invalid_filters(
        self, service: BuscaService, monkeypatch
    ):
        request = BuscaRequest(query="tributário", filtros={"classe": "INVALIDA"})
        monkeypatch.setattr(busca_module, "validate_classe", lambda value: False)

        with pytest.raises(BuscaServiceError, match="Classe inválida: INVALIDA"):
            await service.buscar(request)

    @pytest.mark.asyncio
    async def test_buscar_wraps_unexpected_errors(
        self, service: BuscaService, monkeypatch
    ):
        request = BuscaRequest(query="tributário")
        dummy_client = DummyTJDFTClient(None)
        dummy_client.buscar_simples = AsyncMock(side_effect=RuntimeError("boom"))
        monkeypatch.setattr(busca_module, "TJDFTClient", MagicMock(return_value=dummy_client))

        with pytest.raises(BuscaServiceError, match="Erro ao realizar busca"):
            await service.buscar(request)


class TestBuscaPublicMethods:
    @pytest.mark.asyncio
    async def test_buscar_com_filtro_avancado_builds_request_and_delegates(
        self, service: BuscaService, monkeypatch
    ):
        service.buscar = AsyncMock(return_value={"ok": True})

        resultado = await service.buscar_com_filtro_avancado(
            query="tributário",
            relator="desembargador-faustolo",
            classe="APC",
            pagina=2,
            tamanho=10,
        )

        assert resultado == {"ok": True}
        request_arg = service.buscar.await_args.args[0]
        assert isinstance(request_arg, BuscaRequest)
        assert request_arg.filtros == {
            "relator": "desembargador-faustolo",
            "classe": "APC",
        }

    @pytest.mark.asyncio
    async def test_recuperar_busca_returns_none_for_invalid_uuid(self, service: BuscaService):
        resultado = await service.recuperar_busca("not-a-uuid")

        assert resultado is None

    @pytest.mark.asyncio
    async def test_recuperar_busca_returns_serialized_consulta(
        self, service: BuscaService, consulta_stub
    ):
        service.consulta_repo.get_by_id = AsyncMock(return_value=consulta_stub)

        resultado = await service.recuperar_busca(str(uuid4()))

        assert resultado["query"] == consulta_stub.query
        assert resultado["criado_em"] == consulta_stub.criado_em.isoformat()

    @pytest.mark.asyncio
    async def test_recuperar_busca_returns_none_when_not_found(self, service: BuscaService):
        service.consulta_repo.get_by_id = AsyncMock(return_value=None)

        resultado = await service.recuperar_busca(str(uuid4()))

        assert resultado is None

    @pytest.mark.asyncio
    async def test_buscar_todas_paginas_aggregates_and_persists(
        self, service: BuscaService, monkeypatch
    ):
        all_results = [
            {
                "uuid_tjdft": "u1",
                "processo": "0701",
                "ementa": "Ementa 1",
                "relator": "Relator 1",
                "data_julgamento": "2024-01-10",
                "orgao_julgador": "1ª Câmara Cível",
                "classe": "Apelação",
            },
            {
                "uuid_tjdft": "u2",
                "processo": "0702",
                "ementa": "Ementa 2",
                "relator": "Relator 2",
                "data_julgamento": "2024-02-10",
                "orgao_julgador": "2ª Câmara Cível",
                "classe": "Agravo",
            },
        ]
        DummyTJDFTClient.all_results = all_results
        monkeypatch.setattr(busca_module, "TJDFTClient", DummyTJDFTClient)
        service.consulta_repo.create = AsyncMock()
        service._salvar_decisoes_cache = AsyncMock()

        resultado = await service.buscar_todas_paginas(
            query="tributário",
            max_paginas=3,
            relator="desembargador-faustolo",
        )

        assert resultado["total"] == 2
        assert resultado["paginas_busca"] == 3
        assert len(resultado["resultados"]) == 2
        service.consulta_repo.create.assert_awaited_once()
        service._salvar_decisoes_cache.assert_awaited_once_with(all_results)

    @pytest.mark.asyncio
    async def test_buscar_todas_paginas_wraps_errors(
        self, service: BuscaService, monkeypatch
    ):
        dummy_client = DummyTJDFTClient(None)
        dummy_client.buscar_todas_paginas = AsyncMock(side_effect=RuntimeError("boom"))
        monkeypatch.setattr(busca_module, "TJDFTClient", MagicMock(return_value=dummy_client))

        with pytest.raises(BuscaServiceError, match="Erro ao buscar todas as páginas"):
            await service.buscar_todas_paginas(query="tributário")

    @pytest.mark.asyncio
    async def test_buscar_similares_returns_empty_when_reference_missing(self, service: BuscaService):
        service.decisao_repo.get_by_uuid = AsyncMock(return_value=None)

        resultado = await service.buscar_similares("uuid-missing")

        assert resultado == []

    @pytest.mark.asyncio
    async def test_buscar_similares_returns_empty_when_no_filters(self, service: BuscaService):
        service.decisao_repo.get_by_uuid = AsyncMock(
            return_value=SimpleNamespace(
                uuid_tjdft="u1",
                relator=None,
                classe=None,
                orgao_julgador=None,
            )
        )

        resultado = await service.buscar_similares("u1")

        assert resultado == []

    @pytest.mark.asyncio
    async def test_buscar_similares_filters_out_reference_decision(self, service: BuscaService):
        service.decisao_repo.get_by_uuid = AsyncMock(
            return_value=SimpleNamespace(
                uuid_tjdft="u1",
                relator="Relator 1",
                classe="Apelação",
                orgao_julgador="1ª Câmara Cível",
            )
        )
        service.decisao_repo.list = AsyncMock(
            return_value=[
                Decisao(
                    uuid_tjdft="u1",
                    processo="0701",
                    relator="Relator 1",
                    classe="Apelação",
                    orgao_julgador="1ª Câmara Cível",
                ),
                Decisao(
                    uuid_tjdft="u2",
                    processo="0702",
                    relator="Relator 1",
                    classe="Apelação",
                    orgao_julgador="1ª Câmara Cível",
                ),
            ]
        )

        resultado = await service.buscar_similares("u1", limite=5)

        assert [item["uuid_tjdft"] for item in resultado] == ["u2"]

    @pytest.mark.asyncio
    async def test_historico_consultas_returns_empty_for_invalid_user(self, service: BuscaService):
        resultado = await service.historico_consultas(usuario_id="invalid-uuid")

        assert resultado == []

    @pytest.mark.asyncio
    async def test_historico_consultas_serializes_repository_results(
        self, service: BuscaService, consulta_stub
    ):
        service.consulta_repo.list = AsyncMock(return_value=[consulta_stub])

        resultado = await service.historico_consultas(usuario_id=str(uuid4()), limite=10)

        assert len(resultado) == 1
        assert resultado[0]["id"] == str(consulta_stub.id)
        assert resultado[0]["criado_em"] == consulta_stub.criado_em.isoformat()


class TestBuscaHelpers:
    @pytest.mark.asyncio
    async def test_salvar_decisoes_cache_parses_dates_and_skips_invalid_items(
        self, service: BuscaService
    ):
        service.decisao_repo.create_or_update = AsyncMock(side_effect=[None, RuntimeError("boom")])

        await service._salvar_decisoes_cache(
            [
                {
                    "uuid_tjdft": "u1",
                    "processo": "0701",
                    "data_julgamento": "2024-01-10",
                    "data_publicacao": "2024-01-20",
                },
                {
                    "uuid_tjdft": "u2",
                    "processo": "0702",
                    "data_julgamento": "data-invalida",
                    "data_publicacao": None,
                },
                {
                    "processo": "sem-uuid",
                },
            ]
        )

        first_call = service.decisao_repo.create_or_update.await_args_list[0].kwargs
        second_call = service.decisao_repo.create_or_update.await_args_list[1].kwargs

        assert first_call["data_julgamento"].isoformat() == "2024-01-10"
        assert first_call["data_publicacao"].isoformat() == "2024-01-20"
        assert second_call["data_julgamento"] is None

    @pytest.mark.asyncio
    async def test_validar_filtros_returns_input_when_valid(self, service: BuscaService, monkeypatch):
        monkeypatch.setattr(busca_module, "validate_relator", lambda value: True)
        monkeypatch.setattr(busca_module, "validate_classe", lambda value: True)
        monkeypatch.setattr(busca_module, "validate_orgao", lambda value: True)
        filtros = {
            "relator": "desembargador-faustolo",
            "classe": "APC",
            "orgao_julgador": "6CC",
        }

        resultado = await service._validar_filtros(filtros)

        assert resultado == filtros

    @pytest.mark.asyncio
    async def test_validar_filtros_aggregates_errors(self, service: BuscaService, monkeypatch):
        monkeypatch.setattr(busca_module, "validate_relator", lambda value: False)
        monkeypatch.setattr(busca_module, "validate_classe", lambda value: False)
        monkeypatch.setattr(busca_module, "validate_orgao", lambda value: False)

        with pytest.raises(FiltroInvalidoError) as exc:
            await service._validar_filtros(
                {
                    "relator": "x",
                    "classe": "y",
                    "orgao_julgador": "z",
                }
            )

        mensagem = str(exc.value)
        assert "Relator inválido" in mensagem
        assert "Classe inválida" in mensagem
        assert "Órgão julgador inválido" in mensagem

    def test_build_filtros_dict_removes_none_and_empty(self, service: BuscaService):
        resultado = service._build_filtros_dict(
            relator="r1",
            classe="",
            orgao_julgador=None,
            pagina=1,
        )

        assert resultado == {"relator": "r1", "pagina": 1}

    def test_prepare_api_params_maps_only_supported_fields(self, service: BuscaService):
        resultado = service._prepare_api_params(
            {
                "relator": "r1",
                "classe": "APC",
                "orgao_julgador": "6CC",
                "data_inicio": "2024-01-01",
                "data_fim": "2024-01-31",
                "extra": "ignorar",
            }
        )

        assert resultado == {
            "relator": "r1",
            "classe": "APC",
            "orgao_julgador": "6CC",
            "data_inicio": "2024-01-01",
            "data_fim": "2024-01-31",
        }

    @pytest.mark.asyncio
    async def test_paginar_resultados_handles_zero_tamanho(self, service: BuscaService):
        resultado = await service._paginar_resultados(["a", "b", "c"], pagina=1, tamanho=0)

        assert resultado == {
            "resultados": [],
            "total": 3,
            "pagina": 1,
            "tamanho": 0,
            "total_paginas": 1,
        }

    @pytest.mark.asyncio
    async def test_paginar_resultados_returns_expected_slice(self, service: BuscaService):
        resultado = await service._paginar_resultados(
            ["a", "b", "c", "d", "e"],
            pagina=2,
            tamanho=2,
        )

        assert resultado["resultados"] == ["c", "d"]
        assert resultado["total_paginas"] == 3
