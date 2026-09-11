import shutil
from pathlib import Path

from fastapi import HTTPException

from .providers.base import ProviderError
from .providers.process import run_process
from .storage import now, uid


async def save_recording(store, upload):
    mime = (upload.content_type or "").split(";")[0]
    if mime not in (
        "audio/wav",
        "audio/x-wav",
        "audio/webm",
        "video/webm",
        "audio/ogg",
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",
        "video/mp4",
        "audio/flac",
        "audio/x-flac",
        "application/octet-stream",
    ):
        raise HTTPException(415, "Import a WAV, WebM, Ogg, MP3, MP4 or FLAC recording.")
    audio_id = uid()
    path = store.data_dir / "audio" / audio_id
    temporary = path.with_suffix(".part")
    total = 0
    try:
        with temporary.open("wb") as handle:
            while chunk := await upload.read(65536):
                total += len(chunk)
                if total > 50 * 1024 * 1024:
                    raise HTTPException(413, "Recording exceeds the 50 MB upload limit.")
                handle.write(chunk)
        if total == 0:
            raise HTTPException(422, "This recording is empty.")
        temporary.replace(path)
        with store.connect() as db:
            db.execute("INSERT INTO audio VALUES (?,?,?,?)", (audio_id, audio_id, mime, now()))
        return audio_id
    except BaseException:
        temporary.unlink(missing_ok=True)
        path.unlink(missing_ok=True)
        with store.connect() as db:
            db.execute("DELETE FROM audio WHERE id=?", (audio_id,))
        raise


async def save_audio(store, upload, dreamed_on):
    audio_id = await save_recording(store, upload)
    try:
        return store.create_audio_dream(str(dreamed_on), audio_id)
    except BaseException:
        (store.data_dir / "audio" / audio_id).unlink(missing_ok=True)
        with store.connect() as db:
            db.execute("DELETE FROM audio WHERE id=?", (audio_id,))
        raise


def audio_record(store, audio_id):
    with store.connect() as db:
        row = db.execute("SELECT * FROM audio WHERE id=?", (audio_id,)).fetchone()
    if row is None:
        raise KeyError("Recording not found")
    return dict(row)


def transcription_status(store):
    prefs = store.preferences()
    binary = shutil.which(prefs.whisper_binary or "whisper-cli")
    ffmpeg = shutil.which(prefs.ffmpeg_binary)
    model = Path(prefs.whisper_model).expanduser() if prefs.whisper_model else None
    return dict(
        ready=bool(binary and ffmpeg and model and model.is_file()),
        binary=binary,
        ffmpeg=ffmpeg,
        model=str(model) if model else None,
    )


async def transcribe_dream(store, dream_id, job_id, job_dir):
    dream = store.get_dream(dream_id)
    if not dream.audio_id:
        raise ValueError("This entry has no recording.")
    text = await transcribe_recording(store, dream.audio_id, job_id, job_dir)
    transcript_id = uid()
    with store.connect() as db:
        db.execute(
            "INSERT INTO transcripts VALUES (?,?,?,?,?)",
            (transcript_id, dream_id, dream.revision, text, now()),
        )
    return transcript_id


async def transcribe_recording(store, audio_id, job_id, job_dir):
    status = transcription_status(store)
    if not status["ready"]:
        raise ProviderError(
            "transcription_setup",
            "Set up the local transcription tool and model in Settings, then retry.",
        )
    row = audio_record(store, audio_id)
    source = store.data_dir / "audio" / row["filename"]
    wav = job_dir / "input.wav"
    store.set_job(job_id, stage="Preparing recording")
    converted = await run_process(
        [
            status["ffmpeg"],
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(source),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(wav),
        ],
        "",
        job_dir,
        120,
    )
    if converted.returncode:
        raise ProviderError(
            "audio_format",
            "This recording could not be decoded. The original is still saved.",
        )
    store.set_job(job_id, stage="Transcribing locally")
    prefix = job_dir / "transcript"
    result = await run_process(
        [
            status["binary"],
            "-m",
            status["model"],
            "-f",
            str(wav),
            "-otxt",
            "-of",
            str(prefix),
        ],
        "",
        job_dir,
        600,
    )
    if result.returncode or not prefix.with_suffix(".txt").is_file():
        raise ProviderError(
            "transcription_failed",
            "Local transcription did not finish. You can retry or type the dream.",
        )
    text = prefix.with_suffix(".txt").read_text().strip()
    if not text:
        raise ProviderError(
            "empty_transcript",
            "No speech was found. The original recording is still saved.",
        )
    return text
