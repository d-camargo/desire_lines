# coding=utf-8
"""PT-BR Translations Test.

.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.

"""
from .utilities import get_qgis_app

import unittest
import os

from qgis.PyQt.QtCore import QCoreApplication, QTranslator

QGIS_APP = get_qgis_app()


class PtBrTranslationsTest(unittest.TestCase):
    """Test that the plugin's PT-BR translation loads and applies."""

    def setUp(self):
        """Runs before each test."""
        if 'LANG' in iter(os.environ.keys()):
            os.environ.__delitem__('LANG')

    def tearDown(self):
        """Runs after each test."""
        if 'LANG' in iter(os.environ.keys()):
            os.environ.__delitem__('LANG')

    def test_pt_translations(self):
        """Test that a real plugin string is translated to PT-BR."""
        parent_path = os.path.join(__file__, os.path.pardir, os.path.pardir)
        dir_path = os.path.abspath(parent_path)
        file_path = os.path.join(
            dir_path, 'i18n', 'DesireLines_pt.qm')
        translator = QTranslator()
        translator.load(file_path)
        QCoreApplication.installTranslator(translator)

        expected_message = 'Ler CSV'
        real_message = QCoreApplication.translate(
            'DesireLinesDialogBase', 'Read CSV')
        self.assertEqual(real_message, expected_message)


if __name__ == "__main__":
    suite = unittest.makeSuite(PtBrTranslationsTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
