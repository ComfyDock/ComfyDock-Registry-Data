#!/usr/bin/env python3
"""URL normalization utilities for repository matching.

Implements the normalization strategy from node_mappings_schema_condensed.md
to ensure consistent URL matching between Registry and Manager data sources.
"""

from urllib.parse import urlparse, urlunparse


def normalize_repository_url(url: str) -> str:
    """Convert all URL variants to canonical form.

    Handles:
    - GitHub repos: github.com/user/repo
    - GitHub raw: raw.githubusercontent.com/user/repo/... → github.com/user/repo
    - Gist raw: gist.githubusercontent.com/user/hash/raw/... → gist.github.com/user/hash
    - Gist canonical: gist.github.com/user/hash
    - .git suffix removal
    - Trailing slash removal
    - Lowercase normalization

    Args:
        url: Repository URL in any supported format

    Returns:
        Canonical normalized URL
    """
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
        # gist.githubusercontent.com/USER/HASH/raw/... → gist.github.com/USER/HASH
        if len(path_parts) >= 2:
            return f'https://gist.github.com/{path_parts[0]}/{path_parts[1]}'

    # Standard normalization
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))


def is_supported_repo_url(url: str) -> bool:
    """Check if URL is a supported repository type.

    Args:
        url: Repository URL to check

    Returns:
        True if URL is from a supported platform
    """
    url_lower = url.lower()
    return any([
        'github.com' in url_lower,
        'githubusercontent.com' in url_lower,
        'gist.github.com' in url_lower,
        'gitee.com' in url_lower,
        'git.mmaker.moe' in url_lower,
    ])


def generate_manager_package_id(normalized_url: str) -> str:
    """Generate package ID for Manager-only packages.

    Strategy:
    - GitHub repos: manager_user_repo
    - Gists: manager_gist_hash
    - Other: manager_domain_user_repo

    Args:
        normalized_url: Already normalized repository URL

    Returns:
        Package ID with manager_ prefix
    """
    parsed = urlparse(normalized_url)
    path_parts = parsed.path.strip('/').split('/')

    # Gist: manager_gist_HASH
    if 'gist.github.com' in parsed.netloc:
        if len(path_parts) >= 2:
            gist_hash = path_parts[1]
            return f"manager_gist_{gist_hash}"

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
