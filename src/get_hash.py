#!/usr/bin/env python3
import argparse
import hashlib
import sys
import time
import zlib
from pathlib import Path

from blake3 import blake3


def format_bytes(size):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"

def main():
    parser = argparse.ArgumentParser(description="Calculate file hash")
    parser.add_argument("file_path", help="Path to the file to hash")
    parser.add_argument("--sha256", action="store_true", help="Use SHA256 instead of BLAKE3")
    parser.add_argument("--crc32", action="store_true", help="Use CRC32 instead of BLAKE3")

    args = parser.parse_args()
    file_path = Path(args.file_path)

    # Check for conflicting options
    if args.sha256 and args.crc32:
        print("Error: Cannot use --sha256 and --crc32 together", file=sys.stderr)
        sys.exit(1)

    if not file_path.exists():
        print(f"Error: File '{file_path}' not found", file=sys.stderr)
        sys.exit(1)

    if not file_path.is_file():
        print(f"Error: '{file_path}' is not a file", file=sys.stderr)
        sys.exit(1)

    try:
        # Get file size
        file_size = file_path.stat().st_size
        print(f"Size: {format_bytes(file_size)}", file=sys.stderr)

        # Choose hasher based on flag
        if args.sha256:
            hasher = hashlib.sha256()
            hash_type = "sha256"
            use_crc32 = False
        elif args.crc32:
            crc = 0
            hash_type = "crc32"
            use_crc32 = True
        else:
            hasher = blake3()
            hash_type = "blake3"
            use_crc32 = False

        # Start timing
        start_time = time.perf_counter()

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                if use_crc32:
                    crc = zlib.crc32(chunk, crc)
                else:
                    hasher.update(chunk)

        # End timing
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        if use_crc32:
            print(f"{hash_type}:{crc:08x}")
        else:
            print(f"{hash_type}:{hasher.hexdigest()}")
        print(f"Time: {elapsed_time:.4f}s", file=sys.stderr)

    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
