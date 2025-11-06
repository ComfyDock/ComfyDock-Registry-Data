#!/bin/bash
# Test metadata override functionality
# This script uses CONSERVATIVE settings (concurrency=1) to guarantee no rate limits
#
# Available settings profiles:
# - Conservative (this script): --concurrency 1 --rate-limit-delay 0.5  (~25 min for full override)
# - Balanced (production):      --concurrency 5 --rate-limit-delay 0.1  (~5 min for full override)
# - Aggressive:                 --concurrency 10 --rate-limit-delay 0.05 (~2.5 min, may hit limits)

set -e  # Exit on error

echo "🧪 METADATA OVERRIDE TEST (Conservative Settings)"
echo "="
echo ""
echo "⏱️  Expected duration: ~25 minutes (using concurrency=1 for safety)"
echo "📝 Log file: test_override_v2_run.log"
echo "📂 Output directory: data_test_override_v2/"
echo ""
echo "🔍 What to expect:"
echo "  - Phase 1: ~90 seconds (fetch basic node info)"
echo "  - Phase 2: ~2 seconds (13 nodes with version updates)"
echo "  - Phase 3: ~24 minutes (re-fetch metadata for ~1,700 nodes @ 1 req/sec)"
echo ""
echo "Starting in 3 seconds..."
sleep 3

# 1. Create fresh test directory
echo "📁 Creating fresh test directory..."
rm -rf data_test_override_v2
mkdir -p data_test_override_v2

# 2. Copy input cache as starting point
echo "📦 Copying input cache..."
cp data/full_registry_cache.json data_test_override_v2/

# 3. Show before state
echo ""
echo "📊 BEFORE STATE:"
jq -r '"  Cached: \(.cached_at)\n  Nodes: \(.node_count)\n  Versions: \(.versions_processed)\n  Metadata: \(.metadata_entries)"' data/full_registry_cache.json

echo ""
echo "🚀 Starting metadata override test..."
echo ""

# 4. Run with metadata override (outputs to log file)
# Note: Using conservative settings to guarantee zero rate limit errors
uv run --no-sources python src/update_registry.py \
  --data-dir data_test_override_v2 \
  --schema-config config/output_schema.toml \
  --incremental \
  --metadata-override \
  --max-versions 1 \
  --rate-limit-delay 0.5 \
  --max-retries 5 \
  --concurrency 1 \
  --checkpoint-interval 500 \
  --log-level INFO \
  2>&1 | tee test_override_v2_run.log

# 5. Show after state
echo ""
echo "📊 AFTER STATE:"
jq -r '"  Cached: \(.cached_at)\n  Nodes: \(.node_count)\n  Versions: \(.versions_processed)\n  Metadata: \(.metadata_entries)"' data_test_override_v2/full_registry_cache.json

# 6. Verify FL_PathAnimator is in registry source
echo ""
echo "=========================================="
echo "🔍 VERIFICATION: FL_PathAnimator mapping"
echo "=========================================="
echo ""
echo "Expected: Should have comfyui_fill-nodes with version 2.1.0"
echo ""
jq '.mappings["FL_PathAnimator::_"]' data_test_override_v2/node_mappings.json

echo ""
echo "=========================================="
echo "✅ Test complete!"
echo "=========================================="
echo ""
echo "📝 Full log saved to: test_override_v2_run.log"
echo "📂 Output files in: data_test_override_v2/"
echo ""
echo "To check if FL_PathAnimator has registry source:"
echo "  jq '.mappings[\"FL_PathAnimator::_\"] | .[] | select(.source == \"registry\")' data_test_override_v2/node_mappings.json"
