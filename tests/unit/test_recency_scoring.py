#!/usr/bin/env python3
"""Unit tests for recency-based scoring."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from build_global_mappings import GlobalMappingsBuilder


def create_test_package_with_recency(package_id, downloads, stars, days_old):
    """Create test package with specific age."""
    now = datetime.now(timezone.utc)
    version_date = (now - timedelta(days=days_old)).isoformat()

    return {
        "id": package_id,
        "name": f"Package {package_id}",
        "downloads": downloads,
        "github_stars": stars,
        "versions_list": [{
            "version": "1.0.0",
            "createdAt": version_date,
            "comfy_nodes": [{
                "comfy_node_name": "TestNode",
                "input_types": ""
            }]
        }]
    }


class TestRecencyMultiplier(unittest.TestCase):
    """Test recency multiplier calculation."""

    def setUp(self):
        self.builder = GlobalMappingsBuilder()

    def test_fresh_package_no_penalty(self):
        """Package < 90 days old gets no penalty (multiplier = 1.0)."""
        # Create package 30 days old
        pkg = create_test_package_with_recency("fresh-pkg", 1000, 50, 30)
        cache_data = {
            "cached_at": "2025-01-01T00:00:00",
            "node_count": 1,
            "versions_processed": 1,
            "metadata_entries": 1,
            "nodes": [pkg]
        }

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(cache_data, temp_file)
        temp_file.close()

        result = self.builder.build_mappings(Path(temp_file.name))

        # Verify mapping exists and rank is assigned
        entries = result["mappings"]["TestNode::_"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["rank"], 1)
        self.assertEqual(entries[0]["package_id"], "fresh-pkg")

        # Schema: score should NOT be in output
        self.assertNotIn("score", entries[0])

        Path(temp_file.name).unlink()

    def test_moderately_old_package_small_penalty(self):
        """Package 90-180 days old gets 5% penalty (multiplier = 0.95)."""
        # Test penalty by comparing with fresh package
        nodes = [
            create_test_package_with_recency("fresh-pkg", 1000, 50, 30),    # No penalty
            create_test_package_with_recency("moderate-pkg", 1000, 50, 120), # 5% penalty
        ]
        cache_data = {
            "cached_at": "2025-01-01T00:00:00",
            "node_count": 2,
            "versions_processed": 2,
            "metadata_entries": 2,
            "nodes": nodes
        }

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(cache_data, temp_file)
        temp_file.close()

        result = GlobalMappingsBuilder().build_mappings(Path(temp_file.name))

        entries = result["mappings"]["TestNode::_"]
        self.assertEqual(len(entries), 2)

        # Fresh package should rank higher (same base stats, but no recency penalty)
        self.assertEqual(entries[0]["package_id"], "fresh-pkg")
        self.assertEqual(entries[0]["rank"], 1)
        self.assertEqual(entries[1]["package_id"], "moderate-pkg")
        self.assertEqual(entries[1]["rank"], 2)

        # Schema: score should NOT be in output
        for entry in entries:
            self.assertNotIn("score", entry)

        Path(temp_file.name).unlink()

    def test_old_package_moderate_penalty(self):
        """Package 180-365 days old gets 15% penalty (multiplier = 0.85)."""
        # Test penalty by comparing with fresh package
        nodes = [
            create_test_package_with_recency("fresh-pkg", 1000, 50, 30),  # No penalty
            create_test_package_with_recency("old-pkg", 1000, 50, 270),   # 15% penalty
        ]
        cache_data = {
            "cached_at": "2025-01-01T00:00:00",
            "node_count": 2,
            "versions_processed": 2,
            "metadata_entries": 2,
            "nodes": nodes
        }

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(cache_data, temp_file)
        temp_file.close()

        result = GlobalMappingsBuilder().build_mappings(Path(temp_file.name))

        entries = result["mappings"]["TestNode::_"]
        # Fresh package ranks higher due to recency
        self.assertEqual(entries[0]["package_id"], "fresh-pkg")
        self.assertEqual(entries[1]["package_id"], "old-pkg")

        for entry in entries:
            self.assertNotIn("score", entry)

        Path(temp_file.name).unlink()

    def test_very_old_package_significant_penalty(self):
        """Package 365-730 days old gets 30% penalty (multiplier = 0.70)."""
        # Test penalty by comparing with fresh package
        nodes = [
            create_test_package_with_recency("fresh-pkg", 1000, 50, 30),      # No penalty
            create_test_package_with_recency("very-old-pkg", 1000, 50, 500),  # 30% penalty
        ]
        cache_data = {
            "cached_at": "2025-01-01T00:00:00",
            "node_count": 2,
            "versions_processed": 2,
            "metadata_entries": 2,
            "nodes": nodes
        }

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(cache_data, temp_file)
        temp_file.close()

        result = GlobalMappingsBuilder().build_mappings(Path(temp_file.name))

        entries = result["mappings"]["TestNode::_"]
        # Fresh package ranks higher
        self.assertEqual(entries[0]["package_id"], "fresh-pkg")
        self.assertEqual(entries[1]["package_id"], "very-old-pkg")

        for entry in entries:
            self.assertNotIn("score", entry)

        Path(temp_file.name).unlink()

    def test_ancient_package_heavy_penalty(self):
        """Package > 730 days old gets 50% penalty (multiplier = 0.50)."""
        # Test penalty by comparing with fresh package
        nodes = [
            create_test_package_with_recency("fresh-pkg", 1000, 50, 30),     # No penalty
            create_test_package_with_recency("ancient-pkg", 1000, 50, 800),  # 50% penalty
        ]
        cache_data = {
            "cached_at": "2025-01-01T00:00:00",
            "node_count": 2,
            "versions_processed": 2,
            "metadata_entries": 2,
            "nodes": nodes
        }

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(cache_data, temp_file)
        temp_file.close()

        result = GlobalMappingsBuilder().build_mappings(Path(temp_file.name))

        entries = result["mappings"]["TestNode::_"]
        # Fresh package ranks higher
        self.assertEqual(entries[0]["package_id"], "fresh-pkg")
        self.assertEqual(entries[1]["package_id"], "ancient-pkg")

        for entry in entries:
            self.assertNotIn("score", entry)

        Path(temp_file.name).unlink()

    def test_no_version_dates_no_penalty(self):
        """Package with no version dates gets no penalty (benefit of doubt)."""
        # Compare package without dates to old package with dates
        pkg_no_dates = {
            "id": "no-dates-pkg",
            "name": "No Dates Package",
            "downloads": 1000,
            "github_stars": 50,
            "versions_list": [{
                "version": "1.0.0",
                # No createdAt field
                "comfy_nodes": [{
                    "comfy_node_name": "TestNode",
                    "input_types": ""
                }]
            }]
        }
        pkg_old = create_test_package_with_recency("old-pkg", 1000, 50, 500)  # 30% penalty

        cache_data = {
            "cached_at": "2025-01-01T00:00:00",
            "node_count": 2,
            "versions_processed": 2,
            "metadata_entries": 2,
            "nodes": [pkg_no_dates, pkg_old]
        }

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(cache_data, temp_file)
        temp_file.close()

        result = GlobalMappingsBuilder().build_mappings(Path(temp_file.name))

        entries = result["mappings"]["TestNode::_"]
        # Package without dates should rank higher (gets benefit of doubt)
        self.assertEqual(entries[0]["package_id"], "no-dates-pkg")
        self.assertEqual(entries[1]["package_id"], "old-pkg")

        for entry in entries:
            self.assertNotIn("score", entry)

        Path(temp_file.name).unlink()

    def test_multiple_versions_uses_latest(self):
        """Package with multiple versions uses the most recent version date."""
        now = datetime.now(timezone.utc)
        old_date = (now - timedelta(days=500)).isoformat()
        recent_date = (now - timedelta(days=30)).isoformat()

        pkg_multi = {
            "id": "multi-version-pkg",
            "name": "Multi Version Package",
            "downloads": 1000,
            "github_stars": 50,
            "versions_list": [
                {
                    "version": "2.0.0",
                    "createdAt": recent_date,  # Recent version
                    "comfy_nodes": [{"comfy_node_name": "TestNode", "input_types": ""}]
                },
                {
                    "version": "1.0.0",
                    "createdAt": old_date,  # Old version
                    "comfy_nodes": [{"comfy_node_name": "TestNode", "input_types": ""}]
                }
            ]
        }
        # Compare with package that only has old version
        pkg_old_only = create_test_package_with_recency("old-only", 1000, 50, 500)

        cache_data = {
            "cached_at": "2025-01-01T00:00:00",
            "node_count": 2,
            "versions_processed": 3,
            "metadata_entries": 3,
            "nodes": [pkg_multi, pkg_old_only]
        }

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(cache_data, temp_file)
        temp_file.close()

        result = GlobalMappingsBuilder().build_mappings(Path(temp_file.name))

        entries = result["mappings"]["TestNode::_"]
        # Multi-version package should rank higher (uses recent date, no penalty)
        self.assertEqual(entries[0]["package_id"], "multi-version-pkg")
        self.assertEqual(entries[1]["package_id"], "old-only")

        for entry in entries:
            self.assertNotIn("score", entry)

        Path(temp_file.name).unlink()


class TestRecencyRanking(unittest.TestCase):
    """Test that recency affects package ranking correctly."""

    def test_active_beats_stale_when_similar_popularity(self):
        """Active package beats stale package when popularity is similar."""
        nodes = [
            create_test_package_with_recency("stale", 5000, 200, 500),  # Base: 900, Penalized: 630
            create_test_package_with_recency("active", 4000, 300, 30),  # Base: 1000, No penalty: 1000
        ]

        cache_data = {
            "cached_at": "2025-01-01T00:00:00",
            "node_count": 2,
            "versions_processed": 2,
            "metadata_entries": 2,
            "nodes": nodes
        }

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(cache_data, temp_file)
        temp_file.close()

        builder = GlobalMappingsBuilder()
        result = builder.build_mappings(Path(temp_file.name))

        entries = result["mappings"]["TestNode::_"]
        self.assertEqual(len(entries), 2)

        # Active package should rank first
        self.assertEqual(entries[0]["package_id"], "active")
        self.assertEqual(entries[0]["rank"], 1)
        self.assertEqual(entries[1]["package_id"], "stale")
        self.assertEqual(entries[1]["rank"], 2)

        # Schema: score should NOT be in output
        for entry in entries:
            self.assertNotIn("score", entry)

        Path(temp_file.name).unlink()

    def test_very_popular_old_still_beats_unpopular_new(self):
        """Very popular but old package still beats unpopular new package."""
        nodes = [
            create_test_package_with_recency("popular-old", 100000, 1000, 500),  # Score: 12000 * 0.7 = 8400
            create_test_package_with_recency("unpopular-new", 500, 30, 20),      # Score: 110 * 1.0 = 110
        ]

        cache_data = {
            "cached_at": "2025-01-01T00:00:00",
            "node_count": 2,
            "versions_processed": 2,
            "metadata_entries": 2,
            "nodes": nodes
        }

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(cache_data, temp_file)
        temp_file.close()

        builder = GlobalMappingsBuilder()
        builder.build_mappings(Path(temp_file.name))

        entries = builder.mappings["TestNode::_"]

        # Popular old package should still rank first (quality matters)
        self.assertEqual(entries[0]["package_id"], "popular-old")
        self.assertEqual(entries[0]["rank"], 1)

        Path(temp_file.name).unlink()

    def test_recency_breaks_tie(self):
        """When popularity is identical, recency breaks the tie."""
        nodes = [
            create_test_package_with_recency("pkg-old", 1000, 50, 500),   # Score: 200 * 0.7 = 140
            create_test_package_with_recency("pkg-new", 1000, 50, 30),    # Score: 200 * 1.0 = 200
        ]

        cache_data = {
            "cached_at": "2025-01-01T00:00:00",
            "node_count": 2,
            "versions_processed": 2,
            "metadata_entries": 2,
            "nodes": nodes
        }

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(cache_data, temp_file)
        temp_file.close()

        builder = GlobalMappingsBuilder()
        builder.build_mappings(Path(temp_file.name))

        entries = builder.mappings["TestNode::_"]

        # New package should rank first (same base metrics but fresher)
        self.assertEqual(entries[0]["package_id"], "pkg-new")
        self.assertEqual(entries[1]["package_id"], "pkg-old")

        Path(temp_file.name).unlink()


if __name__ == "__main__":
    unittest.main()
