# Repository URL Analysis

## Overview

Analysis of all repository URL patterns found in ComfyUI Manager's `extension-node-map.json` to inform normalization strategy for matching Manager data with Registry packages.

**Data analyzed**: 3,033 extension entries from Manager data

---

## URL Pattern Distribution

| Pattern | Count | Percentage | Description |
|---------|-------|------------|-------------|
| `github.com` | 3,003 | 99.0% | Standard GitHub repository URLs |
| `raw.githubusercontent.com` | 27 | 0.9% | Direct links to single Python files in GitHub repos |
| `gist.githubusercontent.com` | 1 | 0.03% | Direct links to gist raw files |
| `gitee.com` | 1 | 0.03% | Chinese Git hosting platform |
| `git.mmaker.moe` | 1 | 0.03% | Custom Git server |

**Key Finding**: 99% of extensions are GitHub-based, but we must handle edge cases.

---

## Pattern Categories

### 1. Standard GitHub Repositories (99.0%)

**Manager format**:
```
https://github.com/USER/REPO
```

**Registry format**:
```
https://github.com/USER/REPO
```

**Matching**: Direct match after normalization (remove trailing `/`, `.git` suffix)

**Examples**:
- `https://github.com/Gourieff/comfyui-reactor`
- `https://github.com/city96/ComfyUI-GGUF`
- `https://github.com/TRI3D-LC/ComfyUI-MiroBoard`

---

### 2. GitHub Raw File Links (0.9%)

**Manager format**:
```
https://raw.githubusercontent.com/USER/REPO/BRANCH/path/to/file.py
```

**Registry format** (inferred):
```
https://github.com/USER/REPO
```

**Normalization required**: Extract `USER` and `REPO` from path, convert to standard repo URL

**Examples**:

| Manager URL | Inferred Repository |
|-------------|---------------------|
| `https://raw.githubusercontent.com/1shadow1/hayo_comfyui_nodes/main/LZCNodes.py` | `https://github.com/1shadow1/hayo_comfyui_nodes` |
| `https://raw.githubusercontent.com/CaptainGrock/ComfyUIInvisibleWatermark/main/Invisible%20Watermark.py` | `https://github.com/CaptainGrock/ComfyUIInvisibleWatermark` |
| `https://raw.githubusercontent.com/SadaleNet/CLIPTextEncodeA1111-ComfyUI/master/custom_nodes/clip_text_encoder_a1111.py` | `https://github.com/SadaleNet/CLIPTextEncodeA1111-ComfyUI` |

**URL Structure**:
```
https://raw.githubusercontent.com/
  ├─ USER/           (path segment 1)
  ├─ REPO/           (path segment 2)
  ├─ BRANCH/         (path segment 3: main, master, refs/heads/...)
  └─ FILE_PATH       (remaining segments)
```

**Verification**: Checked that `hayo_comfyui_nodes` and `ComfyUIInvisibleWatermark` exist in registry with matching inferred URLs ✅

---

### 3. Gist Raw File Links (0.03%)

**Manager format**:
```
https://gist.githubusercontent.com/USER/GIST_HASH/raw/COMMIT_HASH/file.py
```

**Registry format**:
```
https://gist.github.com/USER/GIST_HASH
```

**Normalization required**: Extract `USER` and `GIST_HASH`, convert to canonical gist URL

**Example**:

| Manager URL | Registry URL |
|-------------|--------------|
| `https://gist.githubusercontent.com/alkemann/7361b8eb966f29c8238fd323409efb68/raw/f9605be0b38d38d3e3a2988f89248ff557010076/alkemann.py` | `https://gist.github.com/alkemann/7361b8eb966f29c8238fd323409efb68` |

**URL Structure**:
```
https://gist.githubusercontent.com/
  ├─ USER/           (path segment 1)
  ├─ GIST_HASH/      (path segment 2)
  ├─ raw/            (literal "raw")
  ├─ COMMIT_HASH/    (path segment 4)
  └─ FILE_NAME       (path segment 5)
```

**Registry Package ID**: Uses `GIST_HASH` directly as package ID
- Package ID: `7361b8eb966f29c8238fd323409efb68`
- Repository: `https://gist.github.com/alkemann/7361b8eb966f29c8238fd323409efb68`

---

### 4. Non-GitHub Platforms (0.06%)

#### Gitee (Chinese GitHub alternative)

**Format**:
```
https://gitee.com/USER/REPO
```

**Example**: `https://gitee.com/yyh915/jkha-load-img`

**Normalization**: Same as GitHub (remove trailing `/`)

#### Custom Git Servers

**Format**:
```
https://git.CUSTOM_DOMAIN/USER/REPO
```

**Example**: `https://git.mmaker.moe/mmaker/sd-webui-color-enhance`

**Normalization**: Generic handling for any Git-compatible host

---

## Normalization Strategy

### Requirements

1. **Handle multiple URL formats for same repository**:
   - `github.com/user/repo` ← Standard
   - `raw.githubusercontent.com/user/repo/branch/file.py` ← Raw file
   - `gist.githubusercontent.com/user/hash/raw/commit/file.py` ← Gist raw
   - `gist.github.com/user/hash` ← Gist canonical

2. **Platform-agnostic**: Don't assume GitHub-only
   - Support `gitee.com`, custom Git servers
   - Use generic host-based approach

3. **Preserve original URLs**: Store normalized form for matching, but keep original in package metadata

4. **Handle edge cases**:
   - `.git` suffix removal
   - Trailing slash normalization
   - Case normalization
   - URL encoding (e.g., `%20` for spaces)

### Proposed Normalization Algorithm

```python
def normalize_repository_url(url: str) -> str:
    """
    Normalize repository URLs for consistent matching.

    Handles:
    - GitHub repos: github.com/user/repo
    - GitHub raw files: raw.githubusercontent.com/user/repo/branch/file.py
    - Gist raw files: gist.githubusercontent.com/user/hash/raw/commit/file.py
    - Gist canonical: gist.github.com/user/hash
    - Gitee: gitee.com/user/repo
    - Custom Git: git.example.com/user/repo

    Returns canonical repository URL (lowercase, no trailing slash, no .git)
    """

    url = url.strip().lower()

    # Remove .git suffix
    if url.endswith('.git'):
        url = url[:-4]

    # Remove trailing slash
    url = url.rstrip('/')

    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')

    # Handle GitHub raw file URLs
    if parsed.netloc == 'raw.githubusercontent.com':
        # Extract: raw.githubusercontent.com/USER/REPO/BRANCH/...
        # Convert to: github.com/USER/REPO
        if len(path_parts) >= 2:
            user, repo = path_parts[0], path_parts[1]
            return f'https://github.com/{user}/{repo}'

    # Handle gist raw URLs
    if parsed.netloc == 'gist.githubusercontent.com':
        # Extract: gist.githubusercontent.com/USER/HASH/raw/...
        # Convert to: gist.github.com/USER/HASH
        if len(path_parts) >= 2:
            user, gist_hash = path_parts[0], path_parts[1]
            return f'https://gist.github.com/{user}/{gist_hash}'

    # Standard normalization for all other URLs
    # (github.com, gist.github.com, gitee.com, custom Git servers)
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        '',  # params
        '',  # query
        ''   # fragment
    ))

    return normalized
```

---

## Synthetic Package ID Strategy

### Current Problem

Old code used `github_author_repo` prefix, which:
- ❌ Assumes all repos are GitHub
- ❌ Doesn't work for Gitee, custom Git servers
- ❌ Creates different IDs for gists vs. registry

### Proposed Solution: Source-Aware IDs

**Principle**: Manager-created packages should be easily identifiable but platform-agnostic.

#### Strategy A: Simple Prefix (Recommended)

Use `manager_` prefix for ALL manager-created packages:

| Repository Type | Package ID Format | Example |
|----------------|-------------------|---------|
| GitHub repo | `manager_user_repo` | `manager_gourieff_comfyui-reactor` |
| GitHub raw file | `manager_user_repo` | `manager_1shadow1_hayo_comfyui_nodes` |
| Gist | `manager_gist_hash` | `manager_gist_7361b8eb966f29c8238fd323409efb68` |
| Gitee | `manager_user_repo` | `manager_yyh915_jkha-load-img` |
| Custom Git | `manager_domain_user_repo` | `manager_git.mmaker.moe_mmaker_sd-webui-color-enhance` |

**Collision Handling**: If registry package exists with same normalized URL, use registry package (don't create synthetic).

#### Strategy B: Match Registry IDs

Try to match registry's ID convention:

| Repository Type | Package ID Format | Example |
|----------------|-------------------|---------|
| GitHub repo | Extract from repo name | `comfyui-reactor` (match registry) |
| Gist | Use gist hash | `7361b8eb966f29c8238fd323409efb68` (match registry) |

**Problem**: High risk of ID collisions if registry later adds the package with different ID extraction logic.

### Recommendation

**Use Strategy A (simple prefix)** because:
1. ✅ Clear provenance (all Manager packages have `manager_` prefix)
2. ✅ No collision risk with registry IDs
3. ✅ Platform-agnostic
4. ✅ Easy to identify and filter
5. ✅ Consistent with having `source: "manager"` field

The `source` field in package metadata is sufficient to track origin; we don't need to duplicate this in the ID scheme.

---

## Registry Matching Logic

### Two-Pass Augmentation

**Pass 1: Augment Existing Registry Packages**

```
For each Manager extension URL:
  1. normalized_url = normalize_repository_url(url)
  2. Look up normalized_url in registry_url_map
  3. If FOUND:
     - Add Manager nodes to existing registry package
     - Mark mappings with source: "manager"
  4. If NOT FOUND:
     - Add to unmatched_extensions list
```

**Pass 2: Create Manager Packages**

```
For each unmatched_extension:
  1. normalized_url = normalize_repository_url(url)
  2. package_id = generate_manager_package_id(normalized_url)
  3. Create package entry:
     - display_name: from Manager metadata or extracted from URL
     - repository: normalized_url
     - source: "manager"
     - versions: {} (empty)
  4. Add Manager nodes
     - Mark mappings with source: "manager"
```

### URL Map Building

```python
def build_registry_url_map(packages: dict) -> dict:
    """Build normalized URL -> package ID map for registry packages."""
    url_map = {}

    for package_id, package_info in packages.items():
        repo_url = package_info.get('repository', '')
        if repo_url:
            normalized = normalize_repository_url(repo_url)
            url_map[normalized] = package_id

    return url_map
```

---

## Edge Cases & Considerations

### 1. URL Encoding

Some Manager URLs contain encoded characters (e.g., `%20` for spaces):
```
https://raw.githubusercontent.com/CaptainGrock/ComfyUIInvisibleWatermark/main/Invisible%20Watermark.py
```

**Solution**: `urlparse()` handles this automatically, decoded in `parsed.path`

### 2. Multiple Files from Same Repo

Manager may have multiple raw file URLs from same repository:
```
https://raw.githubusercontent.com/user/repo/main/file1.py
https://raw.githubusercontent.com/user/repo/main/file2.py
```

Both normalize to: `https://github.com/user/repo`

**Solution**: First file creates the package, subsequent files add to same package.

### 3. Branch Variations

Raw file URLs may reference different branches:
```
https://raw.githubusercontent.com/user/repo/main/file.py
https://raw.githubusercontent.com/user/repo/master/file.py
```

Both normalize to same repo URL.

**Solution**: Correct behavior - we track packages, not branches.

### 4. Registry Updates

What if Manager package later added to registry?

**Scenario**:
1. Build creates `manager_user_repo` package
2. Next week, registry adds same repo as `comfyui-repo`
3. Next build now finds registry package

**Solution**:
- Augment registry package (correct)
- Old synthetic package becomes orphaned (has no mappings)
- Cleanup step: Remove packages with no mappings

---

## Summary

**URL Patterns Found**: 5 distinct types
- GitHub repos (99.0%)
- GitHub raw files (0.9%)
- Gist raw files (0.03%)
- Gitee (0.03%)
- Custom Git (0.03%)

**Normalization Requirements**:
- Convert raw file URLs → repository URLs
- Convert gist raw URLs → canonical gist URLs
- Platform-agnostic handling
- Case normalization, suffix removal

**Package ID Strategy**:
- Use `manager_` prefix for all synthetic packages
- Platform-agnostic extraction from normalized URLs
- No collision risk with registry IDs

**Next Steps**:
1. Implement `normalize_repository_url()` function
2. Update `build_registry_url_map()` to use normalized URLs
3. Update augmentation to use two-pass approach
4. Add cleanup step to remove orphaned packages
