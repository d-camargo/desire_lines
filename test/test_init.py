# coding=utf-8
"""Tests QGIS plugin init."""

__author__ = 'Tim Sutton <tim@linfiniti.com>'
__revision__ = '$Format:%H$'
__date__ = '17/10/2010'
__license__ = "GPL"
__copyright__ = 'Copyright 2012, Australia Indonesia Facility for '
__copyright__ += 'Disaster Reduction'

import os
import unittest
import logging
import configparser

LOGGER = logging.getLogger('QGIS')


class TestInit(unittest.TestCase):
    """Test that the plugin init is usable for QGIS.

    Based heavily on the validator class by Alessandro
    Passoti available here:

    http://github.com/qgis/qgis-django/blob/master/qgis-app/
             plugins/validator.py

    """

    def test_read_init(self):
        """Test that the plugin __init__ will validate on plugins.qgis.org."""

        # You should update this list according to the latest in
        # https://github.com/qgis/qgis-django/blob/master/qgis-app/
        #        plugins/validator.py

        required_metadata = [
            'name',
            'description',
            'version',
            'qgisMinimumVersion',
            'email',
            'author']

        file_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), os.pardir,
            'desire_lines', 'metadata.txt'))
        LOGGER.info(file_path)
        metadata = []
        parser = configparser.ConfigParser()
        parser.optionxform = str
        parser.read(file_path)
        message = 'Cannot find a section named "general" in %s' % file_path
        assert parser.has_section('general'), message
        metadata.extend(parser.items('general'))

        for expectation in required_metadata:
            message = ('Cannot find metadata "%s" in metadata source (%s).' % (
                expectation, file_path))

            self.assertIn(expectation, dict(metadata), message)

        meta_dict = dict(metadata)
        self.assertEqual(meta_dict.get('qgisMaximumVersion'), '4.99', "qgisMaximumVersion must be 4.99")
        self.assertEqual(meta_dict.get('supportsQt6'), 'True', "supportsQt6 must be True")

    def test_no_plugin_dependencies(self):
        """Test that plugin_dependencies is not present in metadata.txt."""
        file_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), os.pardir,
            'desire_lines', 'metadata.txt'))
        parser = configparser.ConfigParser()
        parser.read(file_path)
        self.assertTrue(parser.has_section('general'), 'Cannot find a section named "general" in %s' % file_path)
        message = (
            'O metadado não deve conter a chave plugin_dependencies: '
            'o QGIS compara pelo nome exato e o GISBR se chama GISBR instalado '
            'e GisBR no repositório, então qualquer valor faz o gerenciador pedir instalação.'
        )
        self.assertNotIn('plugin_dependencies', parser['general'], message)


if __name__ == '__main__':
    unittest.main()
