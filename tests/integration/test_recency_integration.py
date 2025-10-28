"""Integration tests for recency-weighted scoring in full pipeline."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from build_global_mappings import GlobalMappingsBuilder


def create_package_with_age(package_id, name, downloads, stars, days_old, sample_node):
    """Create package with specific age."""
    now = datetime.now(timezone.utc)
    version_date = (now - timedelta(days=days_old)).isoformat()

    return {
        "id": package_id,
        "name": name,
        "downloads": downloads,
        "github_stars": stars,
        "versions_list": [{
            "version": "1.0.0",
            "createdAt": version_date,
            "comfy_nodes": [sample_node("TestNode")]
        }]
    }


class TestRecencyIntegration:
    """Test recency weighting in realistic scenarios."""

    def test_real_world_scenario_active_vs_abandoned(
        self, temp_cache_file, sample_node, write_cache_helper
    ):
        """Test real-world scenario: popular abandoned vs active maintained."""
        nodes = [
            # Very popular but abandoned for over a year
            create_package_with_age(
                "comfyui-popular-abandoned",
                "Popular But Abandoned",
                downloads=50000,
                stars=500,
                days_old=450,  # 15 months
                sample_node=sample_node
            ),
            # Moderately popular, actively maintained
            create_package_with_age(
                "comfyui-active-maintained",
                "Active Maintained",
                downloads=20000,
                stars=250,
                days_old=30,  # 1 month
                sample_node=sample_node
            ),
        ]

        write_cache_helper(temp_cache_file, nodes)

        builder = GlobalMappingsBuilder()
        result = builder.build_mappings(temp_cache_file)

        entries = result["mappings"]["TestNode::_"]
        assert len(entries) == 2

        # Abandoned still wins (significantly more popular even with penalty)
        assert entries[0]["package_id"] == "comfyui-popular-abandoned"
        assert entries[0]["rank"] == 1
        assert entries[1]["package_id"] == "comfyui-active-maintained"
        assert entries[1]["rank"] == 2

        # Schema: score should NOT be in output
        for entry in entries:
            assert "score" not in entry

    def test_crossover_point_recency_wins(
        self, temp_cache_file, sample_node, write_cache_helper
    ):
        """Test crossover where recency bonus causes rank flip."""
        nodes = [
            # Slightly more popular but stale
            create_package_with_age(
                "slightly-popular-stale",
                "Slightly Popular Stale",
                downloads=6000,
                stars=250,
                days_old=500,  # Old
                sample_node=sample_node
            ),
            # Slightly less popular but fresh
            create_package_with_age(
                "less-popular-fresh",
                "Less Popular Fresh",
                downloads=5000,
                stars=300,
                days_old=20,  # Fresh
                sample_node=sample_node
            ),
        ]

        write_cache_helper(temp_cache_file, nodes)

        builder = GlobalMappingsBuilder()
        result = builder.build_mappings(temp_cache_file)

        entries = result["mappings"]["TestNode::_"]

        # Fresh package should win
        assert entries[0]["package_id"] == "less-popular-fresh"
        assert entries[0]["rank"] == 1
        assert entries[1]["package_id"] == "slightly-popular-stale"
        assert entries[1]["rank"] == 2

    def test_three_packages_different_ages(
        self, temp_cache_file, sample_node, write_cache_helper
    ):
        """Test three packages with different recency profiles."""
        nodes = [
            create_package_with_age(
                "fresh", "Fresh Package",
                downloads=3000, stars=150, days_old=20,
                sample_node=sample_node
            ),
            create_package_with_age(
                "moderate", "Moderate Age",
                downloads=3000, stars=150, days_old=120,
                sample_node=sample_node
            ),
            create_package_with_age(
                "stale", "Stale Package",
                downloads=3000, stars=150, days_old=600,
                sample_node=sample_node
            ),
        ]

        write_cache_helper(temp_cache_file, nodes)

        builder = GlobalMappingsBuilder()
        result = builder.build_mappings(temp_cache_file)

        entries = result["mappings"]["TestNode::_"]
        assert len(entries) == 3

        # Should rank by recency (same base metrics)
        assert entries[0]["package_id"] == "fresh"
        assert entries[1]["package_id"] == "moderate"
        assert entries[2]["package_id"] == "stale"

        # Verify rank ordering
        assert entries[0]["rank"] == 1
        assert entries[1]["rank"] == 2
        assert entries[2]["rank"] == 3

        # Schema: score should NOT be in output
        for entry in entries:
            assert "score" not in entry

    def test_recency_across_multiple_nodes(
        self, temp_cache_file, sample_packages, sample_node, write_cache_helper
    ):
        """Test recency applies consistently across different node types."""
        nodes = [
            {
                **sample_packages(
                    "old-multi", "Old Multi-Node",
                    downloads=5000, github_stars=200
                ),
                "versions_list": [{
                    "version": "1.0.0",
                    "createdAt": (datetime.now(timezone.utc) - timedelta(days=500)).isoformat(),
                    "comfy_nodes": [
                        sample_node("NodeA"),
                        sample_node("NodeB"),
                    ]
                }]
            },
            {
                **sample_packages(
                    "new-multi", "New Multi-Node",
                    downloads=4000, github_stars=200
                ),
                "versions_list": [{
                    "version": "1.0.0",
                    "createdAt": (datetime.now(timezone.utc) - timedelta(days=25)).isoformat(),
                    "comfy_nodes": [
                        sample_node("NodeA"),
                        sample_node("NodeB"),
                    ]
                }]
            },
        ]

        write_cache_helper(temp_cache_file, nodes)

        builder = GlobalMappingsBuilder()
        result = builder.build_mappings(temp_cache_file)

        # Both nodes should have same ranking pattern
        for node_key in ["NodeA::_", "NodeB::_"]:
            entries = result["mappings"][node_key]
            assert len(entries) == 2

            # New package should rank first for both nodes
            assert entries[0]["package_id"] == "new-multi"
            assert entries[1]["package_id"] == "old-multi"

    def test_no_dates_mixed_with_dated(
        self, temp_cache_file, sample_node, write_cache_helper
    ):
        """Test packages without dates compete fairly with dated packages."""
        now = datetime.now(timezone.utc)

        nodes = [
            {
                "id": "no-dates",
                "name": "No Dates",
                "downloads": 3000,
                "github_stars": 150,
                "versions_list": [{
                    "version": "1.0.0",
                    # No createdAt
                    "comfy_nodes": [sample_node("TestNode")]
                }]
            },
            {
                "id": "recent",
                "name": "Recent",
                "downloads": 2500,
                "github_stars": 150,
                "versions_list": [{
                    "version": "1.0.0",
                    "createdAt": (now - timedelta(days=30)).isoformat(),
                    "comfy_nodes": [sample_node("TestNode")]
                }]
            },
            {
                "id": "old",
                "name": "Old",
                "downloads": 3500,
                "github_stars": 150,
                "versions_list": [{
                    "version": "1.0.0",
                    "createdAt": (now - timedelta(days=600)).isoformat(),
                    "comfy_nodes": [sample_node("TestNode")]
                }]
            },
        ]

        write_cache_helper(temp_cache_file, nodes)

        builder = GlobalMappingsBuilder()
        result = builder.build_mappings(temp_cache_file)

        entries = result["mappings"]["TestNode::_"]
        assert len(entries) == 3

        # no-dates gets benefit of doubt (no penalty)
        # Base scores: no-dates=600, old=650*0.7=455, recent=550
        # Order: no-dates, recent, old
        package_ids = [e["package_id"] for e in entries]
        assert package_ids[0] == "no-dates"
        assert package_ids[1] == "recent"
        assert package_ids[2] == "old"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
