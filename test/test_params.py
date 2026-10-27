# coding=utf-8
"""Testes unitários para o módulo de parâmetros (params.py)."""

import unittest
from desire_lines.traffic.params import PARAMS, resolve


class TestParamsCatalog(unittest.TestCase):
    """Testa a integridade do catálogo declarativo PARAMS."""

    def test_catalog_structure(self):
        """Verifica se todo item de PARAMS possui default e unidade."""
        self.assertIn('urbano', PARAMS)
        self.assertEqual(PARAMS['urbano']['default'], False)

        for param_id, spec in PARAMS.items():
            self.assertIn('default', spec, f"Parâmetro {param_id} não possui 'default'")
            self.assertIn('unidade', spec, f"Parâmetro {param_id} não possui 'unidade'")
            self.assertIn('rotulo', spec, f"Parâmetro {param_id} não possui 'rotulo'")
            self.assertIn('tipo', spec, f"Parâmetro {param_id} não possui 'tipo'")
            self.assertIn('campos_candidatos', spec, f"Parâmetro {param_id} não possui 'campos_candidatos'")
            self.assertIsInstance(spec['unidade'], str)


class TestParamsResolve(unittest.TestCase):
    """Testa a resolução de parâmetros e origens ('padrao', 'oficial', 'usuario')."""

    def test_resolve_padrao(self):
        """Quando nem a feição nem overrides possuem dados, deve usar 'padrao'."""
        valores, origens = resolve(feature={}, overrides={})
        for param_id, spec in PARAMS.items():
            self.assertEqual(origens[param_id], 'padrao')
            self.assertEqual(valores[param_id], spec['default'])

    def test_resolve_oficial(self):
        """Quando a feição traz atributos oficiais, a origem deve ser 'oficial'."""
        feature = {
            'travessia_urbana': True,
            'pista': 'duplicada',
            'faixas': 2,
            'vel_livre': 110.0,
        }
        valores, origens = resolve(feature=feature, overrides={})

        self.assertEqual(origens['urbano'], 'oficial')
        self.assertEqual(valores['urbano'], True)

        self.assertEqual(origens['lanes'], 'oficial')
        self.assertEqual(valores['lanes'], 2)

        self.assertEqual(origens['vel_livre'], 'oficial')
        self.assertEqual(valores['vel_livre'], 110.0)

        # Outros parâmetros não informados continuam como 'padrao'
        self.assertEqual(origens['largura_faixa'], 'padrao')
        self.assertEqual(valores['largura_faixa'], 3.5)

    def test_resolve_usuario(self):
        """Overrides do usuário devem ter precedência e indicar origem 'usuario'."""
        feature = {
            'travessia_urbana': False,
            'vel_livre': 80.0,
        }
        overrides = {
            'urbano': True,
            'vel_livre': 120.0,
        }
        valores, origens = resolve(feature=feature, overrides=overrides)

        self.assertEqual(origens['urbano'], 'usuario')
        self.assertEqual(valores['urbano'], True)

        self.assertEqual(origens['vel_livre'], 'usuario')
        self.assertEqual(valores['vel_livre'], 120.0)

    def test_resolve_capacidade_tempo_livre_mao_unica_candidatos(self):
        """Testa resolução de candidatos para capacidade, tempo_livre e mao_unica (D1)."""
        for cand in ['capacidade', 'capacity', 'cap', 'capacidade_vph']:
            val, orig = resolve(feature={cand: 2200.0})
            self.assertEqual(val['capacidade'], 2200.0)
            self.assertEqual(orig['capacidade'], 'oficial')

        for cand in ['tempo_livre', 'free_flow_time', 'fft', 't0']:
            val, orig = resolve(feature={cand: 4.5})
            self.assertEqual(val['tempo_livre'], 4.5)
            self.assertEqual(orig['tempo_livre'], 'oficial')

        for cand in ['mao_unica', 'oneway', 'one_way', 'sentido_unico']:
            val, orig = resolve(feature={cand: 1})
            self.assertTrue(val['mao_unica'])
            self.assertEqual(orig['mao_unica'], 'oficial')

    def test_resolve_defaults_sentinelas(self):
        """Sem atributos, capacidade e tempo_livre devem ser 0.0 e mao_unica False (D1)."""
        val, orig = resolve(feature={})
        self.assertEqual(val['capacidade'], 0.0)
        self.assertEqual(orig['capacidade'], 'padrao')
        self.assertEqual(val['tempo_livre'], 0.0)
        self.assertEqual(orig['tempo_livre'], 'padrao')
        self.assertEqual(val['mao_unica'], False)
        self.assertEqual(orig['mao_unica'], 'padrao')

    def test_resolve_field_map_campo_fora_dos_candidatos(self):
        """Campo mapeado fora dos candidatos vira valor 'oficial' (D2)."""
        self.assertNotIn('cap_x', PARAMS['capacidade']['campos_candidatos'])
        val, orig = resolve(feature={'cap_x': 1800.0},
                            field_map={'capacidade': 'cap_x'})
        self.assertEqual(val['capacidade'], 1800.0)
        self.assertEqual(orig['capacidade'], 'oficial')
        # Sem field_map o campo é ignorado (retrocompatível)
        val, orig = resolve(feature={'cap_x': 1800.0})
        self.assertEqual(orig['capacidade'], 'padrao')

    def test_resolve_field_map_null_cai_para_padrao(self):
        """NULL no campo mapeado cai para candidatos → padrão (D2)."""
        val, orig = resolve(feature={'cap_x': None},
                            field_map={'capacidade': 'cap_x'})
        self.assertEqual(val['capacidade'], PARAMS['capacidade']['default'])
        self.assertEqual(orig['capacidade'], 'padrao')


if __name__ == '__main__':
    unittest.main()
