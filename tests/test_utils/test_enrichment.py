"""Testes para utilitários de enriquecimento de dados de jurisprudência."""

import pytest

from app.utils.enrichment import (
    DensidadeCategoria,
    InstanciaTipo,
    calcular_densidade,
    calcular_instancia,
    extrair_marcadores_relevancia,
)

pytestmark = pytest.mark.unit


class TestCalcularDensidade:
    """Testes para função calcular_densidade."""

    def test_escasso(self):
        """Testa categoria escasso (total < 20)."""
        resultado = calcular_densidade(10)
        assert resultado["categoria"] == DensidadeCategoria.ESCASSO.value
        assert resultado["total"] == 10
        assert "Poucos precedentes" in resultado["alerta"]

    def test_moderado(self):
        """Testa categoria moderado (20 <= total < 500)."""
        resultado = calcular_densidade(100)
        assert resultado["categoria"] == DensidadeCategoria.MODERADO.value
        assert resultado["total"] == 100
        assert "moderada" in resultado["alerta"].lower()

    def test_consolidado(self):
        """Testa categoria consolidado (500 <= total < 5000)."""
        resultado = calcular_densidade(1000)
        assert resultado["categoria"] == DensidadeCategoria.CONSOLIDADO.value
        assert resultado["total"] == 1000
        assert "consolidado" in resultado["alerta"].lower()

    def test_massivo(self):
        """Testa categoria massivo (total >= 5000)."""
        resultado = calcular_densidade(10000)
        assert resultado["categoria"] == DensidadeCategoria.MASSIVO.value
        assert resultado["total"] == 10000
        assert "massiva" in resultado["alerta"].lower()

    def test_limite_inferior_escasso(self):
        """Testa limite inferior (total = 0)."""
        resultado = calcular_densidade(0)
        assert resultado["categoria"] == DensidadeCategoria.ESCASSO.value

    def test_limite_superior_escasso(self):
        """Testa limite superior de escasso (total = 19)."""
        resultado = calcular_densidade(19)
        assert resultado["categoria"] == DensidadeCategoria.ESCASSO.value

    def test_limite_inferior_moderado(self):
        """Testa limite inferior de moderado (total = 20)."""
        resultado = calcular_densidade(20)
        assert resultado["categoria"] == DensidadeCategoria.MODERADO.value

    def test_limite_superior_moderado(self):
        """Testa limite superior de moderado (total = 499)."""
        resultado = calcular_densidade(499)
        assert resultado["categoria"] == DensidadeCategoria.MODERADO.value

    def test_limite_inferior_consolidado(self):
        """Testa limite inferior de consolidado (total = 500)."""
        resultado = calcular_densidade(500)
        assert resultado["categoria"] == DensidadeCategoria.CONSOLIDADO.value

    def test_limite_superior_consolidado(self):
        """Testa limite superior de consolidado (total = 4999)."""
        resultado = calcular_densidade(4999)
        assert resultado["categoria"] == DensidadeCategoria.CONSOLIDADO.value

    def test_limite_inferior_massivo(self):
        """Testa limite inferior de massivo (total = 5000)."""
        resultado = calcular_densidade(5000)
        assert resultado["categoria"] == DensidadeCategoria.MASSIVO.value


class TestCalcularInstancia:
    """Testes para função calcular_instancia."""

    def test_juizado_especial_turma_recursal_true(self):
        """Testa detecção de juizado especial quando turma_recursal=True."""
        resultado = calcular_instancia(turma_recursal=True)
        assert resultado == InstanciaTipo.JUIZADO_ESPECIAL.value

    def test_juizado_especial_subbase_tr(self):
        """Testa detecção de juizado especial quando subbase='acordaos-tr'."""
        resultado = calcular_instancia(subbase="acordaos-tr")
        assert resultado == InstanciaTipo.JUIZADO_ESPECIAL.value

    def test_tjdft_2a_instancia_turma_recursal_false(self):
        """Testa detecção de 2a instância quando turma_recursal=False."""
        resultado = calcular_instancia(turma_recursal=False, subbase="acordaos")
        assert resultado == InstanciaTipo.TJDFT_2A_INSTANCIA.value

    def test_tjdft_2a_instancia_subbase_outra(self):
        """Testa detecção de 2a instância com subbase diferente de 'acordaos-tr'."""
        resultado = calcular_instancia(subbase="acordaos")
        assert resultado == InstanciaTipo.TJDFT_2A_INSTANCIA.value

    def test_retorna_none_sem_parametros(self):
        """Testa que retorna None quando não há parâmetros suficientes."""
        resultado = calcular_instancia()
        assert resultado is None

    def test_prioridade_turma_recursal_true(self):
        """Testa que turma_recursal=True tem prioridade sobre subbase."""
        resultado = calcular_instancia(turma_recursal=True, subbase="acordaos")
        assert resultado == InstanciaTipo.JUIZADO_ESPECIAL.value


class TestExtrairMarcadoresRelevancia:
    """Testes para extração de marcadores de relevância."""

    def test_retorna_dict_vazio_quando_marcadores_ausentes(self):
        assert extrair_marcadores_relevancia(None) == {}
        assert extrair_marcadores_relevancia({}) == {}

    def test_extrai_primeiro_item_de_lista_e_strings(self):
        resultado = extrair_marcadores_relevancia(
            {
                "trecho": ["texto destacado", "outro"],
                "palavra": "tributário",
            }
        )

        assert resultado == {
            "trecho": "texto destacado",
            "palavra": "tributário",
        }

    def test_ignora_listas_vazias_e_tipos_nao_suportados(self):
        resultado = extrair_marcadores_relevancia(
            {
                "lista_vazia": [],
                "numero": 123,
                "objeto": {"valor": "x"},
            }
        )

        assert resultado == {}
