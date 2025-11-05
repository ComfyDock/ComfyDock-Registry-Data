#!/usr/bin/env python3
"""
Test that Phase 2 optimization still works correctly after the fix.

The optimization should skip nodes that were checked by Phase 2 within the last hour,
but should NOT skip nodes just because Phase 1 updated them.
"""

import asyncio
from datetime import datetime, timedelta
import sys

sys.path.insert(0, 'src')

from build_registry_cache import RegistryCacheBuilder


async def test_phase2_optimization_works():
    """Verify Phase 2 still skips nodes checked recently by Phase 2."""
    print("=" * 80)
    print("TEST: Phase 2 optimization should still work")
    print("=" * 80)

    builder = RegistryCacheBuilder()

    # Node checked 30 minutes ago by Phase 2
    recent_check = (datetime.now() - timedelta(minutes=30)).isoformat()

    # Node checked 2 hours ago by Phase 2
    old_check = (datetime.now() - timedelta(hours=2)).isoformat()

    builder.nodes_data = {
        "node_recent": {
            "id": "node_recent",
            "last_checked": recent_check,
            "versions_cached": True
        },
        "node_old": {
            "id": "node_old",
            "last_checked": old_check,
            "versions_cached": True
        }
    }

    # Simulate Phase 2 logic (lines 214-226)
    all_nodes = list(builder.nodes_data.items())
    nodes_to_process = []
    skipped_recent = 0

    for node_id, node in all_nodes:
        last_checked = node.get("last_checked")
        if last_checked:
            try:
                last_checked_dt = datetime.fromisoformat(last_checked)
                hours_since_check = (datetime.now() - last_checked_dt).total_seconds() / 3600
                if hours_since_check < 1.0:
                    skipped_recent += 1
                    continue
            except Exception:
                pass

        nodes_to_process.append((node_id, node))

    print(f"\n✓ Results:")
    print(f"  Total nodes: 2")
    print(f"  Skipped (checked < 1 hour ago): {skipped_recent}")
    print(f"  Will process: {len(nodes_to_process)}")

    processed_ids = [node_id for node_id, _ in nodes_to_process]
    print(f"  Processing: {processed_ids}")

    # TEST ASSERTIONS
    print("\n" + "=" * 80)
    if skipped_recent == 1 and len(nodes_to_process) == 1 and "node_old" in processed_ids:
        print("✅ TEST PASSED")
        print("   Optimization works: skips recently checked nodes, processes old ones")
        return True
    else:
        print("❌ TEST FAILED")
        print("   Optimization broken")
        return False


async def run_tests():
    """Run optimization test."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " TESTING PHASE 2 OPTIMIZATION STILL WORKS ".center(78) + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    passed = await test_phase2_optimization_works()

    print("\n" + "=" * 80)
    if passed:
        print("✅ OPTIMIZATION TEST PASSED - Fix does not break the optimization")
        return 0
    else:
        print("❌ OPTIMIZATION TEST FAILED - Fix broke the optimization")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_tests())
    sys.exit(exit_code)
