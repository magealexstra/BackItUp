import yaml
import os
from pathlib import Path
import logging

from .constants import CONFIG_DIR
from .utils import sanitize_filename, validate_schema_paths

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SchemaManager:
    def __init__(self, config_dir=CONFIG_DIR):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def get_schema_filepath(self, schema_name):
        """Generates the expected filepath for a given schema name."""
        sanitized_name = sanitize_filename(schema_name)
        return self.config_dir / f"{sanitized_name}.yaml"

    def load_schemas(self):
        """Loads all valid schemas from the configuration directory."""
        schemas = {}
        for filepath in self.config_dir.glob("*.yaml"):
            try:
                with open(filepath, 'r') as f:
                    schema_data = yaml.safe_load(f)
                # Basic validation: check for required keys
                if schema_data and 'schema_name' in schema_data and 'sources' in schema_data and 'destination' in schema_data:
                    # Use the name from the file content, not the filename itself
                    schema_name = schema_data['schema_name']
                    # Perform path validation
                    is_valid, invalid_paths = validate_schema_paths(schema_data)
                    schema_data['_is_valid'] = is_valid # Store validation status
                    schema_data['_invalid_paths'] = invalid_paths
                    schema_data['_filepath'] = str(filepath) # Store filepath for reference
                    schemas[schema_name] = schema_data
                else:
                    logging.warning(f"Skipping invalid schema file (missing keys): {filepath.name}")
            except yaml.YAMLError as e:
                logging.error(f"Error loading schema file {filepath.name}: {e}")
            except Exception as e:
                logging.error(f"Unexpected error loading schema {filepath.name}: {e}")
        return schemas

    def load_single_schema(self, schema_name):
        """Loads a single schema by its name."""
        filepath = self.get_schema_filepath(schema_name)
        if filepath.exists():
            try:
                with open(filepath, 'r') as f:
                    schema_data = yaml.safe_load(f)
                if schema_data and schema_data.get('schema_name') == schema_name:
                     # Perform path validation
                    is_valid, invalid_paths = validate_schema_paths(schema_data)
                    schema_data['_is_valid'] = is_valid
                    schema_data['_invalid_paths'] = invalid_paths
                    schema_data['_filepath'] = str(filepath)
                    return schema_data
                else:
                    logging.warning(f"Schema name mismatch or invalid data in file: {filepath.name}")
                    return None
            except yaml.YAMLError as e:
                logging.error(f"Error loading schema file {filepath.name}: {e}")
                return None
            except Exception as e:
                logging.error(f"Unexpected error loading schema {filepath.name}: {e}")
                return None
        else:
            logging.warning(f"Schema file not found for name: {schema_name} (expected: {filepath.name})")
            return None


    def save_schema(self, schema_data):
        """
        Saves a schema to a .yaml file. Overwrites if exists based on sanitized name.
        Ensures 'schema_name' exists in the data.
        """
        if not schema_data or 'schema_name' not in schema_data:
            logging.error("Cannot save schema: 'schema_name' is missing.")
            return False, "Schema name is missing."

        schema_name = schema_data['schema_name']
        filepath = self.get_schema_filepath(schema_name)

        # Clean up internal keys before saving
        data_to_save = {k: v for k, v in schema_data.items() if not k.startswith('_')}

        try:
            with open(filepath, 'w') as f:
                yaml.dump(data_to_save, f, default_flow_style=False, sort_keys=False)
            logging.info(f"Schema '{schema_name}' saved to {filepath.name}")
            return True, f"Schema '{schema_name}' saved successfully."
        except Exception as e:
            logging.error(f"Error saving schema '{schema_name}' to {filepath.name}: {e}")
            return False, f"Error saving schema '{schema_name}'."

    def delete_schema(self, schema_name):
        """Deletes the .yaml file corresponding to the schema name."""
        filepath = self.get_schema_filepath(schema_name)
        if filepath.exists():
            try:
                os.remove(filepath)
                logging.info(f"Schema file '{filepath.name}' deleted.")
                return True, f"Schema '{schema_name}' deleted."
            except OSError as e:
                logging.error(f"Error deleting schema file {filepath.name}: {e}")
                return False, f"Error deleting schema '{schema_name}'."
        else:
            logging.warning(f"Schema file not found for deletion: {filepath.name}")
            return False, f"Schema '{schema_name}' not found."
