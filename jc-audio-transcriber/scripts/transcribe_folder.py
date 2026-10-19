#!/usr/bin/env python3
"""将一个录音文件夹转成带文件边界的单份完整逐字稿。"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
import wave
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable


SCRIPT_VERSION = "5"
SUPPORTED_AUDIO_SUFFIXES = {
    ".wav",
    ".mp3",
    ".m4a",
    ".wma",
    ".aac",
    ".ogg",
    ".amr",
    ".flac",
    ".aiff",
    ".opus",
}
FILENAME_TIME_RE = re.compile(r"_(\d{8})_(\d{6})(?:_|$)")
DEFAULT_LOCAL_MODEL = "FunAudioLLM/Fun-ASR-Nano-2512"
LOCAL_PYTHON_PACKAGES = [
    "funasr==1.4.3",
    "torch",
    "torchaudio",
    "modelscope",
]
FUNASR_LANGUAGE = {
    "zh": "中文",
    "en": "英文",
    "ja": "日文",
    "yue": "中文",
    "chinese": "中文",
    "english": "英文",
    "japanese": "日文",
}
_FUNASR_MODEL = None
DEFAULT_QWEN_MODEL = "qwen-audio-3.0-asr-flash-filetrans"
DEFAULT_DOUBAO_RESOURCE_ID = "volc.bigasr.auc_turbo"
DOUBAO_SEED_RESOURCE_ID = "volc.seedasr.auc"
DEFAULT_DOUBAO_MODEL = "bigmodel"
DOUBAO_FLASH_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
DOUBAO_SUBMIT_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit"
DOUBAO_QUERY_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query"
DOUBAO_FLASH_MAX_SECONDS = 2 * 3600
DOUBAO_FLASH_MAX_BYTES = 100 * 1024 * 1024
DOUBAO_STANDARD_MAX_SECONDS = 5 * 3600
DOUBAO_STANDARD_MAX_BYTES = 512 * 1024 * 1024
DOUBAO_BASE64_MAX_BYTES = 12 * 1024 * 1024
DOUBAO_SUCCESS_CODES = {"20000000", "0"}
DOUBAO_PENDING_CODES = {"20000001", "20000002"}
LEGACY_ENV_FILE = Path("~/dji-audio-transcriber/.env")


class TranscriberError(RuntimeError):
    pass


class ConfigError(TranscriberError):
    pass


@dataclass(frozen=True)
class AudioItem:
    path: Path
    recorded_at: datetime | None
    duration_seconds: float | None


def parse_recorded_at(path: Path) -> datetime | None:
    match = FILENAME_TIME_RE.search(path.stem)
    if not match:
        return None
    try:
        return datetime.strptime("".join(match.groups()), "%Y%m%d%H%M%S")
    except ValueError:
        return None


def probe_duration(path: Path) -> float | None:
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as handle:
                rate = handle.getframerate()
                return handle.getnframes() / rate if rate else None
        except (wave.Error, OSError):
            pass

    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        try:
            return float(result.stdout.strip())
        except ValueError:
            pass

    afinfo = shutil.which("afinfo")
    if afinfo:
        result = subprocess.run(
            [afinfo, str(path)], capture_output=True, text=True, check=False
        )
        match = re.search(r"estimated duration:\s+([\d.]+) sec", result.stdout)
        if match:
            return float(match.group(1))
    return None


def discover_audio_files(
    input_dir: Path, only_names: set[str] | None = None
) -> list[AudioItem]:
    directory = input_dir.expanduser().resolve()
    if not directory.is_dir():
        raise ConfigError(f"录音目录不存在：{directory}")
    items: list[AudioItem] = []
    for path in directory.iterdir():
        if path.name.startswith("._") or path.name.startswith("."):
            continue
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_AUDIO_SUFFIXES:
            continue
        if only_names and path.name not in only_names:
            continue
        items.append(
            AudioItem(
                path=path.resolve(),
                recorded_at=parse_recorded_at(path),
                duration_seconds=probe_duration(path),
            )
        )
    items.sort(
        key=lambda item: (
            item.recorded_at or datetime.fromtimestamp(item.path.stat().st_mtime),
            item.path.name,
        )
    )
    return items


def default_cache_root() -> Path:
    value = os.getenv("XDG_CACHE_HOME", "").strip()
    return Path(value).expanduser() if value else Path.home() / ".cache"


def cache_dir_for(input_dir: Path, cache_root: Path | None = None) -> Path:
    directory = input_dir.expanduser().resolve()
    digest = hashlib.sha256(str(directory).encode("utf-8")).hexdigest()[:12]
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", directory.name).strip("_")
    root = (cache_root or default_cache_root()).expanduser().resolve()
    return root / "jc-audio-transcriber" / f"{safe_name or 'recordings'}-{digest}"


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(text)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(
        path, json.dumps(payload, ensure_ascii=False, indent=2, default=json_default)
    )


def json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "tolist"):
        return value.tolist()
    raise TypeError(f"无法序列化 {type(value).__name__}")


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TranscriberError(f"无法读取缓存状态：{path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise TranscriberError(f"缓存状态不是 JSON 对象：{path}")
    return payload


def profile_for(args: argparse.Namespace) -> dict[str, Any]:
    if args.provider == "local":
        return {
            "provider": "local",
            "engine": "funasr",
            "model": args.local_model,
            "language": args.language,
            "hotwords": sorted(args.hotword or []),
        }
    if args.provider == "doubao":
        resource_id = args.doubao_resource_id or DEFAULT_DOUBAO_RESOURCE_ID
        return {
            "provider": "doubao",
            "engine": "volc-flash" if is_doubao_flash(resource_id) else "volc-standard",
            "model": DEFAULT_DOUBAO_MODEL,
            "resource_id": resource_id,
            "diarization": bool(args.diarization),
            "language": args.language,
            "hotwords": sorted(args.hotword or []),
        }
    return {
        "provider": "qwen",
        "model": args.qwen_model or DEFAULT_QWEN_MODEL,
        "diarization": args.diarization,
        "speaker_count": args.speaker_count,
        "language_hints": args.language_hint or ["zh", "en"],
        "hotwords": sorted(args.hotword or []),
    }


def model_name_for(args: argparse.Namespace) -> str:
    if args.provider == "local":
        return args.local_model
    if args.provider == "doubao":
        return args.doubao_resource_id or DEFAULT_DOUBAO_RESOURCE_ID
    return args.qwen_model or DEFAULT_QWEN_MODEL


def fingerprint(item: AudioItem, profile: dict[str, Any]) -> str:
    stat = item.path.stat()
    raw = json.dumps(
        {
            "script_version": SCRIPT_VERSION,
            "path": str(item.path),
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "profile": profile,
        },
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def job_paths(cache_dir: Path, digest: str) -> tuple[Path, Path, Path]:
    jobs = cache_dir / "jobs"
    return (
        jobs / f"{digest}.state.json",
        jobs / f"{digest}.result.json",
        jobs / f"{digest}.txt",
    )


def format_timestamp(seconds: float | int | None) -> str:
    value = max(0, int(float(seconds or 0)))
    hours, remainder = divmod(value, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_local_result(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    segments = payload.get("segments")
    if isinstance(segments, list):
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            text = str(segment.get("text", "")).strip()
            if not text:
                continue
            lines.append(f"[{format_timestamp(segment.get('start'))}] {text}")
    if not lines:
        text = str(payload.get("text", "")).strip()
        if text:
            lines.extend(line.strip() for line in text.splitlines() if line.strip())
    return "\n".join(lines).strip() + ("\n" if lines else "")


def format_qwen_result(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    transcripts = payload.get("transcripts")
    if not isinstance(transcripts, list):
        transcripts = []
    for transcript in transcripts:
        if not isinstance(transcript, dict):
            continue
        sentences = transcript.get("sentences")
        if isinstance(sentences, list):
            for sentence in sentences:
                if not isinstance(sentence, dict):
                    continue
                text = str(sentence.get("text", "")).strip()
                if not text:
                    continue
                begin_ms = sentence.get("begin_time", 0)
                try:
                    begin_seconds = float(begin_ms) / 1000
                except (TypeError, ValueError):
                    begin_seconds = 0
                speaker = sentence.get("speaker_id")
                prefix = f"[{format_timestamp(begin_seconds)}] "
                if speaker is not None:
                    try:
                        speaker_label = int(speaker) + 1
                    except (TypeError, ValueError):
                        speaker_label = speaker
                    prefix += f"说话人 {speaker_label}："
                lines.append(prefix + text)
        elif transcript.get("text"):
            text = str(transcript["text"]).strip()
            if text:
                lines.append(text)
    return "\n".join(lines).strip() + ("\n" if lines else "")


def format_doubao_result(payload: dict[str, Any]) -> str:
    result = payload.get("result")
    if not isinstance(result, dict):
        result = payload if isinstance(payload, dict) else {}
    lines: list[str] = []
    utterances = result.get("utterances")
    if isinstance(utterances, list):
        for utterance in utterances:
            if not isinstance(utterance, dict):
                continue
            text = str(utterance.get("text", "")).strip()
            if not text:
                continue
            try:
                begin_seconds = float(utterance.get("start_time") or 0) / 1000
            except (TypeError, ValueError):
                begin_seconds = 0
            prefix = f"[{format_timestamp(begin_seconds)}] "
            speaker = utterance.get("speaker")
            additions = utterance.get("additions")
            if speaker is None and isinstance(additions, dict):
                speaker = additions.get("speaker")
            if speaker is not None and str(speaker).strip() != "":
                raw = str(speaker).strip()
                try:
                    speaker_label = int(raw) + (0 if int(raw) >= 1 else 1)
                except ValueError:
                    speaker_label = raw
                prefix += f"说话人 {speaker_label}："
            lines.append(prefix + text)
    if not lines:
        text = str(result.get("text") or payload.get("text") or "").strip()
        if text:
            lines.append(text)
    return "\n".join(lines).strip() + ("\n" if lines else "")


def ensure_python_dependencies(packages: list[str], modules: list[str]) -> None:
    missing = False
    for module in modules:
        try:
            importlib.import_module(module)
        except ImportError:
            missing = True
            break
    if not missing:
        return
    joined = ", ".join(packages)
    if os.getenv("JC_AUDIO_TRANSCRIBER_UV_BOOTSTRAPPED") == "1":
        raise ConfigError(f"缺少 Python 依赖 {joined}")
    uv = shutil.which("uv")
    if not uv:
        raise ConfigError(f"缺少 Python 依赖 {joined}，并且未安装 uv")
    print(f"缺少 {joined}，使用 uv 在隔离环境中运行", file=sys.stderr)
    environment = os.environ.copy()
    environment["JC_AUDIO_TRANSCRIBER_UV_BOOTSTRAPPED"] = "1"
    command = [uv, "run"]
    for package in packages:
        command.extend(["--with", package])
    command.extend(["python", str(Path(__file__).resolve()), *sys.argv[1:]])
    os.execve(uv, command, environment)


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def resolve_funasr_language(value: str | None) -> str:
    if not value:
        return "中文"
    return FUNASR_LANGUAGE.get(value.strip().lower(), value)


def resolve_local_device() -> str:
    try:
        import torch

        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda:0"
    except Exception:
        pass
    return "cpu"


def funasr_payload(result: Any) -> dict[str, Any]:
    item = result[0] if isinstance(result, list) and result else result
    if not isinstance(item, dict):
        text = str(item).strip()
        return {"text": text, "segments": [{"start": 0, "text": text}] if text else []}
    segments: list[dict[str, Any]] = []
    info = item.get("sentence_info")
    if isinstance(info, list):
        for sent in info:
            if not isinstance(sent, dict):
                continue
            text = str(sent.get("text") or sent.get("sentence") or "").strip()
            if not text:
                continue
            start = sent.get("start", sent.get("begin_time", 0))
            try:
                start_seconds = float(start) / 1000.0
            except (TypeError, ValueError):
                start_seconds = 0.0
            segments.append({"start": start_seconds, "text": text})
    text = str(item.get("text") or "").strip()
    if not segments and text:
        segments.append({"start": 0, "text": text})
    return {
        "text": text,
        "segments": segments,
        "sentence_info": jsonable(info) if info is not None else [],
    }


def get_funasr_model(args: argparse.Namespace) -> Any:
    global _FUNASR_MODEL
    if _FUNASR_MODEL is not None:
        return _FUNASR_MODEL
    from funasr import AutoModel

    device = resolve_local_device()
    kwargs: dict[str, Any] = {
        "model": args.local_model,
        "trust_remote_code": True,
        "vad_model": "fsmn-vad",
        "vad_kwargs": {"max_single_segment_time": 30000},
        "device": device,
        "hub": "ms",
    }
    print(f"加载 FunASR：{args.local_model}（{device}）", file=sys.stderr)
    try:
        _FUNASR_MODEL = AutoModel(**kwargs)
    except Exception as exc:
        if device == "cpu":
            raise
        print(f"{device} 不可用，改用 CPU：{exc}", file=sys.stderr)
        kwargs["device"] = "cpu"
        _FUNASR_MODEL = AutoModel(**kwargs)
    return _FUNASR_MODEL


def wav_frame_count(path: Path) -> int | None:
    if path.suffix.lower() != ".wav":
        return None
    try:
        with wave.open(str(path), "rb") as handle:
            return handle.getnframes()
    except (wave.Error, OSError):
        return None


def is_empty_audio(path: Path, duration_seconds: float | None = None) -> bool:
    frames = wav_frame_count(path)
    if frames is not None and frames <= 0:
        return True
    duration = duration_seconds if duration_seconds is not None else probe_duration(path)
    return duration is not None and duration <= 0


def is_empty_asr_error(exc: BaseException) -> bool:
    message = str(exc)
    return "cannot reshape tensor of 0 elements" in message or "empty speech" in message.lower()


def complete_empty_local(
    state: dict[str, Any],
    state_path: Path,
    raw_path: Path,
    fragment_path: Path,
) -> dict[str, Any]:
    payload = {"text": "", "segments": [], "empty_speech": True}
    atomic_write_json(raw_path, payload)
    atomic_write_text(fragment_path, "")
    state.update(
        {
            "status": "completed",
            "raw_path": str(raw_path),
            "fragment_path": str(fragment_path),
            "text_chars": 0,
            "empty_speech": True,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    atomic_write_json(state_path, state)
    return state


def process_local(
    item: AudioItem,
    args: argparse.Namespace,
    state_path: Path,
    raw_path: Path,
    fragment_path: Path,
    digest: str,
) -> dict[str, Any]:
    require_ffmpeg("本地 Fun-ASR")
    ensure_python_dependencies(LOCAL_PYTHON_PACKAGES, ["funasr", "torch", "torchaudio", "modelscope"])

    state = {
        "fingerprint": digest,
        "provider": "local",
        "source_path": str(item.path),
        "status": "running",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    atomic_write_json(state_path, state)
    print(f"本地转写：{item.path.name}")
    if is_empty_audio(item.path, item.duration_seconds):
        print(f"空录音，标记为未识别到有效语音：{item.path.name}")
        return complete_empty_local(state, state_path, raw_path, fragment_path)
    try:
        model = get_funasr_model(args)
        generate_kwargs: dict[str, Any] = {
            "input": [str(item.path)],
            "cache": {},
            "batch_size": 1,
            "language": resolve_funasr_language(args.language),
            "itn": True,
        }
        if args.hotword:
            generate_kwargs["hotwords"] = " ".join(
                hotword.split("=", 1)[0] for hotword in args.hotword
            )
        result = model.generate(**generate_kwargs)
        payload = funasr_payload(result)
        fragment = format_local_result(payload)
        atomic_write_json(raw_path, payload)
        atomic_write_text(fragment_path, fragment)
        state.update(
            {
                "status": "completed",
                "raw_path": str(raw_path),
                "fragment_path": str(fragment_path),
                "text_chars": len(fragment.strip()),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        atomic_write_json(state_path, state)
        return state
    except Exception as exc:
        if is_empty_asr_error(exc):
            print(f"空语音，标记为未识别到有效语音：{item.path.name}")
            return complete_empty_local(state, state_path, raw_path, fragment_path)
        state.update(
            {
                "status": "failed",
                "error": str(exc),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        atomic_write_json(state_path, state)
        raise


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value[:1] == value[-1:] and value[:1] in {"'", '"'}:
            value = value[1:-1]
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            os.environ.setdefault(key, value)


def resolve_env_file(explicit: str | None) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    configured = os.getenv("JC_AUDIO_TRANSCRIBER_ENV", "").strip()
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.extend(
        [Path.home() / ".config/jc-audio-transcriber/.env", LEGACY_ENV_FILE]
    )
    return next((path.resolve() for path in candidates if path.is_file()), None)


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"缺少环境变量 {name}")
    return value


def qwen_base_url() -> str:
    explicit = os.getenv("DASHSCOPE_BASE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    workspace = os.getenv("DASHSCOPE_WORKSPACE_ID", "").strip()
    region = os.getenv("DASHSCOPE_REGION", "cn-beijing").strip()
    if workspace:
        return f"https://{workspace}.{region}.maas.aliyuncs.com/api/v1"
    return "https://dashscope.aliyuncs.com/api/v1"


def http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    result, _headers = http_json_response(
        method, url, headers=headers, payload=payload, timeout=timeout
    )
    return result


def http_json_response(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 120,
) -> tuple[dict[str, Any], dict[str, str]]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method=method, headers=headers or {}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            header_map = {key.lower(): value for key, value in response.headers.items()}
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")[:1000]
        raise TranscriberError(f"HTTP {exc.code}: {message}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise TranscriberError(f"请求失败：{url}: {exc}") from exc
    try:
        result = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as exc:
        raise TranscriberError(f"请求失败：{url}: {exc}") from exc
    if not isinstance(result, dict):
        raise TranscriberError(f"接口返回不是 JSON 对象：{url}")
    return result, header_map


def parse_hotwords(values: list[str] | None) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values or []:
        word, separator, weight_text = value.rpartition("=")
        if not separator:
            word, weight_text = value, "5"
        word = word.strip()
        try:
            weight = int(weight_text)
        except ValueError as exc:
            raise ConfigError(f"热词权重无效：{value}") from exc
        if not word or weight not in {1, 2, 3, 4, 5, 50}:
            raise ConfigError(f"热词格式应为 词语=1..5 或 词语=50：{value}")
        result[word] = weight
    return result


def qwen_request_body(args: argparse.Namespace, file_url: str) -> dict[str, Any]:
    parameters: dict[str, Any] = {
        "channel_id": [0],
        "diarization_enabled": bool(args.diarization),
        "language_hints": args.language_hint or ["zh", "en"],
        "special_word_filter": {
            "filter_with_signed": {"word_list": []},
            "filter_with_empty": {"word_list": []},
            "system_reserved_filter": False,
        },
    }
    if args.speaker_count:
        if args.speaker_count < 2 or args.speaker_count > 100:
            raise ConfigError("speaker-count 必须为 0 或 2..100")
        parameters["speaker_count"] = args.speaker_count
    hotwords = parse_hotwords(args.hotword)
    if hotwords:
        parameters["vocabulary"] = hotwords
    return {
        "model": args.qwen_model or DEFAULT_QWEN_MODEL,
        "input": {"file_urls": [file_url]},
        "parameters": parameters,
    }


def create_s3_client():
    ensure_python_dependencies(["boto3==1.40.1"], ["boto3"])
    import boto3  # type: ignore
    from botocore.client import Config as BotoConfig  # type: ignore

    return boto3.client(
        "s3",
        endpoint_url=require_env("MINIO_ENDPOINT").rstrip("/"),
        aws_access_key_id=require_env("MINIO_ACCESS_KEY"),
        aws_secret_access_key=require_env("MINIO_SECRET_KEY"),
        region_name=os.getenv("MINIO_REGION", "us-east-1").strip() or "us-east-1",
        config=BotoConfig(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            retries={"max_attempts": 5, "mode": "standard"},
        ),
    )


def object_key_for(item: AudioItem, digest: str) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", item.path.name)
    date_prefix = datetime.now().strftime("%Y/%m/%d")
    return f"jc-audio-transcriber/{date_prefix}/{digest[:12]}-{safe_name}"


def upload_and_presign(
    s3: Any,
    item: AudioItem,
    digest: str,
    source_path: Path | None = None,
) -> tuple[str, str]:
    local_path = source_path or item.path
    bucket = require_env("MINIO_BUCKET")
    object_key = object_key_for(item, digest)
    content_type = mimetypes.guess_type(local_path.name)[0] or "application/octet-stream"
    print(f"上传临时音频：{item.path.name}")
    s3.upload_file(
        str(local_path), bucket, object_key, ExtraArgs={"ContentType": content_type}
    )
    hours = int(os.getenv("MINIO_PRESIGN_HOURS", "12"))
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": object_key},
        ExpiresIn=hours * 3600,
    )
    return object_key, url


def delete_remote_object(s3: Any, object_key: str) -> None:
    s3.delete_object(Bucket=require_env("MINIO_BUCKET"), Key=object_key)


def require_ffmpeg(purpose: str) -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ConfigError(f"{purpose}需要 ffmpeg；macOS 可运行 brew install ffmpeg")
    return ffmpeg


def resample_wav_16k_mono(source: Path, destination: Path) -> None:
    ffmpeg = require_ffmpeg("豆包转写")
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(source),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-sample_fmt",
            "s16",
            str(destination),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not destination.is_file():
        detail = (result.stderr or result.stdout or "").strip()[-500:]
        raise TranscriberError(f"ffmpeg 转码失败：{source.name}: {detail}")


def is_doubao_flash(resource_id: str) -> bool:
    value = (resource_id or "").strip().lower()
    return value.endswith("auc_turbo") or "flash" in value


def doubao_status(result: dict[str, Any], headers: dict[str, str]) -> str:
    return str(
        headers.get("x-api-status-code")
        or result.get("code")
        or result.get("status_code")
        or ""
    )


def doubao_status_message(result: dict[str, Any], headers: dict[str, str]) -> str:
    return str(
        headers.get("x-api-message")
        or result.get("message")
        or result
    )


def doubao_headers(api_key: str, resource_id: str, request_id: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": request_id,
        "X-Api-Connect-Id": str(uuid.uuid4()),
    }


def doubao_request_body(
    args: argparse.Namespace,
    *,
    file_url: str | None = None,
    audio_b64: str | None = None,
) -> dict[str, Any]:
    if bool(file_url) == bool(audio_b64):
        raise ConfigError("豆包请求必须提供 audio.url 或 audio.data 之一")
    audio: dict[str, Any] = {
        "format": "wav",
        "codec": "raw",
        "rate": 16000,
        "bits": 16,
        "channel": 1,
    }
    if file_url:
        audio["url"] = file_url
    else:
        audio["data"] = audio_b64
    request: dict[str, Any] = {
        "model_name": DEFAULT_DOUBAO_MODEL,
        "enable_itn": True,
        "enable_punc": True,
        "enable_ddc": True,
        "show_utterances": True,
        "enable_speaker_info": bool(args.diarization),
    }
    if args.language:
        mapped = {"zh": "zh-CN", "yue": "zh-CN", "en": "en-US"}.get(
            args.language.strip().lower(), args.language
        )
        request["language"] = mapped
    return {
        "user": {"uid": os.getenv("VOLC_SPEECH_UID", "jc-audio-transcriber").strip() or "jc-audio-transcriber"},
        "audio": audio,
        "request": request,
    }


def finish_doubao_result(
    result: dict[str, Any],
    *,
    state: dict[str, Any],
    state_path: Path,
    raw_path: Path,
    fragment_path: Path,
    request_id: str,
    s3: Any,
    object_key: str,
    delete_remote: bool,
) -> dict[str, Any]:
    fragment = format_doubao_result(result)
    if not fragment.strip():
        raise TranscriberError("豆包返回空转写")
    atomic_write_json(raw_path, result)
    atomic_write_text(fragment_path, fragment)
    state.update(
        {
            "status": "completed",
            "raw_path": str(raw_path),
            "fragment_path": str(fragment_path),
            "text_chars": len(fragment.strip()),
            "request_id": request_id,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    atomic_write_json(state_path, state)
    if delete_remote and s3 and object_key:
        delete_remote_object(s3, object_key)
        state["remote_deleted"] = True
        atomic_write_json(state_path, state)
    return state


def process_doubao(
    item: AudioItem,
    args: argparse.Namespace,
    state_path: Path,
    raw_path: Path,
    fragment_path: Path,
    digest: str,
) -> dict[str, Any]:
    api_key = require_env("VOLC_SPEECH_API_KEY")
    resource_id = args.doubao_resource_id or DEFAULT_DOUBAO_RESOURCE_ID
    flash = is_doubao_flash(resource_id)
    duration = item.duration_seconds or 0
    max_seconds = DOUBAO_FLASH_MAX_SECONDS if flash else DOUBAO_STANDARD_MAX_SECONDS
    max_bytes = DOUBAO_FLASH_MAX_BYTES if flash else DOUBAO_STANDARD_MAX_BYTES
    if duration > max_seconds:
        limit_label = "极速版 2 小时" if flash else "标准版 5 小时"
        raise ConfigError(f"{item.path.name} 时长超过豆包{limit_label}上限")
    converted = raw_path.with_suffix(".16k.wav")
    existing = read_json(state_path) if state_path.exists() else {}
    request_id = str(existing.get("request_id") or "")
    object_key = str(existing.get("object_key") or "")
    state: dict[str, Any] = {
        "fingerprint": digest,
        "provider": "doubao",
        "resource_id": resource_id,
        "source_path": str(item.path),
        "status": existing.get("status", "running"),
        "request_id": request_id,
        "object_key": object_key,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    atomic_write_json(state_path, state)
    s3 = None
    print(f"豆包转写：{item.path.name}（{resource_id}）")
    try:
        if flash:
            resample_wav_16k_mono(item.path, converted)
            size = converted.stat().st_size
            if size > max_bytes:
                raise ConfigError(
                    f"{item.path.name} 转 16 kHz 后仍超过 100MB，豆包极速版无法接收"
                )
            if size <= DOUBAO_BASE64_MAX_BYTES:
                payload = doubao_request_body(
                    args,
                    audio_b64=base64.b64encode(converted.read_bytes()).decode("ascii"),
                )
            else:
                s3 = create_s3_client()
                object_key, file_url = upload_and_presign(s3, item, digest, converted)
                state.update({"status": "uploaded", "object_key": object_key})
                atomic_write_json(state_path, state)
                payload = doubao_request_body(args, file_url=file_url)
            request_id = str(uuid.uuid4())
            result, response_headers = http_json_response(
                "POST",
                DOUBAO_FLASH_URL,
                headers=doubao_headers(api_key, resource_id, request_id),
                payload=payload,
                timeout=max(180, int(duration) + 120),
            )
            status_code = doubao_status(result, response_headers)
            if status_code and status_code not in DOUBAO_SUCCESS_CODES:
                raise TranscriberError(
                    f"豆包失败 {status_code}：{doubao_status_message(result, response_headers)}"
                )
            return finish_doubao_result(
                result,
                state=state,
                state_path=state_path,
                raw_path=raw_path,
                fragment_path=fragment_path,
                request_id=request_id,
                s3=s3,
                object_key=object_key,
                delete_remote=bool(args.delete_remote),
            )

        if not request_id:
            resample_wav_16k_mono(item.path, converted)
            if converted.stat().st_size > max_bytes:
                raise ConfigError(
                    f"{item.path.name} 转 16 kHz 后仍超过 512MB，豆包标准版无法接收"
                )
            s3 = create_s3_client()
            object_key, file_url = upload_and_presign(s3, item, digest, converted)
            request_id = str(uuid.uuid4())
            state.update(
                {
                    "status": "uploaded",
                    "object_key": object_key,
                    "request_id": request_id,
                }
            )
            atomic_write_json(state_path, state)
            result, response_headers = http_json_response(
                "POST",
                DOUBAO_SUBMIT_URL,
                headers=doubao_headers(api_key, resource_id, request_id),
                payload=doubao_request_body(args, file_url=file_url),
                timeout=60,
            )
            status_code = doubao_status(result, response_headers)
            if status_code and status_code not in DOUBAO_SUCCESS_CODES | DOUBAO_PENDING_CODES:
                raise TranscriberError(
                    f"豆包提交失败 {status_code}：{doubao_status_message(result, response_headers)}"
                )
            state.update({"status": "submitted", "request_id": request_id})
            atomic_write_json(state_path, state)
            print(f"已提交豆包标准版：{item.path.name}，任务 {request_id}")
        else:
            print(f"继续豆包标准版：{item.path.name}，任务 {request_id}")
            if object_key:
                s3 = create_s3_client()

        deadline = time.monotonic() + args.timeout_hours * 3600
        while True:
            result, response_headers = http_json_response(
                "POST",
                DOUBAO_QUERY_URL,
                headers=doubao_headers(api_key, resource_id, request_id),
                payload={},
                timeout=60,
            )
            status_code = doubao_status(result, response_headers)
            if status_code in DOUBAO_SUCCESS_CODES or (
                not status_code and format_doubao_result(result).strip()
            ):
                return finish_doubao_result(
                    result,
                    state=state,
                    state_path=state_path,
                    raw_path=raw_path,
                    fragment_path=fragment_path,
                    request_id=request_id,
                    s3=s3,
                    object_key=object_key,
                    delete_remote=bool(args.delete_remote),
                )
            if status_code in DOUBAO_PENDING_CODES or not status_code:
                if time.monotonic() >= deadline:
                    raise TranscriberError(
                        f"等待豆包标准版超时（{args.timeout_hours} 小时）；下次运行会继续查询"
                    )
                print(f"  {item.path.name}：{status_code or 'PENDING'}")
                time.sleep(args.poll_seconds)
                continue
            raise TranscriberError(
                f"豆包查询失败 {status_code}：{doubao_status_message(result, response_headers)}"
            )
    except Exception as exc:
        state.update(
            {
                "status": "failed",
                "error": str(exc),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        atomic_write_json(state_path, state)
        raise
    finally:
        if converted.exists():
            converted.unlink()


def process_qwen(
    item: AudioItem,
    args: argparse.Namespace,
    state_path: Path,
    raw_path: Path,
    fragment_path: Path,
    digest: str,
) -> dict[str, Any]:
    api_key = require_env("DASHSCOPE_API_KEY")
    base_url = qwen_base_url()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    existing = read_json(state_path) if state_path.exists() else {}
    s3 = create_s3_client()
    task_id = str(existing.get("task_id", ""))
    object_key = str(existing.get("object_key", ""))
    state: dict[str, Any] = {
        "fingerprint": digest,
        "provider": "qwen",
        "source_path": str(item.path),
        "status": existing.get("status", "pending"),
        "task_id": task_id,
        "object_key": object_key,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }

    try:
        if not task_id:
            object_key, file_url = upload_and_presign(s3, item, digest)
            state.update({"status": "uploaded", "object_key": object_key})
            atomic_write_json(state_path, state)
            response = http_json(
                "POST",
                f"{base_url}/services/audio/asr/transcription",
                headers=headers,
                payload=qwen_request_body(args, file_url),
            )
            output = response.get("output", {})
            if not isinstance(output, dict) or not output.get("task_id"):
                raise TranscriberError(f"Qwen 提交结果缺少 task_id：{response}")
            task_id = str(output["task_id"])
            state.update({"status": "submitted", "task_id": task_id})
            atomic_write_json(state_path, state)
            print(f"已提交 Qwen：{item.path.name}，任务 {task_id}")
        else:
            print(f"继续 Qwen 任务：{item.path.name}，任务 {task_id}")

        deadline = time.monotonic() + args.timeout_hours * 3600
        while True:
            response = http_json(
                "GET",
                f"{base_url}/tasks/{task_id}",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            output = response.get("output", {})
            if not isinstance(output, dict):
                raise TranscriberError(f"Qwen 查询结果缺少 output：{response}")
            status = str(output.get("task_status", "UNKNOWN"))
            if status == "SUCCEEDED":
                results = output.get("results")
                if not isinstance(results, list) or not results:
                    raise TranscriberError(f"Qwen 成功任务缺少 results：{response}")
                result = results[0]
                if not isinstance(result, dict) or result.get("subtask_status") != "SUCCEEDED":
                    raise TranscriberError(f"Qwen 子任务失败：{result}")
                transcription_url = result.get("transcription_url")
                if not transcription_url:
                    raise TranscriberError("Qwen 结果缺少 transcription_url")
                payload = http_json("GET", str(transcription_url), timeout=180)
                fragment = format_qwen_result(payload)
                atomic_write_json(raw_path, payload)
                atomic_write_text(fragment_path, fragment)
                state.update(
                    {
                        "status": "completed",
                        "raw_path": str(raw_path),
                        "fragment_path": str(fragment_path),
                        "text_chars": len(fragment.strip()),
                        "updated_at": datetime.now().isoformat(timespec="seconds"),
                    }
                )
                atomic_write_json(state_path, state)
                if args.delete_remote and object_key:
                    delete_remote_object(s3, object_key)
                    state["remote_deleted"] = True
                    atomic_write_json(state_path, state)
                return state
            if status in {"FAILED", "CANCELED", "UNKNOWN"}:
                raise TranscriberError(f"Qwen 任务 {status}：{output}")
            if time.monotonic() >= deadline:
                raise TranscriberError(
                    f"等待 Qwen 任务超时（{args.timeout_hours} 小时）；下次运行会继续查询"
                )
            print(f"  {item.path.name}：{status}")
            time.sleep(args.poll_seconds)
    except Exception as exc:
        state.update(
            {
                "status": "failed",
                "error": str(exc),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        atomic_write_json(state_path, state)
        raise


def transcribe_item(
    item: AudioItem,
    args: argparse.Namespace,
    cache_dir: Path,
    profile: dict[str, Any],
) -> dict[str, Any]:
    digest = fingerprint(item, profile)
    state_path, raw_path, fragment_path = job_paths(cache_dir, digest)
    if not args.force and state_path.exists() and fragment_path.exists():
        state = read_json(state_path)
        if state.get("status") == "completed":
            print(f"复用缓存：{item.path.name}")
            return state
    if args.force:
        for path in (state_path, raw_path, fragment_path):
            if path.exists():
                path.unlink()
    if args.provider == "local":
        return process_local(
            item, args, state_path, raw_path, fragment_path, digest
        )
    if args.provider == "doubao":
        return process_doubao(item, args, state_path, raw_path, fragment_path, digest)
    return process_qwen(item, args, state_path, raw_path, fragment_path, digest)


def human_duration(seconds: float | None) -> str:
    if seconds is None:
        return "未知"
    value = int(round(seconds))
    hours, remainder = divmod(value, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}小时{minutes:02d}分{secs:02d}秒"
    if minutes:
        return f"{minutes}分{secs:02d}秒"
    return f"{secs}秒"


def recording_range(items: Iterable[AudioItem]) -> str:
    dated = [item for item in items if item.recorded_at]
    if not dated:
        return "未知"
    start = min(item.recorded_at for item in dated if item.recorded_at)
    end_candidates = [
        item.recorded_at + timedelta(seconds=item.duration_seconds or 0)
        for item in dated
        if item.recorded_at
    ]
    end = max(end_candidates)
    return f"{start:%Y-%m-%d %H:%M:%S} 至 {end:%Y-%m-%d %H:%M:%S}"


def build_transcript(
    input_dir: Path,
    items: list[AudioItem],
    states: list[dict[str, Any]],
    provider: str,
    model: str,
) -> str:
    total = sum(item.duration_seconds or 0 for item in items)
    lines = [
        "录音完整逐字稿",
        f"转写日期：{datetime.now():%Y-%m-%d}",
        f"录音范围：{recording_range(items)}",
        f"来源目录：{input_dir.expanduser().resolve()}",
        f"来源文件：{len(items)} 个，音频总时长约 {human_duration(total)}",
        f"转写引擎：{provider} / {model}",
        "说明：以下为自动语音识别结果，未经过观点改写。时间戳是当前源文件内的相对时间。",
        "质量提示：嘈杂、多人重叠、音乐或游戏音效可能造成错字和循环识别；关键细节请回听原始音频。",
        "",
    ]
    for item, state in zip(items, states):
        recorded = (
            item.recorded_at.strftime("%Y-%m-%d %H:%M:%S")
            if item.recorded_at
            else "录制时间未知"
        )
        lines.extend(
            [
                f"===== {recorded}｜{item.path.name}｜{human_duration(item.duration_seconds)} =====",
                "",
            ]
        )
        fragment_value = str(state.get("fragment_path", ""))
        fragment_path = Path(fragment_value) if fragment_value else Path()
        fragment = (
            fragment_path.read_text(encoding="utf-8").strip()
            if fragment_value and fragment_path.is_file()
            else ""
        )
        lines.append(fragment or "（未识别到有效语音）")
        lines.extend(["", ""])
    return "\n".join(lines).rstrip() + "\n"


def build_quality_report(
    input_dir: Path,
    items: list[AudioItem],
    states: list[dict[str, Any]],
    provider: str,
    model: str,
    output_path: Path,
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    warnings: list[str] = []
    for item, state in zip(items, states):
        fragment_value = str(state.get("fragment_path", ""))
        fragment_path = Path(fragment_value) if fragment_value else Path()
        text = (
            fragment_path.read_text(encoding="utf-8").strip()
            if fragment_value and fragment_path.is_file()
            else ""
        )
        lines = [line for line in text.splitlines() if line.strip()]
        spoken_lines = [
            re.sub(
                r"^(?:\[\d{2}:\d{2}:\d{2}\]\s*)?(?:说话人\s*\d+[:：]\s*)?",
                "",
                line,
            ).strip()
            for line in lines
        ]
        spoken_lines = [line for line in spoken_lines if line]
        compact_chars = len(re.sub(r"\s+", "", text))
        item_warnings: list[str] = []
        if item.duration_seconds is not None and item.duration_seconds <= 5:
            item_warnings.append("极短录音")
        if not text:
            item_warnings.append("未识别到有效语音")
        if item.duration_seconds and item.duration_seconds >= 60:
            chars_per_minute = compact_chars / (item.duration_seconds / 60)
            if chars_per_minute < 2:
                item_warnings.append("文字密度异常低")
        if spoken_lines:
            most_common = Counter(spoken_lines).most_common(1)[0][1]
            longest_run = 1
            current_run = 1
            for previous, current in zip(spoken_lines, spoken_lines[1:]):
                current_run = current_run + 1 if current == previous else 1
                longest_run = max(longest_run, current_run)
            if longest_run >= 5 or (
                most_common >= 8 and most_common / len(spoken_lines) >= 0.05
            ):
                item_warnings.append("疑似循环重复")
        warnings.extend(f"{item.path.name}：{warning}" for warning in item_warnings)
        entries.append(
            {
                "source": str(item.path),
                "recorded_at": item.recorded_at.isoformat() if item.recorded_at else None,
                "duration_seconds": item.duration_seconds,
                "status": state.get("status"),
                "text_chars": compact_chars,
                "warnings": item_warnings,
            }
        )
    return {
        "input_dir": str(input_dir.expanduser().resolve()),
        "provider": provider,
        "model": model,
        "output_path": str(output_path),
        "source_count": len(items),
        "completed_count": sum(1 for state in states if state.get("status") == "completed"),
        "warnings": warnings,
        "files": entries,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def inventory_command(args: argparse.Namespace) -> int:
    items = discover_audio_files(Path(args.input_dir), set(args.only or []))
    if args.json:
        payload = {
            "input_dir": str(Path(args.input_dir).expanduser().resolve()),
            "count": len(items),
            "total_duration_seconds": sum(item.duration_seconds or 0 for item in items),
            "files": [
                {
                    "path": str(item.path),
                    "recorded_at": item.recorded_at.isoformat() if item.recorded_at else None,
                    "duration_seconds": item.duration_seconds,
                }
                for item in items
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    print(f"录音目录：{Path(args.input_dir).expanduser().resolve()}")
    for index, item in enumerate(items, start=1):
        recorded = item.recorded_at.strftime("%Y-%m-%d %H:%M:%S") if item.recorded_at else "时间未知"
        print(f"{index:02d}. {recorded} | {human_duration(item.duration_seconds)} | {item.path.name}")
    total = sum(item.duration_seconds or 0 for item in items)
    print(f"合计：{len(items)} 个音频，约 {human_duration(total)}")
    return 0


def transcribe_command(args: argparse.Namespace) -> int:
    env_file = resolve_env_file(args.env_file)
    if env_file:
        load_dotenv(env_file)
    items = discover_audio_files(Path(args.input_dir), set(args.only or []))
    if not items:
        raise ConfigError("没有发现可转写的音频")
    cache_dir = cache_dir_for(
        Path(args.input_dir), Path(args.cache_root) if args.cache_root else None
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    profile = profile_for(args)
    states: list[dict[str, Any]] = []
    failures: list[str] = []
    for item in items:
        try:
            states.append(transcribe_item(item, args, cache_dir, profile))
        except KeyboardInterrupt:
            print("已停止；下次运行会复用现有缓存或继续云端任务", file=sys.stderr)
            return 130
        except Exception as exc:
            failures.append(f"{item.path.name}: {exc}")
            states.append(
                {
                    "source_path": str(item.path),
                    "status": "failed",
                    "error": str(exc),
                }
            )
            print(f"失败：{item.path.name}: {exc}", file=sys.stderr)
            if not args.allow_partial:
                break
    if failures and not args.allow_partial:
        raise TranscriberError(
            "转写未完成，不生成完整逐字稿：\n" + "\n".join(failures)
        )
    if len(states) != len(items):
        raise TranscriberError("转写状态数量与音频数量不一致")
    if any(state.get("status") != "completed" for state in states):
        raise TranscriberError("仍有音频未完成，不生成完整逐字稿")

    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else cache_dir / "complete-transcript.txt"
    )
    model = model_name_for(args)
    transcript = build_transcript(
        Path(args.input_dir), items, states, args.provider, model
    )
    atomic_write_text(output_path, transcript)
    report = build_quality_report(
        Path(args.input_dir), items, states, args.provider, model, output_path
    )
    report_path = cache_dir / "quality-report.json"
    atomic_write_json(report_path, report)
    print(f"完整逐字稿：{output_path}")
    print(f"质量报告：{report_path}")
    for warning in report["warnings"]:
        print(f"警告：{warning}", file=sys.stderr)
    return 0


def add_common_input_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("input_dir", help="包含录音的文件夹")
    parser.add_argument(
        "--only", action="append", default=[], help="只处理指定文件名；可重复"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory = subparsers.add_parser("inventory", help="只读列出音频清单")
    add_common_input_arguments(inventory)
    inventory.add_argument("--json", action="store_true", help="输出 JSON")

    transcribe = subparsers.add_parser("transcribe", help="转写并合并为一个 TXT")
    add_common_input_arguments(transcribe)
    transcribe.add_argument(
        "--provider", choices=("local", "qwen", "doubao"), default="local"
    )
    transcribe.add_argument("--output", help="合并逐字稿输出路径")
    transcribe.add_argument("--cache-root", help="缓存根目录")
    transcribe.add_argument("--env-file", help="云端配置文件")
    transcribe.add_argument("--force", action="store_true", help="忽略已完成缓存并重跑")
    transcribe.add_argument(
        "--allow-partial", action="store_true", help="调试用；仍不会把部分结果称为完整逐字稿"
    )

    transcribe.add_argument("--local-model", default=DEFAULT_LOCAL_MODEL)
    transcribe.add_argument("--language", default="zh")
    transcribe.add_argument("--initial-prompt")
    transcribe.add_argument(
        "--condition-on-previous-text",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    transcribe.add_argument(
        "--hallucination-silence-threshold",
        type=float,
        default=2.0,
        help="疑似幻觉前后的静音跳过阈值（秒）；设为 0 关闭",
    )

    transcribe.add_argument("--qwen-model", default=os.getenv("QWEN_ASR_MODEL", DEFAULT_QWEN_MODEL))
    transcribe.add_argument(
        "--doubao-resource-id",
        default=os.getenv("VOLC_SPEECH_RESOURCE_ID", DEFAULT_DOUBAO_RESOURCE_ID),
    )
    transcribe.add_argument(
        "--diarization", action=argparse.BooleanOptionalAction, default=True
    )
    transcribe.add_argument("--speaker-count", type=int, default=0)
    transcribe.add_argument("--language-hint", action="append", default=[])
    transcribe.add_argument("--hotword", action="append", default=[])
    transcribe.add_argument("--poll-seconds", type=int, default=5)
    transcribe.add_argument("--timeout-hours", type=int, default=6)
    transcribe.add_argument(
        "--delete-remote", action=argparse.BooleanOptionalAction, default=True
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "inventory":
            return inventory_command(args)
        return transcribe_command(args)
    except (ConfigError, TranscriberError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"运行失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
