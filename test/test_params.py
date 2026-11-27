# coding=utf-8
"""Testes unitários para o módulo de parâmetros (params.py)."""

import unittest
from desire_lines.traffic.params import (
    PADRAO_POR_CLASSE,
    PARAMS,
    _coerce_value,
    _get_attribute_from_feature,
    resolve,
)


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


class TestParamsCascata(unittest.TestCase):
    """Cascata de resolução em 8 etapas e origem 'complementar' (D4)."""

    def _assert_pista_dupla_padrao(self, feature):
        val, orig = resolve(feature=feature)
        self.assertEqual(val['tipo_segmento'], 'pista_dupla')
        self.assertEqual(orig['tipo_segmento'], 'oficial')
        self.assertEqual(val['lanes'], 2)
        self.assertEqual(orig['lanes'], 'padrao')
        self.assertEqual(val['vel_livre'], 100)
        self.assertEqual(orig['vel_livre'], 'padrao')

    def test_a_feicao_padronizada(self):
        """(a) Malha padronizada: pista_dupla oficial, lanes/vel_livre por classe."""
        self._assert_pista_dupla_padrao({'tipo_segmento': 'pista_dupla', 'lanes': None})

    def test_b_feicao_bruta_gpkg_antigo(self):
        """(b) Atributo bruto do DER (GPKG antigo) é traduzido na hora."""
        self._assert_pista_dupla_padrao({'TipoPista': 'DUP'})

    def test_c_override_vence_dado(self):
        """(c) Parâmetro fixado vence o dado oficial."""
        val, orig = resolve(feature={'TipoPista': 'DUP', 'lanes': 3},
                            overrides={'tipo_segmento': '2_faixas', 'lanes': 1})
        self.assertEqual((val['tipo_segmento'], orig['tipo_segmento']), ('2_faixas', 'usuario'))
        self.assertEqual((val['lanes'], orig['lanes']), (1, 'usuario'))

    def test_d_field_map_vence_traducao(self):
        """(d) Campo mapeado vence a tradução automática."""
        val, orig = resolve(feature={'TipoPista': 'DUP', 'meu_tipo': '2_faixas'},
                            field_map={'tipo_segmento': 'meu_tipo'})
        self.assertEqual((val['tipo_segmento'], orig['tipo_segmento']), ('2_faixas', 'oficial'))

    def test_e_complemento(self):
        """(e) Complemento OSM preenche lanes/mao_unica como 'complementar'."""
        val, orig = resolve(feature={'tipo_segmento': '2_faixas'},
                            complemento={'lanes': '3', 'oneway': 'yes'})
        self.assertEqual((val['lanes'], orig['lanes']), (3, 'complementar'))
        self.assertEqual((val['mao_unica'], orig['mao_unica']), (True, 'complementar'))
        self.assertEqual(orig['tipo_segmento'], 'oficial')

    def test_f_oficial_vence_complemento(self):
        """(f) Dado oficial da feição vence o complemento."""
        val, orig = resolve(feature={'lanes': 2, 'vel_livre': 90},
                            complemento={'lanes': '3', 'oneway': 'yes', 'maxspeed': '110'})
        self.assertEqual((val['lanes'], orig['lanes']), (2, 'oficial'))
        self.assertEqual((val['vel_livre'], orig['vel_livre']), (90.0, 'oficial'))

    def test_g_defaults_sem_dado(self):
        """(g) Valor onde não há dado vira 'usuario'; dado oficial vence o default."""
        val, orig = resolve(feature={}, defaults={'pct_veic_pesados': 35})
        self.assertEqual((val['pct_veic_pesados'], orig['pct_veic_pesados']), (35.0, 'usuario'))
        val, orig = resolve(feature={'pct_pesados': 12}, defaults={'pct_veic_pesados': 35})
        self.assertEqual((val['pct_veic_pesados'], orig['pct_veic_pesados']), (12.0, 'oficial'))

    def test_h_sem_nada_padrao_por_classe(self):
        """(h) Sem dado: padrão por classe para lanes/vel_livre, catálogo no resto."""
        val, orig = resolve()
        cls = PADRAO_POR_CLASSE['pista_simples_pavimentada']
        self.assertEqual(val['lanes'], cls['lanes'])
        self.assertEqual(val['vel_livre'], cls['vel_livre'])
        self.assertEqual(val['terreno'], PARAMS['terreno']['default'])
        self.assertTrue(all(o == 'padrao' for o in orig.values()))
        # Não pavimentada: vel_livre 60, lanes 1
        val, orig = resolve(feature={'TipoPista': 'IMP'})
        self.assertEqual((val['pavimentado'], orig['pavimentado']), (False, 'oficial'))
        self.assertEqual((val['lanes'], val['vel_livre']), (1, 60.0))
        self.assertEqual(orig['vel_livre'], 'padrao')

    def test_i_perimetro_na(self):
        """(i) PerimetroU='Nã' (DER-SP truncado) → urbano=False."""
        val, orig = resolve(feature={'PerimetroU': 'Nã'})
        self.assertEqual((val['urbano'], orig['urbano']), (False, 'oficial'))

    def test_j_qgsfeature_null_cai_para_etapa_seguinte(self):
        """(j) QgsFeature de camada de memória com lanes NULL segue a cascata."""
        from test.utilities import get_qgis_app
        get_qgis_app()
        from qgis.core import QgsVectorLayer, QgsFeature
        layer = QgsVectorLayer(
            'LineString?crs=EPSG:31983&field=tipo_segmento:string&field=lanes:integer',
            'malha', 'memory')
        feat = QgsFeature(layer.fields())
        feat.setAttribute('tipo_segmento', 'pista_dupla')
        layer.dataProvider().addFeatures([feat])
        lida = next(layer.getFeatures())
        val, orig = resolve(feature=lida, complemento={'lanes': '3', 'oneway': 'yes'})
        self.assertEqual((val['tipo_segmento'], orig['tipo_segmento']), ('pista_dupla', 'oficial'))
        self.assertEqual((val['lanes'], orig['lanes']), (3, 'complementar'))
        val, orig = resolve(feature=lida)
        self.assertEqual((val['lanes'], orig['lanes']), (2, 'padrao'))

    def test_id_em_campos_candidatos(self):
        """Todo parâmetro tem o próprio id em campos_candidatos (malha padronizada)."""
        for param_id, spec in PARAMS.items():
            self.assertIn(param_id, spec['campos_candidatos'])

    def test_valor_que_nao_converte_segue_cascata(self):
        """Valor inválido não para a cascata: cai para o complemento."""
        val, orig = resolve(feature={'lanes': 'muitas'}, complemento={'faixas': 2})
        self.assertEqual((val['lanes'], orig['lanes']), (2, 'complementar'))


class TestCoerceBool(unittest.TestCase):
    """_coerce_value(bool) (D4)."""

    def test_falsos_com_acento(self):
        for s in ('nã', 'nao', 'não', 'Não ', 'NAO'):
            self.assertFalse(_coerce_value(s, bool))

    def test_string_desconhecida_levanta(self):
        with self.assertRaises(ValueError):
            _coerce_value('talvez', bool)

    def test_numero_e_bool(self):
        self.assertTrue(_coerce_value(1, bool))
        self.assertFalse(_coerce_value(0, bool))
        self.assertTrue(_coerce_value(True, bool))


class TestGetAttributeFromFeature(unittest.TestCase):
    """Testa busca de atributos em feições com _get_attribute_from_feature."""

    def test_getitem_keyerror_fallback(self):
        """(a) Objeto com __getitem__ que levanta KeyError para um candidato e devolve valor para outro acha o segundo."""
        class ContainerWithMissingKey:
            def __getitem__(self, key):
                if key == 'campo2':
                    return 'valor_encontrado'
                raise KeyError(key)

        feat = ContainerWithMissingKey()
        val, found = _get_attribute_from_feature(feat, ['campo1', 'campo2'])
        self.assertTrue(found)
        self.assertEqual(val, 'valor_encontrado')

    def test_object_without_getitem(self):
        """(b) Objeto sem __getitem__ retorna (None, False) sem exceção."""
        class DummyObject:
            pass

        feat = DummyObject()
        val, found = _get_attribute_from_feature(feat, ['campo1', 'campo2'])
        self.assertFalse(found)
        self.assertIsNone(val)

    def test_getitem_runtimeerror_propagates(self):
        """(c) __getitem__ que levanta RuntimeError propaga a exceção."""
        class BuggyContainer:
            def __getitem__(self, key):
                raise RuntimeError("Falha interna inesperada")

        feat = BuggyContainer()
        with self.assertRaises(RuntimeError):
            _get_attribute_from_feature(feat, ['campo1'])


if __name__ == '__main__':
    unittest.main()
