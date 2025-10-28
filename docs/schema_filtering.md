# Schema-Based Output Filtering

## Overview

The registry data pipeline supports configurable schema filtering to reduce output file size by excluding unused fields from the final `node_mappings.json` file.

**Key Benefits:**
- **22% size reduction** on production data (~3MB saved)
- **Config-driven** - change schema without code changes
- **Backward compatible** - CLI handles missing fields gracefully
- **Safe defaults** - includes all fields if config missing

## Configuration

Schema is defined in `config/output_schema.toml`:

```toml
[packages]
display_name = true   # Include in output
author = false        # Exclude from output
...

[versions]
version = true
changelog = false
...

[mappings]
package_id = true
...
```

## Usage

### Automatic (Default)

All scripts use `config/output_schema.toml` by default:

```bash
# Uses config/output_schema.toml automatically
uv run src/update_registry.py --data-dir data
uv run src/build_global_mappings.py --cache data/cache.json --output data/mappings.json
uv run src/augment_mappings.py --mappings data/mappings.json --manager data/manager.json
```

### Custom Schema

Override with `--schema-config`:

```bash
uv run src/update_registry.py --data-dir data --schema-config config/full_schema.toml
```

### Disable Filtering

Point to non-existent file to disable filtering:

```bash
uv run src/update_registry.py --data-dir data --schema-config /dev/null
```

## Current Minimal Schema

Based on field usage audit of comfydock CLI:

### Package Fields (Included)
- `display_name` - Used in CLI for package selection
- `description` - Used in CLI for package info
- `repository` - Critical for git clone operations
- `github_stars` - Used for popularity scoring
- `versions` - Critical for version selection
- `source` - Distinguishes registry vs manager packages

### Package Fields (Excluded)
- `author`, `downloads`, `rating`, `license`, `category`, `icon`, `tags`, `status`, `created_at`
- These are loaded but never referenced in CLI logic

### Version Fields (Included)
- `version` - Version selection
- `download_url` - Critical for downloading packages
- `deprecated` - Used to skip deprecated versions
- `dependencies` - Shown in CLI

### Version Fields (Excluded)
- `changelog`, `release_date`, `status`, `supported_accelerators`, `supported_comfyui_version`, `supported_os`
- These are loaded but never used

### Mapping Fields (All Included)
- `package_id`, `versions`, `rank`, `source`
- All required for CLI functionality

## File Size Impact

**Production Data (test_mappings.json):**
- Original: 13.7 MB
- Filtered: 10.7 MB
- **Reduction: 22% (3.0 MB saved)**

**Test Data (100 synthetic packages):**
- Original: 166 KB
- Filtered: 76 KB
- **Reduction: 54%**

Lower reduction on production data due to:
- Many synthetic packages with empty versions (nothing to filter)
- Large mappings section (all fields required)

## Implementation

### Filter Module: `src/schema_filter.py`

```python
from schema_filter import SchemaFilter

filter = SchemaFilter(Path('config/output_schema.toml'))
filtered_data = filter.filter_mappings_output(data)
```

### Integration Points

1. **augment_mappings.py** - Filters after augmentation (final output)
2. **build_global_mappings.py** - Filters for standalone usage
3. **update_registry.py** - Orchestrator passes config through

### Fail-Safe Behavior

- **Missing config**: Returns data unfiltered
- **Malformed TOML**: Logs error, returns unfiltered
- **Unknown fields**: Defaults to include (forward compatible)

## Testing

Run schema filter tests:

```bash
pytest tests/unit/test_schema_filter.py -v
```

Test on real data:

```bash
python3 << 'EOF'
import json
from pathlib import Path
from schema_filter import SchemaFilter

with open('test_mappings.json') as f:
    data = json.load(f)

filter = SchemaFilter(Path('config/output_schema.toml'))
filtered = filter.filter_mappings_output(data)

original_size = len(json.dumps(data))
filtered_size = len(json.dumps(filtered))
print(f"Reduction: {((original_size - filtered_size) / original_size) * 100:.1f}%")
EOF
```

## Future Enhancements

### Multiple Schemas

Create alternate configs for different use cases:

```bash
config/output_schema_minimal.toml  # Default (current)
config/output_schema_full.toml     # All fields
config/output_schema_analytics.toml # Custom for analytics
```

### Schema Versioning

Embed schema version in output metadata:

```json
{
  "version": "2025.01.01",
  "schema_version": "minimal-v1",
  ...
}
```

### Field Aliasing

Rename fields for shorter keys:

```toml
[packages.aliases]
github_stars = "stars"
display_name = "name"
```

## Notes

- **Cache file unchanged**: `full_registry_cache.json` always contains all data
- **No validation**: Disabling required fields won't error (fails at CLI runtime)
- **Python 3.13+**: Uses stdlib `tomllib` for TOML parsing
