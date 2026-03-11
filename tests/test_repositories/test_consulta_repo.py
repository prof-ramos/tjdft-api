import uuid
from datetime import date, datetime

import pytest

from app.models.consulta import Consulta
from app.repositories.consulta_repository import ConsultaRepository

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_get_by_id_returns_consulta(db_session):
    repo = ConsultaRepository(db_session)
    usuario_id = uuid.uuid4()
    consulta = await repo.create(
        query="tributário",
        filtros={"classe": "APC"},
        resultados=3,
        usuario_id=usuario_id,
    )

    encontrada = await repo.get_by_id(uuid.UUID(consulta.id))

    assert encontrada is not None
    assert encontrada.id == consulta.id
    assert encontrada.usuario_id == str(usuario_id)


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing(db_session):
    repo = ConsultaRepository(db_session)

    encontrada = await repo.get_by_id(uuid.uuid4())

    assert encontrada is None


@pytest.mark.asyncio
async def test_list_filters_by_usuario_period_and_pagination(db_session):
    repo = ConsultaRepository(db_session)
    usuario_alvo = str(uuid.uuid4())
    outro_usuario = str(uuid.uuid4())

    db_session.add_all(
        [
            Consulta(
                id=str(uuid.uuid4()),
                query="primeira",
                filtros={"classe": "APC"},
                resultados_encontrados=1,
                pagina=1,
                tamanho=20,
                usuario_id=usuario_alvo,
                criado_em=datetime(2024, 1, 10, 9, 0, 0),
            ),
            Consulta(
                id=str(uuid.uuid4()),
                query="segunda",
                filtros={"classe": "AGR"},
                resultados_encontrados=2,
                pagina=1,
                tamanho=20,
                usuario_id=usuario_alvo,
                criado_em=datetime(2024, 1, 15, 18, 30, 0),
            ),
            Consulta(
                id=str(uuid.uuid4()),
                query="fora-do-usuario",
                filtros=None,
                resultados_encontrados=3,
                pagina=1,
                tamanho=20,
                usuario_id=outro_usuario,
                criado_em=datetime(2024, 1, 12, 12, 0, 0),
            ),
            Consulta(
                id=str(uuid.uuid4()),
                query="fora-do-periodo",
                filtros=None,
                resultados_encontrados=4,
                pagina=1,
                tamanho=20,
                usuario_id=usuario_alvo,
                criado_em=datetime(2024, 2, 1, 8, 0, 0),
            ),
        ]
    )
    await db_session.flush()

    consultas = await repo.list(
        usuario_id=uuid.UUID(usuario_alvo),
        data_inicio=date(2024, 1, 1),
        data_fim=date(2024, 1, 31),
        offset=0,
        limit=1,
    )

    assert len(consultas) == 1
    assert consultas[0].query == "segunda"


@pytest.mark.asyncio
async def test_list_validates_offset_and_limit(db_session):
    repo = ConsultaRepository(db_session)

    with pytest.raises(ValueError, match="offset must be >= 0"):
        await repo.list(offset=-1)

    with pytest.raises(ValueError, match="limit must be > 0"):
        await repo.list(limit=0)


@pytest.mark.asyncio
async def test_delete_returns_true_when_row_removed(db_session):
    repo = ConsultaRepository(db_session)
    consulta = await repo.create(
        query="tributário",
        filtros=None,
        resultados=1,
    )

    removido = await repo.delete(uuid.UUID(consulta.id))
    encontrada = await repo.get_by_id(uuid.UUID(consulta.id))

    assert removido is True
    assert encontrada is None


@pytest.mark.asyncio
async def test_delete_returns_false_when_row_missing(db_session):
    repo = ConsultaRepository(db_session)

    removido = await repo.delete(uuid.uuid4())

    assert removido is False
