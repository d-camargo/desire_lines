# coding=utf-8
import unittest
from unittest.mock import MagicMock, patch

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QToolButton
from qgis.PyQt import sip
from qgis.core import QgsSettings
from desire_lines.desirelines import DesireLines
from desire_lines.traffic import gisbr_bridge

from .utilities import get_qgis_app

QGIS_APP = get_qgis_app()


class TestPluginActions(unittest.TestCase):
    """Test plugin actions registration, dock widget creation and cleanup."""

    def setUp(self):
        QgsSettings().remove('desire_lines/skip_gisbr_check')
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
        QgsSettings().remove('desire_lines/skip_gisbr_check')
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

    @patch('desire_lines.desirelines.QTimer.singleShot')
    def test_init_gui_schedules_gisbr_check(self, mock_single_shot):
        """initGui() schedules _check_gisbr via QTimer.singleShot(0, self._check_gisbr)."""
        self.plugin.initGui()
        mock_single_shot.assert_called_once_with(0, self.plugin._check_gisbr)

    @patch('desire_lines.desirelines.QMessageBox')
    @patch('desire_lines.desirelines.gisbr_bridge.is_available', return_value=True)
    def test_check_gisbr_when_available_returns_false_and_no_dialog(self, mock_available, mock_box_cls):
        """(a) GISBR present -> returns False and QMessageBox is not instantiated."""
        result = self.plugin._check_gisbr()
        self.assertFalse(result)
        mock_box_cls.assert_not_called()

    @patch('desire_lines.desirelines.QMessageBox')
    @patch('desire_lines.desirelines.gisbr_bridge.is_available', return_value=False)
    def test_check_gisbr_when_missing_shows_box_with_missing_message(self, mock_available, mock_box_cls):
        """(b) GISBR absent -> returns True and box is created with missing_message() text."""
        mock_box = mock_box_cls.return_value
        result = self.plugin._check_gisbr()
        self.assertTrue(result)
        mock_box_cls.assert_called_once()
        mock_box.setText.assert_called_once()
        text_arg = mock_box.setText.call_args[0][0]
        self.assertIn(gisbr_bridge.missing_message(), text_arg)

    @patch('desire_lines.desirelines.QMessageBox')
    @patch('desire_lines.desirelines.gisbr_bridge.is_available', return_value=False)
    def test_check_gisbr_click_manage_plugins_triggers_action(self, mock_available, mock_box_cls):
        """(c) GISBR absent, click 'Abrir Gerenciador de Complementos' -> actionManagePlugins().trigger called once."""
        mock_box = mock_box_cls.return_value
        btn_manage = MagicMock()
        btn_not_now = MagicMock()
        mock_box.addButton.side_effect = [btn_manage, btn_not_now]
        mock_box.clickedButton.return_value = btn_manage

        result = self.plugin._check_gisbr()
        self.assertTrue(result)
        self.iface.actionManagePlugins().trigger.assert_called_once()

    @patch('desire_lines.desirelines.QMessageBox')
    @patch('desire_lines.desirelines.gisbr_bridge.is_available', return_value=False)
    def test_check_gisbr_dont_show_again_sets_setting_and_skips_next_checks(self, mock_available, mock_box_cls):
        """(d) GISBR absent with checkbox marked -> key is set True, next call returns False without consulting is_available."""
        mock_box = mock_box_cls.return_value

        def check_box_on_exec():
            cb = mock_box.setCheckBox.call_args[0][0]
            cb.setChecked(True)

        mock_box.exec.side_effect = check_box_on_exec
        mock_box.exec_.side_effect = check_box_on_exec

        result = self.plugin._check_gisbr()
        self.assertTrue(result)
        self.assertTrue(QgsSettings().value('desire_lines/skip_gisbr_check', False, type=bool))

        mock_available.reset_mock()
        mock_box_cls.reset_mock()

        # Subsequent call returns False without consulting is_available
        result2 = self.plugin._check_gisbr()
        self.assertFalse(result2)
        mock_available.assert_not_called()
        mock_box_cls.assert_not_called()


if __name__ == '__main__':
    unittest.main()
