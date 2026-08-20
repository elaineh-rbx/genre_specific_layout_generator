"""Find a scene's images, whether they are on this disk or in the bucket.

The renders are 700 MB - too much to carry in git, and regenerating them costs about
900 model calls - so they live in S3 and the repo holds only the code, the scores and
the runs. A clone is a few megabytes and still shows every page.

The bucket blocks public access, which decides the design: a browser cannot fetch the
objects itself, so the pages keep asking this server for `/results/...` and the server
fetches what it does not have. Nothing in the built HTML changes, and no URL in a page
is a credential with an expiry date, which is what presigned links would have made it.

A fetched object is kept under `run/cache/`, so a page costs one round trip per image
per process rather than one per view.

Configuration, all optional:

    LAYOUTGEN_S3          s3://bucket/prefix holding `scenes/` and `thumbs/`
    LAYOUTGEN_S3_PROFILE  the credentials profile to read it with
    LAYOUTGEN_S3_CACHE    local cache directory (use /tmp for an ephemeral cache)
    LAYOUTGEN_S3_OFF      set to anything to refuse the network and serve local only
"""

from __future__ import annotations

import functools
import os
import pathlib
import threading

from layoutgen import paths

#: Where the golden set's images live when they are not on this machine. Overridable,
#: because the bucket is one team's and the code is not.
BUCKET_URI = os.getenv("LAYOUTGEN_S3", "s3://3dfm-data/users/elaineh/layoutgen/results")
COMPARISON_BUCKET_URI = os.getenv(
    "LAYOUTGEN_COMPARISON_S3",
    "s3://3dfm-data/users/elaineh/layoutgen_genre_images_260806",
)
PROFILE = os.getenv("LAYOUTGEN_S3_PROFILE", "3dfm")
CACHE = pathlib.Path(
    os.getenv("LAYOUTGEN_S3_CACHE", str(paths.RUN / "cache"))
).expanduser()

_lock = threading.Lock()


def enabled() -> bool:
    return not os.getenv("LAYOUTGEN_S3_OFF") and bool(BUCKET_URI)


def _split(uri: str) -> tuple[str, str]:
    rest = uri.removeprefix("s3://").strip("/")
    bucket, _, prefix = rest.partition("/")
    return bucket, prefix


@functools.lru_cache(maxsize=1)
def _client():
    """One boto3 client, made on first miss.

    Built with an explicit session profile because this box also carries a web
    identity role in its environment, and that role wins the default credential chain
    while having no access to the bucket - which fails as a confusing permission error
    rather than as a missing-credentials one.
    """
    import boto3

    try:
        session = boto3.Session(profile_name=PROFILE)
    except Exception:
        session = boto3.Session()
    return session.client("s3")


def fetch(rel: str) -> pathlib.Path | None:
    """The local path for a results-relative file, downloading it if need be.

    `rel` is a path under `results/`, exactly as a page asks for it - for instance
    `scenes/rules/iso/0053.png`. Returns None when the object is not there, so a
    caller can answer 404 rather than raise.
    """
    local = paths.RESULTS / rel
    if local.is_file():
        return local
    if not enabled():
        return None

    cached = CACHE / rel
    if cached.is_file():
        return cached

    uri = BUCKET_URI
    remote_rel = rel
    if rel.startswith("comparison/"):
        uri = COMPARISON_BUCKET_URI
        remote_rel = rel.removeprefix("comparison/")
    bucket, prefix = _split(uri)
    key = f"{prefix}/{remote_rel}" if prefix else remote_rel
    tmp = cached.with_suffix(cached.suffix + f".part{os.getpid()}")
    try:
        with _lock:
            cached.parent.mkdir(parents=True, exist_ok=True)
        _client().download_file(bucket, key, str(tmp))
        tmp.replace(cached)
    except Exception:
        tmp.unlink(missing_ok=True)
        return None
    return cached


def status() -> dict:
    """What a running server can say about where its images are coming from."""
    have = sum(1 for _ in (paths.SCENES).rglob("*.png")) if paths.SCENES.is_dir() else 0
    return {"local_scenes": have, "bucket": BUCKET_URI if enabled() else "",
            "cached": sum(1 for _ in CACHE.rglob("*")) if CACHE.is_dir() else 0}
