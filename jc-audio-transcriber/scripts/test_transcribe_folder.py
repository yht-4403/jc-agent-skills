import importlib.util
import sys
import tempfile
import unittest
import wave
from argparse import Namespace
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("transcribe_folder.py")
SPEC = importlib.util.spec_from_file_location("transcribe_folder", MODULE_PATH)
assert SPEC and SPEC.loader
transcriber = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = transcriber
SPEC.loader.exec_module(transcriber)


def write_silent_wav(path: Path, seconds: float = 1.0) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\0\0" * int(16000 * seconds))


class InventoryTests(unittest.TestCase):
    def test_discovers_only_audio_and_orders_by_filename_time(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            late = root / "TX00_MIC002_20260820_000000_orig.wav"
            early = root / "TX00_MIC001_20260819_230000_orig.wav"
            write_silent_wav(late)
            write_silent_wav(early)
            write_silent_wav(root / "._TX00_MIC000_20260819_220000_orig.wav")
            (root / "完整转写稿.txt").write_text("旧结果", encoding="utf-8")
            items = transcriber.discover_audio_files(root)
        self.assertEqual([item.path.name for item in items], [early.name, late.name])

    def test_reads_wav_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.wav"
            write_silent_wav(path, 1.5)
            duration = transcriber.probe_duration(path)
        self.assertAlmostEqual(duration, 1.5, places=2)

    def test_zero_frame_wav_is_empty_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.wav"
            write_silent_wav(path, 0)
            self.assertTrue(transcriber.is_empty_audio(path, 0.0))
            self.assertEqual(transcriber.wav_frame_count(path), 0)

    def test_empty_asr_reshape_error_is_recognized(self):
        exc = RuntimeError(
            "cannot reshape tensor of 0 elements into shape [-1, 0] because "
            "the unspecified dimension size -1 can be any value and is ambiguous"
        )
        self.assertTrue(transcriber.is_empty_asr_error(exc))
        self.assertFalse(transcriber.is_empty_asr_error(RuntimeError("CUDA OOM")))


class FormattingTests(unittest.TestCase):
    def test_formats_local_segments(self):
        payload = {"segments": [{"start": 65.2, "text": " 你好 "}]}
        self.assertEqual(transcriber.format_local_result(payload), "[00:01:05] 你好\n")

    def test_formats_funasr_sentence_info(self):
        payload = transcriber.funasr_payload(
            [
                {
                    "text": "你好世界",
                    "sentence_info": [
                        {"start": 1200, "text": "你好"},
                        {"start": 3100, "sentence": "世界"},
                    ],
                }
            ]
        )
        self.assertEqual(
            transcriber.format_local_result(payload),
            "[00:00:01] 你好\n[00:00:03] 世界\n",
        )

    def test_formats_doubao_utterances(self):
        payload = {
            "result": {
                "text": "用那个金蝶的",
                "utterances": [
                    {"start_time": 87000, "text": "用那个金蝶的"},
                    {
                        "start_time": 91000,
                        "text": "然后 hr 的，用北森的",
                        "additions": {"speaker": "1"},
                    },
                ],
            }
        }
        self.assertEqual(
            transcriber.format_doubao_result(payload),
            "[00:01:27] 用那个金蝶的\n[00:01:31] 说话人 1：然后 hr 的，用北森的\n",
        )

    def test_formats_qwen_speakers(self):
        payload = {
            "transcripts": [
                {
                    "sentences": [
                        {"begin_time": 1200, "speaker_id": 0, "text": "开始吧"},
                        {"begin_time": 3100, "speaker_id": 1, "text": "好"},
                    ]
                }
            ]
        }
        self.assertEqual(
            transcriber.format_qwen_result(payload),
            "[00:00:01] 说话人 1：开始吧\n[00:00:03] 说话人 2：好\n",
        )


class QualityTests(unittest.TestCase):
    def test_detects_repetition_after_removing_timestamps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio_path = root / "TX00_MIC001_20260820_000000_orig.wav"
            fragment_path = root / "fragment.txt"
            write_silent_wav(audio_path, 10)
            fragment_path.write_text(
                "\n".join(
                    f"[00:00:{second:02d}] 我看你很久了" for second in range(6)
                ),
                encoding="utf-8",
            )
            item = transcriber.AudioItem(
                path=audio_path,
                recorded_at=None,
                duration_seconds=10,
            )
            report = transcriber.build_quality_report(
                root,
                [item],
                [{"status": "completed", "fragment_path": str(fragment_path)}],
                "local",
                "test-model",
                root / "complete.txt",
            )
        self.assertIn("疑似循环重复", report["files"][0]["warnings"])

    def test_qwen_request_keeps_full_words_and_diarization(self):
        args = Namespace(
            qwen_model="qwen-audio-3.0-asr-flash-filetrans",
            diarization=True,
            speaker_count=2,
            language_hint=["zh", "en"],
            hotword=["BOSS直聘=5"],
        )
        body = transcriber.qwen_request_body(args, "https://example.com/audio.wav")
        parameters = body["parameters"]
        self.assertTrue(parameters["diarization_enabled"])
        self.assertEqual(parameters["speaker_count"], 2)
        self.assertFalse(parameters["special_word_filter"]["system_reserved_filter"])
        self.assertEqual(parameters["vocabulary"], {"BOSS直聘": 5})


class CacheTests(unittest.TestCase):
    def test_cache_key_is_stable_per_source_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache_root = root / "cache"
            one = transcriber.cache_dir_for(root, cache_root)
            two = transcriber.cache_dir_for(root, cache_root)
        self.assertEqual(one, two)

    def test_local_profile_uses_funasr_nano(self):
        args = transcriber.build_parser().parse_args(
            ["transcribe", "/tmp/example", "--provider", "local"]
        )
        profile = transcriber.profile_for(args)
        self.assertEqual(profile["engine"], "funasr")
        self.assertEqual(profile["model"], "FunAudioLLM/Fun-ASR-Nano-2512")

    def test_default_provider_is_local(self):
        args = transcriber.build_parser().parse_args(["transcribe", "/tmp/example"])
        self.assertEqual(args.provider, "local")

    def test_doubao_profile_uses_flash_resource(self):
        args = transcriber.build_parser().parse_args(
            ["transcribe", "/tmp/example", "--provider", "doubao"]
        )
        profile = transcriber.profile_for(args)
        self.assertEqual(profile["provider"], "doubao")
        self.assertEqual(profile["engine"], "volc-flash")
        self.assertEqual(profile["model"], "bigmodel")
        self.assertEqual(profile["resource_id"], "volc.bigasr.auc_turbo")

    def test_doubao_seed_profile_uses_standard_resource(self):
        args = transcriber.build_parser().parse_args(
            [
                "transcribe",
                "/tmp/example",
                "--provider",
                "doubao",
                "--doubao-resource-id",
                "volc.seedasr.auc",
            ]
        )
        profile = transcriber.profile_for(args)
        self.assertEqual(profile["engine"], "volc-standard")
        self.assertEqual(profile["resource_id"], "volc.seedasr.auc")
        self.assertFalse(transcriber.is_doubao_flash(profile["resource_id"]))

    def test_doubao_request_uses_url_or_data(self):
        args = transcriber.build_parser().parse_args(
            ["transcribe", "/tmp/example", "--provider", "doubao"]
        )
        url_body = transcriber.doubao_request_body(args, file_url="https://example.com/a.wav")
        self.assertEqual(url_body["audio"]["url"], "https://example.com/a.wav")
        self.assertEqual(url_body["request"]["model_name"], "bigmodel")
        data_body = transcriber.doubao_request_body(args, audio_b64="AAAA")
        self.assertEqual(data_body["audio"]["data"], "AAAA")
        self.assertNotIn("url", data_body["audio"])


if __name__ == "__main__":
    unittest.main()
