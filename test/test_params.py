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


if __name__ == '__main__':
    unittest.main()
