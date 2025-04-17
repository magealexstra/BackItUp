import sys
import os
import collections
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QListWidget, QTextEdit, QPushButton, QSplitter, QTreeView,
    QLineEdit, QComboBox, QFileSystemModel, QProgressBar, QListWidgetItem,
    QStyle, QMessageBox, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, QDir, QModelIndex, Slot, QSize, QTimer, QCoreApplication # Removed qApp import
from PySide6.QtGui import QIcon, QPalette, QColor, QFont

# Local imports
from .constants import APP_NAME, CONFIG_DIR, DATA_DIR, DARK_STYLESHEET
from .utils import sanitize_filename, validate_schema_paths
from .schema_manager import SchemaManager
from .worker import BackupWorker

# Configure logging for the main application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - Main - %(message)s')


# --- Custom List Widget Item ---
class SchemaListItemWidget(QWidget):
    """Custom widget for displaying schema info in the QListWidget."""
    def __init__(self, schema_name, is_valid, parent=None):
        super().__init__(parent)
        self.schema_name = schema_name
        self.is_valid = is_valid

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2) # Original tighter margins
        layout.setSpacing(5)

        # Validity Indicator (Red 'X' if invalid)
        self.validity_label = QLabel("❌" if not is_valid else "")
        self.validity_label.setObjectName("InvalidPathIndicator") # For styling
        self.validity_label.setFixedWidth(20) # Original width for alignment
        layout.addWidget(self.validity_label)

        # Schema Name
        self.name_label = QLabel(schema_name)
        self.name_label.setMinimumWidth(150) # Smaller minimum width
        self.name_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        self.name_label.setWordWrap(False) # Don't wrap text
        layout.addWidget(self.name_label) # No stretch factor - use only needed width

        # Progress Bar (initially hidden or minimal)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False) # Show percentage later if needed
        self.progress_bar.setFixedHeight(15) # Original height
        # Allow progress bar to expand to fill all available space
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.progress_bar.setVisible(False) # Initially hidden
        layout.addWidget(self.progress_bar, 1) # Stretch factor of 1 - takes all remaining space

    def set_progress(self, value):
        self.progress_bar.setValue(value)
        self.progress_bar.setVisible(True)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat(f"{value}%")
        # Reset state property initially
        self.progress_bar.setProperty("state", "")
        self.progress_bar.setStyle(self.progress_bar.style()) # Force style refresh

    def set_status(self, status):
        """Sets the final state of the progress bar (success, failed, cancelled, warning)."""
        self.progress_bar.setValue(100) # Always fill bar on completion
        self.progress_bar.setVisible(True)
        self.progress_bar.setTextVisible(True)
        
        # Check if the status message is a warning (partial success)
        if status.lower().startswith("completed with warnings"):
            display_text = "Warning"
            property_state = "warning"
        else:
            display_text = status.capitalize()
            property_state = status.lower()
            
        self.progress_bar.setFormat(display_text)
        self.progress_bar.setProperty("state", property_state) # Set custom property for styling
        self.progress_bar.setStyle(self.progress_bar.style()) # Force style refresh

    def reset_status(self):
        """Resets the progress bar to its initial hidden state."""
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setProperty("state", "")
        self.progress_bar.setStyle(self.progress_bar.style())

    def update_validity(self, is_valid):
        self.is_valid = is_valid
        self.validity_label.setText("❌" if not is_valid else "")


# --- Main Application Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, 1200, 750) # Increased window size from 950x650 to 1200x750

        # Ensure Config and Data directories exist
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        self.schema_manager = SchemaManager()
        self.schemas = {} # Holds loaded schema data {schema_name: data}
        self.backup_queue = collections.deque()
        self.current_worker = None
        self.schema_list_items = {} # Maps schema_name to QListWidgetItem
        self.schema_custom_widgets = {} # Maps schema_name to SchemaListItemWidget

        self.setup_ui()
        self.apply_styles()
        self.connect_signals()

        self.load_and_display_schemas()

        # Timer to periodically check queue and start next backup
        self.queue_timer = QTimer(self)
        self.queue_timer.timeout.connect(self.process_backup_queue)
        self.queue_timer.start(1000) # Check every second

    def setup_ui(self):
        """Sets up the main UI layout and widgets."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5) # Add some padding
        main_layout.setSpacing(5) # Add spacing between elements

        # --- Tab Widget ---
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # --- Run Tab ---
        self.run_tab = QWidget()
        self.tab_widget.addTab(self.run_tab, "Run")
        self.setup_run_tab()

        # --- Edit Schemas Tab ---
        self.edit_tab = QWidget()
        self.tab_widget.addTab(self.edit_tab, "Edit Schemas")
        self.setup_edit_tab()

        # --- Bottom Status Bar ---
        self.status_bar_label = QLabel("Ready.")
        self.status_bar_label.setObjectName("StatusBar") # For specific styling
        self.status_bar_label.setFixedHeight(60) # Increased height to show more text
        self.status_bar_label.setWordWrap(True) # Allow text to wrap
        self.status_bar_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft) # Align text to top-left
        main_layout.addWidget(self.status_bar_label)

    def setup_run_tab(self):
        """Sets up the widgets and layout for the 'Run' tab."""
        layout = QVBoxLayout(self.run_tab)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1) # Allow splitter to take up space

        # Left Panel: Schema List
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.addWidget(QLabel("Backup Schemas:"))
        self.schema_list_widget = QListWidget()
        self.schema_list_widget.setObjectName("SchemaList") # For styling
        self.schema_list_widget.setMinimumWidth(400) # Increased minimum width from 300 to 400
        left_layout.addWidget(self.schema_list_widget)
        splitter.addWidget(left_panel)

        # Right Panel: Activity Log
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("Activity Log:"))
        self.activity_log = QTextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setFontFamily("monospace") # Good for logs
        right_layout.addWidget(self.activity_log)
        splitter.addWidget(right_panel)

        splitter.setSizes([450, 750]) # Increased left panel size proportion (from 350,600)

        # Bottom Icons/Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.queue_button = QPushButton("Queue Backup")
        self.queue_button.setIcon(QIcon(str(Path(__file__).parent / "ui/resources/icons/queue.svg")))
        self.queue_button.setIconSize(QSize(24, 24))
        self.queue_button.setEnabled(False) # Initially disabled
        button_layout.addWidget(self.queue_button)

        self.cancel_button = QPushButton("Cancel Running")
        self.cancel_button.setIcon(QIcon(str(Path(__file__).parent / "ui/resources/icons/cancel.svg")))
        self.cancel_button.setIconSize(QSize(24, 24))
        self.cancel_button.setEnabled(False) # Initially disabled
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

    def setup_edit_tab(self):
        """Sets up the widgets and layout for the 'Edit Schemas' tab."""
        layout = QVBoxLayout(self.edit_tab)

        # Top Bar: Schema Selection and Actions
        top_bar_layout = QHBoxLayout()
        top_bar_layout.addWidget(QLabel("Edit Schema:"))
        self.schema_selector_combo = QComboBox()
        self.schema_selector_combo.setMinimumWidth(200)
        self.schema_selector_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        top_bar_layout.addWidget(self.schema_selector_combo)

        self.new_schema_button = QPushButton("New")
        self.new_schema_button.setIcon(QIcon(str(Path(__file__).parent / "ui/resources/icons/add.svg")))
        self.new_schema_button.setIconSize(QSize(24, 24))
        top_bar_layout.addWidget(self.new_schema_button)

        self.save_schema_button = QPushButton("Save")
        # Using add.svg as a fallback since save.svg isn't available
        self.save_schema_button.setIcon(QIcon(str(Path(__file__).parent / "ui/resources/icons/add.svg")))
        self.save_schema_button.setIconSize(QSize(24, 24))
        self.save_schema_button.setEnabled(False) # Enable when changes are made
        top_bar_layout.addWidget(self.save_schema_button)

        self.delete_schema_button = QPushButton("Delete")
        self.delete_schema_button.setIcon(QIcon(str(Path(__file__).parent / "ui/resources/icons/delete.svg")))
        self.delete_schema_button.setIconSize(QSize(24, 24))
        self.delete_schema_button.setEnabled(False) # Enable when schema selected
        top_bar_layout.addWidget(self.delete_schema_button)
        layout.addLayout(top_bar_layout)


        # Main Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1) # Allow splitter to take up space

        # Left Panel: File System Tree
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.addWidget(QLabel("Select Paths:"))
        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath(QDir.rootPath()) # Start at root
        self.fs_model.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot | QDir.Filter.Hidden) # Show all dirs, files and hidden items

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.fs_model)
        # Set root to "" to potentially show drives/computer level
        self.tree_view.setRootIndex(self.fs_model.index(""))
        # Expand the root item slightly? Optional.
        # self.tree_view.expand(self.fs_model.index(""))
        self.tree_view.setMinimumWidth(300)
        # Hide unnecessary columns (size, type, date modified)
        self.tree_view.setColumnHidden(1, True)
        self.tree_view.setColumnHidden(2, True)
        self.tree_view.setColumnHidden(3, True)
        self.tree_view.setHeaderHidden(True) # Hide header row

        left_layout.addWidget(self.tree_view)
        splitter.addWidget(left_panel)

        # Right Panel: Schema Configuration
        right_panel = QWidget()
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setContentsMargins(10, 10, 10, 10)

        # Schema Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Schema Name:"))
        self.schema_name_edit = QLineEdit()
        name_layout.addWidget(self.schema_name_edit)
        right_layout.addLayout(name_layout)

        # Source Paths
        right_layout.addWidget(QLabel("Source Paths:"))
        self.source_paths_list = QListWidget()
        self.source_paths_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection) # Allow multi-select for removal
        right_layout.addWidget(self.source_paths_list)

        source_button_layout = QHBoxLayout()
        self.add_source_button = QPushButton("Add Selected to Sources")
        self.remove_source_button = QPushButton("Remove Selected Source(s)")
        source_button_layout.addWidget(self.add_source_button)
        source_button_layout.addWidget(self.remove_source_button)
        source_button_layout.addStretch()
        right_layout.addLayout(source_button_layout)

        # Destination Path
        right_layout.addWidget(QLabel("Destination Path:"))
        dest_layout = QHBoxLayout()
        self.destination_path_edit = QLineEdit()
        self.destination_path_edit.setReadOnly(True) # Set via button
        dest_layout.addWidget(self.destination_path_edit)
        self.set_destination_button = QPushButton("Set Selected as Destination")
        dest_layout.addWidget(self.set_destination_button)
        right_layout.addLayout(dest_layout)

        right_layout.addStretch() # Push elements to top
        splitter.addWidget(right_panel)

        splitter.setSizes([350, 600]) # Initial sizes

    def apply_styles(self):
        """Applies the dark stylesheet."""
        self.setStyleSheet(DARK_STYLESHEET)
        # Optional: Force fusion style for more consistency if needed
        # QApplication.setStyle(QStyleFactory.create('Fusion'))

    def connect_signals(self):
        """Connects UI signals to their slots."""
        # Run Tab
        self.schema_list_widget.itemSelectionChanged.connect(self.update_run_button_state)
        self.queue_button.clicked.connect(self.queue_selected_backup)
        self.cancel_button.clicked.connect(self.cancel_current_backup)

        # Edit Tab
        self.schema_selector_combo.currentIndexChanged.connect(self.load_selected_schema_for_edit)
        self.new_schema_button.clicked.connect(self.clear_edit_fields_for_new)
        self.save_schema_button.clicked.connect(self.save_current_schema)
        self.delete_schema_button.clicked.connect(self.delete_selected_schema)

        self.add_source_button.clicked.connect(self.add_selected_path_to_sources)
        self.remove_source_button.clicked.connect(self.remove_selected_sources)
        self.set_destination_button.clicked.connect(self.set_selected_path_as_destination)

        # Enable save button when fields change
        self.schema_name_edit.textChanged.connect(lambda: self.save_schema_button.setEnabled(True))
        self.source_paths_list.model().rowsInserted.connect(lambda: self.save_schema_button.setEnabled(True))
        self.source_paths_list.model().rowsRemoved.connect(lambda: self.save_schema_button.setEnabled(True))
        self.destination_path_edit.textChanged.connect(lambda: self.save_schema_button.setEnabled(True))


    # --- Schema Loading and Display ---
    @Slot()
    def load_and_display_schemas(self):
        """Loads schemas from disk and updates both UI lists."""
        logging.info("Reloading schemas...")
        self.schemas = self.schema_manager.load_schemas()
        sorted_schema_names = sorted(self.schemas.keys())

        # --- Update Run Tab List ---
        self.schema_list_widget.clear()
        self.schema_list_items.clear()
        self.schema_custom_widgets.clear() # Clear old custom widgets
        for name in sorted_schema_names:
            schema_data = self.schemas[name]
            is_valid = schema_data.get('_is_valid', True) # Default to valid if key missing

            item = QListWidgetItem(self.schema_list_widget)
            widget = SchemaListItemWidget(name, is_valid)

            # Store references
            self.schema_list_items[name] = item
            self.schema_custom_widgets[name] = widget

            # Force a minimum height for proper text display with larger font
            size_hint = widget.sizeHint()
            size_hint.setHeight(max(50, size_hint.height())) # Ensure minimum height of 50px
            size_hint.setWidth(size_hint.width() + 50) # Add 50px extra width padding
            
            item.setSizeHint(size_hint) # Set the adjusted size hint
            self.schema_list_widget.addItem(item)
            self.schema_list_widget.setItemWidget(item, widget)

        # --- Update Edit Tab ComboBox ---
        self.schema_selector_combo.blockSignals(True) # Prevent triggering load while populating
        self.schema_selector_combo.clear()
        self.schema_selector_combo.addItem("") # Add blank option
        self.schema_selector_combo.addItems(sorted_schema_names)
        self.schema_selector_combo.blockSignals(False)

        self.clear_edit_fields() # Clear fields after reloading
        self.update_run_button_state()
        self.update_edit_delete_button_state()
        logging.info(f"Loaded {len(self.schemas)} schemas.")
        self.update_status_bar(f"Loaded {len(self.schemas)} schemas.")


    @Slot()
    def update_run_button_state(self):
        """Enables/disables Run tab buttons based on selection and state."""
        selected_items = self.schema_list_widget.selectedItems()
        is_schema_selected = bool(selected_items)
        is_worker_running = self.current_worker is not None and self.current_worker.isRunning()

        can_queue = False
        if is_schema_selected:
            # Check if the selected schema is valid
            item_widget = self.schema_list_widget.itemWidget(selected_items[0])
            if item_widget and item_widget.is_valid:
                can_queue = True

        self.queue_button.setEnabled(can_queue)
        self.cancel_button.setEnabled(is_worker_running)

    # --- Run Tab Logic ---
    @Slot()
    def queue_selected_backup(self):
        """Adds the selected valid schema to the backup queue."""
        selected_items = self.schema_list_widget.selectedItems()
        if not selected_items:
            return

        item_widget = self.schema_list_widget.itemWidget(selected_items[0])
        schema_name = item_widget.schema_name

        if not item_widget.is_valid:
            self.update_status_bar(f"Cannot queue '{schema_name}': Contains invalid paths.", error=True)
            return

        if schema_name not in self.backup_queue:
            self.backup_queue.append(schema_name)
            self.update_status_bar(f"'{schema_name}' added to queue. Queue size: {len(self.backup_queue)}")
            logging.info(f"Added '{schema_name}' to queue. Queue: {list(self.backup_queue)}")
        else:
            self.update_status_bar(f"'{schema_name}' is already in the queue.")

    @Slot()
    def process_backup_queue(self):
        """Checks the queue and starts the next backup if idle."""
        if self.current_worker is None or not self.current_worker.isRunning():
            if self.backup_queue:
                schema_name = self.backup_queue.popleft()
                logging.info(f"Dequeuing '{schema_name}'. Queue remaining: {len(self.backup_queue)}")
                if schema_name in self.schemas:
                    schema_data = self.schemas[schema_name]
                    self.start_backup(schema_data)
                else:
                    logging.warning(f"Schema '{schema_name}' not found in loaded schemas. Skipping.")
                    self.update_status_bar(f"Error: Schema '{schema_name}' not found. Skipping.", error=True)
                    # Try processing next item immediately
                    QTimer.singleShot(10, self.process_backup_queue) # Use singleShot to avoid recursion depth issues

    def start_backup(self, schema_data):
        """Starts the BackupWorker thread for the given schema."""
        schema_name = schema_data['schema_name']
        logging.info(f"Attempting to start backup for: {schema_name}")

        # Reset progress bar for this schema
        if schema_name in self.schema_custom_widgets:
            self.schema_custom_widgets[schema_name].reset_status()
            self.schema_custom_widgets[schema_name].set_progress(0) # Show 0%

        self.current_worker = BackupWorker(schema_data)

        # Connect worker signals
        self.current_worker.progressUpdated.connect(self.update_progress)
        self.current_worker.logMessage.connect(self.append_log_message)
        self.current_worker.jobFinished.connect(self.handle_job_finished)
        self.current_worker.diskSpaceError.connect(self.handle_worker_error)
        self.current_worker.validationError.connect(self.handle_worker_error)
        self.current_worker.finished.connect(self.worker_thread_finished) # For cleanup

        self.current_worker.start()
        self.update_status_bar(f"Running backup for '{schema_name}'...")
        self.activity_log.clear() # Clear log for new job
        self.append_log_message(schema_name, f"--- Starting Backup: {schema_name} ---")
        self.update_run_button_state() # Disable queue, enable cancel

    @Slot()
    def cancel_current_backup(self):
        """Requests cancellation of the currently running backup."""
        if self.current_worker and self.current_worker.isRunning():
            logging.info(f"User requested cancellation for schema: {self.current_worker.schema_name}")
            self.update_status_bar(f"Attempting to cancel backup for '{self.current_worker.schema_name}'...")
            self.current_worker.cancel()
            # UI updates (like progress bar state) will happen via jobFinished signal
        else:
            logging.warning("Cancel requested but no worker is running.")
            self.update_status_bar("No backup is currently running.")

    @Slot(str, int)
    def update_progress(self, schema_name, percentage):
        """Updates the progress bar for the specific schema."""
        if schema_name in self.schema_custom_widgets:
            self.schema_custom_widgets[schema_name].set_progress(percentage)

    @Slot(str, str)
    def append_log_message(self, schema_name, message):
        """Appends a message to the activity log."""
        # Only append if the message is from the currently running job
        if self.current_worker and self.current_worker.schema_name == schema_name:
            self.activity_log.append(message)

    @Slot(str, bool, str)
    def handle_job_finished(self, schema_name, success, status_message):
        """Handles the completion, failure, or cancellation of a backup job."""
        logging.info(f"Job finished for '{schema_name}'. Success: {success}, Message: {status_message}")

        status = "unknown"
        if "Cancelled" in status_message:
            status = "cancelled"
            self.update_status_bar(f"Backup for '{schema_name}' cancelled.")
        elif success:
            status = "success"
            self.update_status_bar(f"Backup for '{schema_name}' completed successfully.")
        else:
            status = "failed"
            self.update_status_bar(f"Backup for '{schema_name}' failed: {status_message}", error=True)

        # Update the persistent progress bar state
        if schema_name in self.schema_custom_widgets:
            self.schema_custom_widgets[schema_name].set_status(status)

        self.append_log_message(schema_name, f"--- Finished: {schema_name} ({status_message}) ---")

        # Worker cleanup happens in worker_thread_finished slot

    @Slot(str, str)
    def handle_worker_error(self, schema_name, error_message):
        """Handles specific errors emitted by the worker before or during run."""
        logging.error(f"Worker error for '{schema_name}': {error_message}")
        self.update_status_bar(f"Error for '{schema_name}': {error_message}", error=True)
        # The jobFinished signal will likely follow, setting the final progress bar state

    @Slot()
    def worker_thread_finished(self):
        """Called when the worker thread actually finishes execution."""
        logging.info("Worker thread finished.")
        if self.current_worker:
             # Ensure signals are disconnected if object persists briefly
            try:
                self.current_worker.progressUpdated.disconnect(self.update_progress)
                self.current_worker.logMessage.disconnect(self.append_log_message)
                self.current_worker.jobFinished.disconnect(self.handle_job_finished)
                self.current_worker.diskSpaceError.disconnect(self.handle_worker_error)
                self.current_worker.validationError.disconnect(self.handle_worker_error)
                self.current_worker.finished.disconnect(self.worker_thread_finished)
            except RuntimeError as e:
                 logging.warning(f"Error disconnecting worker signals: {e}") # May happen if already disconnected

            self.current_worker = None # Allow garbage collection

        self.update_run_button_state() # Re-enable queue button if needed, disable cancel
        # Trigger queue check shortly after to start next job if any
        QTimer.singleShot(100, self.process_backup_queue)


    # --- Edit Tab Logic ---
    @Slot()
    def load_selected_schema_for_edit(self):
        """Loads the schema selected in the ComboBox into the edit fields."""
        schema_name = self.schema_selector_combo.currentText()
        self.clear_edit_fields() # Clear first

        if schema_name and schema_name in self.schemas:
            schema_data = self.schemas[schema_name]
            self.schema_name_edit.setText(schema_data.get('schema_name', ''))
            self.source_paths_list.addItems(schema_data.get('sources', []))
            self.destination_path_edit.setText(schema_data.get('destination', ''))
            self.update_edit_delete_button_state()
            self.save_schema_button.setEnabled(False) # Disable save initially after loading
            self.update_status_bar(f"Loaded '{schema_name}' for editing.")
        else:
             self.update_edit_delete_button_state()
             self.save_schema_button.setEnabled(False)


    @Slot()
    def clear_edit_fields_for_new(self):
        """Clears the edit fields to define a new schema."""
        self.schema_selector_combo.setCurrentIndex(0) # Select blank item
        self.clear_edit_fields()
        self.schema_name_edit.setFocus() # Focus on name field
        self.save_schema_button.setEnabled(False) # Disable save until something is entered
        self.update_status_bar("Enter details for new schema.")

    def clear_edit_fields(self):
        """Helper to clear all edit fields."""
        self.schema_name_edit.clear()
        self.source_paths_list.clear()
        self.destination_path_edit.clear()
        self.update_edit_delete_button_state()
        self.save_schema_button.setEnabled(False)

    @Slot()
    def update_edit_delete_button_state(self):
        """Enables/disables Edit tab delete button based on selection."""
        is_schema_selected = bool(self.schema_selector_combo.currentText())
        self.delete_schema_button.setEnabled(is_schema_selected)
        # Save button is handled by field changes

    @Slot()
    def add_selected_path_to_sources(self):
        """Adds the path selected in the QTreeView to the sources list."""
        selected_indexes = self.tree_view.selectedIndexes()
        if selected_indexes:
            # Use the first column index (column 0)
            index = selected_indexes[0]
            filepath = self.fs_model.filePath(index)
            
            # If this is the first source and schema name is empty, use folder name
            if self.source_paths_list.count() == 0 and not self.schema_name_edit.text():
                # Extract folder name from the path
                folder_name = Path(filepath).name
                if folder_name:
                    self.schema_name_edit.setText(folder_name)
                    
            # Check if it's already in the list
            current_sources = [self.source_paths_list.item(i).text() for i in range(self.source_paths_list.count())]
            if filepath not in current_sources:
                self.source_paths_list.addItem(filepath)
                self.update_status_bar(f"Added source: {filepath}")
            else:
                self.update_status_bar(f"Source already exists: {filepath}")

    @Slot()
    def remove_selected_sources(self):
        """Removes the selected item(s) from the source paths list."""
        selected_items = self.source_paths_list.selectedItems()
        if not selected_items:
            self.update_status_bar("No source selected to remove.")
            return

        for item in selected_items:
            row = self.source_paths_list.row(item)
            self.source_paths_list.takeItem(row)
            self.update_status_bar(f"Removed source: {item.text()}")

    @Slot()
    def set_selected_path_as_destination(self):
        """Sets the path selected in the QTreeView as the destination."""
        selected_indexes = self.tree_view.selectedIndexes()
        if selected_indexes:
             # Use the first column index (column 0)
            index = selected_indexes[0]
            filepath = self.fs_model.filePath(index)
            # Ensure it's a directory
            if Path(filepath).is_dir():
                self.destination_path_edit.setText(filepath)
                self.update_status_bar(f"Set destination: {filepath}")
            else:
                self.update_status_bar("Destination must be a directory.", error=True)

    @Slot()
    def save_current_schema(self):
        """Gathers data from edit fields and saves the schema."""
        schema_name = self.schema_name_edit.text().strip()
        if not schema_name:
            self.update_status_bar("Schema name cannot be empty.", error=True)
            return

        sources = [self.source_paths_list.item(i).text() for i in range(self.source_paths_list.count())]
        destination = self.destination_path_edit.text().strip()

        if not sources:
            self.update_status_bar("Schema must have at least one source path.", error=True)
            return
        if not destination:
            self.update_status_bar("Schema must have a destination path.", error=True)
            return

        schema_data = {
            'schema_name': schema_name,
            'sources': sources,
            'destination': destination
        }

        # Check for overwrite
        original_schema_name = self.schema_selector_combo.currentText()
        sanitized_new_name = sanitize_filename(schema_name)
        filepath_new = self.schema_manager.get_schema_filepath(schema_name)

        # If the sanitized filename exists AND it's not the file corresponding to the schema we are currently editing
        if filepath_new.exists() and (not original_schema_name or self.schema_manager.get_schema_filepath(original_schema_name) != filepath_new):
             # Simple overwrite confirmation via status bar - requires second click
             if self.save_schema_button.property("confirm_overwrite") == schema_name:
                 # Second click confirmed
                 self.save_schema_button.setProperty("confirm_overwrite", None) # Reset confirmation state
                 self._perform_save(schema_data)
             else:
                 # First click - ask for confirmation
                 self.update_status_bar(f"File '{sanitized_new_name}.yaml' exists. Click Save again to overwrite.", error=True)
                 self.save_schema_button.setProperty("confirm_overwrite", schema_name) # Store name for confirmation check
                 # Change button text/style slightly? (Optional)
                 # self.save_schema_button.setText("Confirm Save")
                 return # Don't save yet
        else:
            # No conflict or saving over itself, proceed directly
            self.save_schema_button.setProperty("confirm_overwrite", None) # Clear any previous confirmation state
            self._perform_save(schema_data)

    def _perform_save(self, schema_data):
        """Internal method to perform the actual save operation."""
        schema_name = schema_data['schema_name']
        success, message = self.schema_manager.save_schema(schema_data)
        if success:
            self.update_status_bar(message)
            self.save_schema_button.setEnabled(False) # Disable save after successful save
            self.load_and_display_schemas() # Reload all schemas
            # Re-select the saved schema in the combo box
            index = self.schema_selector_combo.findText(schema_name)
            if index >= 0:
                self.schema_selector_combo.setCurrentIndex(index)
        else:
            self.update_status_bar(message, error=True)
        # Reset button text if it was changed for confirmation
        # self.save_schema_button.setText("Save")


    @Slot()
    def delete_selected_schema(self):
        """Deletes the schema selected in the ComboBox."""
        schema_name = self.schema_selector_combo.currentText()
        if not schema_name:
            self.update_status_bar("No schema selected to delete.", error=True)
            return

        # Simple confirmation via status bar - requires second click
        if self.delete_schema_button.property("confirm_delete") == schema_name:
            # Second click confirmed
            self.delete_schema_button.setProperty("confirm_delete", None) # Reset confirmation state
            success, message = self.schema_manager.delete_schema(schema_name)
            self.update_status_bar(message, error=not success)
            if success:
                self.load_and_display_schemas() # Reload schemas, which clears edit fields
            # Reset button text/style if changed
            # self.delete_schema_button.setText("Delete")
        else:
             # First click - ask for confirmation
            self.update_status_bar(f"Really delete '{schema_name}'? Click Delete again to confirm.", error=True)
            self.delete_schema_button.setProperty("confirm_delete", schema_name) # Store name for confirmation check
            # Change button text/style slightly? (Optional)
            # self.delete_schema_button.setText("Confirm Delete")


    # --- Status Bar ---
    @Slot(str, bool)
    def update_status_bar(self, message, error=False):
        """Updates the text and style of the bottom status bar."""
        self.status_bar_label.setText(message)
        if error:
            # Apply a style to indicate error (e.g., red text)
            # This requires the stylesheet to handle a property or use rich text
            self.status_bar_label.setStyleSheet("QLabel#StatusBar { color: #cc3333; background-color: #353535; border-top: 1px solid #4f4f4f; font-weight: bold; padding: 3px; }")
        else:
            # Reset to default style
             self.status_bar_label.setStyleSheet("QLabel#StatusBar { color: #ffffff; background-color: #353535; border-top: 1px solid #4f4f4f; font-weight: bold; padding: 3px; }")
        logging.info(f"Status Bar: {message}")


    # --- Application Exit ---
    def closeEvent(self, event):
        """Handles the main window closing event."""
        logging.info("Close event triggered.")
        if self.current_worker and self.current_worker.isRunning():
            # Prompt user? Or just try to cancel? Let's try to cancel.
            logging.warning("Backup in progress. Attempting to cancel...")
            self.update_status_bar("Backup in progress. Attempting to cancel before exit...")
            self.current_worker.cancel()
            # Give it a moment to try and terminate
            # In a real app, might wait briefly or ask user to confirm exit
            # self.current_worker.wait(500) # Wait max 500ms - might block GUI
            # For simplicity, we'll just let it try to terminate and exit
            # Note: rsync might continue if termination fails quickly

        logging.info("Exiting BackItUp.")
        event.accept()


# --- Entry Point ---
def main():
    app = QApplication(sys.argv)
    # app.setStyle('Fusion') # Optional: Enforce Fusion style
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
