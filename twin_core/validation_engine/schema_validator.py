"""Artifact schema validation engine.

Validates artifacts against their type-specific schemas,
ensuring metadata conforms to expected structure and
file contents match declared content hashes.
"""

import json
from pathlib import Path
from uuid import UUID

from ..exceptions import ValidationError
from ..models import Artifact, ArtifactType, compute_content_hash


class ValidationResult:
    """Result of schema validation.

    Attributes:
        valid: Whether validation passed
        errors: List of error messages
    """

    def __init__(self, valid: bool = True, errors: list[str] | None = None):
        self.valid = valid
        self.errors = errors or []

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.valid = False
        self.errors.append(error)


class ArtifactSchemaValidator:
    """Validates artifacts against type-specific schemas.

    Each ArtifactType can have a JSON schema defining required
    metadata fields and their types. This validator loads those
    schemas and validates artifact metadata.
    """

    def __init__(self, schema_dir: str | None = None):
        """Initialize validator with schema directory.

        Args:
            schema_dir: Path to directory containing JSON schemas.
                       Defaults to validation_engine/schemas/
        """
        if schema_dir is None:
            schema_dir = Path(__file__).parent / "schemas"
        self.schema_dir = Path(schema_dir)
        self.schemas: dict[ArtifactType, dict] = {}
        self._load_schemas()

    def _load_schemas(self) -> None:
        """Load all JSON schemas from schema directory."""
        for artifact_type in ArtifactType:
            schema_file = self.schema_dir / f"{artifact_type.value}_schema.json"
            if schema_file.exists():
                with open(schema_file, "r") as f:
                    self.schemas[artifact_type] = json.load(f)

    def validate_artifact(self, artifact: Artifact) -> ValidationResult:
        """Validate an artifact against its type schema.

        Args:
            artifact: Artifact to validate

        Returns:
            ValidationResult with errors if validation fails.
        """
        result = ValidationResult()

        # 1. Validate metadata against schema
        metadata_result = self.validate_metadata(artifact.type, artifact.metadata)
        if not metadata_result.valid:
            for error in metadata_result.errors:
                result.add_error(f"Metadata validation: {error}")

        # 2. Validate file format
        format_result = self.validate_file_format(
            artifact.file_path, artifact.format
        )
        if not format_result.valid:
            for error in format_result.errors:
                result.add_error(f"Format validation: {error}")

        return result

    def validate_metadata(
        self, artifact_type: ArtifactType, metadata: dict
    ) -> ValidationResult:
        """Validate metadata against artifact type schema.

        Args:
            artifact_type: Type of artifact
            metadata: Metadata dictionary to validate

        Returns:
            ValidationResult with errors if validation fails.
        """
        result = ValidationResult()

        # Get schema for artifact type
        schema = self.schemas.get(artifact_type)
        if not schema:
            # No schema defined - pass validation
            return result

        # Check required fields
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in metadata:
                result.add_error(f"Missing required field: {field}")

        # Check field types (basic type checking)
        properties = schema.get("properties", {})
        for field, value in metadata.items():
            if field in properties:
                expected_type = properties[field].get("type")
                actual_type = type(value).__name__

                # Map Python types to JSON schema types
                type_mapping = {
                    "str": "string",
                    "int": "integer",
                    "float": "number",
                    "bool": "boolean",
                    "list": "array",
                    "dict": "object",
                }
                actual_json_type = type_mapping.get(actual_type, actual_type)

                if expected_type and actual_json_type != expected_type:
                    result.add_error(
                        f"Field '{field}': expected {expected_type}, got {actual_json_type}"
                    )

        return result

    def verify_content_hash(
        self, file_path: str, expected_hash: str
    ) -> bool:
        """Verify that file content hash matches expected hash.

        Args:
            file_path: Path to the file
            expected_hash: Expected SHA-256 hash

        Returns:
            True if hash matches, False otherwise.
        """
        try:
            actual_hash = compute_content_hash(file_path)
            return actual_hash == expected_hash
        except FileNotFoundError:
            return False

    def validate_file_format(
        self, file_path: str, expected_format: str
    ) -> ValidationResult:
        """Validate file format.

        Args:
            file_path: Path to the file
            expected_format: Expected file format (e.g., "step", "json")

        Returns:
            ValidationResult with errors if validation fails.
        """
        result = ValidationResult()

        # Basic file extension check
        path = Path(file_path)
        actual_extension = path.suffix.lstrip(".")

        # Map common format names to extensions
        format_mapping = {
            "step": ["step", "stp"],
            "stl": ["stl"],
            "json": ["json"],
            "kicad_sch": ["kicad_sch"],
            "kicad_pcb": ["kicad_pcb"],
            "gerber": ["gbr", "gtl", "gbl", "gts", "gbs", "gto", "gbo"],
            "csv": ["csv"],
            "md": ["md"],
        }

        expected_extensions = format_mapping.get(
            expected_format, [expected_format]
        )
        if actual_extension not in expected_extensions:
            result.add_error(
                f"File extension '{actual_extension}' does not match format '{expected_format}'"
            )

        return result
