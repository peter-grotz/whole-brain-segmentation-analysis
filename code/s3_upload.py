#!/usr/bin/env python3
"""Recursively upload a local directory to an S3 prefix using boto3.

The capsule image ships boto3/s3fs (used to read the zarr) but NOT the `aws` CLI, so
`aws s3 sync` fails with "command not found". This is a drop-in replacement.

Credentials come from the standard environment (the Code Ocean AWS assumable role).
Uploads in parallel; a preflight upload of the first file surfaces auth/permission
errors immediately (so a perms problem fails fast instead of hammering every file).

Usage:
    python s3_upload.py <local_dir> <s3://bucket/prefix> [--exclude name1,name2] [--workers N]

Exit status is non-zero if any file failed (so callers can warn and continue).
"""
from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("local_dir")
    ap.add_argument("dest", help="s3://bucket/prefix")
    ap.add_argument("--exclude", default="",
                    help="comma-separated top-level subdir names under local_dir to skip")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()

    local_dir = args.local_dir.rstrip("/")
    if not args.dest.startswith("s3://"):
        sys.exit(f"destination must be s3://...: {args.dest}")
    bucket, _, prefix = args.dest[len("s3://"):].partition("/")
    prefix = prefix.rstrip("/")
    excluded = {e for e in args.exclude.split(",") if e}

    files = []
    for root, _, fns in os.walk(local_dir):
        for fn in fns:
            lpath = os.path.join(root, fn)
            rel = os.path.relpath(lpath, local_dir)
            top = rel.split(os.sep, 1)[0]
            if top in excluded:
                continue
            key = f"{prefix}/{rel}" if prefix else rel
            files.append((lpath, key))

    if not files:
        print(f"s3_upload: nothing to upload from {local_dir}")
        return

    s3 = boto3.client("s3")

    def put(item):
        lpath, key = item
        s3.upload_file(lpath, bucket, key)

    # Preflight: one synchronous upload to surface credential/permission errors fast.
    try:
        put(files[0])
    except (ClientError, NoCredentialsError, BotoCoreError) as exc:
        sys.exit(f"s3_upload: cannot write to s3://{bucket}/{prefix}/ -> {exc}")

    errors = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(put, it): it for it in files[1:]}
        for fut in as_completed(futs):
            try:
                fut.result()
            except Exception as exc:  # noqa: BLE001 - report and keep going
                errors += 1
                if errors <= 5:
                    print(f"  failed {futs[fut][1]}: {exc}", file=sys.stderr)

    print(f"s3_upload: {len(files) - errors}/{len(files)} files -> s3://{bucket}/{prefix}/")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
