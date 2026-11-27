# coding=utf-8
"""Testes do módulo desire_lines.traffic.oficiais (D2)."""

import os
from unittest.mock import patch

import pytest

from desire_lines.traffic import hcm, oficiais
from desire_lines.traffic.oficiais import (
    CAMPOS_CAPACIDADE,
    ESQUEMA_PADRONIZADO,
    IDENTIFICACAO,
    REGRAS,
    padroniza,
    traduz,
)
from desire_lines.traffic.params import PARAMS


def test_traduz_tipopista_dup():
    """(a) {'TipoPista': 'DUP'} -> pista_dupla, pavimentado=True."""
    res = traduz({'TipoPista': 'DUP'})
    assert res.get('tipo_segmento') == 'pista_dupla'
    assert res.get('pavimentado') is True


def test_traduz_superficie_federal_pav():
    """(b) {'Superficie_Federal': 'pav'} -> 2_faixas/True."""
    res = traduz({'Superficie_Federal': 'pav'})
    assert res.get('tipo_segmento') == '2_faixas'
    assert res.get('pavimentado') is True


@pytest.mark.parametrize('val', ['IMP', 'EOP', 'LEN', 'imp', 'eop', 'len'])
def test_traduz_nao_pavimentado(val):
    """(c) IMP/EOP/LEN -> pavimentado=False."""
    res_der = traduz({'TipoPista': val})
    assert res_der.get('tipo_segmento') == '2_faixas'
    assert res_der.get('pavimentado') is False

    res_dnit = traduz({'Superficie_Federal': val})
    assert res_dnit.get('tipo_segmento') == '2_faixas'
    assert res_dnit.get('pavimentado') is False


def test_traduz_perimetrou():
    """(d) PerimetroU 'Sim' -> True, e 'Nã'/'Não' -> False."""
    assert traduz({'PerimetroU': 'Sim'}).get('urbano') is True
    assert traduz({'PerimetroU': 'SIM'}).get('urbano') is True
    assert traduz({'PerimetroU': 's'}).get('urbano') is True
    assert traduz({'PerimetroU': 'Nã'}).get('urbano') is False
    assert traduz({'PerimetroU': 'Não'}).get('urbano') is False
    assert traduz({'PerimetroU': 'nao'}).get('urbano') is False
    assert traduz({'PerimetroU': 'N'}).get('urbano') is False


def test_traduz_valor_desconhecido_ou_nulo():
    """(e) valor desconhecido ou nulo -> {}."""
    assert traduz({'TipoPista': 'DESCONHECIDO'}) == {}
    assert traduz({'TipoPista': None}) == {}
    assert traduz({'Superficie_Federal': None}) == {}
    assert traduz({'PerimetroU': None}) == {}
    assert traduz({'PerimetroU': 'Talvez'}) == {}
    assert traduz({'lanes': None}) == {}
    assert traduz({'lanes': 'invalid'}) == {}
    assert traduz({'oneway': None}) == {}
    assert traduz({'oneway': 'unknown'}) == {}
    assert traduz({'maxspeed': None}) == {}
    assert traduz({}) == {}
    assert traduz(None) == {}


def test_traduz_lanes_e_oneway():
    """(f) lanes='3', oneway='yes' -> lanes=3 e mao_unica=True;
    lanes='2' sem oneway -> lanes=1; oneway='-1' -> sem mao_unica.
    """
    res1 = traduz({'lanes': '3', 'oneway': 'yes'})
    assert res1.get('lanes') == 3
    assert res1.get('mao_unica') is True

    res2 = traduz({'lanes': '2'})
    assert res2.get('lanes') == 1
    assert 'mao_unica' not in res2

    res3 = traduz({'oneway': '-1'})
    assert 'mao_unica' not in res3

    # oneway='-1' com lanes='4' -> não define mao_unica e divide por 2
    res4 = traduz({'lanes': '4', 'oneway': '-1'})
    assert res4.get('lanes') == 2
    assert 'mao_unica' not in res4


def test_traduz_maxspeed_e_velocidade_kmh():
    """(g) maxspeed='100' -> vel_livre=108, '60' -> 71, 'none' -> ausente;
    velocidade_kmh sozinho -> ausente.
    """
    assert traduz({'maxspeed': '100'}).get('vel_livre') == 108
    assert traduz({'maxspeed': '60'}).get('vel_livre') == 71
    assert 'vel_livre' not in traduz({'maxspeed': 'none'})
    assert 'vel_livre' not in traduz({'maxspeed': ''})
    assert traduz({'velocidade_kmh': 100}) == {}
    assert traduz({'velocidade_kmh': '80'}) == {}


def test_padroniza_der_sp_real():
    """(h) padroniza com a feição real do DER do levantamento (Rodovia='SP 095',
    Subtrecho='095SPE3394', KmInicial=39.68, KmFinal=42.75, Administra='Prefeitura',
    TipoPista='PAV', PerimetroU='Sim', mais Observacao etc.) e 'der_sp_rodovias' ->
    devolve exatamente as chaves de ESQUEMA_PADRONIZADO, com:
    - rodovia='SP 095', km_ini=39.68;
    - tipo_segmento='2_faixas', pavimentado=True, urbano=True;
    - lanes=None;
    - sem Observacao.
    """
    attrs = {
        'Rodovia': 'SP 095',
        'Subtrecho': '095SPE3394',
        'KmInicial': 39.68,
        'KmFinal': 42.75,
        'Administra': 'Prefeitura',
        'TipoPista': 'PAV',
        'PerimetroU': 'Sim',
        'Observacao': 'trecho teste em levantamento',
    }
    res = padroniza(attrs, 'der_sp_rodovias')

    # Devolve exatamente as chaves de ESQUEMA_PADRONIZADO
    assert list(res.keys()) == list(ESQUEMA_PADRONIZADO.keys())

    assert res['fonte'] == 'der_sp_rodovias'
    assert res['rodovia'] == 'SP 095'
    assert res['codigo_trecho'] == '095SPE3394'
    assert res['km_ini'] == 39.68
    assert res['km_fim'] == 42.75
    assert res['administracao'] == 'Prefeitura'

    assert res['tipo_segmento'] == '2_faixas'
    assert res['pavimentado'] is True
    assert res['urbano'] is True
    assert res['lanes'] is None

    assert 'Observacao' not in res


def test_padroniza_dnit_snv():
    """(i) idem para o DNIT, com Codigo_BR/Codigo_SNV/Superficie_Federal='DUP',
    que dá pista_dupla e urbano=None.
    """
    attrs = {
        'Codigo_BR': '101',
        'Codigo_SNV': '101BSP0010',
        'Superficie_Federal': 'DUP',
    }
    res = padroniza(attrs, 'dnit_snv')

    assert list(res.keys()) == list(ESQUEMA_PADRONIZADO.keys())
    assert res['fonte'] == 'dnit_snv'
    assert res['rodovia'] == '101'
    assert res['codigo_trecho'] == '101BSP0010'
    assert res['tipo_segmento'] == 'pista_dupla'
    assert res['pavimentado'] is True
    assert res['urbano'] is None
    assert res['lanes'] is None


def test_padroniza_fonte_desconhecida():
    """(j) fonte desconhecida ('der_mg_rodovias') -> identificação None, traduz aplicado."""
    attrs = {
        'Rodovia': 'MG 050',
        'Subtrecho': 'MG050TRECHO',
        'TipoPista': 'DUP',
    }
    res = padroniza(attrs, 'der_mg_rodovias')

    assert list(res.keys()) == list(ESQUEMA_PADRONIZADO.keys())
    assert res['fonte'] == 'der_mg_rodovias'
    # Identificação fica None porque a fonte não está em IDENTIFICACAO
    assert res['rodovia'] is None
    assert res['codigo_trecho'] is None
    assert res['km_ini'] is None
    assert res['km_fim'] is None
    assert res['administracao'] is None

    # traduz aplicado
    assert res['tipo_segmento'] == 'pista_dupla'
    assert res['pavimentado'] is True


def test_campos_capacidade_subset_params():
    """(k) CAMPOS_CAPACIDADE ⊂ PARAMS, e cada um tem o próprio id em campos_candidatos."""
    assert set(CAMPOS_CAPACIDADE).issubset(set(PARAMS.keys()))
    for campo in CAMPOS_CAPACIDADE:
        assert campo in PARAMS
        candidatos = PARAMS[campo].get('campos_candidatos', [])
        assert campo in candidatos, f"Campo {campo} não encontrado em campos_candidatos de PARAMS"


def test_arquivo_nao_contem_palavra_proibida():
    """(l) teste de texto: o arquivo não contém qgis."""
    caminho = oficiais.__file__
    with open(caminho, 'r', encoding='utf-8') as f:
        conteudo = f.read().lower()
    assert 'qgis' not in conteudo, "O arquivo oficiais.py não deve conter menção a 'qgis'"


def test_traduz_pista_dupla_cai_no_ramo_multilane():
    """(m) traduz com tipo_segmento='pista_dupla' passado a hcm.segment_capacity
    cai no ramo multilane.
    """
    params_trad = traduz({'TipoPista': 'DUP'})
    assert params_trad.get('tipo_segmento') == 'pista_dupla'

    with patch.object(hcm, 'multilane_freeway_capacity', wraps=hcm.multilane_freeway_capacity) as mock_ml, \
         patch.object(hcm, 'two_lane_capacity', wraps=hcm.two_lane_capacity) as mock_tl:
        cap, escopo = hcm.segment_capacity(params_trad)
        assert mock_ml.called, "segment_capacity deveria chamar multilane_freeway_capacity"
        assert not mock_tl.called, "segment_capacity não deveria chamar two_lane_capacity"
        assert cap > 0
