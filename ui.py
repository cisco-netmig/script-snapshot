import logging
import os
from PyQt5 import QtWidgets, QtGui, QtCore
from .workers import RunEvent


class Ui_Form:
    """
    A PyQt5 UI form class for configuring and executing network diagnostics.

    """

    def setup_ui(self, form):
        """
        Set up the layout and UI elements of the diagnostics form.

        Args:
            form (QWidget): The parent widget to apply the layout and components to.
        """
        self.grid_layout = QtWidgets.QGridLayout(form)

        # Devices group box
        self.device_group_box = QtWidgets.QGroupBox("Devices", form)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        size_policy.setVerticalStretch(80)
        self.device_group_box.setSizePolicy(size_policy)

        self.device_layout = QtWidgets.QGridLayout(self.device_group_box)
        self.device_layout.setContentsMargins(5, 5, 5, 5)
        self.device_layout.setSpacing(0)

        self.devices_text_edit = QtWidgets.QPlainTextEdit(self.device_group_box)
        self.device_layout.addWidget(self.devices_text_edit)

        self.grid_layout.addWidget(self.device_group_box, 0, 0)

        # Commands group box
        self.commands_group_box = QtWidgets.QGroupBox("Commands", form)
        self.commands_layout = QtWidgets.QGridLayout(self.commands_group_box)
        self.commands_layout.setContentsMargins(5, 5, 5, 5)
        self.commands_layout.setSpacing(0)

        self.commands_text_edit = QtWidgets.QPlainTextEdit(self.commands_group_box)
        self.commands_layout.addWidget(self.commands_text_edit)

        self.grid_layout.addWidget(self.commands_group_box, 0, 1)

        # Output type combo box
        self.type_combo_box = QtWidgets.QComboBox(form)
        self.type_combo_box.setMaximumSize(QtCore.QSize(100, 16777215))
        self.type_combo_box.addItems(["Text", "Excel"])
        self.grid_layout.addWidget(self.type_combo_box, 1, 0)

        # Actions group box
        self.actions_group_box = QtWidgets.QGroupBox("Actions", form)
        self.actions_layout = QtWidgets.QGridLayout(self.actions_group_box)

        self.run_button = QtWidgets.QPushButton("Run", self.actions_group_box)
        self.run_button.setMinimumSize(QtCore.QSize(120, 0))
        self.run_button.setMaximumSize(QtCore.QSize(100, 16777215))
        self.run_button.setIcon(self._get_icon("run-command"))
        self.run_button.setIconSize(QtCore.QSize(20, 20))
        self.run_button.setCheckable(True)
        self.actions_layout.addWidget(self.run_button, 0, 0)

        spacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.actions_layout.addItem(spacer, 0, 1)

        self.grid_layout.addWidget(self.actions_group_box, 2, 0, 1, 2)

        # Progress bar
        self.progress_bar = QtWidgets.QProgressBar(form)
        self.progress_bar.setProperty("value", 0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.grid_layout.addWidget(self.progress_bar, 3, 0, 1, 2)

        # Outputs group box
        self.outputs_group_box = QtWidgets.QGroupBox("Outputs", form)
        self.outputs_layout = QtWidgets.QGridLayout(self.outputs_group_box)
        self.outputs_layout.setHorizontalSpacing(50)

        self.folder_button = QtWidgets.QPushButton("Folder", self.outputs_group_box)
        self.folder_button.setMinimumSize(QtCore.QSize(120, 0))
        self.folder_button.setIcon(self._get_icon("opened-folder"))
        self.folder_button.setIconSize(QtCore.QSize(20, 20))
        self.folder_button.setCheckable(True)
        self.outputs_layout.addWidget(self.folder_button, 0, 1)

        self.outputs_layout.addItem(
            QtWidgets.QSpacerItem(86, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), 0, 2)

        self.grid_layout.addWidget(self.outputs_group_box, 4, 0, 1, 2)

    def _get_icon(self, filename: str) -> QtGui.QIcon:
        """
        Load an icon from the assets directory.

        Args:
            filename (str): Name of the icon file (without extension).

        Returns:
            QtGui.QIcon: The QIcon object.
        """
        icon_path = os.path.join(os.path.dirname(__file__), "assets", f"{filename}.ico")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(icon_path), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        return icon


class Form(QtWidgets.QWidget, Ui_Form):
    """
    UI Form class.

    """

    def __init__(self, parent=None, **kwargs):
        """
        Initialize the UI form.

        Args:
            parent (QWidget): Parent widget.
            **kwargs: Additional arguments for customization or metadata.
        """
        super().__init__(parent)
        self.kwargs = kwargs
        self.session = kwargs.get("session")

        self.setup_ui(self)

        self.output_dir = os.path.join(self.kwargs.get("output_dir"),
                                       os.path.basename(os.path.dirname(__file__).upper()))

        self.run_button.clicked.connect(self.run_start_event)
        self.folder_button.clicked.connect(lambda: self.open_path(self.output_dir))

        logging.debug("Form initialized with output_dir: %s", self.output_dir)

    def run_start_event(self):
        """
        Handles the logic to start the worker thread for running the task.
        Disables the run button and initializes the worker thread.
        """
        self.run_button.setEnabled(False)
        self.progress_bar.setValue(0)

        self.run_worker = RunEvent(self)
        self.run_worker.start()

        self.run_worker.add_progress.connect(self.update_progress)
        self.run_worker.finished.connect(self.run_finish_event)

        logging.info("Worker thread started")

    def run_finish_event(self):
        """
        Handles UI updates and alerts the user when the task is completed.
        """
        self.run_button.setEnabled(True)
        self.progress_bar.setValue(100)

        QtWidgets.QMessageBox.information(self, "Info", "Task completed!!")

        logging.info("Worker task completed and UI updated")

    def update_progress(self, value):
        """
        Updates the progress bar with the received value.

        Args:
            value (int): The increment value to add to the current progress.
        """
        new_value = self.progress_bar.value() + int(value)
        self.progress_bar.setValue(new_value)

        logging.debug("Progress bar updated: %d", new_value)

    def open_path(self, path: str):
        """
        Open a file or directory using the system's default handler.

        Args:
            path (str): File or directory path to open.
        """
        try:
            if path and os.path.exists(path):
                logging.info(f"Opening path: {path}")
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))
            else:
                logging.error(f"Invalid or non-existent path: {path}")
        except Exception as e:
            logging.exception(f"Failed to open path: {e}")
