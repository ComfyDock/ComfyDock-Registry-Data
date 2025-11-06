#!/usr/bin/env python3
"""Refresh metadata for specific nodes in the cache."""

import argparse
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from registry_client import RegistryClient

from logging import getLogger, basicConfig, INFO, DEBUG

logger = getLogger(__name__)


class MetadataRefresher:
    """Refreshes metadata for nodes in the cache."""

    def __init__(
        self,
        delay_seconds: float = 0.5,
        checkpoint_interval: int = 10,
        max_versions: int = 10,
        max_retries: int = 5
    ):
        self.delay = delay_seconds
        self.checkpoint_interval = checkpoint_interval
        self.max_versions = max_versions
        self.max_retries = max_retries
        self.stats = {
            "nodes_processed": 0,
            "versions_attempted": 0,
            "versions_with_data": 0,
            "versions_confirmed_empty": 0,
            "versions_failed": 0,
            "total_metadata_entries": 0
        }

    async def refresh_cache(
        self,
        cache_file: Path,
        output_file: Path,
        target_nodes: Optional[List[str]] = None,
        max_nodes: Optional[int] = None,
        force_refresh_empty: bool = True
    ):
        """Refresh metadata for specified nodes."""
        start_time = time.time()

        logger.info("=" * 60)
        logger.info("METADATA REFRESH")
        logger.info("=" * 60)
        logger.info(f"Cache file: {cache_file}")
        logger.info(f"Output file: {output_file}")
        logger.info(f"Delay between requests: {self.delay}s")
        logger.info(f"Max versions per node: {self.max_versions}")
        logger.info(f"Force refresh empty: {force_refresh_empty}")

        # Load cache
        logger.info("Loading cache...")
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)

        nodes_list = cache_data.get("nodes", [])
        logger.info(f"Loaded {len(nodes_list)} nodes from cache")

        # Filter to target nodes if specified
        if target_nodes:
            original_count = len(nodes_list)
            nodes_list = [n for n in nodes_list if n["id"] in target_nodes]
            logger.info(f"Filtered to {len(nodes_list)} target nodes (from {original_count})")

        if not nodes_list:
            logger.error("No nodes to process!")
            return

        # Limit max nodes if specified
        if max_nodes:
            nodes_list = nodes_list[:max_nodes]
            logger.info(f"Limited to first {max_nodes} nodes")

        # Process nodes with checkpointing
        async with RegistryClient(max_retries=self.max_retries) as client:
            for i, node in enumerate(nodes_list):
                node_id = node["id"]
                logger.info(f"\n[{i+1}/{len(nodes_list)}] Processing {node_id}...")

                await self._refresh_node_metadata(client, node, force_refresh_empty)
                self.stats["nodes_processed"] += 1

                # Checkpoint save
                if (i + 1) % self.checkpoint_interval == 0:
                    self._save_cache(cache_data, output_file)
                    logger.info(f"✅ Checkpoint saved ({i+1}/{len(nodes_list)} nodes)")

        # Final save
        self._save_cache(cache_data, output_file)

        # Print summary
        elapsed = time.time() - start_time
        self._print_summary(elapsed)

    async def _refresh_node_metadata(
        self,
        client: RegistryClient,
        node: dict,
        force_refresh_empty: bool
    ):
        """Refresh metadata for top N versions of a node."""
        node_id = node["id"]
        versions_list = node.get("versions_list", [])

        if not versions_list:
            logger.warning(f"  No versions found for {node_id}")
            return

        # Get top N versions
        top_versions = versions_list[:self.max_versions]
        logger.info(f"  Checking top {len(top_versions)} versions")

        versions_needing_refresh = []
        for version_info in top_versions:
            comfy_nodes = version_info.get("comfy_nodes", [])
            metadata_cached = version_info.get("metadata_cached", False)

            # Determine if needs refresh
            needs_refresh = False
            if not metadata_cached:
                needs_refresh = True
                reason = "not cached"
            elif force_refresh_empty and len(comfy_nodes) == 0:
                needs_refresh = True
                reason = "empty (forced refresh)"
            elif len(comfy_nodes) > 0:
                reason = f"has {len(comfy_nodes)} entries (skipping)"
            else:
                reason = "cached as empty (skipping)"

            if needs_refresh:
                versions_needing_refresh.append((version_info, reason))
            else:
                logger.debug(f"    {version_info['version']}: {reason}")

        if not versions_needing_refresh:
            logger.info(f"  ✅ All top {len(top_versions)} versions already have metadata")
            return

        logger.info(f"  Found {len(versions_needing_refresh)} versions needing refresh")

        # Fetch metadata for each version
        for version_info, reason in versions_needing_refresh:
            version = version_info["version"]
            logger.info(f"    Fetching {node_id}@{version} ({reason})...")

            self.stats["versions_attempted"] += 1

            # Fetch with rate limiting
            result = await client.get_comfy_nodes(node_id, version)
            await asyncio.sleep(self.delay)

            # Update cache based on result
            if result is None:
                # Failed to fetch
                logger.warning(f"      ❌ Failed to fetch (rate limit/timeout/error)")
                version_info["metadata_refresh_attempted"] = datetime.now().isoformat()
                version_info["metadata_refresh_failed"] = True
                self.stats["versions_failed"] += 1
            elif result:
                # Success with data!
                version_info["comfy_nodes"] = result
                version_info["metadata_cached"] = True
                version_info["metadata_refresh_attempted"] = datetime.now().isoformat()
                version_info["metadata_refresh_failed"] = False
                logger.info(f"      ✅ Fetched {len(result)} comfy-nodes")
                self.stats["versions_with_data"] += 1
                self.stats["total_metadata_entries"] += len(result)
            else:
                # Confirmed empty (legitimate)
                version_info["comfy_nodes"] = []
                version_info["metadata_cached"] = True
                version_info["metadata_refresh_attempted"] = datetime.now().isoformat()
                version_info["metadata_refresh_failed"] = False
                logger.info(f"      ✅ Confirmed empty (no metadata exists)")
                self.stats["versions_confirmed_empty"] += 1

        # Update node metadata_count
        node["metadata_count"] = sum(
            1 for v in versions_list
            if v.get("metadata_cached", False) and v.get("comfy_nodes") is not None
        )

    def _save_cache(self, cache_data: dict, output_file: Path):
        """Save cache atomically."""
        try:
            # Update top-level stats
            nodes = cache_data["nodes"]
            total_versions = sum(len(n.get("versions_list", [])) for n in nodes)
            total_metadata = sum(
                sum(len(v.get("comfy_nodes", [])) for v in n.get("versions_list", []))
                for n in nodes
            )

            cache_data["cached_at"] = datetime.now().isoformat()
            cache_data["node_count"] = len(nodes)
            cache_data["versions_processed"] = total_versions
            cache_data["metadata_entries"] = total_metadata

            # Atomic write
            output_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file = Path(str(output_file) + '.tmp')

            try:
                with open(temp_file, 'w') as f:
                    json.dump(cache_data, f, indent=2)
                temp_file.replace(output_file)

                file_size = output_file.stat().st_size / 1024 / 1024
                logger.debug(f"Cache saved: {cache_data['node_count']} nodes, {file_size:.1f} MB")
            finally:
                if temp_file.exists():
                    temp_file.unlink()

        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
            raise

    def _print_summary(self, elapsed: float):
        """Print refresh summary."""
        logger.info("=" * 60)
        logger.info("📊 REFRESH SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Nodes processed: {self.stats['nodes_processed']}")
        logger.info(f"Versions attempted: {self.stats['versions_attempted']}")
        logger.info(f"  - With data: {self.stats['versions_with_data']}")
        logger.info(f"  - Confirmed empty: {self.stats['versions_confirmed_empty']}")
        logger.info(f"  - Failed: {self.stats['versions_failed']}")
        logger.info(f"Total metadata entries fetched: {self.stats['total_metadata_entries']}")
        logger.info(f"Time elapsed: {elapsed:.1f}s")
        logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Refresh metadata for specific nodes in the cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Refresh metadata for specific nodes
  uv run src/refresh_metadata.py \\
    --cache data/full_registry_cache.json \\
    --output data/full_registry_cache_refreshed.json \\
    --nodes comfyui_fill-nodes

  # Refresh top 100 nodes
  uv run src/refresh_metadata.py \\
    --cache data/full_registry_cache.json \\
    --output data/full_registry_cache_refreshed.json \\
    --max-nodes 100 \\
    --delay 0.5
        """
    )

    parser.add_argument(
        "--cache", "-c",
        type=Path,
        required=True,
        help="Input cache file"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        required=True,
        help="Output cache file (can be same as input for in-place update)"
    )
    parser.add_argument(
        "--nodes",
        nargs="+",
        help="Specific node IDs to refresh (if not specified, all nodes)"
    )
    parser.add_argument(
        "--max-nodes",
        type=int,
        help="Maximum number of nodes to process"
    )
    parser.add_argument(
        "--max-versions",
        type=int,
        default=10,
        help="Max versions per node to refresh (default: 10)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between API requests in seconds (default: 0.5)"
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=10,
        help="Save checkpoint every N nodes (default: 10)"
    )
    parser.add_argument(
        "--no-force-empty",
        action="store_true",
        help="Don't force refresh of empty metadata (respect metadata_cached flag)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )

    args = parser.parse_args()

    # Setup logging
    basicConfig(
        level=getattr(__import__('logging'), args.log_level),
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    refresher = MetadataRefresher(
        delay_seconds=args.delay,
        checkpoint_interval=args.checkpoint_interval,
        max_versions=args.max_versions,
        max_retries=5
    )

    asyncio.run(
        refresher.refresh_cache(
            cache_file=args.cache,
            output_file=args.output,
            target_nodes=args.nodes,
            max_nodes=args.max_nodes,
            force_refresh_empty=not args.no_force_empty
        )
    )


if __name__ == "__main__":
    main()
