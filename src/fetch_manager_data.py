#!/usr/bin/env python3
"""
Fetch ComfyUI Manager extension-node-map data.
Standalone utility to download and cache Manager's extension data.
"""

import argparse
import asyncio
import aiohttp
import json
from datetime import datetime
from pathlib import Path

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ManagerDataFetcher:
    """Fetches and caches ComfyUI Manager extension data."""

    MANAGER_URL = "https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/extension-node-map.json"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def fetch(self, output_file: Path, force: bool = False) -> bool:
        """
        Fetch Manager extension data and save to file.

        Args:
            output_file: Path to save the data
            force: Force fetch even if file exists and is recent

        Returns:
            True if fetched successfully, False otherwise
        """
        # Check if we need to fetch
        if not force and output_file.exists():
            try:
                with open(output_file) as f:
                    existing_data = json.load(f)
                fetched_at = existing_data.get("fetched_at", "")
                if fetched_at:
                    # Check if less than 6 hours old
                    fetch_time = datetime.fromisoformat(fetched_at)
                    hours_old = (datetime.now() - fetch_time).total_seconds() / 3600
                    if hours_old < 6:
                        logger.info(f"Manager data is recent ({hours_old:.1f}h old), skipping fetch")
                        return True
            except Exception as e:
                logger.warning(f"Could not check existing file age: {e}")

        logger.info(f"Fetching Manager extension data from {self.MANAGER_URL}")

        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.MANAGER_URL) as response:
                    if response.status == 200:
                        # GitHub raw URLs return text/plain, so get text and parse manually
                        text_content = await response.text()
                        data = json.loads(text_content)

                        # Validate data structure
                        if not isinstance(data, dict):
                            logger.error("Invalid data format: expected dict")
                            return False

                        # Wrap with metadata
                        wrapped_data = {
                            "fetched_at": datetime.now().isoformat(),
                            "source": self.MANAGER_URL,
                            "extension_count": len(data),
                            "extensions": data
                        }

                        # Ensure output directory exists
                        output_file.parent.mkdir(parents=True, exist_ok=True)

                        # Atomic write
                        temp_file = output_file.with_suffix('.tmp')
                        try:
                            with open(temp_file, 'w') as f:
                                json.dump(wrapped_data, f, indent=2)
                            temp_file.replace(output_file)

                            file_size = output_file.stat().st_size / 1024
                            logger.info(f"✅ Fetched {len(data)} Manager extensions ({file_size:.1f} KB)")
                            return True

                        finally:
                            if temp_file.exists():
                                temp_file.unlink()

                    else:
                        logger.error(f"Failed to fetch Manager data: HTTP {response.status}")
                        return False

        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching Manager data ({self.timeout}s)")
            return False
        except Exception as e:
            logger.error(f"Failed to fetch Manager data: {e}")
            return False

    def validate_data(self, data_file: Path) -> bool:
        """Validate Manager data file structure."""
        try:
            with open(data_file) as f:
                data = json.load(f)

            # Check required fields
            required = ["fetched_at", "source", "extension_count", "extensions"]
            for field in required:
                if field not in data:
                    logger.error(f"Missing required field: {field}")
                    return False

            # Validate extensions data
            extensions = data["extensions"]
            if not isinstance(extensions, dict):
                logger.error("Extensions field must be a dict")
                return False

            # Count and validate structure
            valid_extensions = 0
            for url, ext_data in extensions.items():
                if isinstance(ext_data, list) and len(ext_data) > 0:
                    if isinstance(ext_data[0], list):  # Node list
                        valid_extensions += 1

            logger.info(f"Validation passed: {valid_extensions} valid extensions")
            return True

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False


async def main():
    parser = argparse.ArgumentParser(description="Fetch ComfyUI Manager extension data")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("data/extension-node-map.json"),
        help="Output file path (default: data/extension-node-map.json)"
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force fetch even if file is recent"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate existing file instead of fetching"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )

    args = parser.parse_args()

    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    fetcher = ManagerDataFetcher(timeout=args.timeout)

    if args.validate:
        # Validate existing file
        if not args.output.exists():
            logger.error(f"File not found: {args.output}")
            return 1

        if fetcher.validate_data(args.output):
            logger.info("✅ Validation passed")
            return 0
        else:
            logger.error("❌ Validation failed")
            return 1
    else:
        # Fetch data
        success = await fetcher.fetch(args.output, force=args.force)
        if success:
            # Validate what we just fetched
            if fetcher.validate_data(args.output):
                logger.info("✅ Fetch and validation completed successfully")
                return 0
            else:
                logger.error("❌ Fetch succeeded but validation failed")
                return 1
        else:
            logger.error("❌ Fetch failed")
            return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))