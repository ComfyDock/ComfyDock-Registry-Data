#!/usr/bin/env python3
"""Tests for global mappings builder with multi-package support."""

import json
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from build_global_mappings import GlobalMappingsBuilder


def create_test_cache(nodes_data):
    """Helper to create a test cache file."""
    cache_data = {
        "cached_at": "2025-01-01T00:00:00",
        "node_count": len(nodes_data),
        "versions_processed": sum(len(n.get("versions_list", [])) for n in nodes_data),
        "metadata_entries": 0,
        "nodes": nodes_data
    }

    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(cache_data, temp_file)
    temp_file.close()
    return Path(temp_file.name)


class TestMultiPackageMappings(unittest.TestCase):
    """Test cases for multi-package node mappings."""

    def test_single_package_single_node(self):
        """Test basic case: one package with one node."""
        nodes = [{
            "id": "package-a",
            "name": "Package A",
            "author": "Author A",
            "downloads": 1000,
            "github_stars": 50,
            "versions_list": [{
                "version": "1.0.0",
                "comfy_nodes": [{
                    "comfy_node_name": "TestNode",
                    "input_types": ""
                }]
            }]
        }]

        cache_file = create_test_cache(nodes)
        builder = GlobalMappingsBuilder()
        result = builder.build_mappings(cache_file)

        mappings = result["mappings"]
        self.assertIn("TestNode::_", mappings)
        self.assertIsInstance(mappings["TestNode::_"], list)
        self.assertEqual(len(mappings["TestNode::_"]), 1)

        entry = mappings["TestNode::_"][0]
        self.assertEqual(entry["package_id"], "package-a")
        self.assertEqual(entry["versions"], ["1.0.0"])
        self.assertEqual(entry["rank"], 1)
        # Schema: score should NOT be in output
        self.assertNotIn("score", entry)
        # Schema: Registry mappings should NOT have source field (default)
        self.assertNotIn("source", entry)

        cache_file.unlink()

    def test_multiple_packages_same_node(self):
        """Test multiple packages providing the same node type."""
        nodes = [
            {
                "id": "popular-package",
                "name": "Popular Package",
                "author": "Popular Author",
                "downloads": 10000,
                "github_stars": 500,
                "versions_list": [{
                    "version": "2.0.0",
                    "comfy_nodes": [{
                        "comfy_node_name": "IntToFloat",
                        "input_types": ""
                    }]
                }]
            },
            {
                "id": "less-popular-package",
                "name": "Less Popular Package",
                "author": "Author B",
                "downloads": 100,
                "github_stars": 5,
                "versions_list": [{
                    "version": "1.0.0",
                    "comfy_nodes": [{
                        "comfy_node_name": "IntToFloat",
                        "input_types": ""
                    }]
                }]
            },
            {
                "id": "no-stats-package",
                "name": "No Stats Package",
                "author": "Author C",
                "downloads": 0,
                "github_stars": 0,
                "versions_list": [{
                    "version": "0.5.0",
                    "comfy_nodes": [{
                        "comfy_node_name": "IntToFloat",
                        "input_types": ""
                    }]
                }]
            }
        ]

        cache_file = create_test_cache(nodes)
        builder = GlobalMappingsBuilder()
        result = builder.build_mappings(cache_file)

        mappings = result["mappings"]
        self.assertIn("IntToFloat::_", mappings)
        self.assertIsInstance(mappings["IntToFloat::_"], list)
        self.assertEqual(len(mappings["IntToFloat::_"]), 3)

        # Verify ordering by rank (most popular first)
        entries = mappings["IntToFloat::_"]
        self.assertEqual(entries[0]["package_id"], "popular-package")
        self.assertEqual(entries[0]["rank"], 1)
        self.assertEqual(entries[1]["package_id"], "less-popular-package")
        self.assertEqual(entries[1]["rank"], 2)
        self.assertEqual(entries[2]["package_id"], "no-stats-package")
        self.assertEqual(entries[2]["rank"], 3)

        # Schema: score should NOT be in output
        for entry in entries:
            self.assertNotIn("score", entry)
            # Schema: Registry mappings should NOT have source field
            self.assertNotIn("source", entry)

        cache_file.unlink()

    def test_different_signatures_same_node_type(self):
        """Test same node type with different input signatures."""
        nodes = [
            {
                "id": "package-a",
                "name": "Package A",
                "downloads": 1000,
                "github_stars": 50,
                "versions_list": [{
                    "version": "1.0.0",
                    "comfy_nodes": [{
                        "comfy_node_name": "LoadImage",
                        "input_types": json.dumps({"required": {"image": ["IMAGE"]}})
                    }]
                }]
            },
            {
                "id": "package-b",
                "name": "Package B",
                "downloads": 2000,
                "github_stars": 100,
                "versions_list": [{
                    "version": "1.0.0",
                    "comfy_nodes": [{
                        "comfy_node_name": "LoadImage",
                        "input_types": json.dumps({"required": {"path": ["STRING"], "image": ["IMAGE"]}})
                    }]
                }]
            }
        ]

        cache_file = create_test_cache(nodes)
        builder = GlobalMappingsBuilder()
        result = builder.build_mappings(cache_file)

        mappings = result["mappings"]

        # Should create two different keys due to different signatures
        keys = [k for k in mappings.keys() if k.startswith("LoadImage::")]
        self.assertEqual(len(keys), 2)

        # Each should have one entry
        for key in keys:
            self.assertIsInstance(mappings[key], list)
            self.assertEqual(len(mappings[key]), 1)

        cache_file.unlink()

    def test_multiple_versions_same_package(self):
        """Test package with multiple versions providing the same node."""
        nodes = [{
            "id": "package-a",
            "name": "Package A",
            "downloads": 1000,
            "github_stars": 50,
            "versions_list": [
                {
                    "version": "2.0.0",
                    "comfy_nodes": [{
                        "comfy_node_name": "TestNode",
                        "input_types": ""
                    }]
                },
                {
                    "version": "1.5.0",
                    "comfy_nodes": [{
                        "comfy_node_name": "TestNode",
                        "input_types": ""
                    }]
                },
                {
                    "version": "1.0.0",
                    "comfy_nodes": [{
                        "comfy_node_name": "TestNode",
                        "input_types": ""
                    }]
                }
            ]
        }]

        cache_file = create_test_cache(nodes)
        builder = GlobalMappingsBuilder()
        result = builder.build_mappings(cache_file)

        mappings = result["mappings"]
        self.assertIn("TestNode::_", mappings)
        self.assertEqual(len(mappings["TestNode::_"]), 1)

        entry = mappings["TestNode::_"][0]
        self.assertEqual(entry["package_id"], "package-a")
        self.assertEqual(set(entry["versions"]), {"2.0.0", "1.5.0", "1.0.0"})

        cache_file.unlink()

    def test_ranking_reflects_popularity(self):
        """Test that ranking reflects download/star popularity."""
        nodes = [
            {
                "id": "high-downloads",
                "name": "High Downloads",
                "downloads": 10000,
                "github_stars": 10,
                "versions_list": [{
                    "version": "1.0.0",
                    "comfy_nodes": [{"comfy_node_name": "Test", "input_types": ""}]
                }]
            },
            {
                "id": "high-stars",
                "name": "High Stars",
                "downloads": 100,
                "github_stars": 1000,
                "versions_list": [{
                    "version": "1.0.0",
                    "comfy_nodes": [{"comfy_node_name": "Test", "input_types": ""}]
                }]
            },
            {
                "id": "balanced",
                "name": "Balanced",
                "downloads": 5000,
                "github_stars": 500,
                "versions_list": [{
                    "version": "1.0.0",
                    "comfy_nodes": [{"comfy_node_name": "Test", "input_types": ""}]
                }]
            }
        ]

        cache_file = create_test_cache(nodes)
        builder = GlobalMappingsBuilder()
        result = builder.build_mappings(cache_file)

        entries = result["mappings"]["Test::_"]

        # Schema: scores should NOT be in output
        for entry in entries:
            self.assertNotIn("score", entry)
            self.assertNotIn("source", entry)

        # Ranking should reflect popularity (high-stars should rank first: 100/10 + 1000*2 = 2010)
        # vs high-downloads: 10000/10 + 10*2 = 1020
        # vs balanced: 5000/10 + 500*2 = 1500
        self.assertEqual(entries[0]["package_id"], "high-stars")
        self.assertEqual(entries[0]["rank"], 1)
        self.assertEqual(entries[1]["package_id"], "balanced")
        self.assertEqual(entries[1]["rank"], 2)
        self.assertEqual(entries[2]["package_id"], "high-downloads")
        self.assertEqual(entries[2]["rank"], 3)

        cache_file.unlink()

    def test_empty_cache(self):
        """Test handling of empty cache."""
        nodes = []
        cache_file = create_test_cache(nodes)

        builder = GlobalMappingsBuilder()
        result = builder.build_mappings(cache_file)

        self.assertEqual(result["mappings"], {})
        self.assertEqual(result["stats"]["packages"], 0)
        self.assertEqual(result["stats"]["signatures"], 0)

        cache_file.unlink()

    def test_package_without_comfy_nodes(self):
        """Test package with version but no comfy_nodes metadata."""
        nodes = [{
            "id": "package-a",
            "name": "Package A",
            "downloads": 1000,
            "versions_list": [{
                "version": "1.0.0",
                # No comfy_nodes
            }]
        }]

        cache_file = create_test_cache(nodes)
        builder = GlobalMappingsBuilder()
        result = builder.build_mappings(cache_file)

        # Should not create any mappings
        self.assertEqual(result["mappings"], {})
        # But package should still be tracked
        self.assertIn("package-a", result["packages"])

        cache_file.unlink()

    def test_stats_calculation(self):
        """Test that stats are calculated correctly."""
        nodes = [
            {
                "id": "package-a",
                "name": "Package A",
                "downloads": 1000,
                "github_stars": 50,
                "versions_list": [{
                    "version": "1.0.0",
                    "comfy_nodes": [
                        {"comfy_node_name": "NodeA", "input_types": ""},
                        {"comfy_node_name": "NodeB", "input_types": ""}
                    ]
                }]
            },
            {
                "id": "package-b",
                "name": "Package B",
                "downloads": 500,
                "github_stars": 25,
                "versions_list": [{
                    "version": "1.0.0",
                    "comfy_nodes": [
                        {"comfy_node_name": "NodeA", "input_types": ""}  # Duplicate
                    ]
                }]
            }
        ]

        cache_file = create_test_cache(nodes)
        builder = GlobalMappingsBuilder()
        result = builder.build_mappings(cache_file)

        stats = result["stats"]
        self.assertEqual(stats["packages"], 2)
        self.assertEqual(stats["signatures"], 2)  # NodeA::_, NodeB::_
        # NodeA has 2 entries, NodeB has 1, total = 3
        self.assertEqual(stats["total_nodes"], 3)

        cache_file.unlink()


if __name__ == "__main__":
    unittest.main()
