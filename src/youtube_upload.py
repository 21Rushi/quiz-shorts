"""Upload a video to YouTube using a stored OAuth refresh token.

Needs these environment variables (set them as GitHub Actions secrets):
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
"""
import datetime as dt
import os
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(path, title, description, tags, privacy="public", category_id="27", publish_at=None, synthetic=False, language="en",
           localizations=None, audio_language=None):
    """publish_at: timezone-aware datetime. The video is uploaded private and YouTube
    itself makes it public at that exact minute (so GitHub delays don't matter).
    localizations: {"hi": {"title": ..., "description": ...}, "en": {...}} - YouTube shows each
    viewer the title/description in their YouTube language (English for US/Europe, Hindi in India).
    audio_language: language of the spoken voice ("hi"/"en"), if any."""
    yt = get_service()
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": tags,
            "categoryId": category_id,  # 27 = Education
            "defaultLanguage": language,
        },
        "localizations": {k: {"title": v["title"][:100], "description": v.get("description", description)[:4900]}
                          for k, v in (localizations or {}).items() if k != language and v.get("title")},
        "status": {
            "privacyStatus": "private" if publish_at else privacy,
            "selfDeclaredMadeForKids": False,
            # YouTube AI disclosure: True for realistic AI video/voice (e.g. Google Flow / Veo)
            "containsSyntheticMedia": bool(synthetic),
        },
    }
    if audio_language:
        body["snippet"]["defaultAudioLanguage"] = audio_language
    parts = "snippet,status" + (",localizations" if body["localizations"] else "")
    if not body["localizations"]:
        del body["localizations"]
    if publish_at:
        body["status"]["publishAt"] = publish_at.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    media = MediaFileUpload(path, mimetype="video/mp4", resumable=True, chunksize=8 * 1024 * 1024)
    req = yt.videos().insert(part=parts, body=body, media_body=media)
    response, retries = None, 0
    while response is None:
        try:
            status, response = req.next_chunk()
            if status:
                print(f"  uploaded {int(status.progress() * 100)}%")
        except HttpError as e:
            if publish_at and e.resp.status == 400:
                print(f"::warning title=Scheduling rejected, publishing now::{str(e)[:300]}")
                return upload(path, title, description, tags, privacy, category_id, None, synthetic, language,
                              localizations, audio_language)
            if e.resp.status in (500, 502, 503, 504) and retries < 5:
                retries += 1
                time.sleep(2 ** retries)
                continue
            raise
    return response["id"]
