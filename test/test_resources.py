# coding=utf-8
"""Resources test.

.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.

"""

__author__ = 'dg.camargo@proton.me'
__date__ = '2024-07-13'
__copyright__ = 'Copyright 2024, Diego Camargo'

import os
import unittest

from qgis.PyQt.QtGui import QIcon



class DesireLinesDialogTest(unittest.TestCase):
    """Test rerources work."""

    def setUp(self):
        """Runs before each test."""
        pass

    def tearDown(self):
        """Runs after each test."""
        pass

    def test_icon_png(self):
        """The plugin icon file exists and loads.

        Path is relative to the plugin package folder (desire_lines/), not the
        repo root — Qt5's QIcon(path) is lazy and reports a missing file as
        non-null, so a stale path here only fails under Qt6.
        """
        path = os.path.join(
            os.path.dirname(__file__), '..', 'desire_lines', 'icon.png')
        self.assertTrue(os.path.exists(path), path)
        icon = QIcon(path)
        self.assertFalse(icon.isNull())

if __name__ == "__main__":
    suite = unittest.makeSuite(DesireLinesResourcesTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)



