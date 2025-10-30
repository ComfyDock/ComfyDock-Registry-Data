# ComfyDock Registry Data

Automated data pipeline for ComfyUI node mappings and package discovery. Provides comprehensive, continuously updated registry data for efficient node resolution and package management.

## Quick Start

```bash
# Run incremental update (recommended)
python src/update_registry.py --data-dir data --incremental

# Force full rebuild
python src/update_registry.py --data-dir data --force-full

# Validate data integrity
python src/validate_data.py --data-dir data
```

## Data Pipeline

```
ComfyUI Registry API → Registry Cache → Node Mappings → Community Extensions
```

The pipeline operates in phases:
1. **Cache Building** - Incremental fetch from ComfyUI registry
2. **Mapping Generation** - Create node signatures with input types
3. **Community Integration** - Augment with ecosystem extensions
4. **Validation** - Ensure data integrity and consistency

## Output Files

### `data/node_mappings.json` (~10MB)
Primary output file containing node signatures and package mappings.

**Structure:**
```json
{
  "version": "2024.10.28",
  "generated_at": "2024-10-28T12:21:00",
  "stats": {
    "packages": 1234,
    "signatures": 5678,
    "total_nodes": 9012
  },
  "mappings": {
    "node_name|input_signature": [
      {
        "package_id": "author/package-name",
        "versions": ["1.0.0", "0.9.0"],
        "rank": 1
      }
    ]
  },
  "packages": {
    "author/package-name": {
      "display_name": "Package Name",
      "repository": "https://github.com/author/package-name",
      "downloads": 1000,
      "github_stars": 50,
      "versions": { ... }
    }
  }
}
```

**Package Ranking:** Packages are ranked by popularity score:
- Downloads (weighted 0.1x)
- GitHub stars (weighted 2x)
- Recency multiplier (0.5-1.0 based on last release age)

### `data/full_registry_cache.json` (~65MB)
Complete registry cache stored in GitHub Releases (not committed to git).

## Key Features

- **Incremental Updates** - Never removes data, only adds new entries
- **Timestamp Tracking** - Audit trails with `first_seen` and `last_checked`
- **Version Preservation** - Deprecated versions marked but retained
- **Multi-Source Resolution** - Handles packages from multiple sources
- **Atomic Operations** - All writes are atomic to prevent corruption
- **Schema Filtering** - Configurable output schema via `config/output_schema.toml`

## Automated Updates

GitHub Actions workflow (currently disabled pending dependency availability):
- Daily incremental updates at 2 AM UTC
- Automatic validation and error handling
- Cache stored in releases, mappings committed to git
- Detailed metrics in commit messages

## Development

```bash
# Install dependencies
uv sync

# Test with limited data
python src/build_registry_cache.py --pages 5 --output test_cache.json
python src/build_global_mappings.py --cache test_cache.json --output test_mappings.json

# Validate output
python src/validate_data.py --cache test_cache.json --mappings test_mappings.json
```

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `update_registry.py` | Main orchestrator for complete pipeline |
| `build_registry_cache.py` | Fetch and cache registry data incrementally |
| `build_global_mappings.py` | Generate node mappings from cache |
| `augment_mappings.py` | Add community extensions |
| `validate_data.py` | Verify data integrity |

## Requirements

- Python 3.13+
- Dependencies: `aiohttp`, `comfydock-core`
- UV package manager (recommended)

## License

This project is licensed under **GNU Affero General Public License v3.0 (AGPL-3.0)**.

**Commercial Licensing:** Businesses requiring integration into proprietary systems can request a more permissive license. Contact the project maintainers for commercial licensing options.
