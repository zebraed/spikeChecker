#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
"""
GUI module for spikeChecker
"""
import os
import json
import functools
import platform
import subprocess

from Qt import QtWidgets, QtCore, QtGui
from PySide2 import QtUiTools

from shiboken2 import wrapInstance

from maya.app.general.mayaMixin import MayaQWidgetBaseMixin

from maya import cmds
from maya import OpenMayaUI as omui

from . import checker
from . import validators


DIR_NAME = os.path.dirname(__file__)
OPTIONVAR_KEY = "spikeChecker_settings"


__all__ = ["showUI"]


class ItemData(object):
    """Item data class

    Attributes:
        name (str): item name
        value (float): value
    """
    def __init__(self, name, value=0.0):
        """Initialize

        Args:
            name (str): item name
            value (float): value
        """
        self.name = name
        self.value = value

    def __repr__(self):
        return f"ItemData(name={self.name}, value={self.value})"


class SpikeCheckerModel(QtCore.QObject):
    """Spike Checker model class

    Attributes:
        items_changed (QtCore.Signal): signal emitted when items are changed
    """
    items_changed = QtCore.Signal()

    def __init__(self, parent=None):
        """Initialize

        Args:
            parent (QtCore.QObject | None): parent object
        """
        super().__init__(parent)
        self._items = []

    def add_item(self, name, value=0.0):
        """Add item

        Args:
            name (str): item name
            value (float): value

        Returns:
            int: index of added item
        """
        item = ItemData(name, value)
        self._items.append(item)
        self.items_changed.emit()
        return len(self._items) - 1

    def remove_item(self, index):
        """Remove item

        Args:
            index (int): index of item to remove
        """
        if 0 <= index < len(self._items):
            del self._items[index]
            self.items_changed.emit()

    def clear_items(self):
        """
        Clear all items
        """
        self._items = []
        self.items_changed.emit()

    def get_item(self, index):
        """Get item

        Args:
            index (int): index of item

        Returns:
            ItemData | None: item data, None if not found
        """
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def get_item_name(self, index):
        """
        Get item name

        Args:
            index (int): index of item

        Returns:
            str: item name, empty string if not found
        """
        item = self.get_item(index)
        return item.name if item else ""

    def get_item_value(self, index):
        """
        Get item value

        Args:
            index (int): index of item

        Returns:
            float: value, 0.0 if not found
        """
        item = self.get_item(index)
        return item.value if item else 0.0

    def set_item_value(self, index, value):
        """
        Set item value

        Args:
            index (int): index of item
            value (float): value
        """
        item = self.get_item(index)
        if item:
            item.value = value
            self.items_changed.emit()

    def get_items(self):
        """
        Get all items

        Returns:
            list[ItemData]: list of items
        """
        return list(self._items)

    def item_count(self):
        """
        Get item count

        Returns:
            int: item count
        """
        return len(self._items)

    def has_item(self, name):
        """
        Check if item with given name exists

        Args:
            name (str): item name

        Returns:
            bool: True if item exists, False otherwise
        """
        return any(item.name == name for item in self._items)


class SpikeCheckerController(object):
    """
    Spike Checker controller class
    """
    def __init__(self):
        """
        Initialize
        """
        self.model = SpikeCheckerModel()
        self.view = SpikeCheckerGUI()
        self._connect_signals()

    def _connect_signals(self):
        """
        Connect signals and slots
        """
        # View -> Controller
        self.view.scan_clicked.connect(
            lambda: self._on_scan_clicked(
                start_frame=int(self.view.ui.spinBox_start.value()),
                end_frame=int(self.view.ui.spinBox_end.value())
            )
        )
        self.view.value_changed.connect(self._on_value_changed)
        self.view.add_node_clicked.connect(
            functools.partial(self._on_add_node_clicked)
        )
        self.view.register_clicked.connect(self._on_register_clicked)
        self.view.del_sel_clicked.connect(
            functools.partial(self._on_del_sel_clicked)
        )
        self.view.clear_all_clicked.connect(
            functools.partial(self._on_clear_all_clicked)
        )
        self.view.clear_results_clicked.connect(
            functools.partial(self._on_clear_results_clicked)
        )

        # Model -> View
        self.model.items_changed.connect(self._on_items_changed)

    def _on_scan_clicked(self, start_frame, end_frame):
        """
        Scan button clicked

        Args:
            start_frame (int): start frame
            end_frame (int): end frame
        """
        items = self.model.get_items()
        if not items:
            cmds.warning("No items to scan.")
            return

        # Fallback to playback range if not specified
        if start_frame is None:
            start_frame = int(cmds.playbackOptions(q=True, minTime=True))
        if end_frame is None:
            end_frame = int(cmds.playbackOptions(q=True, maxTime=True))

        # Validate frame range
        if start_frame > end_frame:
            cmds.warning(
                "Start frame must be less than or equal to end frame."
            )
            return

        node_attr_threshold_dict = {}
        for i_item in items:
            node_attr = i_item.name
            threshold = i_item.value

            if not cmds.objExists(node_attr):
                cmds.warning(f"Warning: {node_attr} does not exist. Skipping.")
                continue

            node_attr_threshold_dict[node_attr] = threshold

        if not node_attr_threshold_dict:
            cmds.warning("No valid attributes to scan.")
            return

        print(f"Scanning {len(node_attr_threshold_dict)} attribute(s)...")
        print(f"Scan Range: {start_frame} to {end_frame}")
        for attr, thresh in list(node_attr_threshold_dict.items())[:3]:
            print(f"  {attr}: threshold={thresh}")
        if len(node_attr_threshold_dict) > 3:
            print(f"  ... and {len(node_attr_threshold_dict) - 3} more")

        # create progress dialog
        progress = QtWidgets.QProgressDialog(
            "Scanning animation...",
            "Cancel",
            0,
            100,  # 100%
            self.view
        )
        progress.setWindowTitle("Scanning animation...")
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.setAutoClose(True)
        progress.setAutoReset(True)
        progress.show()
        QtWidgets.QApplication.processEvents()

        last_update_percent = [0]

        def update_progress(current, total):
            percent = int((current / total) * 100)

            # update if: 0%, 10% or more changed, or final frame
            if (percent == 0 or
                    percent - last_update_percent[0] >= 10 or
                    current == total):

                if percent == 0:
                    progress.setLabelText("Scanning animation...")
                else:
                    progress.setLabelText(f"Scanning animation... {percent}%")

                progress.setValue(percent)
                QtWidgets.QApplication.processEvents()
                last_update_percent[0] = percent

                if progress.wasCanceled():
                    raise RuntimeError("Scan cancelled by user")

        try:
            all_results = checker.check_attr_spike(
                node_attr_threshold_dict,
                start_frame=start_frame,
                end_frame=end_frame,
                progress_callback=update_progress
            )
        except RuntimeError as e:
            progress.close()
            raise e
        finally:
            progress.close()

        self.view.clear_scan_results()
        self.view.display_scan_results(all_results)
        num_attrs = len(all_results)
        print(f"Scan completed. Found spikes in {num_attrs} attributes.")

    def _on_value_changed(self, row, value):
        """
        Value changed

        Args:
            row (int): row index
            value (float): new value
        """
        self.model.set_item_value(row, value)

    def _on_add_node_clicked(self):
        """
        Add node button clicked
        """
        node_attr_list = checker.list_nodeattr_from_cb()
        if not node_attr_list:
            cmds.warning("No node attributes selected in channel box.")
            return

        added_count = 0
        skipped_count = 0
        for node_attr in node_attr_list:
            if self.model.has_item(node_attr):
                skipped_count += 1
                continue
            self.model.add_item(node_attr, value=1.0)
            added_count += 1

        if skipped_count > 0:
            print(f"Skipped {skipped_count} duplicate node attribute(s).")

    def _on_del_sel_clicked(self):
        """
        Delete selected button clicked
        """
        selected_rows = self.view.get_selected_rows()
        if not selected_rows:
            print("No rows selected.")
            return

        selected_rows.sort(reverse=True)
        for row in selected_rows:
            self.model.remove_item(row)

        print(f"Deleted {len(selected_rows)} row(s).")

    def _on_register_clicked(self, node_pattern, attr_name):
        """
        Register button clicked

        Args:
            node_pattern (str): node name pattern (supports wildcards)
            attr_name (str): attribute name
        """
        if not node_pattern or not attr_name:
            cmds.warning("Please input both node name and attribute name.")
            return

        nodes = cmds.ls(node_pattern)
        if not nodes:
            cmds.warning(f"No nodes found matching pattern: {node_pattern}")
            return

        added_count = 0
        skipped_count = 0
        invalid_count = 0

        for node in nodes:
            node_attr = f"{node}.{attr_name}"

            if not cmds.objExists(node_attr):
                cmds.warning(f"Warning: {node_attr} does not exist. Skipping.")
                invalid_count += 1
                continue

            # check duplicate
            if self.model.has_item(node_attr):
                skipped_count += 1
                continue

            # add with default threshold
            self.model.add_item(node_attr, value=0.0)
            added_count += 1

        # display results
        if added_count > 0:
            print(f"Added {added_count} node attribute(s).")
        if skipped_count > 0:
            print(f"Skipped {skipped_count} duplicate node attribute(s).")
        if invalid_count > 0:
            cmds.warning(f"Skipped {invalid_count} invalid node attribute(s).")

        # clear input fields
        self.view.clear_input_fields()

    def _on_items_changed(self):
        """
        Items changed
        """
        # update view
        self.view.clear_items()
        items = self.model.get_items()
        for i, item in enumerate(items):
            self.view.add_item_row(i, item.name, item.value)

    def _on_clear_all_clicked(self):
        """
        Clear all clicked
        """
        self.clear_items()

    def _on_clear_results_clicked(self):
        """
        Clear results clicked
        """
        self.view.clear_scan_results()

    def add_item(self, name, value=0.0):
        """
        Add item

        Args:
            name (str): item name
            value (float): value
        """
        self.model.add_item(name, value)

    def remove_item(self, index):
        """
        Remove item

        Args:
            index (int): index of item to remove
        """
        self.model.remove_item(index)

    def clear_items(self):
        """
        Clear all items
        """
        self.model.clear_items()

    def show(self):
        """
        Show view
        """
        self.view.show()
        self.view.raise_()
        self.view.activateWindow()


class SpikeCheckerGUI(MayaQWidgetBaseMixin, QtWidgets.QMainWindow):
    """
    Spike Checker GUI class
    """
    object_name = "SpikeCheckerWindow_object"
    window_title = "Spike Checker"

    # signals
    scan_clicked = QtCore.Signal()
    value_changed = QtCore.Signal(int, float)  # row index, value
    add_node_clicked = QtCore.Signal()
    register_clicked = QtCore.Signal(str, str)  # node_name, attr_name
    del_sel_clicked = QtCore.Signal()
    clear_all_clicked = QtCore.Signal()
    clear_results_clicked = QtCore.Signal()

    def __init__(self):
        """
        Initialize
        """
        maya_main_window_ptr = omui.MQtUtil.mainWindow()
        maya_main_window = wrapInstance(int(maya_main_window_ptr),
                                        QtWidgets.QWidget)
        super().__init__(maya_main_window)

        self._close_other_instances()
        self._menu_bar = None
        self._load_ui()
        self._setup_ui()
        self._create_connections()

        # self._qss_template = self._load_qss_template()
        # self._set_style_sheet()
        self._setup_focus_clear()
        try:
            self._load_settings()
        except Exception:
            pass

        self.set_framerange()

    def _close_other_instances(self):
        """
        Close other instances
        """
        for q_window in self.parent().findChildren(QtWidgets.QMainWindow):
            if q_window.windowTitle() == self.window_title:
                q_window.close()

    def _load_ui(self):
        """
        Load UI file
        """
        ui_file = os.path.join(DIR_NAME, "gui_main.ui")
        loader = QtUiTools.QUiLoader()
        file_obj = QtCore.QFile(ui_file)
        file_obj.open(QtCore.QFile.ReadOnly)
        self.ui = loader.load(file_obj, self)
        file_obj.close()
        self.setCentralWidget(self.ui)

    def _setup_ui(self):
        """
        Setup UI
        """
        self.setWindowTitle(self.window_title)
        self.setObjectName(self.object_name)
        self._create_menu_bar(self.ui.horizontalLayout_check)

        start_spinbox = self.ui.spinBox_start
        end_spinbox = self.ui.spinBox_end
        start_spinbox.setMinimum(-999999)
        start_spinbox.setMaximum(999999)
        end_spinbox.setMinimum(-999999)
        end_spinbox.setMaximum(999999)

        # setting for scan tabel
        table = self.ui.tableWidget_entry
        table.setColumnCount(2)
        headers = ["Node Attribute", "Threshold"]
        table.setHorizontalHeaderLabels(headers)

        # setting for column resize mode
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionsMovable(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Interactive)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        table.setColumnWidth(0, 300)

        # connect section resized signal
        header.sectionResized.connect(self._on_section_resized)

        table.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )  # disable cell direct edit (edit by widget)
        table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows
        )
        table.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )

        # setting for results tree widget
        tree = self.ui.treeWidget_results
        tree.setHeaderLabels(["Node Attribute / Frame", "Info"])
        tree.setColumnWidth(0, 200)
        tree.setAlternatingRowColors(True)

        # debug dummy items
        # self._add_debug_dummy_items()

        # set validators
        self.ui.lineEdit_node.setValidator(
            validators.MayaNodePatternValidator()
        )
        self.ui.lineEdit_attr.setValidator(
            validators.AlphanumericValidator()
        )

        self.resize(650, 600)

    def _create_connections(self):
        """
        Create connections between signals and slots
        """
        self.ui.pushButton_set_range.clicked.connect(self._on_set_range_clicked)
        self.ui.pushButton_scan.clicked.connect(self.scan_clicked.emit)
        self.ui.pushButton_add_node.clicked.connect(
            self.add_node_clicked.emit
        )
        self.ui.pushButton_register.clicked.connect(
            self._on_register_button_clicked
        )
        self.ui.pushButton_del_sel.clicked.connect(
            self.del_sel_clicked.emit
        )
        self.ui.pushButton_clear_all.clicked.connect(
            self.clear_all_clicked.emit
        )
        self.ui.tableWidget_entry.cellClicked.connect(
            self._on_table_item_clicked
        )
        self.ui.treeWidget_results.itemClicked.connect(
            self._on_tree_item_clicked
        )

        self.ui.pushButton_clear_results.clicked.connect(
            self.clear_results_clicked.emit
        )

    def _setup_focus_clear(self):
        """
        Setup focus clear
        """
        self.ui.installEventFilter(self)

    def eventFilter(self, obj, event):  # noqa: N802 - Qt method name
        """
        Event filter

        Args:
            obj (QtCore.QObject): event sender
            event (QtCore.QEvent): event object

        Returns:
            bool: True if event is handled, False otherwise
        """
        if isinstance(obj, QtWidgets.QDoubleSpinBox):
            if event.type() == QtCore.QEvent.FocusIn:
                self.ui.tableWidget_entry.clearSelection()

        if obj is self.ui and event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == QtCore.Qt.LeftButton:
                focused_widget = QtWidgets.QApplication.focusWidget()
                if focused_widget and focused_widget != self:
                    focused_widget.clearFocus()

        if obj is self.parent() and event.type() == QtCore.QEvent.Close:
            self.close()
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):  # noqa: N802 - Qt method name
        """
        Mouse press event

        Args:
            event (QtCore.QEvent): event object
        """
        if event.button() == QtCore.Qt.LeftButton:
            if self.rect().contains(event.pos()):
                focused_widget = QtWidgets.QApplication.focusWidget()
                if focused_widget and focused_widget != self:
                    focused_widget.clearFocus()
        super().mousePressEvent(event)

    def closeEvent(self, event):  # noqa: N802 - Qt method name
        """Window close cleanup"""
        try:
            self._save_settings()
        except Exception:
            pass
        super().closeEvent(event)

    def _save_settings(self):
        """Save settings to file"""
        settings = {
            "window_geometry": {
                "x": self.x(),
                "y": self.y(),
                "width": self.width(),
                "height": self.height(),
            }
        }

        try:
            cmds.optionVar(sv=(OPTIONVAR_KEY, json.dumps(settings)))
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def _load_settings(self) -> None:
        """Load settings from optionVar"""
        try:
            if cmds.optionVar(exists=OPTIONVAR_KEY):
                raw = cmds.optionVar(q=OPTIONVAR_KEY)
                if isinstance(raw, (list, tuple)) and raw:
                    raw = raw[0]
                if isinstance(raw, str) and raw:
                    s = json.loads(raw)
                    self._apply_settings_to_ui(s)
        except Exception:
            pass

    def _apply_settings_to_ui(self, settings: dict) -> None:
        """Apply settings to UI"""
        if not isinstance(settings, dict):
            return
        try:
            # Restore window geometry
            geom = settings.get("window_geometry")
            if isinstance(geom, dict):
                x = geom.get("x", 650)
                y = geom.get("y", 600)
                w = geom.get("width", 500)
                h = geom.get("height", 300)
                self.move(x, y)
                self.resize(w, h)

        except Exception:
            pass

    def _on_table_item_clicked(self, row, _column):
        """
        Table item clicked

        Args:
            row (int): clicked row index
            column (int): clicked column index
        """
        table = self.ui.tableWidget_entry
        if row < 0 or row >= table.rowCount():
            return

        item = table.item(row, 0)
        if item is None:
            return

        node_attr = item.text()
        node_name = node_attr.split('.')[0]

        if cmds.objExists(node_name):
            cmds.select(node_name, replace=True)
        else:
            cmds.warning(f"Node {node_name} does not exist.")

    def _on_section_resized(self, logical_index, _old_size, _new_size):
        """
        Table column resized

        Args:
            logical_index (int): column index
            _old_size (int): old size
            _new_size (int): new size
        """
        table = self.ui.tableWidget_entry
        for row in range(table.rowCount()):
            widget = table.cellWidget(row, logical_index)
            if widget is not None:
                model_index = table.model().index(row, logical_index)
                rect = table.visualRect(model_index)
                widget.setGeometry(rect)

    def _on_tree_item_clicked(self, item, _column):
        """
        Tree item clicked

        Args:
            item (QtWidgets.QTreeWidgetItem): clicked item
            column (int): clicked column
        """
        # if parent is None, selet node
        if item.parent() is None:
            node_attr = item.text(0)
            node_name = node_attr.split('.')[0]
            if cmds.objExists(node_name):
                cmds.select(node_name, replace=True)
            return

        # if child item, move time slider to frame
        frame = item.data(0, QtCore.Qt.UserRole)
        if frame is not None:
            cmds.currentTime(frame)
            print(frame)

    def _on_set_range_clicked(self):
        """
        Set range button clicked
        """
        self.set_framerange()

    def _on_register_button_clicked(self):
        """
        Register button clicked
        """
        node_name = self.ui.lineEdit_node.text().strip()
        attr_name = self.ui.lineEdit_attr.text().strip()
        self.register_clicked.emit(node_name, attr_name)

    def clear_input_fields(self):
        """
        Clear input fields
        """
        self.ui.lineEdit_node.clear()
        self.ui.lineEdit_attr.clear()

    def add_item_row(self, row, name, value):
        """
        Add item row to entry table

        Args:
            row (int): row index
            name (str): item name
            value (float): value
        """
        table = self.ui.tableWidget_entry
        table.insertRow(row)
        table.verticalHeader().setVisible(False)

        name_item = QtWidgets.QTableWidgetItem(name)
        name_item.setFlags(
            name_item.flags() & ~QtCore.Qt.ItemIsEditable
        )
        table.setItem(row, 0, name_item)

        spinbox = QtWidgets.QDoubleSpinBox()
        spinbox.setMinimum(-999999.0)
        spinbox.setMaximum(999999.0)
        spinbox.setValue(value)
        spinbox.setDecimals(2)
        spinbox.valueChanged.connect(
            lambda val, r=row: self.value_changed.emit(r, val)
        )

        # clear selection when spinbox gets focus
        spinbox.installEventFilter(self)

        table.setCellWidget(row, 1, spinbox)

    def remove_item_row(self, row):
        """
        Remove item row from entry table

        Args:
            row (int): row index
        """
        table = self.ui.tableWidget_entry
        if 0 <= row < table.rowCount():
            table.removeRow(row)

    def clear_items(self):
        """
        Clear all items from entry table
        """
        self.ui.tableWidget_entry.setRowCount(0)

    def get_selected_rows(self):
        """
        Get selected row indices from entry table

        Returns:
            list[int]: list of selected row indices
        """
        table = self.ui.tableWidget_entry
        selected_rows = set()
        for item in table.selectedItems():
            selected_rows.add(item.row())
        return sorted(list(selected_rows))

    def update_item_value(self, row, value):
        """
        Update item value in entry table

        Args:
            row (int): row index
            value (float): value
        """
        table = self.ui.tableWidget_entry
        if 0 <= row < table.rowCount():
            widget = table.cellWidget(row, 1)
            if isinstance(widget, QtWidgets.QDoubleSpinBox):
                widget.blockSignals(True)
                widget.setValue(value)
                widget.blockSignals(False)

    def display_scan_results(self, result_dict):
        """
        Display scan results in tree widget

        Args:
            result_dict (dict): return value of check_attr_spike
                {
                    "node.attr": [
                        (prev_frame, current_frame, prev_val, val, diff),
                        ...
                    ],
                    ...
                }
        """
        tree = self.ui.treeWidget_results
        tree.clear()

        for node_attr, spike_list in result_dict.items():
            # top level item (node attribute name)
            parent_item = QtWidgets.QTreeWidgetItem(tree)
            parent_item.setText(0, node_attr)
            parent_item.setText(1, f"{len(spike_list)} spike(s)")
            parent_item.setExpanded(True)

            # child item (each spike)
            for _prev_frame, current_frame, prev_val, val, diff in spike_list:
                child_item = QtWidgets.QTreeWidgetItem(parent_item)
                child_item.setText(0, f"Frame {current_frame}")
                child_item.setText(
                    1,
                    f"{prev_val:.2f} -> {val:.2f} (diff: {diff:.2f})"
                )
                child_item.setData(0, QtCore.Qt.UserRole, current_frame)

        checker.print_result(result_dict)

    def clear_scan_results(self):
        """
        Clear scan results
        """
        self.ui.treeWidget_results.clear()

    def set_framerange(self):
        """
        Set frame range
        """
        start_frame = int(cmds.playbackOptions(q=True, minTime=True))
        end_frame = int(cmds.playbackOptions(q=True, maxTime=True))
        self.ui.spinBox_start.setValue(start_frame)
        self.ui.spinBox_end.setValue(end_frame)

    def _add_debug_dummy_items(self):
        """
        Added debug dummy items
        """
        dummy_data = {
            "pSphere1.translateX": [
                (10, 11, 5.0, 25.0, 20.0),
                (15, 16, 10.0, 35.0, 25.0),
                (20, 21, 12.0, 50.0, 38.0),
            ],
            "pCube1.rotateY": [
                (5, 6, 0.0, 180.0, 180.0),
                (12, 13, 90.0, 270.0, 180.0),
            ]
        }
        self.display_scan_results(dummy_data)

    def _create_menu_bar(self, root_layout: QtWidgets.QBoxLayout):
        """
        Create menu bar

        Args:
            root_layout (QtWidgets.QBoxLayout): top level layout
        """
        menubar = QtWidgets.QMenuBar(self)
        help_menu = menubar.addMenu("Help")

        act_help = QtWidgets.QAction("Open Quick Start Document", self)
        act_help.triggered.connect(self._open_document)
        help_menu.addAction(act_help)

        if hasattr(self, "setMenuBar"):
            self.setMenuBar(menubar)
        else:
            root_layout.addWidget(menubar)
        self._menu_bar = menubar

    def _open_document(self):
        """
        Open Quick Start Document
        """
        try:
            pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                       "docs", "README.pdf"))
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(pdf_path)

            opened = False
            try:
                url = QtCore.QUrl.fromLocalFile(pdf_path)
                opened = bool(QtGui.QDesktopServices.openUrl(url))
            except Exception:
                opened = False

            if not opened:
                if platform.system() == "Windows":
                    try:
                        os.startfile(pdf_path)  # type: ignore[attr-defined]
                    except Exception:
                        subprocess.Popen(["cmd", "/c", "start", "", pdf_path],
                                         shell=True)
                else:
                    subprocess.Popen(["xdg-open", pdf_path])
        except Exception:
            cmds.warning(f"Failed to open Quick Start Document: {pdf_path}")
        else:
            print(f"Opened Quick Start Document: {pdf_path}")



def showUI():
    """
    Show GUI
    """
    controller = SpikeCheckerController()
    controller.show()
