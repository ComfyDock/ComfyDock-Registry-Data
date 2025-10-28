"""Pytest fixtures for integration tests."""

import json
import tempfile
from pathlib import Path
from typing import Dict, List

import pytest


@pytest.fixture
def temp_cache_file():
    """Create a temporary cache file that auto-cleans."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='_cache.json', delete=False)
    temp_file.close()
    yield Path(temp_file.name)
    Path(temp_file.name).unlink(missing_ok=True)


@pytest.fixture
def temp_mappings_file():
    """Create a temporary mappings file that auto-cleans."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='_mappings.json', delete=False)
    temp_file.close()
    yield Path(temp_file.name)
    Path(temp_file.name).unlink(missing_ok=True)


@pytest.fixture
def temp_manager_file():
    """Create a temporary manager data file that auto-cleans."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='_manager.json', delete=False)
    temp_file.close()
    yield Path(temp_file.name)
    Path(temp_file.name).unlink(missing_ok=True)


def create_package(
    package_id: str,
    name: str,
    downloads: int = 1000,
    github_stars: int = 50,
    versions = None
) -> Dict:
    """Helper to create package data."""
    if versions is None:
        versions = [{
            "version": "1.0.0",
            "comfy_nodes": []
        }]

    return {
        "id": package_id,
        "name": name,
        "author": f"Author of {name}",
        "description": f"Description for {name}",
        "repository": f"https://github.com/author/{package_id}",
        "downloads": downloads,
        "github_stars": github_stars,
        "rating": 4.5,
        "license": "MIT",
        "category": "nodes",
        "icon": "",
        "tags": ["math", "utility"],
        "status": "active",
        "created_at": "2024-01-01T00:00:00",
        "versions_list": versions
    }


def create_node(node_name: str, input_types: str = "") -> Dict:
    """Helper to create comfy node metadata."""
    return {
        "comfy_node_name": node_name,
        "input_types": input_types
    }


@pytest.fixture
def sample_packages():
    """Sample package factory."""
    return create_package


@pytest.fixture
def sample_node():
    """Sample node factory."""
    return create_node


def write_cache(file_path: Path, nodes: List[Dict]):
    """Write cache data to file."""
    cache_data = {
        "cached_at": "2025-01-01T00:00:00",
        "node_count": len(nodes),
        "versions_processed": sum(len(n.get("versions_list", [])) for n in nodes),
        "metadata_entries": sum(
            sum(len(v.get("comfy_nodes", [])) for v in n.get("versions_list", []))
            for n in nodes
        ),
        "nodes": nodes
    }

    with open(file_path, 'w') as f:
        json.dump(cache_data, f, indent=2)


def write_manager_data(file_path: Path, extensions: Dict[str, List]):
    """Write manager extension data to file."""
    manager_data = {
        "fetched_at": "2025-01-01T00:00:00",
        "extension_count": len(extensions),
        "extensions": extensions
    }

    with open(file_path, 'w') as f:
        json.dump(manager_data, f, indent=2)


@pytest.fixture
def write_cache_helper():
    """Helper to write cache files."""
    return write_cache


@pytest.fixture
def write_manager_helper():
    """Helper to write manager files."""
    return write_manager_data
