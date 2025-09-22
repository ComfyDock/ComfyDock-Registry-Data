#!/usr/bin/env python3
"""
Data validation script for registry cache and mappings.
Ensures data integrity and consistency across files.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataValidator:
    """Validates registry data files for integrity and consistency."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate_cache(self, cache_file: Path) -> bool:
        """Validate registry cache file structure and content."""
        logger.info(f"Validating cache file: {cache_file}")

        try:
            with open(cache_file) as f:
                cache = json.load(f)

            # Check required top-level fields
            required_fields = ["cached_at", "node_count", "nodes"]
            for field in required_fields:
                if field not in cache:
                    self.errors.append(f"Cache missing required field: {field}")

            # Validate nodes structure
            nodes = cache.get("nodes", [])
            if not isinstance(nodes, list):
                self.errors.append("Cache 'nodes' field must be a list")
                return False

            # Validate node count consistency
            declared_count = cache.get("node_count", 0)
            actual_count = len(nodes)
            if declared_count != actual_count:
                self.warnings.append(f"Node count mismatch: declared {declared_count}, actual {actual_count}")

            # Validate individual nodes
            valid_nodes = 0
            nodes_with_versions = 0
            total_versions = 0

            for i, node in enumerate(nodes):
                if not isinstance(node, dict):
                    self.errors.append(f"Node {i} is not a dict")
                    continue

                # Check required node fields
                node_required = ["id", "name"]
                for field in node_required:
                    if field not in node:
                        self.errors.append(f"Node {i} missing required field: {field}")

                # Check versions
                versions_list = node.get("versions_list", [])
                if versions_list:
                    nodes_with_versions += 1
                    total_versions += len(versions_list)

                    # Validate version structure
                    for j, version in enumerate(versions_list):
                        if not isinstance(version, dict):
                            self.errors.append(f"Node {node.get('id', i)} version {j} is not a dict")
                            continue

                        if "version" not in version:
                            self.errors.append(f"Node {node.get('id', i)} version {j} missing 'version' field")

                valid_nodes += 1

            logger.info(f"Cache validation: {valid_nodes} valid nodes, {nodes_with_versions} with versions, {total_versions} total versions")

        except json.JSONDecodeError as e:
            self.errors.append(f"Cache file JSON decode error: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Cache validation error: {e}")
            return False

        return len(self.errors) == 0

    def validate_mappings(self, mappings_file: Path) -> bool:
        """Validate node mappings file structure and content."""
        logger.info(f"Validating mappings file: {mappings_file}")

        try:
            with open(mappings_file) as f:
                mappings = json.load(f)

            # Check required top-level fields
            required_fields = ["version", "stats", "mappings", "packages"]
            for field in required_fields:
                if field not in mappings:
                    self.errors.append(f"Mappings missing required field: {field}")

            # Validate stats
            stats = mappings.get("stats", {})
            declared_packages = stats.get("packages", 0)
            declared_signatures = stats.get("signatures", 0)

            # Validate mappings structure
            mapping_dict = mappings.get("mappings", {})
            if not isinstance(mapping_dict, dict):
                self.errors.append("Mappings 'mappings' field must be a dict")
                return False

            # Validate packages structure
            packages_dict = mappings.get("packages", {})
            if not isinstance(packages_dict, dict):
                self.errors.append("Mappings 'packages' field must be a dict")
                return False

            # Check consistency
            actual_packages = len(packages_dict)
            actual_signatures = len(mapping_dict)

            if declared_packages != actual_packages:
                self.warnings.append(f"Package count mismatch: declared {declared_packages}, actual {actual_packages}")

            if declared_signatures != actual_signatures:
                self.warnings.append(f"Signature count mismatch: declared {declared_signatures}, actual {actual_signatures}")

            # Validate mapping entries
            valid_mappings = 0
            orphaned_mappings = 0

            for node_key, mapping_info in mapping_dict.items():
                if not isinstance(mapping_info, dict):
                    self.errors.append(f"Mapping {node_key} is not a dict")
                    continue

                # Check required mapping fields
                if "package_id" not in mapping_info:
                    self.errors.append(f"Mapping {node_key} missing 'package_id' field")
                    continue

                package_id = mapping_info["package_id"]
                if package_id not in packages_dict:
                    orphaned_mappings += 1
                    if orphaned_mappings <= 5:  # Only show first 5
                        self.warnings.append(f"Mapping {node_key} references missing package: {package_id}")

                valid_mappings += 1

            if orphaned_mappings > 5:
                self.warnings.append(f"... and {orphaned_mappings - 5} more orphaned mappings")

            # Validate package entries
            valid_packages = 0
            for package_id, package_info in packages_dict.items():
                if not isinstance(package_info, dict):
                    self.errors.append(f"Package {package_id} is not a dict")
                    continue

                # Check basic package structure
                if "display_name" not in package_info:
                    self.warnings.append(f"Package {package_id} missing 'display_name'")

                valid_packages += 1

            logger.info(f"Mappings validation: {valid_mappings} mappings, {valid_packages} packages, {orphaned_mappings} orphaned")

        except json.JSONDecodeError as e:
            self.errors.append(f"Mappings file JSON decode error: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Mappings validation error: {e}")
            return False

        return len(self.errors) == 0

    def validate_consistency(self, cache_file: Path, mappings_file: Path) -> bool:
        """Validate consistency between cache and mappings files."""
        logger.info("Validating cross-file consistency")

        try:
            # Load both files
            with open(cache_file) as f:
                cache = json.load(f)
            with open(mappings_file) as f:
                mappings = json.load(f)

            # Get package IDs from both files
            cache_packages = {node["id"] for node in cache.get("nodes", [])}
            mappings_packages = set(mappings.get("packages", {}).keys())

            # Find discrepancies
            only_in_cache = cache_packages - mappings_packages
            only_in_mappings = mappings_packages - cache_packages

            if only_in_cache:
                self.warnings.append(f"{len(only_in_cache)} packages in cache but not in mappings")

            if only_in_mappings:
                self.warnings.append(f"{len(only_in_mappings)} packages in mappings but not in cache")

            # Check timestamp consistency
            cache_time = cache.get("cached_at", "")
            mappings_time = mappings.get("generated_at", "")

            if cache_time and mappings_time:
                try:
                    cache_dt = datetime.fromisoformat(cache_time)
                    mappings_dt = datetime.fromisoformat(mappings_time)

                    if mappings_dt < cache_dt:
                        self.warnings.append("Mappings are older than cache - may need regeneration")
                except Exception:
                    self.warnings.append("Could not parse timestamps for consistency check")

            logger.info(f"Consistency check: {len(cache_packages)} cache packages, {len(mappings_packages)} mapping packages")

        except Exception as e:
            self.errors.append(f"Consistency validation error: {e}")
            return False

        return True

    def get_results(self) -> Tuple[bool, List[str], List[str]]:
        """Get validation results."""
        success = len(self.errors) == 0
        return success, self.errors, self.warnings

    def print_results(self):
        """Print validation results."""
        success, errors, warnings = self.get_results()

        if success:
            print("✅ Validation PASSED")
        else:
            print("❌ Validation FAILED")

        if errors:
            print(f"\n🚨 {len(errors)} Error(s):")
            for error in errors:
                print(f"  - {error}")

        if warnings:
            print(f"\n⚠️  {len(warnings)} Warning(s):")
            for warning in warnings:
                print(f"  - {warning}")

        if not errors and not warnings:
            print("🎉 All checks passed with no issues!")


def main():
    parser = argparse.ArgumentParser(description="Validate registry data files")
    parser.add_argument(
        "--cache",
        type=Path,
        help="Registry cache file to validate"
    )
    parser.add_argument(
        "--mappings",
        type=Path,
        help="Node mappings file to validate"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Data directory containing files to validate (default: data/)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )

    args = parser.parse_args()

    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Determine files to validate
    cache_file = args.cache or (args.data_dir / "full_registry_cache.json")
    mappings_file = args.mappings or (args.data_dir / "node_mappings.json")

    validator = DataValidator()

    # Validate cache if exists
    if cache_file.exists():
        validator.validate_cache(cache_file)
    else:
        validator.errors.append(f"Cache file not found: {cache_file}")

    # Validate mappings if exists
    if mappings_file.exists():
        validator.validate_mappings(mappings_file)
    else:
        validator.errors.append(f"Mappings file not found: {mappings_file}")

    # Cross-validate if both exist
    if cache_file.exists() and mappings_file.exists():
        validator.validate_consistency(cache_file, mappings_file)

    # Print and return results
    validator.print_results()
    success, errors, warnings = validator.get_results()

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())