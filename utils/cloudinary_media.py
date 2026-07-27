"""Cloudinary helpers: HLS playback URLs, thumbnails (poster), and absolute URLs.

Streaming delivery is **only** HLS (``.m3u8``). The URL uses **two chained** transformation
segments (see ``HLS_TRANSFORMATION``): ``streaming_profile`` (``sp_hd``) alone, then
``vc_h264`` + ``ac_aac`` + 1280x720 ``c_limit`` + ``q_auto``. Cloudinary rejects ``sp_hd`` in the
same comma-separated group as ``vc_h264`` / ``ac_aac`` (HTTP 400).

Reels-style portrait thumbnails:
    - gravity=face  (built-in, no add-on required)
    - 720x1280 fill (9:16 portrait, never landscape)
    - start_offset=auto (Cloudinary picks the most interesting frame automatically)
"""
import logging
from urllib.parse import urlparse

from django.conf import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# HLS transformation
# Two separate segments — Cloudinary rejects sp_hd in same group as vc_/ac_.
# sp_hd auto-generates 360p / 480p / 720p adaptive bitrate ladder.
# h264 baseline profile — fixes old Android decoder failures.
# ─────────────────────────────────────────────────────────────────────────────
# sp_hd generates 360p / 480p / 720p adaptive bitrate ladder.
# Available on Cloudinary Plus plan ($99) — the current plan.
# Upgrade to Advanced ($299) and change to "full_hd" to unlock 1080p tier.
HLS_TRANSFORMATION = [
    {
        "streaming_profile": "hd",
    },
    {
        "video_codec": "h264",
        "audio_codec": "aac",
        "width": 1280,
        "height": 720,
        "crop": "limit",
        "quality": "auto:best",   # best quality within the 720p cap
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Thumbnail transformation
#
# gravity=face        → built-in face detection, no Cloudinary add-on needed
# start_offset=auto   → Cloudinary picks the most visual/interesting frame
#                        (avoids black frames at second 0 or 2)
# crop=fill           → always fills 720x1280 exactly, never letterboxed
# width=720,height=1280 → 9:16 portrait (Reels / TikTok style), never landscape
# quality=auto:good   → good quality without huge file size
# fetch_format=jpg    → always JPEG output
# ─────────────────────────────────────────────────────────────────────────────
REELS_THUMBNAIL_TRANSFORMATION = [
    {
        "start_offset": "auto",
        "crop": "fill",
        "gravity": "face",        # built-in face detection, no add-on needed
        "width": 720,
        "height": 1280,           # 9:16 portrait — matches HLS 720p cap on Plus
        "quality": "auto:best",   # best quality (was auto:good — Plus supports best)
        "fetch_format": "jpg",
    }
]


# ─────────────────────────────────────────────────────────────────────────────
# Video file extensions — stripped from public_id before building URLs.
# Cloudinary public_id must not include extension or format=m3u8
# yields invalid ....mp4.m3u8 URLs.
# ─────────────────────────────────────────────────────────────────────────────
_VIDEO_FILE_EXTENSIONS = (
    ".mp4",
    ".m4v",
    ".mov",
    ".webm",
    ".mkv",
    ".avi",
    ".mpg",
    ".mpeg",
    ".wmv",
    ".flv",
    ".3gp",
)


def _strip_video_extension_from_public_id(public_id: str) -> str:
    if not public_id:
        return ""
    lower = public_id.lower()
    for ext in _VIDEO_FILE_EXTENSIONS:
        if lower.endswith(ext):
            return public_id[: -len(ext)]
    return public_id


def _video_public_id(file_field) -> str:
    """
    Extract clean Cloudinary public_id from a FileField.
    Handles both raw names (videos/abc.mp4) and full Cloudinary URLs.
    """
    if not file_field or not getattr(file_field, "name", None):
        return ""
    name = str(file_field.name).strip().lstrip("/")

    # Full Cloudinary URL stored in name field
    if name.startswith("http://") or name.startswith("https://"):
        try:
            path = urlparse(name).path.strip("/")
            parts = path.split("/")
            if "upload" in parts:
                idx = parts.index("upload")
                tail = parts[idx + 1 :]
                # Strip version segment (v1234567890)
                if tail and tail[0].startswith("v") and tail[0][1:].isdigit():
                    tail = tail[1:]
                base = "/".join(tail)
                # Strip extension
                if "." in base:
                    base = base.rsplit(".", 1)[0]
                return base
        except Exception:
            return ""

    return _strip_video_extension_from_public_id(name)


def file_field_absolute_url(file_field, request=None) -> str | None:
    """Return absolute URL for an ImageField/FileField (Cloudinary or local)."""
    if not file_field:
        return None
    try:
        path = file_field.url
    except ValueError:
        return None
    if request:
        return request.build_absolute_uri(path)
    return path


def _absolute_from_maybe_relative(url: str | None, request=None) -> str | None:
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if request:
        return request.build_absolute_uri(url)
    return url


# ─────────────────────────────────────────────────────────────────────────────
# Thumbnail
# ─────────────────────────────────────────────────────────────────────────────

def build_cloudinary_video_thumbnail_source_url(public_id: str) -> str | None:
    """
    Generate a Reels-style portrait JPEG thumbnail URL from a Cloudinary video.

    Uses:
      - gravity=face    (built-in, no add-on required)
      - start_offset=auto  (best frame, avoids black screen)
      - 720x1280 fill   (9:16 portrait, never landscape)

    Used by Celery to download and persist the thumbnail to Video.thumbnail.
    """
    if not public_id or not getattr(settings, "USE_CLOUDINARY", False):
        return None
    public_id = _strip_video_extension_from_public_id(public_id.strip().lstrip("/"))
    if not public_id:
        return None
    try:
        import cloudinary.utils

        url, _opts = cloudinary.utils.cloudinary_url(
            public_id,
            resource_type="video",
            transformation=REELS_THUMBNAIL_TRANSFORMATION,
            format="jpg",
            secure=True,
        )
        return url or None
    except Exception as exc:
        logger.warning("build_cloudinary_video_thumbnail_source_url failed: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# HLS
# ─────────────────────────────────────────────────────────────────────────────

def build_video_hls_url(file_field, request=None) -> str | None:
    """
    Adaptive HLS master (.m3u8) for Cloudinary-hosted video.

    Uses HLS_TRANSFORMATION:
      - sp_hd  → auto-generates 360p / 480p / 720p bitrate ladder
      - h264 + aac → maximum device compatibility
    """
    if not file_field:
        return None
    if not getattr(settings, "USE_CLOUDINARY", False):
        return None
    public_id = _video_public_id(file_field)
    if not public_id:
        return None
    try:
        import cloudinary.utils

        url, _opts = cloudinary.utils.cloudinary_url(
            public_id,
            resource_type="video",
            format="m3u8",
            transformation=HLS_TRANSFORMATION,
            secure=True,
        )
        return _absolute_from_maybe_relative(url or None, request)
    except Exception as exc:
        logger.warning("build_video_hls_url failed: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Playback URL (main API field)
# ─────────────────────────────────────────────────────────────────────────────

def build_video_playback_url(file_field, request=None) -> str | None:
    """
    Canonical playback URL:
      - Cloudinary → HLS .m3u8  (adaptive, all devices)
      - Local dev  → raw file URL (fallback)

    Never returns None if a file exists.
    """
    if not file_field:
        return None

    # Try HLS first
    hls = build_video_hls_url(file_field, request=request)
    if hls:
        return hls

    # Fallback: raw file URL (local dev / non-Cloudinary)
    url = file_field_absolute_url(file_field, request)
    if url:
        return url

    # Last resort
    try:
        return file_field.url
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Poster / thumbnail URL
# ─────────────────────────────────────────────────────────────────────────────

def build_video_poster_url(thumbnail_field, video_field, request=None) -> str | None:
    """
    Poster image for the player:
      1. Persisted thumbnail (already saved to Video.thumbnail) — fastest
      2. On-the-fly Cloudinary JPEG frame — fallback if thumbnail not yet saved
         (gravity=face, 720x1280, start_offset=auto — portrait, never landscape)

    This ensures clients never see a black screen while the first HLS
    segment loads.
    """
    # 1. Use persisted thumbnail if available
    stored = file_field_absolute_url(thumbnail_field, request)
    if stored:
        return stored

    # 2. On-the-fly from Cloudinary
    if not getattr(settings, "USE_CLOUDINARY", False) or not video_field:
        return None
    public_id = _video_public_id(video_field)
    if not public_id:
        return None
    src = build_cloudinary_video_thumbnail_source_url(public_id)
    return _absolute_from_maybe_relative(src, request)