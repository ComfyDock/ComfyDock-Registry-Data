# Node Mappings Schema (Condensed)

**Version**: 2.0 | **Date**: 2025-10-10

Quick reference for implementing node mappings data structure.

---

## Core Schema

```typescript
interface NodeMappingsData {
  version: string;              // "YYYY.MM.DD"
  generated_at: string;         // ISO 8601
  stats: {
    packages: number;
    signatures: number;
    total_nodes: number;
    augmented?: boolean;
    augmentation_date?: string;
    nodes_from_manager?: number;
    manager_packages?: number;
  };
  mappings: {
    [nodeKey: string]: PackageMapping[];  // "NodeName::signature_hash"
  };
  packages: {
    [packageId: string]: PackageInfo;
  };
}

interface PackageMapping {
  package_id: string;
  versions: string[];           // Empty [] for Manager data
  rank: number;                 // 1-based, sorted by popularity
  source?: "manager";           // Omit for Registry (default)
}

interface PackageInfo {
  display_name: string;
  author: string;
  description: string;
  repository: string;           // MUST be normalized
  downloads: number;
  github_stars: number;
  rating: number;
  license: string;
  category: string;
  icon: string;
  tags: string[];
  status: string;
  created_at: string;
  source?: "manager";           // Omit for Registry (default)
  versions: {
    [version: string]: VersionInfo;
  };
}

interface VersionInfo {
  version: string;
  changelog: string;
  release_date: string;
  dependencies: string[];
  deprecated: boolean;
  download_url: string;
  status: string;
  supported_accelerators: string[] | null;
  supported_comfyui_version: string;
  supported_os: string[] | null;
}
```

---

## Key Rules

### Node Keys
- Format: `"NodeName::signature_hash"`
- Registry: `"NodeName::a1b2c3d4"` (8-char hash of input signature)
- Manager: `"NodeName::_"` (placeholder, no signature data)

### Source Field
- **Optional field** - omit for Registry (default), add `"manager"` for Manager data
- Package level: `source?: "manager"`
- Mapping level: `source?: "manager"`
- Check Registry: `if 'source' not in item`
- Check Manager: `if item.get('source') == 'manager'`

### Package IDs

**Registry**: Use registry's own IDs (no prefix)
- Examples: `"comfyui-reactor"`, `"7361b8eb966f29c8238fd323409efb68"`

**Manager**: Prefix with `manager_`
- GitHub: `manager_user_repo`
- Gist: `manager_gist_hash`
- Other: `manager_domain_user_repo`

### Ranking
- **Score**: Calculated internally, NOT stored in output
- **Rank**: 1-based integer (1 = most popular)
- Formula: `score = (downloads / 10.0) + (github_stars * 2.0) * recency_multiplier`
- Sort by score DESC, assign ranks 1, 2, 3...

---

## URL Normalization

**Critical**: Always normalize URLs before matching/storing.

```python
def normalize_repository_url(url: str) -> str:
    """Convert all URL variants to canonical form."""
    url = url.strip().lower()

    # Remove .git suffix
    if url.endswith('.git'):
        url = url[:-4]

    # Remove trailing slash
    url = url.rstrip('/')

    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')

    # GitHub raw file → repo
    if parsed.netloc == 'raw.githubusercontent.com':
        # raw.githubusercontent.com/USER/REPO/BRANCH/... → github.com/USER/REPO
        if len(path_parts) >= 2:
            return f'https://github.com/{path_parts[0]}/{path_parts[1]}'

    # Gist raw → canonical
    if parsed.netloc == 'gist.githubusercontent.com':
        # gist.githubusercontent.com/USER/HASH/... → gist.github.com/USER/HASH
        if len(path_parts) >= 2:
            return f'https://gist.github.com/{path_parts[0]}/{path_parts[1]}'

    # Standard normalization
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
```

**Supported platforms**: github.com, raw.githubusercontent.com, gist.github.com, gist.githubusercontent.com, gitee.com, git.* (custom)

---

## Build Process

### Step 1: Registry Mappings (`build_global_mappings.py`)

```python
# 1. Load registry cache
# 2. For each package version with comfy_nodes:
for node in comfy_nodes:
    node_key = create_node_key(node.name, normalize_inputs(node.input_types))

    if node_key not in mappings:
        mappings[node_key] = []

    # Find or create entry for this package
    entry = find_entry(mappings[node_key], package_id)
    if not entry:
        entry = {
            "package_id": package_id,
            "versions": [],
            "rank": 0  # Set later
            # NO source field (Registry is default)
        }
        mappings[node_key].append(entry)

    if version not in entry["versions"]:
        entry["versions"].append(version)

# 3. Rank all mappings
for node_key, entries in mappings.items():
    # Calculate scores (not stored)
    for entry in entries:
        pkg = packages[entry["package_id"]]
        score = calculate_score(pkg["downloads"], pkg["github_stars"])
        entry["_temp_score"] = score

    # Sort by score DESC, assign ranks
    entries.sort(key=lambda x: x["_temp_score"], reverse=True)
    for rank, entry in enumerate(entries, 1):
        entry["rank"] = rank
        del entry["_temp_score"]  # Remove temporary score
```

### Step 2: Manager Augmentation (`augment_mappings.py`)

```python
# 1. Build URL map
url_to_package = {}
for pkg_id, pkg_info in packages.items():
    normalized = normalize_repository_url(pkg_info["repository"])
    url_to_package[normalized] = pkg_id

# 2. Process Manager extensions
unmatched = []
for manager_url, extension_data in manager_extensions.items():
    normalized_url = normalize_repository_url(manager_url)

    # Try to match with Registry
    package_id = url_to_package.get(normalized_url)

    if package_id:
        # Augment existing Registry package
        for node_name in extension_data[0]:  # node list
            node_key = create_node_key(node_name, "_")

            # Skip if package already mapped to this node
            if any(e["package_id"] == package_id for e in mappings.get(node_key, [])):
                continue

            mappings[node_key].append({
                "package_id": package_id,
                "versions": [],  # Manager has no version info
                "rank": 0,  # Set later
                "source": "manager"  # Mark as Manager data
            })
    else:
        unmatched.append((manager_url, extension_data))

# 3. Create Manager packages
for manager_url, extension_data in unmatched:
    normalized_url = normalize_repository_url(manager_url)
    package_id = generate_manager_package_id(normalized_url)

    # Create package
    metadata = extension_data[1] if len(extension_data) > 1 else {}
    packages[package_id] = {
        "display_name": metadata.get("title_aux", extract_name(normalized_url)),
        "author": extract_author(normalized_url),
        "description": metadata.get("description", ""),
        "repository": normalized_url,
        "downloads": 0,
        "github_stars": 0,
        "rating": 0,
        "license": "{}",
        "category": "",
        "icon": "",
        "tags": [],
        "status": "NodeStatusActive",
        "created_at": datetime.now().isoformat(),
        "source": "manager",  # Mark as Manager package
        "versions": {}
    }

    # Add mappings
    for node_name in extension_data[0]:
        node_key = create_node_key(node_name, "_")
        mappings[node_key].append({
            "package_id": package_id,
            "versions": [],
            "rank": 0,
            "source": "manager"
        })

# 4. Re-rank ALL mappings (Registry + Manager)
for node_key, entries in mappings.items():
    # Calculate scores
    for entry in entries:
        pkg = packages[entry["package_id"]]
        score = calculate_score(pkg["downloads"], pkg["github_stars"])
        entry["_temp_score"] = score

    # Sort and rank
    entries.sort(key=lambda x: x["_temp_score"], reverse=True)
    for rank, entry in enumerate(entries, 1):
        entry["rank"] = rank
        del entry["_temp_score"]
```

---

## Manager Package ID Generation

```python
def generate_manager_package_id(normalized_url: str) -> str:
    """Generate package ID for Manager-only packages."""
    parsed = urlparse(normalized_url)
    path_parts = parsed.path.strip('/').split('/')

    # Gist: manager_gist_HASH
    if 'gist.github.com' in parsed.netloc:
        if len(path_parts) >= 2:
            return f"manager_gist_{path_parts[1]}"

    # GitHub: manager_USER_REPO
    if 'github.com' in parsed.netloc:
        if len(path_parts) >= 2:
            user = path_parts[0].lower().replace('-', '_')
            repo = path_parts[1].lower().replace('-', '_')
            return f"manager_{user}_{repo}"

    # Other: manager_DOMAIN_USER_REPO
    domain = parsed.netloc.replace('.', '_').replace('-', '_')
    if len(path_parts) >= 2:
        user = path_parts[0].lower().replace('-', '_')
        repo = path_parts[1].lower().replace('-', '_')
        return f"manager_{domain}_{user}_{repo}"

    # Fallback
    return f"manager_{domain}"
```

---

## Examples

### Registry Mapping (No Source)
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

### Manager Mapping (With Source)
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

### Manager Package
```json
{
  "manager_gist_7361b8eb966f29c8238fd323409efb68": {
    "display_name": "alkemann nodes",
    "author": "alkemann",
    "description": "Nodes:Int to Text, Seed With Text, Save A1 Image.",
    "repository": "https://gist.github.com/alkemann/7361b8eb966f29c8238fd323409efb68",
    "downloads": 0,
    "github_stars": 0,
    "rating": 0,
    "license": "{}",
    "category": "",
    "icon": "",
    "tags": [],
    "status": "NodeStatusActive",
    "created_at": "2025-03-12T00:15:42.633008Z",
    "source": "manager",
    "versions": {}
  }
}
```

---

## Validation Checklist

1. ✅ All `repository` URLs are normalized
2. ✅ Manager packages have `source: "manager"` field
3. ✅ Manager mappings have `source: "manager"` field
4. ✅ Registry packages/mappings omit `source` field
5. ✅ Ranks are consecutive: 1, 2, 3... (no gaps)
6. ✅ Ranks match popularity order (rank 1 = highest)
7. ✅ All `package_id` refs exist in `packages`
8. ✅ No `score` field in output (internal only)
9. ✅ Manager packages have empty `versions: {}`
10. ✅ Manager mappings have empty `versions: []`

---

## Common Patterns

### Check if Registry data
```python
is_registry = "source" not in item
```

### Check if Manager data
```python
is_manager = item.get("source") == "manager"
```

### Filter Registry mappings only
```python
registry_mappings = [m for m in mappings if "source" not in m]
```

### Get top package for node
```python
top_package = mappings[node_key][0]  # rank 1
```

---

**Full documentation**: See `node_mappings_schema.md`
