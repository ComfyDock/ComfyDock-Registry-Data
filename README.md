# ComfyDock Registry Data Pipeline

Automated incremental data pipeline for ComfyUI node mappings.

## Quick Start

```bash
# Run incremental update (recommended)
python src/update_registry.py --data-dir data --incremental

# Force full rebuild
python src/update_registry.py --data-dir data --force-full

# Validate data integrity
python src/validate_data.py --data-dir data
```

## Data Flow

```
ComfyUI Registry API -> Registry Cache -> Node Mappings -> Augmented with Manager Data
```

1. **Cache Building**: Incremental fetch from ComfyUI registry
2. **Mapping Generation**: Create node signatures from cache data
3. **Manager Integration**: Add community extensions from ComfyUI-Manager
4. **Validation**: Ensure data integrity and consistency

## Automated Updates

GitHub Actions runs daily at 2 AM UTC:
- Incremental updates (preserves all existing data)
- Automatic validation and error handling
- Atomic commits with detailed summaries

Trigger manual update: **Actions** -> **Update Registry Data** -> **Run workflow**

## Output Files

- `data/full_registry_cache.json` - Complete registry cache (~30MB)
- `data/node_mappings.json` - Node signatures and package mappings (~10MB)

**Note**: ComfyUI Manager data is GPL-3 licensed and used temporarily during generation only. It's automatically cleaned up to prevent license contamination.

## Scripts

| Script | Purpose |
|--------|---------|
| `update_registry.py` | **Main orchestrator** - runs complete pipeline |
| `build_registry_cache.py` | Fetch and cache registry data incrementally |
| `build_global_mappings.py` | Generate node mappings from cache |
| `augment_mappings.py` | Add ComfyUI Manager community data |
| `fetch_manager_data.py` | Download Manager extension map |
| `validate_data.py` | Verify data integrity |

## Key Features

- **True Incremental**: Never removes data, only adds new entries
- **Timestamp Tracking**: `first_seen` and `last_checked` for audit trails
- **Append-Only**: Deprecated versions marked but preserved
- **Conflict Resolution**: Multiple sources handled gracefully
- **Atomic Operations**: All writes are atomic to prevent corruption

## Development

```bash
# Test incremental update with limited data
python src/build_registry_cache.py --pages 5 --output test_cache.json
python src/build_global_mappings.py --cache test_cache.json --output test_mappings.json

# Validate specific files
python src/validate_data.py --cache test_cache.json --mappings test_mappings.json

# Fetch latest Manager data
python src/fetch_manager_data.py --output data/extension-node-map.json
```

## Monitoring

The pipeline tracks:
- Package count and growth
- Version additions per update
- Node signature coverage
- Data file sizes and build times
- Synthetic package creation from Manager

All metrics are captured in commit messages and GitHub Actions logs.
