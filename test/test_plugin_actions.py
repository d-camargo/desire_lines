# coding=utf-8
import unittest
from unittest.mock import MagicMock

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QToolButton
from qgis.PyQt import sip
from desire_lines.desirelines import DesireLines

from .utilities import get_qgis_app

QGIS_APP = get_qgis_app()


class TestPluginActions(unittest.TestCase):
    """Test plugin actions registration, dock widget creation and cleanup."""

    def setUp(self):
        self.iface = MagicMock()
        self.iface.mainWindow.return_value = None
        self.plugin = DesireLines(self.iface)

    def tearDown(self):
        """Destroy the dock deterministically.

        unload() only schedules deleteLater(); without a running event
        loop (mocked iface, headless test) the deferred delete never
        runs and the orphan QgsDockWidget segfaults the interpreter at
        Qt6 shutdown.
        """
        panel = getattr(self.plugin, 'traffic_panel', None)
        if panel is not None:
            sip.delete(panel)
            self.plugin.traffic_panel = None

    def test_init_gui_registers_two_actions(self):
        """initGui() registers two actions, menu entries and a cascade toolbar button."""
        self.plugin.initGui()
        self.assertEqual(len(self.plugin.actions), 2)
        self.assertEqual(self.iface.addPluginToVectorMenu.call_count, 2)
        self.assertEqual(self.iface.addToolBarIcon.call_count, 0)
        self.assertEqual(self.iface.addToolBarWidget.call_count, 1)

        button = self.iface.addToolBarWidget.call_args[0][0]
        self.assertIsInstance(button, QToolButton)
        self.assertEqual(button.popupMode(), QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.assertIsNotNone(button.menu())
        self.assertEqual(button.menu().actions(), [self.plugin.main_action, self.plugin.traffic_action])
        self.assertEqual(button.defaultAction(), self.plugin.main_action)
        self.assertTrue(self.plugin.actions[1].isCheckable())

    def test_show_traffic_panel_calls_add_dock_widget_once(self):
        """show_traffic_panel() calls addDockWidget only once on consecutive calls."""
        self.plugin.initGui()
        self.plugin.show_traffic_panel()
        self.assertEqual(self.iface.addDockWidget.call_count, 1)
        panel = self.plugin.traffic_panel
        self.assertIsNotNone(panel)
        self.iface.addDockWidget.assert_called_once_with(
            Qt.DockWidgetArea.RightDockWidgetArea, panel)

        # Second call toggles visibility and should not add dock widget again
        self.plugin.show_traffic_panel()
        self.assertEqual(self.iface.addDockWidget.call_count, 1)

    def test_unload_removes_dock_widget(self):
        """unload() calls removeDockWidget and cleans up traffic_panel."""
        self.plugin.initGui()
        self.plugin.show_traffic_panel()
        panel = self.plugin.traffic_panel

        self.plugin.unload()
        self.iface.removeDockWidget.assert_called_once_with(panel)
        self.assertIsNone(self.plugin.traffic_panel)
        self.assertEqual(self.iface.removeToolBarIcon.call_count, 1)
        sip.delete(panel)  # deferred delete never runs without an event loop

    def test_unload_calls_remove_toolbar_icon_once(self):
        """unload() calls removeToolBarIcon exactly once."""
        self.plugin.initGui()
        self.plugin.unload()
        self.assertEqual(self.iface.removeToolBarIcon.call_count, 1)


if __name__ == '__main__':
    unittest.main()
