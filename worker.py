import subprocess
import shlex
import re
import os
import shutil
import logging
from pathlib import Path

from PySide6.QtCore import QThread, Signal, QObject

from .utils import validate_schema_paths

# Configure logging for the worker
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - Worker - %(message)s')

class BackupWorker(QThread):
    """
    Worker thread to execute a single rsync backup job.
    """
    # Signals
    progressUpdated = Signal(str, int) # schema_name, percentage
    logMessage = Signal(str, str)      # schema_name, message
    jobFinished = Signal(str, bool, str) # schema_name, success (bool), status_message
    diskSpaceError = Signal(str, str)  # schema_name, error_message
    validationError = Signal(str, str) # schema_name, error_message

    def __init__(self, schema_data, parent=None):
        super().__init__(parent)
        if not schema_data or 'schema_name' not in schema_data:
            raise ValueError("Schema data is invalid or missing 'schema_name'")
        self.schema_data = schema_data
        self.schema_name = schema_data['schema_name']
        self._is_cancelled = False
        self._process = None

    def run(self):
        """Executes the backup process."""
        logging.info(f"Worker started for schema: {self.schema_name}")
        self.logMessage.emit(self.schema_name, f"Starting backup for '{self.schema_name}'...")

        # --- Pre-flight Checks ---
        # 1. Re-validate paths just before running
        is_valid, invalid_paths = validate_schema_paths(self.schema_data)
        if not is_valid:
            error_msg = f"Path validation failed before starting: {', '.join(invalid_paths)}"
            logging.error(f"[{self.schema_name}] {error_msg}")
            self.validationError.emit(self.schema_name, error_msg)
            self.jobFinished.emit(self.schema_name, False, "Path validation failed")
            return

        # 2. Check destination disk space
        destination = self.schema_data.get('destination')
        try:
            # Estimate required space (crude: sum of source sizes)
            # A more accurate check might be complex (consider existing files, etc.)
            # For now, just check if destination has *some* reasonable free space.
            # Let's require at least 100MB free as a basic check.
            free_space_threshold = 100 * 1024 * 1024 # 100 MB
            usage = shutil.disk_usage(destination)
            if usage.free < free_space_threshold:
                 # A more sophisticated check could try to estimate source size
                 # total_source_size = sum(p.stat().st_size for s in self.schema_data['sources'] for p in Path(s).rglob('*') if p.is_file())
                 # if usage.free < total_source_size: # This is still not perfect due to rsync behavior
                error_msg = f"Insufficient disk space at destination '{destination}'. Free: {usage.free / (1024*1024):.2f} MB"
                logging.error(f"[{self.schema_name}] {error_msg}")
                self.diskSpaceError.emit(self.schema_name, error_msg)
                self.jobFinished.emit(self.schema_name, False, "Insufficient disk space")
                return
        except FileNotFoundError:
            error_msg = f"Destination directory '{destination}' not found for disk space check."
            logging.error(f"[{self.schema_name}] {error_msg}")
            self.validationError.emit(self.schema_name, error_msg) # Treat as validation error
            self.jobFinished.emit(self.schema_name, False, "Destination not found")
            return
        except Exception as e:
            error_msg = f"Error checking disk space for '{destination}': {e}"
            logging.error(f"[{self.schema_name}] {error_msg}")
            # Decide if this is fatal or just a warning? Let's make it fatal.
            self.diskSpaceError.emit(self.schema_name, error_msg)
            self.jobFinished.emit(self.schema_name, False, "Disk space check error")
            return

        # --- Construct rsync Command ---
        sources = self.schema_data.get('sources', [])
        source_paths = [str(s) for s in sources]
        dest_path = str(destination)

        # Use -a (archive), --info=progress2 (parsable progress), --delete (optional, consider adding later)
        # Add --no-i-r to potentially speed up progress reporting on large numbers of files
        rsync_command = ["rsync", "-a", "--info=progress2", "--no-i-r"] + source_paths + [dest_path]
        command_str = " ".join(rsync_command)
        logging.info(f"Executing command: {command_str}")
        self.logMessage.emit(self.schema_name, f"Running: {command_str}")

        # --- Execute rsync ---
        try:
            self._process = subprocess.Popen(
                rsync_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace', # Handle potential encoding errors
                bufsize=1 # Line buffered
            )

            # Monitor stdout for progress
            while True:
                if self._is_cancelled:
                    logging.info(f"Cancellation requested for schema: {self.schema_name}")
                    self.terminate_process()
                    self.jobFinished.emit(self.schema_name, False, "Cancelled")
                    return

                line = self._process.stdout.readline()
                if not line and self._process.poll() is not None:
                    break # Process finished

                if line:
                    self.logMessage.emit(self.schema_name, line.strip())
                    # Example rsync --info=progress2 output line:
                    # 1,234,567 10%  10.00MB/s 0:00:10 (xfr#1, to-chk=10/20)
                    # Sometimes it might just be a filename
                    match = re.search(r'\s+(\d+)%\s+', line)
                    if match:
                        progress = int(match.group(1))
                        self.progressUpdated.emit(self.schema_name, progress)

            # Capture any remaining stderr
            stderr_output = self._process.stderr.read()
            if stderr_output:
                logging.warning(f"[{self.schema_name}] rsync stderr: {stderr_output.strip()}")
                self.logMessage.emit(self.schema_name, f"STDERR: {stderr_output.strip()}")

            return_code = self._process.wait() # Wait for process to ensure it's finished

            if self._is_cancelled: # Check again after process finished naturally
                 self.jobFinished.emit(self.schema_name, False, "Cancelled")
                 return

            # Return code 24 is a special case for rsync - it means "some files vanished"
            # This is common when backing up actively used directories like browser data
            if return_code == 0:
                logging.info(f"Schema '{self.schema_name}' backup completed successfully.")
                self.progressUpdated.emit(self.schema_name, 100) # Ensure 100% on success
                self.jobFinished.emit(self.schema_name, True, "Completed")
            elif return_code == 24:
                # Treat code 24 as a partial success with warning
                warning_msg = "Completed with warnings: Some files changed during transfer."
                logging.warning(f"[{self.schema_name}] {warning_msg} Return code: {return_code}")
                if stderr_output:
                    self.logMessage.emit(self.schema_name, f"Warning: {stderr_output.strip()}")
                    warning_msg += f" Details: {stderr_output.strip()}"
                self.progressUpdated.emit(self.schema_name, 100)
                # Pass True to indicate partial success, not complete failure
                self.jobFinished.emit(self.schema_name, True, warning_msg)
            else:
                error_msg = f"rsync failed with return code {return_code}."
                logging.error(f"[{self.schema_name}] {error_msg}")
                # Add stderr to the message if available
                if stderr_output:
                    error_msg += f" Stderr: {stderr_output.strip()}"
                self.jobFinished.emit(self.schema_name, False, error_msg)

        except FileNotFoundError:
            error_msg = "rsync command not found. Please ensure rsync is installed and in your PATH."
            logging.error(f"[{self.schema_name}] {error_msg}")
            self.jobFinished.emit(self.schema_name, False, error_msg)
        except Exception as e:
            error_msg = f"An unexpected error occurred during backup: {e}"
            logging.exception(f"[{self.schema_name}] Unexpected error") # Log full traceback
            self.jobFinished.emit(self.schema_name, False, error_msg)
        finally:
            self._process = None # Clear process reference

    def cancel(self):
        """Signals the worker to cancel the backup."""
        logging.info(f"Cancel method called for schema: {self.schema_name}")
        self._is_cancelled = True
        self.terminate_process() # Attempt immediate termination

    def terminate_process(self):
        """Terminates the running rsync process if it exists."""
        if self._process and self._process.poll() is None: # Check if process exists and is running
            try:
                logging.warning(f"Terminating rsync process (PID: {self._process.pid}) for schema: {self.schema_name}")
                self._process.terminate() # Send SIGTERM
                # Optionally, wait a short time and send SIGKILL if it doesn't terminate
                # self._process.wait(timeout=1)
            except ProcessLookupError:
                 logging.info(f"Process for {self.schema_name} already finished.")
            except Exception as e:
                logging.error(f"Error terminating process for schema {self.schema_name}: {e}")
            finally:
                self._process = None # Ensure reference is cleared

    def __del__(self):
        # Ensure thread quits properly if deleted
        self.wait()
