# coding=utf-8
"""Testes unitários para o módulo HCM (hcm.py)."""

import unittest
from desire_lines.traffic.hcm import (
    TERRAIN_ET,
    BASE_TWO_LANE_DIRECTIONAL_CAPACITY,
    BASE_TWO_LANE_TOTAL_CAPACITY,
    get_et,
    heavy_vehicle_factor,
    two_lane_capacity,
    base_capacity_per_lane,
    multilane_freeway_capacity,
    segment_capacity,
)


class TestHeavyVehicleFactor(unittest.TestCase):
    """Testa o cálculo do fator de veículos pesados f_HV."""

    def test_zero_heavy_vehicles(self):
        """Com 0 % de veículos pesados, f_HV deve ser exatamente 1.0."""
        self.assertAlmostEqual(heavy_vehicle_factor(0.0, 2.5), 1.0)
        self.assertAlmostEqual(heavy_vehicle_factor(0.0, 4.5), 1.0)

    def test_standard_values(self):
        """Testa 20 % pesados e E_T = 2.5 (terreno ondulado)."""
        # f_HV = 1 / (1 + 0.20 * (2.5 - 1)) = 1 / 1.30 = 0.769230769...
        f_hv = heavy_vehicle_factor(20.0, 2.5)
        self.assertAlmostEqual(f_hv, 1.0 / 1.30, places=6)

    def test_fraction_vs_percentage(self):
        """Aceita tanto 20.0 (%) quanto 0.20 (fração)."""
        f1 = heavy_vehicle_factor(20.0, 2.5)
        f2 = heavy_vehicle_factor(0.20, 2.5)
        self.assertAlmostEqual(f1, f2)


class TestTerrainEt(unittest.TestCase):
    """Testa a obtenção do E_T por tipo de terreno."""

    def test_terrain_lookup(self):
        """Verifica os valores padronizados de E_T por terreno."""
        self.assertEqual(get_et('plano'), 1.5)
        self.assertEqual(get_et('ondulado'), 2.5)
        self.assertEqual(get_et('montanhoso'), 4.5)
        self.assertEqual(get_et('level'), 1.5)
        self.assertEqual(get_et('rolling'), 2.5)
        self.assertEqual(get_et('mountainous'), 4.5)

    def test_case_insensitive_and_numeric(self):
        """Aceita case-insensitive e valores numéricos diretos."""
        self.assertEqual(get_et('PLANO'), 1.5)
        self.assertEqual(get_et('Ondulado'), 2.5)
        self.assertEqual(get_et(3.0), 3.0)

    def test_fallback(self):
        """Terreno desconhecido usa padrão 'ondulado' (2.5)."""
        self.assertEqual(get_et('desconhecido'), 2.5)


class TestTwoLaneCapacity(unittest.TestCase):
    """Testa a capacidade de rodovia de pista simples (2 faixas, HCM Cap. 15)."""

    def test_zero_hv_base_capacity_split_50_50(self):
        """Com 0 % pesados, PHF=1.0 e divisão 50/50, atinge o teto dos 2 sentidos (1600 veíc/h/sentido)."""
        cap = two_lane_capacity(pct_hv=0.0, terrain='plano', phf=1.0, directional_split=50.0)
        # 3200 * 0.5 = 1600 pc/h. Como f_HV=1.0 e PHF=1.0 => 1600 veíc/h
        self.assertAlmostEqual(cap, 1600.0)

    def test_zero_hv_base_capacity_split_60_40(self):
        """Com divisão 60/40 no sentido de pico, a capacidade base fica limitada ao teto por sentido (1700 pc/h)."""
        cap = two_lane_capacity(pct_hv=0.0, terrain='plano', phf=1.0, directional_split=60.0)
        # min(1700, 3200 * 0.6 = 1920) = 1700 pc/h
        self.assertAlmostEqual(cap, 1700.0)

    def test_standard_rural_defaults(self):
        """Testa com os parâmetros padrão (20 % pesados, ondulado, PHF=0.92, split 50/50)."""
        # base_d = 1600 pc/h
        # f_HV = 1 / 1.30
        # cap = 1600 * (1 / 1.30) * 0.92 = 1132.30769...
        cap = two_lane_capacity(pct_hv=20.0, terrain='ondulado', phf=0.92, directional_split=50.0)
        expected = 1600.0 * (1.0 / 1.30) * 0.92
        self.assertAlmostEqual(cap, expected, places=4)

    def test_monotonicity(self):
        """Verifica a monotonicidade esperada das variáveis de capacidade."""
        cap_level = two_lane_capacity(pct_hv=20.0, terrain='plano', phf=0.92)
        cap_rolling = two_lane_capacity(pct_hv=20.0, terrain='ondulado', phf=0.92)
        cap_mountain = two_lane_capacity(pct_hv=20.0, terrain='montanhoso', phf=0.92)

        # Terreno mais acidentado => menor capacidade
        self.assertGreater(cap_level, cap_rolling)
        self.assertGreater(cap_rolling, cap_mountain)

        # Mais veículos pesados => menor capacidade
        cap_low_hv = two_lane_capacity(pct_hv=10.0, terrain='ondulado')
        cap_high_hv = two_lane_capacity(pct_hv=30.0, terrain='ondulado')
        self.assertGreater(cap_low_hv, cap_high_hv)


class TestBaseCapacityPerLane(unittest.TestCase):
    """Testa a capacidade base por faixa em função do FFS (HCM Cap. 12)."""

    def test_high_ffs(self):
        """FFS alto (>= 120 km/h) atinge o teto de 2400 pc/h/faixa."""
        self.assertEqual(base_capacity_per_lane(120.0), 2400.0)
        self.assertEqual(base_capacity_per_lane(150.0), 2400.0)

    def test_intermediate_thresholds(self):
        """Verifica os patamares intermediários de FFS."""
        self.assertEqual(base_capacity_per_lane(105.0), 2350.0)
        self.assertEqual(base_capacity_per_lane(97.0), 2300.0)
        self.assertEqual(base_capacity_per_lane(88.5), 2250.0)

    def test_below_lowest_threshold_clamps(self):
        """FFS abaixo do menor limiar não extrapola: usa o menor valor tabelado."""
        self.assertEqual(base_capacity_per_lane(50.0), 2250.0)

    def test_between_thresholds_uses_lower_bracket(self):
        """FFS entre dois limiares usa o patamar do limiar inferior mais próximo."""
        self.assertEqual(base_capacity_per_lane(100.0), 2300.0)


class TestMultilaneFreewayCapacity(unittest.TestCase):
    """Testa a capacidade de segmento básico de pista dupla/multilane e freeway."""

    def test_zero_hv_default_lanes_and_ffs(self):
        """Com 0 % pesados, PHF=1.0, 2 faixas e FFS=110, usa a capacidade base cheia."""
        cap = multilane_freeway_capacity(lanes=2, pct_hv=0.0, terrain='plano', phf=1.0, ffs=110.0)
        # base_capacity_per_lane(110) = 2350.0; f_HV=1.0, PHF=1.0 => 2350 * 2 = 4700
        self.assertAlmostEqual(cap, 4700.0)

    def test_standard_dual_carriageway_defaults(self):
        """Testa com os parâmetros padrão da pista dupla (20 % pesados, ondulado, PHF=0.92, FFS=110)."""
        # base_capacity_per_lane(110) = 2350.0
        # f_HV = 1 / (1 + 0.20 * (2.5 - 1)) = 1 / 1.30
        # cap = 2350 * (1/1.30) * 0.92 * 2 faixas
        cap = multilane_freeway_capacity(lanes=2, pct_hv=20.0, terrain='ondulado', phf=0.92, ffs=110.0)
        expected = 2350.0 * (1.0 / 1.30) * 0.92 * 2
        self.assertAlmostEqual(cap, expected, places=4)

    def test_scales_with_lanes(self):
        """A capacidade por sentido escala linearmente com o número de faixas."""
        cap_1_lane = multilane_freeway_capacity(lanes=1, pct_hv=20.0, terrain='ondulado', phf=0.92, ffs=110.0)
        cap_3_lanes = multilane_freeway_capacity(lanes=3, pct_hv=20.0, terrain='ondulado', phf=0.92, ffs=110.0)
        self.assertAlmostEqual(cap_3_lanes, cap_1_lane * 3)

    def test_monotonicity(self):
        """Verifica a monotonicidade esperada das variáveis de capacidade."""
        cap_level = multilane_freeway_capacity(pct_hv=20.0, terrain='plano', phf=0.92)
        cap_rolling = multilane_freeway_capacity(pct_hv=20.0, terrain='ondulado', phf=0.92)
        cap_mountain = multilane_freeway_capacity(pct_hv=20.0, terrain='montanhoso', phf=0.92)

        # Terreno mais acidentado => menor capacidade
        self.assertGreater(cap_level, cap_rolling)
        self.assertGreater(cap_rolling, cap_mountain)

        # FFS maior => capacidade maior ou igual
        cap_low_ffs = multilane_freeway_capacity(pct_hv=20.0, terrain='ondulado', ffs=88.5)
        cap_high_ffs = multilane_freeway_capacity(pct_hv=20.0, terrain='ondulado', ffs=120.0)
        self.assertGreater(cap_high_ffs, cap_low_ffs)


class TestSegmentCapacity(unittest.TestCase):
    """Testa a função de despacho segment_capacity(values)."""

    def test_default_two_lane_dispatch(self):
        """Dicionário vazio ou com tipo_segmento='2_faixas' despacha para pista simples."""
        cap_empty, escopo_empty = segment_capacity({})
        cap_explicit, escopo_explicit = segment_capacity({'tipo_segmento': '2_faixas'})
        cap_expected = two_lane_capacity(pct_hv=20.0, terrain='ondulado', phf=0.92, directional_split=50.0)

        self.assertAlmostEqual(cap_empty, cap_expected)
        self.assertEqual(escopo_empty, 'rodoviario')
        self.assertAlmostEqual(cap_explicit, cap_expected)
        self.assertEqual(escopo_explicit, 'rodoviario')

    def test_multilane_dispatch_by_type(self):
        """tipo_segmento='pista_dupla' despacha para multilane/freeway."""
        cap, escopo = segment_capacity({'tipo_segmento': 'pista_dupla', 'lanes': 2, 'vel_livre': 110.0})
        cap_expected = multilane_freeway_capacity(lanes=2, pct_hv=20.0, terrain='ondulado', phf=0.92, ffs=110.0)

        self.assertAlmostEqual(cap, cap_expected)
        self.assertEqual(escopo, 'rodoviario')

    def test_multilane_dispatch_by_lanes(self):
        """lanes > 1 sem tipo_segmento explícito despacha para multilane."""
        cap, escopo = segment_capacity({'lanes': 3, 'pct_veic_pesados': 10.0, 'terreno': 'plano'})
        cap_expected = multilane_freeway_capacity(lanes=3, pct_hv=10.0, terrain='plano', phf=0.92, ffs=110.0)

        self.assertAlmostEqual(cap, cap_expected)
        self.assertEqual(escopo, 'rodoviario')

    def test_urban_scope_d11(self):
        """Trata o escopo de D11: retorna escopo='urbano' quando o segmento for trecho urbano."""
        cap, escopo1 = segment_capacity({'urbano': True})
        self.assertEqual(escopo1, 'urbano')

        cap, escopo2 = segment_capacity({'trecho_urbano': 'sim'})
        self.assertEqual(escopo2, 'urbano')

        cap, escopo3 = segment_capacity({'urbano': False})
        self.assertEqual(escopo3, 'rodoviario')


if __name__ == '__main__':
    unittest.main()


