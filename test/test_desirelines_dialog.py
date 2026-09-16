# coding=utf-8
"""Dialog test.

.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.

"""

__author__ = 'dg.camargo@proton.me'
__date__ = '2024-07-13'
__copyright__ = 'Copyright 2024, Diego Camargo'

import unittest
from unittest.mock import patch

from qgis.PyQt.QtWidgets import QDialogButtonBox, QDialog

from desire_lines.desirelines_dialog import DesireLinesDialog
from desire_lines.traffic import assignment, network
from desire_lines.traffic import params as traffic_params

from .utilities import get_qgis_app
QGIS_APP = get_qgis_app()

# Two links forming an L, in a metric CRS, with a centroid near each end.


class DesireLinesDialogTest(unittest.TestCase):
    """Test dialog works."""

    def setUp(self):
        """Runs before each test."""
        self.dialog = DesireLinesDialog(None)

    def tearDown(self):
        """Runs after each test."""
        self.dialog = None

    def test_dialog_ok(self):
        """Test we can click OK."""

        button = self.dialog.button_box.button(QDialogButtonBox.StandardButton.Ok)
        button.click()
        result = self.dialog.result()
        self.assertEqual(result, QDialog.DialogCode.Accepted)

    def test_dialog_cancel(self):
        """Test we can click cancel."""
        button = self.dialog.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        button.click()
        result = self.dialog.result()
        self.assertEqual(result, QDialog.DialogCode.Rejected)

    def test_dialog_has_three_tabs(self):
        """The dialog has 3 tabs with correct titles and no ta-prefixed widgets."""
        self.assertEqual(self.dialog.tabWidget.count(), 3)
        self.assertEqual(self.dialog.tabWidget.tabText(0), "Origin/Destination Matrix")
        self.assertEqual(self.dialog.tabWidget.tabText(1), "Desire Lines")
        self.assertEqual(self.dialog.tabWidget.tabText(2), "AoN (Delaunay)")
        ta_widgets = [
            w.objectName() for w in self.dialog.findChildren(object)
            if w.objectName().startswith('ta') and not w.objectName().startswith('tab')
        ]
        self.assertEqual(ta_widgets, [])

if __name__ == "__main__":
    suite = unittest.makeSuite(DesireLinesDialogTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
