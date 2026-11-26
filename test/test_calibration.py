# coding=utf-8
"""Testes unitários para o núcleo puro da calibração (calibration.py)."""

import ast
import math
import unittest

from desire_lines.traffic import calibration
from desire_lines.traffic.calibration import (
    GEH_LIMITES,
    DNIT_MIN_A,
    DNIT_MIN_AB,
    geh,
    faixa_geh,
    volume_no_posto,
    resumo,
)


class TestGeh(unittest.TestCase):
    """Testes da função geh."""

    def test_geh_valores_base(self):
        """(a) geh(100, 100) == 0, geh(0, 0) == 0, e geh(150, 100) ≈ sqrt(2·2500/250) = 4.4721."""
        self.assertEqual(geh(100, 100), 0.0)
        self.assertEqual(geh(0, 0), 0.0)

        # 2 * (150 - 100)^2 / (150 + 100) = 2 * 2500 / 250 = 5000 / 250 = 20
        # sqrt(20) ≈ 4.47213595...
        esperado = math.sqrt(2.0 * 2500.0 / 250.0)
        val = geh(150, 100)
        self.assertAlmostEqual(val, esperado, places=6)
        self.assertAlmostEqual(val, 4.4721, places=4)

    def test_geh_negativo_levanta_value_error(self):
        """(b) negativo levanta ValueError."""
        with self.assertRaises(ValueError):
            geh(-1, 100)
        with self.assertRaises(ValueError):
            geh(100, -1)
        with self.assertRaises(ValueError):
            geh(-5, -10)


class TestFaixaGeh(unittest.TestCase):
    """Testes da classificação de faixas de GEH."""

    def test_bordas_das_faixas(self):
        """(c) bordas das faixas: 4.999→A, 5→B, 9.999→B, 10→C, 12→D."""
        self.assertEqual(faixa_geh(0.0), 'A')
        self.assertEqual(faixa_geh(4.999), 'A')
        self.assertEqual(faixa_geh(5.0), 'B')
        self.assertEqual(faixa_geh(5), 'B')
        self.assertEqual(faixa_geh(9.999), 'B')
        self.assertEqual(faixa_geh(10.0), 'C')
        self.assertEqual(faixa_geh(10), 'C')
        self.assertEqual(faixa_geh(11.999), 'C')
        self.assertEqual(faixa_geh(12.0), 'D')
        self.assertEqual(faixa_geh(12), 'D')
        self.assertEqual(faixa_geh(25.0), 'D')

    def test_faixa_geh_negativo_levanta_value_error(self):
        """Valores negativos levantam ValueError."""
        with self.assertRaises(ValueError):
            faixa_geh(-0.01)


class TestVolumeNoPosto(unittest.TestCase):
    """Testes da agregação de volume no posto."""

    def test_volume_no_posto_soma_fw_bw_e_descarta_outros(self):
        """(d) volume_no_posto soma fw+bw do mesmo link_id na menor distância e ignora
        outro link_id a 0,5 m de diferença, mas de id diferente, e um candidato
        do mesmo id a 5 m."""
        candidatos = [
            (10.0, 'link_A', 300.0),   # menor distância (10.0 m), fw
            (10.2, 'link_A', 250.0),   # mesmo link_id a 0.2 m (<= 1.0 m) da menor distância, bw
            (10.5, 'link_B', 800.0),   # outro link_id a 0.5 m de diferença (deve ser ignorado)
            (15.0, 'link_A', 400.0),   # mesmo link_id a 5.0 m de diferença (> 1.0 m, deve ser ignorado)
        ]
        # Soma esperada: 300.0 + 250.0 = 550.0
        self.assertEqual(volume_no_posto(candidatos, tol_m=1.0), 550.0)

    def test_volume_no_posto_vazio(self):
        """Lista vazia de candidatos retorna 0.0."""
        self.assertEqual(volume_no_posto([]), 0.0)


class TestResumo(unittest.TestCase):
    """Testes da função resumo."""

    def test_resumo_criterio_dnit(self):
        """(e) resumo com 10 postos (6 A, 3 B, 1 C) dá atende_dnit=False (A+B = 90%),
        e com 6 A + 4 B dá True."""
        # 6 A, 3 B, 1 C -> A = 60%, A+B = 90% (< 95% do DNIT)
        postos_nao_atende = (
            [{'contagem': 100, 'modelado': 102, 'geh': 0.2, 'faixa': 'A'}] * 6
            + [{'contagem': 100, 'modelado': 160, 'geh': 5.2, 'faixa': 'B'}] * 3
            + [{'contagem': 100, 'modelado': 220, 'geh': 10.2, 'faixa': 'C'}] * 1
        )
        res_nao = resumo(postos_nao_atende)
        self.assertEqual(res_nao['n'], 10)
        self.assertEqual(res_nao['por_faixa'], {'A': 6, 'B': 3, 'C': 1, 'D': 0})
        self.assertAlmostEqual(res_nao['pct_a'], 0.60)
        self.assertAlmostEqual(res_nao['pct_ab'], 0.90)
        self.assertFalse(res_nao['atende_dnit'])

        # 6 A, 4 B -> A = 60%, A+B = 100% (>= 95% do DNIT)
        postos_atende = (
            [{'contagem': 100, 'modelado': 102, 'geh': 0.2, 'faixa': 'A'}] * 6
            + [{'contagem': 100, 'modelado': 160, 'geh': 5.2, 'faixa': 'B'}] * 4
        )
        res_sim = resumo(postos_atende)
        self.assertEqual(res_sim['n'], 10)
        self.assertEqual(res_sim['por_faixa'], {'A': 6, 'B': 4, 'C': 0, 'D': 0})
        self.assertAlmostEqual(res_sim['pct_a'], 0.60)
        self.assertAlmostEqual(res_sim['pct_ab'], 1.00)
        self.assertTrue(res_sim['atende_dnit'])

    def test_resumo_sem_link_fora_de_n(self):
        """(f) sem_link não entra em n. Com n == 0 devolve percentuais 0.0,
        atende_dnit=False e rmse_pct=None."""
        postos = [
            {'contagem': 100, 'modelado': 100, 'geh': 0.0, 'faixa': 'A'},
            {'contagem': 200, 'modelado': 200, 'geh': 0.0, 'faixa': 'A'},
            {'contagem': 300, 'modelado': 0, 'geh': None, 'faixa': 'sem_link'},
            {'contagem': 400, 'modelado': 0, 'geh': None, 'faixa': 'sem_link'},
        ]
        res = resumo(postos)
        self.assertEqual(res['n'], 2)
        self.assertEqual(res['n_sem_link'], 2)
        self.assertEqual(res['por_faixa']['A'], 2)
        self.assertAlmostEqual(res['pct_a'], 1.0)
        self.assertAlmostEqual(res['pct_ab'], 1.0)
        self.assertTrue(res['atende_dnit'])

        # Todos sem_link -> n == 0
        postos_apenas_sem_link = [
            {'contagem': 300, 'modelado': 0, 'geh': None, 'faixa': 'sem_link'},
        ]
        res_vazio = resumo(postos_apenas_sem_link)
        self.assertEqual(res_vazio['n'], 0)
        self.assertEqual(res_vazio['n_sem_link'], 1)
        self.assertEqual(res_vazio['por_faixa'], {'A': 0, 'B': 0, 'C': 0, 'D': 0})
        self.assertEqual(res_vazio['pct_a'], 0.0)
        self.assertEqual(res_vazio['pct_ab'], 0.0)
        self.assertFalse(res_vazio['atende_dnit'])
        self.assertIsNone(res_vazio['rmse_pct'])

        # Lista totalmente vazia
        res_lista_vazia = resumo([])
        self.assertEqual(res_lista_vazia['n'], 0)
        self.assertEqual(res_lista_vazia['n_sem_link'], 0)
        self.assertEqual(res_lista_vazia['pct_a'], 0.0)
        self.assertEqual(res_lista_vazia['pct_ab'], 0.0)
        self.assertFalse(res_lista_vazia['atende_dnit'])
        self.assertIsNone(res_lista_vazia['rmse_pct'])

    def test_resumo_rmse_pct_calculo_a_mao(self):
        """(g) rmse_pct confere com um cálculo à mão."""
        # Posto 1: C = 100, M = 110 -> diff = 10, diff^2 = 100
        # Posto 2: C = 200, M = 180 -> diff = -20, diff^2 = 400
        # n = 2
        # MSE = (100 + 400) / 2 = 250
        # RMSE = sqrt(250) ≈ 15.8113883
        # mean_C = (100 + 200) / 2 = 150
        # %RMSE = 100 * sqrt(250) / 150 ≈ 10.5409255%
        postos = [
            {'contagem': 100.0, 'modelado': 110.0, 'geh': 0.98, 'faixa': 'A'},
            {'contagem': 200.0, 'modelado': 180.0, 'geh': 1.45, 'faixa': 'A'},
        ]
        res = resumo(postos)
        esperado_rmse_pct = 100.0 * math.sqrt(250.0) / 150.0
        self.assertAlmostEqual(res['rmse_pct'], esperado_rmse_pct, places=6)


class TestSemQgis(unittest.TestCase):
    """(h) teste de texto: calibration.py não contém qgis."""

    def test_calibration_nao_contem_qgis(self):
        """Garante que calibration.py não possui menção ou import de qgis."""
        with open(calibration.__file__, 'r', encoding='utf-8') as f:
            conteudo = f.read()

        # Teste de texto bruto
        self.assertNotIn('qgis', conteudo.lower())

        # Teste de AST para importações
        tree = ast.parse(conteudo)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertFalse(alias.name.startswith('qgis'))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.assertFalse(node.module.startswith('qgis'))
