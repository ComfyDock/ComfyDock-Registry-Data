# Node Mappings Schema

**Version**: 2.0
**Last Updated**: 2025-10-10

---

## Overview

This document defines the formal schema for `node_mappings.json`, the unified data structure that maps ComfyUI node types to packages across the ComfyUI Registry and ComfyUI Manager ecosystems.

**Purpose**: Enable node type resolution for dependency management and package discovery by mapping node display names + input signatures to package sources.

**Data Sources**:
1. **Registry**: ComfyUI Registry API (primary, high-quality data with version metadata)
2. **Manager**: ComfyUI Manager extension-node-map (supplementary, broader coverage)

---

## Schema Structure

### Root Object

```typescript
interface NodeMappingsData {
  version: string;              // Format: "YYYY.MM.DD"
  generated_at: string;         // ISO 8601 timestamp
  stats: Statistics;            // Build statistics
  mappings: NodeMappings;       // Node signature → package mappings
  packages: PackageRegistry;    // Package metadata registry
}
```

---

## Field Definitions

### `version`

**Type**: `string`
**Format**: `YYYY.MM.DD`
**Description**: Semantic version of the mappings data, based on generation date.

**Example**: `"2025.10.10"`

---

### `generated_at`

**Type**: `string`
**Format**: ISO 8601 timestamp
**Description**: Timestamp when mappings were generated.

**Example**: `"2025-10-10T12:54:25.324565"`

---

### `stats`

**Type**: `Statistics`
**Description**: Build statistics and metadata.

```typescript
interface Statistics {
  packages: number;                 // Total packages in registry
  signatures: number;               // Unique node signatures
  total_nodes: number;              // Total mapping entries (sum of all arrays)
  augmented?: boolean;              // Whether Manager data was merged
  augmentation_date?: string;       // ISO timestamp of augmentation
  nodes_from_manager?: number;      // Mappings added from Manager
  manager_packages?: number;        // Packages created from Manager-only data
}
```

**Example**:
```json
{
  "packages": 2917,
  "signatures": 15372,
  "total_nodes": 26004,
  "augmented": true,
  "augmentation_date": "2025-10-10T13:15:42.123456",
  "nodes_from_manager": 8500,
  "manager_packages": 150
}
```

---

### `mappings`

**Type**: `NodeMappings`
**Description**: Maps node signatures to packages that provide them.

```typescript
interface NodeMappings {
  [nodeKey: string]: PackageMapping[];
}

// Node key format: "DisplayName::signature_hash"
// - DisplayName: The node's display_name from comfy_nodes metadata
// - signature_hash: 8-char hash of normalized input signature
//   - "_" for unknown/placeholder signatures (Manager data)
//   - Hash value for known signatures (Registry data)
```

**Key Format**:
- Registry nodes: `"ReActorFaceSwapOpt::079f3587"` (real signature hash)
- Manager nodes: `"Int to Text::_"` (placeholder signature)

**Value**: Array of `PackageMapping` objects, ranked by popularity.

---

### `PackageMapping`

**Type**: `object`
**Description**: Links a specific package to a node signature with ranking metadata.

```typescript
interface PackageMapping {
  package_id: string;           // Package identifier
  versions: string[];           // Package versions providing this node
  rank: number;                 // Ranking (1 = highest, 2 = second, etc.)
  source?: "manager";           // Data source (omitted = registry, default)
}
```

**Field Details**:

#### `package_id`
- **Type**: `string`
- **Description**: Unique package identifier
- **Format**:
  - Registry packages: Use registry's ID (e.g., `"comfyui-reactor"`)
  - Manager packages: Prefixed with `manager_` (e.g., `"manager_user_repo"`)
- **See**: [Package ID Strategy](#package-id-strategy)

#### `versions`
- **Type**: `string[]`
- **Description**: List of package versions that provide this node
- **Sorting**: Descending (newest first)
- **Empty array**: Indicates Manager data (no version information available)

**Example**: `["1.0.0", "0.9.5", "0.9.0"]`

#### `rank`
- **Type**: `number` (integer)
- **Description**: Rank among all packages providing this node
- **Range**: `[1, n]` where `n` is the number of packages
- **Sorting**: By popularity score (rank 1 = highest popularity)
- **Note**: Score is calculated internally but not stored; only rank is persisted

#### `source`
- **Type**: `"manager"` (optional)
- **Description**: Indicates mapping originated from ComfyUI Manager data
- **Default**: If omitted, mapping is from ComfyUI Registry (default assumption)
- **Values**:
  - Omitted: From ComfyUI Registry API (high quality, has real input signature)
  - `"manager"`: From ComfyUI Manager data (lower quality, placeholder signature)

**Purpose**: Track data provenance for quality assessment and debugging.

**Rationale**: Most mappings are from Registry, so we only mark the minority (Manager) explicitly.

---

### `mappings` Examples

#### Single Package (Registry Only)

```json
{
  "MyCustomNode::a1b2c3d4": [
    {
      "package_id": "my-custom-nodes",
      "versions": ["2.0.1", "2.0.0", "1.5.0"],
      "rank": 1
    }
  ]
}
```

#### Multiple Packages (Ranked)

```json
{
  "ReActorFaceSwapOpt::079f3587": [
    {
      "package_id": "comfyui-reactor",
      "versions": ["0.6.1", "0.6.0"],
      "rank": 1
    },
    {
      "package_id": "comfyui-reactor-node",
      "versions": ["0.5.2"],
      "rank": 2
    }
  ]
}
```

#### Manager Augmentation (Placeholder Signature)

```json
{
  "Int to Text::_": [
    {
      "package_id": "manager_gist_7361b8eb966f29c8238fd323409efb68",
      "versions": [],
      "rank": 1,
      "source": "manager"
    }
  ]
}
```

#### Mixed Sources (Registry + Manager)

```json
{
  "LoadImage::_": [
    {
      "package_id": "comfyui-image-loader",
      "versions": ["1.2.0", "1.1.0"],
      "rank": 1
    },
    {
      "package_id": "manager_user_image-utils",
      "versions": [],
      "rank": 2,
      "source": "manager"
    }
  ]
}
```

---

### `packages`

**Type**: `PackageRegistry`
**Description**: Registry of all packages referenced in mappings.

```typescript
interface PackageRegistry {
  [packageId: string]: PackageInfo;
}
```

---

### `PackageInfo`

**Type**: `object`
**Description**: Metadata for a single package.

```typescript
interface PackageInfo {
  // Basic metadata
  display_name: string;             // Human-readable name
  author: string;                   // Package author/maintainer
  description: string;              // Package description
  repository: string;               // Normalized repository URL

  // Popularity metrics
  downloads: number;                // Total downloads (0 for Manager packages)
  github_stars: number;             // GitHub stars (0 for Manager packages)
  rating: number;                   // User rating (0 if unavailable)

  // Additional metadata
  license: string;                  // License info (JSON string or empty)
  category: string;                 // Package category
  icon: string;                     // Icon URL
  tags: string[];                   // Categorization tags
  status: string;                   // "NodeStatusActive", etc.
  created_at: string;               // ISO timestamp

  // Provenance
  source?: "registry" | "manager";  // Package data source

  // Versions
  versions: {
    [version: string]: VersionInfo;
  };
}
```

**Field Details**:

#### Core Fields

- **`display_name`**: Human-readable package name
  - Registry: From package metadata
  - Manager: From `title_aux` or extracted from repo name

- **`author`**: Package author/maintainer
  - Registry: From package metadata
  - Manager: Extracted from repository URL

- **`description`**: Package description
  - Registry: From package metadata
  - Manager: From `description` field or empty string

- **`repository`**: **Normalized** repository URL
  - **Important**: Always normalized using `normalize_repository_url()`
  - Used for matching Manager data with Registry packages
  - See: [URL Normalization](#url-normalization)

#### Popularity Metrics

- **`downloads`**: Total package downloads
  - Registry: Actual download count
  - Manager: Always `0`

- **`github_stars`**: GitHub repository stars
  - Registry: Actual star count
  - Manager: Always `0`

- **`rating`**: User rating
  - Registry: Average user rating
  - Manager: Always `0`

#### Provenance

- **`source`**: Data source for this package
  - **Optional field** (only present for Manager-created packages)
  - Values:
    - `"manager"`: Package created from Manager data (not in Registry)
    - Omitted: Package from Registry (default assumption)

**Rationale**:
- Most packages are from Registry (no need to mark every one)
- Manager packages are minority and need explicit marking
- Absence of field = Registry source

#### Versions

- **`versions`**: Map of version strings to version metadata
  - Registry: Full version metadata with dependencies, download URLs, etc.
  - Manager: Empty object `{}` (no version information available)

**Sorting**: Versions sorted descending by semantic version (newest first)

---

### `VersionInfo`

**Type**: `object`
**Description**: Metadata for a specific package version.

```typescript
interface VersionInfo {
  version: string;                      // Version string
  changelog: string;                    // Release notes
  release_date: string;                 // ISO timestamp
  dependencies: string[];               // Python dependencies
  deprecated: boolean;                  // Deprecation status
  download_url: string;                 // Package download URL
  status: string;                       // Version status
  supported_accelerators: string[] | null;  // GPU requirements
  supported_comfyui_version: string;    // ComfyUI compatibility
  supported_os: string[] | null;        // OS compatibility
}
```

**Notes**:
- Only Registry packages have version data
- Manager packages have `versions: {}`
- Deprecated versions excluded from mappings but kept in package metadata

---

## Package ID Strategy

### Registry Packages

**Source**: ComfyUI Registry API
**Format**: Registry's own ID scheme
**Examples**:
- `"comfyui-reactor"` (GitHub repo)
- `"ComfyUI-GGUF"` (GitHub repo)
- `"7361b8eb966f29c8238fd323409efb68"` (Gist hash)

**Characteristics**:
- Varies by package type
- Registry controls ID generation
- No prefix/namespace

---

### Manager Packages

**Source**: ComfyUI Manager extension-node-map
**Format**: `manager_` prefix + identifier
**Purpose**: Avoid ID collisions with Registry packages

#### ID Generation Rules

```python
def generate_manager_package_id(normalized_url: str) -> str:
    """
    Generate package ID for Manager-only packages.

    Format: manager_{identifier}

    Rules:
    - GitHub repos: manager_user_repo
    - Gists: manager_gist_hash
    - Other platforms: manager_domain_user_repo
    """
```

| Repository Type | Package ID Format | Example |
|----------------|-------------------|---------|
| GitHub repo | `manager_user_repo` | `manager_gourieff_comfyui-reactor` |
| GitHub raw file | `manager_user_repo` | `manager_1shadow1_hayo_comfyui_nodes` |
| Gist | `manager_gist_hash` | `manager_gist_7361b8eb966f29c8238fd323409efb68` |
| Gitee | `manager_user_repo` | `manager_yyh915_jkha-load-img` |
| Custom Git | `manager_domain_user_repo` | `manager_mmaker_moe_mmaker_sd-webui-color-enhance` |

**Character Normalization**:
- Convert to lowercase
- Replace `-` with `_`
- Replace `.` with `_` (for domain names)
- Remove special characters

---

### Package Source Resolution

**Priority**: Registry packages always take precedence over Manager packages.

**Algorithm**:
```
1. Normalize Manager extension URL
2. Look up normalized URL in Registry packages
3. If FOUND → Use Registry package ID
4. If NOT FOUND → Create Manager package with manager_ prefix
```

**Example**:

Manager has:
```
https://raw.githubusercontent.com/user/repo/main/file.py
```

Registry has:
```
package_id: "custom-repo"
repository: "https://github.com/user/repo"
```

**Result**: Use `"custom-repo"` (Registry package), do NOT create `"manager_user_repo"`

---

## URL Normalization

### Purpose

Enable matching between Manager and Registry data despite URL format differences.

**Problem**:
- Manager: `https://raw.githubusercontent.com/user/repo/main/file.py`
- Registry: `https://github.com/user/repo`
- Without normalization: No match ❌

### Normalization Rules

**Function**: `normalize_repository_url(url: str) -> str`

**Transformations**:

1. **GitHub raw files** → GitHub repo
   ```
   https://raw.githubusercontent.com/USER/REPO/BRANCH/path/file.py
   → https://github.com/USER/REPO
   ```

2. **Gist raw files** → Gist canonical
   ```
   https://gist.githubusercontent.com/USER/HASH/raw/COMMIT/file.py
   → https://gist.github.com/USER/HASH
   ```

3. **Standard repos** → Normalized
   ```
   https://github.com/USER/REPO/.git
   → https://github.com/user/repo
   ```

**Standard Normalizations** (all URLs):
- Convert to lowercase
- Remove trailing `/`
- Remove `.git` suffix
- Remove query parameters and fragments
- Decode URL encoding

### Supported Platforms

- GitHub (`github.com`)
- GitHub Raw (`raw.githubusercontent.com`)
- Gist (`gist.github.com`, `gist.githubusercontent.com`)
- Gitee (`gitee.com`)
- Custom Git servers (`git.*`, self-hosted)

**Implementation**: See `docs/url_analysis.md` for detailed platform breakdown.

---

## Data Provenance & Quality

### Source Field Semantics

The `source` field tracks data origin at TWO levels:

#### 1. Package Level (`packages[id].source`)

**Optional field**: Only present for Manager-created packages

- **`"manager"`**: Package created from Manager data (not in Registry)
- **Omitted**: Package from Registry (default)

**Usage**:
```python
# Check if package is Manager-only
is_manager_package = package_info.get("source") == "manager"

# Registry packages
if "source" not in package_info:
    # This is a Registry package
```

#### 2. Mapping Level (`mappings[key][].source`)

**Optional field**: Only present for Manager mappings

- **Omitted**: Mapping from Registry (has real input signature, version info) - default
- **`"manager"`**: Mapping from Manager (placeholder signature, no versions)

**Usage**:
```python
# Find high-quality mappings (Registry only)
registry_mappings = [m for m in mappings if "source" not in m]

# Find Manager augmentations
manager_mappings = [m for m in mappings if m.get("source") == "manager"]
```

### Quality Indicators

| Data Point | Registry | Manager | Quality |
|------------|----------|---------|---------|
| Input signature | ✅ Real hash | ❌ Placeholder `_` | Registry >> Manager |
| Version info | ✅ Full metadata | ❌ Empty `[]` | Registry >> Manager |
| Dependencies | ✅ Listed | ❌ None | Registry >> Manager |
| Download stats | ✅ Real counts | ❌ Always 0 | Registry >> Manager |

**Recommendation**: Prefer Registry mappings when both sources have the same node.

---

## Data Flow & Build Process

### Step 1: Build Registry Mappings

**Script**: `build_global_mappings.py`
**Input**: Registry cache (from API)
**Output**: Base mappings file

**Process**:
1. Load registry cache
2. Extract packages and versions
3. Parse `comfy_nodes` metadata from versions
4. Generate node keys (name + signature hash)
5. Create mappings (omit `source` for Registry data)
6. Rank packages by popularity score

**Result**:
```json
{
  "mappings": {
    "NodeName::hash": [
      {
        "package_id": "registry-package",
        "versions": ["1.0.0"],
        "rank": 1
      }
    ]
  },
  "packages": {
    "registry-package": { /* full metadata */ }
  }
}
```

---

### Step 2: Augment with Manager Data

**Script**: `augment_mappings.py`
**Input**: Base mappings + Manager extension-node-map
**Output**: Augmented mappings file

**Process**:

#### Phase 1: Build URL Lookup
```
For each Registry package:
  normalized_url = normalize_repository_url(package.repository)
  url_map[normalized_url] = package_id
```

#### Phase 2: Augment Registry Packages
```
For each Manager extension:
  normalized_url = normalize_repository_url(extension_url)

  If normalized_url in url_map:
    package_id = url_map[normalized_url]

    For each node in extension:
      node_key = create_node_key(node_name, "_")

      If package NOT already in mappings[node_key]:
        Add mapping:
          package_id: package_id
          versions: []
          score: calculate from package stats
          rank: TBD
          source: "manager"
```

#### Phase 3: Create Manager Packages
```
For each Manager extension NOT matched in Phase 2:
  package_id = generate_manager_package_id(normalized_url)

  Create package:
    display_name: from Manager metadata
    repository: normalized_url
    downloads: 0
    github_stars: 0
    source: "manager"
    versions: {}

  For each node in extension:
    node_key = create_node_key(node_name, "_")

    Add mapping:
      package_id: package_id
      versions: []
      score: 0.1 (minimum)
      rank: TBD
      source: "manager"
```

#### Phase 4: Re-rank All Mappings
```
For each node_key in mappings:
  Sort mappings by score (descending)
  Assign ranks (1, 2, 3, ...)
```

**Result**: Unified mappings with both Registry and Manager data.

---

## Usage Examples

### Example 1: Resolve Node to Package

**Goal**: Find packages that provide node `"ReActorFaceSwapOpt"` with signature `"079f3587"`

```python
import json

with open('node_mappings.json', 'r') as f:
    data = json.load(f)

node_key = "ReActorFaceSwapOpt::079f3587"
packages = data['mappings'].get(node_key, [])

# Get top-ranked package
if packages:
    top = packages[0]
    print(f"Best match: {top['package_id']}")
    print(f"Versions: {top['versions']}")
    print(f"Rank: {top['rank']}")

    # Check source
    if top.get('source') == 'manager':
        print("Source: Manager (placeholder signature)")
    else:
        print("Source: Registry (verified signature)")
```

**Output**:
```
Best match: comfyui-reactor
Versions: ['0.6.1', '0.6.0']
Rank: 1
Source: Registry (verified signature)
```

---

### Example 2: Filter by Source

**Goal**: Get only Registry mappings for a node (ignore Manager placeholders)

```python
node_key = "LoadImage::_"
all_mappings = data['mappings'].get(node_key, [])

registry_only = [
    m for m in all_mappings
    if 'source' not in m
]

print(f"Found {len(registry_only)} Registry packages")
```

---

### Example 3: Check Package Source

**Goal**: Determine if package is from Registry or Manager-only

```python
package_id = "manager_gist_7361b8eb966f29c8238fd323409efb68"
package_info = data['packages'][package_id]

if package_info.get('source') == 'manager':
    print("Manager-only package (not in Registry)")
else:
    print("Registry package")
```

---

### Example 4: Get Package Popularity

**Goal**: Rank packages by popularity

```python
packages = data['packages']

ranked = sorted(
    packages.items(),
    key=lambda x: x[1]['downloads'] + (x[1]['github_stars'] * 20),
    reverse=True
)

for package_id, info in ranked[:10]:
    print(f"{package_id}: {info['downloads']} downloads, {info['github_stars']} stars")
```

---

## Schema Validation

### Required Fields

#### Root Level
- ✅ `version` (string)
- ✅ `generated_at` (string, ISO 8601)
- ✅ `stats` (object)
- ✅ `mappings` (object)
- ✅ `packages` (object)

#### PackageMapping
- ✅ `package_id` (string)
- ✅ `versions` (array of strings)
- ✅ `rank` (number, integer >= 1)
- ⚠️ `source` (optional, string, value: "manager")

#### PackageInfo
- ✅ `display_name` (string)
- ✅ `author` (string)
- ✅ `description` (string)
- ✅ `repository` (string)
- ✅ `downloads` (number, integer >= 0)
- ✅ `github_stars` (number, integer >= 0)
- ✅ `rating` (number, float >= 0)
- ✅ `license` (string)
- ✅ `category` (string)
- ✅ `icon` (string)
- ✅ `tags` (array of strings)
- ✅ `status` (string)
- ✅ `created_at` (string, ISO 8601)
- ✅ `versions` (object)
- ⚠️ `source` (optional, string, enum: "manager")

### Constraints

1. **Unique package IDs**: All keys in `packages` must be unique
2. **Valid package references**: All `package_id` in mappings must exist in `packages`
3. **Rank consistency**: Within each mapping array, ranks must be 1, 2, 3, ... (no gaps)
4. **Rank ordering**: Ranks must correspond to descending popularity (rank 1 = most popular)
5. **Version references**: Versions in mappings must exist in package's version list (if non-empty)
6. **Source consistency**: Manager packages should have `source: "manager"` field
7. **Repository normalization**: All `repository` URLs should be normalized

---

## Version History

### Version 2.0 (2025-10-10)

**Breaking Changes**:
- Changed mappings from single object to array of objects (multi-package support)
- Added `rank` field to mappings
- Made `source` field required on all mappings
- Removed `synthetic` field (replaced by `source: "manager"`)

**New Features**:
- Multi-package support per node signature
- Popularity-based ranking
- Source provenance tracking at package and mapping levels
- Manager package ID prefix (`manager_`)
- URL normalization for cross-source matching

**Improvements**:
- Platform-agnostic repository handling
- Better handling of gist URLs
- Support for raw file URLs
- Comprehensive documentation

### Version 1.0 (Legacy)

- Single package per node signature
- `synthetic` flag for Manager packages
- `github_` prefix for synthetic packages
- Limited to GitHub repositories
- No ranking system

---

## Migration Guide

### From Version 1.0 to 2.0

#### Breaking Changes

**1. Mappings Structure**

Old (v1.0):
```json
{
  "NodeName::hash": {
    "package_id": "single-package",
    "versions": ["1.0.0"],
    "source": "manager"
  }
}
```

New (v2.0):
```json
{
  "NodeName::hash": [
    {
      "package_id": "first-package",
      "versions": ["1.0.0"],
      "rank": 1
    },
    {
      "package_id": "second-package",
      "versions": ["0.9.0"],
      "rank": 2,
      "source": "manager"
    }
  ]
}
```

**Migration**:
```python
# Convert single object to array
for node_key, mapping in old_mappings.items():
    new_mappings[node_key] = [mapping]
    new_mappings[node_key][0]['rank'] = 1
    # Note: score calculated internally but not stored
```

**2. Package IDs**

Old (v1.0):
- Registry: Various formats
- Manager: `github_user_repo`

New (v2.0):
- Registry: Unchanged
- Manager: `manager_user_repo`

**Migration**:
```python
# Rename Manager packages
if package_id.startswith('github_'):
    new_id = package_id.replace('github_', 'manager_', 1)
```

**3. Synthetic Flag**

Old (v1.0):
```json
{
  "package_id": "github_user_repo",
  "synthetic": true,
  "source": "manager"
}
```

New (v2.0):
```json
{
  "package_id": "manager_user_repo",
  "source": "manager"
}
```

**Migration**:
```python
# Remove synthetic field, rely on source
if package_info.get('synthetic'):
    package_info['source'] = 'manager'
    del package_info['synthetic']
```

---

## Best Practices

### For Consumers

1. **Always check `source` field** to assess data quality
2. **Prefer Registry mappings** when multiple sources available
3. **Use rank 1 package** for automatic resolution
4. **Handle empty versions** gracefully (Manager data)
5. **Validate package existence** before use
6. **Cache mappings** (updated daily, not real-time)

### For Producers

1. **Always normalize repository URLs** before lookups
2. **Preserve original URLs** in package metadata
3. **Add source field** to all mappings and Manager packages
4. **Calculate scores consistently** using defined formula
5. **Re-rank after any changes** to ensure consistency
6. **Validate output** against schema
7. **Sort versions descending** in package metadata

---

## Related Documentation

- [URL Analysis](./url_analysis.md) - Detailed analysis of repository URL patterns
- `build_global_mappings.py` - Registry mappings builder
- `augment_mappings.py` - Manager data augmentation
- ComfyUI Registry API: https://registry.comfy.org/api/docs

---

## Contact & Feedback

For schema questions, issues, or suggestions:
- File an issue in the project repository
- Contact the maintainers

**Schema Maintainer**: ComfyDock Registry Data Team
**Last Review**: 2025-10-10
