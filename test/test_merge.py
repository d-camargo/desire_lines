# coding=utf-8
"""Testes para o módulo de limpeza e unificação de esquema (merge.py) — D5, D6."""

import ast
import unittest

from desire_lines.traffic import merge
from desire_lines.traffic.merge import (
    limpa_linhas,
    converte_valor,
    costura_extremidades,
)
from desire_lines.traffic.network import node_key


class TestMergeSemQgis(unittest.TestCase):
    """Garante que o módulo merge.py é Python puro e não importa qgis."""

    def test_merge_nao_importa_qgis(self):
        with open(merge.__file__, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertFalse(
                        alias.name.startswith('qgis'),
                        f"Import proibido encontrado em merge.py: {alias.name}",
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.assertFalse(
                        node.module.startswith('qgis'),
                        f"Import from proibido encontrado em merge.py: {node.module}",
                    )


class TestLimpaLinhas(unittest.TestCase):
    """Testes para limpa_linhas (D5)."""

    def test_zero_length_e_1_ponto_saem(self):
        linhas = [
            {'id': 1, 'pts': []},  # 0 pontos
            {'id': 2, 'pts': [(100.0, 200.0)]},  # 1 ponto
            {'id': 3, 'pts': [(10.0, 20.0), (10.0, 20.0)]},  # zero-length (2 pts idênticos)
            {'id': 4, 'pts': [(5.0, 5.0), (5.0, 5.0), (5.0, 5.0)]},  # zero-length (3 pts idênticos)
            {'id': 5, 'pts': [(0.0, 0.0), (10.0, 0.0)]},  # Válida (comprimento = 10m)
        ]

        mantidas, relatorio = limpa_linhas(linhas)

        self.assertEqual(len(mantidas), 1)
        self.assertEqual(mantidas[0]['id'], 5)
        self.assertEqual(relatorio['total'], 5)
        self.assertEqual(relatorio['mantidas'], 1)
        self.assertEqual(relatorio['removidas'], 4)
        self.assertEqual(relatorio['menos_2_pontos'], 2)
        self.assertEqual(relatorio['zero_length'], 2)

    def test_excluir_com_caixa_e_espaco_diferentes_sai(self):
        excluir = {'campo': 'ds_superfi', 'valores': ['PLA']}

        linhas = [
            {'id': 1, 'pts': [(0, 0), (1, 1)], 'ds_superfi': 'PLA'},  # Exata
            {'id': 2, 'pts': [(2, 2), (3, 3)], 'ds_superfi': 'pla'},  # Minúscula
            {'id': 3, 'pts': [(4, 4), (5, 5)], 'ds_superfi': ' PLA '},  # Espaços nas pontas
            {'id': 4, 'pts': [(6, 6), (7, 7)], 'ds_superfi': '  Pla  '},  # Caixa e espaços
            {'id': 5, 'pts': [(8, 8), (9, 9)], 'ds_superfi': 'PAV'},  # Pavimentada (mantém)
            {'id': 6, 'pts': [(10, 10), (11, 11)], 'ds_superfi': None},  # Nulo (mantém)
            {'id': 7, 'pts': [(12, 12), (13, 13)]},  # Sem o campo (mantém)
        ]

        mantidas, relatorio = limpa_linhas(linhas, excluir=excluir)

        ids_mantidos = [l['id'] for l in mantidas]
        self.assertEqual(ids_mantidos, [5, 6, 7])
        self.assertEqual(relatorio['excluir'], 4)

        # Teste com valores compostos e espaços internos (ex.: 'Em Obra')
        excluir_obra = {'campo': 'situacao', 'valores': ['Em Obra']}
        linhas_obra = [
            {'id': 10, 'pts': [(0, 0), (1, 1)], 'situacao': '  em  obra  '},
            {'id': 11, 'pts': [(2, 2), (3, 3)], 'situacao': 'EM OBRA'},
            {'id': 12, 'pts': [(4, 4), (5, 5)], 'situacao': 'Concluida'},
        ]
        mantidas_obra, rel_obra = limpa_linhas(linhas_obra, excluir=excluir_obra)
        self.assertEqual([l['id'] for l in mantidas_obra], [12])
        self.assertEqual(rel_obra['excluir'], 2)

    def test_duplicata_exata_em_sentido_invertido_sai(self):
        linhas = [
            {'id': 1, 'pts': [(0.0, 0.0), (10.0, 10.0), (20.0, 20.0)]},  # Original
            {'id': 2, 'pts': [(20.0, 20.0), (10.0, 10.0), (0.0, 0.0)]},  # Invertida exata -> sai
            {'id': 3, 'pts': [(0.0001, 0.0002), (10.0004, 9.9998), (20.0, 20.0)]},  # Arredonda a 3 casas -> sai
            {'id': 4, 'pts': [(0.0, 0.0), (10.0, 15.0), (20.0, 20.0)]},  # Geometria distinta -> fica
        ]

        mantidas, relatorio = limpa_linhas(linhas)

        ids_mantidos = [l['id'] for l in mantidas]
        self.assertEqual(ids_mantidos, [1, 4])
        self.assertEqual(relatorio['duplicata'], 2)

    def test_relatorio_conta_cada_motivo(self):
        excluir = {'campo': 'situacao', 'valores': ['PLA']}
        linhas = [
            {'id': 1, 'pts': []},  # menos_2_pontos
            {'id': 2, 'pts': [(1, 1)]},  # menos_2_pontos
            {'id': 3, 'pts': [(0, 0), (0, 0)]},  # zero_length
            {'id': 4, 'pts': [(10, 10), (20, 20)], 'situacao': 'PLA'},  # excluir
            {'id': 5, 'pts': [(30, 30), (40, 40)]},  # mantida 1
            {'id': 6, 'pts': [(30, 30), (40, 40)]},  # duplicata (mesmo sentido)
            {'id': 7, 'pts': [(40, 40), (30, 30)]},  # duplicata (sentido invertido)
            {'id': 8, 'pts': [(50, 50), (60, 60)]},  # mantida 2
        ]

        mantidas, relatorio = limpa_linhas(linhas, excluir=excluir)

        self.assertEqual(relatorio['total'], 8)
        self.assertEqual(relatorio['mantidas'], 2)
        self.assertEqual(relatorio['removidas'], 6)

        # Motivos individuais
        self.assertEqual(relatorio['menos_2_pontos'], 2)
        self.assertEqual(relatorio['zero_length'], 1)
        self.assertEqual(relatorio['excluir'], 1)
        self.assertEqual(relatorio['duplicata'], 2)

        self.assertEqual([l['id'] for l in mantidas], [5, 8])


class TestConverteValor(unittest.TestCase):
    """Testes para converte_valor (D6)."""

    def test_converte_valor(self):
        # Nulo permanece Nulo
        self.assertIsNone(converte_valor(None, 'String'))
        self.assertIsNone(converte_valor(None, 'Integer'))
        self.assertIsNone(converte_valor(None, 'Real'))

        # Conversão para String
        self.assertEqual(converte_valor(123, 'String'), '123')
        self.assertEqual(converte_valor(45.67, 'String'), '45.67')

        # Conversão numérica
        self.assertEqual(converte_valor('10', 'Integer'), 10)
        self.assertEqual(converte_valor('10.5', 'Real'), 10.5)


class TestCosturaExtremidades(unittest.TestCase):
    """Testes para costura_extremidades (D4)."""

    def test_a_ponta_a_10m_de_outra_ponta_vai_para_mesmo_no(self):
        """(a) Ponta a 10 m de outra ponta -> mesmo nó (snap nó-nó)."""
        l1 = {'id': 1, 'pts': [(0.0, 0.0), (50.0, 0.0)]}
        l2 = {'id': 2, 'pts': [(60.0, 0.0), (100.0, 0.0)]}

        saida, rel = costura_extremidades([l1, l2], tol_m=30.0, precision=3)

        self.assertEqual(len(saida), 2)
        self.assertEqual(rel['no_no'], 1)
        self.assertEqual(rel['t'], 0)

        no1 = node_key(saida[0]['pts'][-1], precision=3)
        no2 = node_key(saida[1]['pts'][0], precision=3)
        self.assertEqual(no1, no2)

    def test_b_ponta_a_10m_do_meio_de_outra_linha_vira_2_linhas_e_3_compartilham_no(self):
        """(b) Ponta a 10 m do meio de outra linha -> a outra vira 2 linhas e as 3 compartilham o nó."""
        l1 = {'id': 1, 'pts': [(0.0, 0.0), (100.0, 0.0)]}
        l2 = {'id': 2, 'pts': [(50.0, 50.0), (50.0, 10.0)]}

        saida, rel = costura_extremidades([l1, l2], tol_m=30.0, precision=3)

        # l1 foi dividida em 2, l2 foi mantida com a ponta ajustada -> 3 feições
        self.assertEqual(len(saida), 3)
        self.assertEqual(rel['t'], 1)
        self.assertEqual(rel['no_no'], 0)

        no_t = node_key((50.0, 0.0), precision=3)
        self.assertEqual(node_key(saida[0]['pts'][-1], precision=3), no_t)
        self.assertEqual(node_key(saida[1]['pts'][0], precision=3), no_t)
        self.assertEqual(node_key(saida[2]['pts'][-1], precision=3), no_t)

    def test_c_ponta_a_40m_intocada(self):
        """(c) Ponta a 40 m -> intocada (fora da tolerância de 30 m)."""
        l1 = {'id': 1, 'pts': [(0.0, 0.0), (100.0, 0.0)]}
        l2 = {'id': 2, 'pts': [(50.0, 50.0), (50.0, 40.0)]}

        saida, rel = costura_extremidades([l1, l2], tol_m=30.0, precision=3)

        self.assertEqual(len(saida), 2)
        self.assertEqual(saida[0]['pts'], [(0.0, 0.0), (100.0, 0.0)])
        self.assertEqual(saida[1]['pts'], [(50.0, 50.0), (50.0, 40.0)])
        self.assertEqual(rel['no_no'], 0)
        self.assertEqual(rel['t'], 0)

    def test_d_duas_linhas_que_se_cruzam_sem_ponta_perto_nenhuma_divisao(self):
        """(d) Duas linhas que se cruzam sem ponta perto -> nenhuma divisão."""
        # Cruzam em (50, 50), mas pontas estão a 50 m do cruzamento (> 30 m)
        l1 = {'id': 1, 'pts': [(0.0, 50.0), (100.0, 50.0)]}
        l2 = {'id': 2, 'pts': [(50.0, 0.0), (50.0, 100.0)]}

        saida, rel = costura_extremidades([l1, l2], tol_m=30.0, precision=3)

        self.assertEqual(len(saida), 2)
        self.assertEqual(saida[0]['pts'], [(0.0, 50.0), (100.0, 50.0)])
        self.assertEqual(saida[1]['pts'], [(50.0, 0.0), (50.0, 100.0)])
        self.assertEqual(rel['no_no'], 0)
        self.assertEqual(rel['t'], 0)

    def test_e_ponta_ja_conectada_nao_se_move(self):
        """(e) Ponta já conectada não se move."""
        # l1 e l2 já se conectam em (50.0, 0.0)
        l1 = {'id': 1, 'pts': [(0.0, 0.0), (50.0, 0.0)]}
        l2 = {'id': 2, 'pts': [(50.0, 0.0), (100.0, 0.0)]}
        # l3 chega com ponta solta em (50.0, 10.0), a 10 m do nó conectado
        l3 = {'id': 3, 'pts': [(50.0, 50.0), (50.0, 10.0)]}

        saida, rel = costura_extremidades([l1, l2, l3], tol_m=30.0, precision=3)

        self.assertEqual(len(saida), 3)
        # O nó conectado em (50.0, 0.0) permanece inalterado em l1 e l2
        self.assertEqual(saida[0]['pts'][-1], (50.0, 0.0))
        self.assertEqual(saida[1]['pts'][0], (50.0, 0.0))
        # A ponta solta de l3 vai para o nó já conectado
        self.assertEqual(saida[2]['pts'][-1], (50.0, 0.0))
        self.assertEqual(rel['no_no'], 1)
        self.assertEqual(rel['t'], 0)

    def test_f_atributos_da_linha_dividida_sao_copiados_para_os_pedacos(self):
        """(f) Atributos da linha dividida são copiados para os pedaços."""
        l1 = {
            'id': 42,
            'rodovia': 'BR-101',
            'jurisdicao': 'Federal',
            'faixas': 2,
            'pts': [(0.0, 0.0), (100.0, 0.0)],
        }
        l2 = {'id': 100, 'nome': 'Acesso', 'pts': [(50.0, 50.0), (50.0, 10.0)]}

        saida, rel = costura_extremidades([l1, l2], tol_m=30.0, precision=3)

        self.assertEqual(len(saida), 3)
        pedaco1, pedaco2, acesso = saida[0], saida[1], saida[2]

        for p in (pedaco1, pedaco2):
            self.assertEqual(p['id'], 42)
            self.assertEqual(p['rodovia'], 'BR-101')
            self.assertEqual(p['jurisdicao'], 'Federal')
            self.assertEqual(p['faixas'], 2)

        self.assertEqual(acesso['id'], 100)
        self.assertEqual(acesso['nome'], 'Acesso')

    def test_g_relatorio_conta_no_no_e_t(self):
        """(g) Relatório conta nó-nó e T."""
        # Linha para junção em T
        l1 = {'id': 1, 'pts': [(0.0, 0.0), (100.0, 0.0)]}
        l2 = {'id': 2, 'pts': [(50.0, 50.0), (50.0, 10.0)]}
        # Duas linhas para junção nó-nó
        l3 = {'id': 3, 'pts': [(200.0, 0.0), (250.0, 0.0)]}
        l4 = {'id': 4, 'pts': [(260.0, 0.0), (300.0, 0.0)]}

        saida, rel = costura_extremidades([l1, l2, l3, l4], tol_m=30.0, precision=3)

        self.assertEqual(rel['no_no'], 1)
        self.assertEqual(rel['t'], 1)
        self.assertEqual(rel['total'], 5)
        self.assertEqual(rel['costuradas'], 2)


if __name__ == '__main__':
    unittest.main()
