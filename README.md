# BackItUp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.6+-brightgreen)](https://python.org/)
[![PySide6](https://img.shields.io/badge/PySide6-6.0+-blue)](https://wiki.qt.io/Qt_for_Python)
[![rsync](https://img.shields.io/badge/rsync-Required-orange)](https://rsync.samba.org/)

A desktop backup application that provides a simple, intuitive GUI for managing and executing backup operations using rsync. It allows users to define backup schemas with multiple source locations and destinations, validate paths before backup, and monitor progress in real-time.

## 📋 Table of Contents

- [🔧 Features](#-features)
- [⚙️ Requirements](#️-requirements)
- [⬇️ Installation](#️-installation)
- [🚀 Usage](#-usage)
  - [Starting the Application](#starting-the-application)
  - [Creating a Backup Schema](#creating-a-backup-schema)
  - [Running a Backup](#running-a-backup)
  - [Monitoring Progress](#monitoring-progress)
  - [Canceling a Backup](#canceling-a-backup)
- [🏗️ Architecture](#️-architecture)
  - [Core Components](#core-components)
  - [Configuration Files](#configuration-files)
- [❓ Troubleshooting](#-troubleshooting)
- [📜 License](#-license)

## 🔧 Features

- 🖥️ **Visual Backup Interface**: Dark-themed GUI with progress indicators and status tracking
- 📝 **Backup Schema Management**: Create, edit, and manage multiple backup configurations
- ✅ **Path Validation**: Ensures all source and destination paths exist before starting backup
- 🔄 **Queue System**: Add multiple backup jobs to a queue for sequential execution
- 📊 **Real-time Progress**: Visual progress bars show backup status for each schema
- 📜 **Logging**: Detailed activity logging with error handling
- 💾 **Disk Space Checking**: Verifies sufficient destination space before backup
- 🔁 **Resumable Operation**: Easily restart the application and continue where you left off

## ⚙️ Requirements

- Python 3.6+
- PySide6 (Qt for Python)
- rsync command-line utility
- PyYAML

## ⬇️ Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/magealexstra/BackItUp.git
   ```

2. **Navigate to the project directory:**
   ```bash
   cd BackItUp
   ```

3. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

4. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

5. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

6. **Run the setup script to create necessary directories:**
   ```bash
   ./setup.sh
   ```

## 🚀 Usage

### Starting the Application

Run the main script to launch the application:
```bash
python -m BackItUp.main
```

### Creating a Backup Schema

1. Go to the "Edit Schemas" tab
2. Click "New" to create a new schema
3. Enter a name for the schema
4. Use the file browser to select source paths
5. Set a destination path
6. Click "Save" to save the schema

### Running a Backup

1. Go to the "Run" tab
2. Select a schema from the list
3. Click "Queue Backup" to add it to the queue
4. The application will process the queue and execute backups sequentially

### Monitoring Progress

- The progress bar next to each schema shows current backup progress
- The activity log displays detailed information about the current operation
- The status bar at the bottom shows overall application status

### Canceling a Backup

- Click "Cancel Running" to stop the currently executing backup job
- The status will update to "Cancelled" and the system will move to the next queued job if available

## 🏗️ Architecture

### Core Components

#### Main Window (main.py)

The central GUI component that provides the user interface and coordinates all operations.

**Features:**
- 🖥️ **Two-Tab Interface**: Run and Edit Schemas tabs for different functionality
- 📊 **Schema List**: Visual list with progress bars and status indicators
- 📜 **Activity Log**: Real-time logging of backup operations
- 🔄 **Queue Management**: Automatic processing of queued backup jobs

#### Schema Manager (schema_manager.py)

Handles loading, saving, and managing backup schemas stored as YAML files.

**Features:**
- 💾 **YAML Storage**: Schemas stored as human-readable YAML files
- ✅ **Schema Validation**: Verifies schema contents and path validity
- 🔄 **Automatic Loading**: Loads all valid schemas from the configuration directory

#### Backup Worker (worker.py)

A threaded worker that executes the rsync backup operations, providing progress feedback.

**Features:**
- 🧵 **Threaded Execution**: Non-blocking backup operations
- 📊 **Progress Monitoring**: Real-time progress updates via signals
- 🛑 **Cancellation Support**: Graceful termination of running backups
- 📢 **Signal Communication**: Progress, logging, and error signals

#### Utilities (utils.py)

Helper functions for path validation, filename sanitization, and other common operations.

#### Constants (constants.py)

Application constants and styling information, including the dark theme stylesheet.

### Configuration Files

BackItUp stores all backup schemas as YAML files in the `Config/` directory. Each schema includes:
- Schema name
- Source paths (multiple locations to back up)
- Destination path
- Validation status and other metadata

**Example Schema File Format:**
```yaml
schema_name: Documents Backup
sources:
  - /home/user/Documents
  - /home/user/Work
destination: /media/backup/documents
```

## ❓ Troubleshooting

### Common Issues

- 🔴 **rsync not found**: Ensure rsync is installed on your system and available in the PATH
- ⚠️ **Path validation errors**: Verify that all source and destination paths exist and are accessible
- 💾 **Disk space errors**: Ensure the destination has sufficient free space
- ❌ **Backup failures**: Check the activity log for detailed error messages

### Logs

The application logs detailed information to the terminal from which it was launched. Check these logs for debugging information.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2025 Mage Alexstra

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

Made with ❤️ for the Linux and Python communities.