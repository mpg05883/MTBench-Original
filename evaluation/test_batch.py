"""Tests for evaluation/batch.py with a fake Azure client.

Run from the repo root: python -m unittest evaluation.test_batch
"""

import argparse
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from evaluation.batch import (
    STATE_FILE,
    AzureBatchBackend,
    BatchError,
    BatchPending,
    add_batch_args,
    batch_answers,
    batch_body,
    run_batch,
    take,
)


class FakeClient:
    """Mimics the parts of the OpenAI client the backend uses."""

    def __init__(self, statuses=("completed",), output_lines=None):
        self.statuses = list(statuses)
        self.output_lines = output_lines
        self.created = 0
        self.uploaded = None
        self.files = SimpleNamespace(create=self._upload, content=self._content)
        self.batches = SimpleNamespace(create=self._create, retrieve=self._get)

    def _upload(self, file, purpose):
        self.uploaded = file[1].decode("utf-8")
        return SimpleNamespace(id="file-in")

    def _create(self, input_file_id, endpoint, completion_window):
        self.created += 1
        return SimpleNamespace(id="batch-1")

    def _get(self, batch_id):
        status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        return SimpleNamespace(
            status=status, output_file_id="file-out", error_file_id=None
        )

    def _content(self, file_id):
        lines = self.output_lines
        if lines is None:
            lines = [ok(i, f' "answer {i}" ') for i in range(2)]
        return SimpleNamespace(text="\n".join(json.dumps(x) for x in lines))


def ok(idx, text):
    return {
        "custom_id": str(idx),
        "response": {
            "status_code": 200,
            "body": {"choices": [{"message": {"content": text}}]},
        },
    }


class RunBatchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def test_submit_and_collect(self):
        client = FakeClient()
        answers = run_batch(
            "gpt-5.1", ["p0", "p1"], self.dir, backend=AzureBatchBackend(client)
        )
        self.assertEqual(answers, ["answer 0", "answer 1"])
        lines = [json.loads(x) for x in client.uploaded.splitlines()]
        self.assertEqual([x["custom_id"] for x in lines], ["0", "1"])
        self.assertEqual(lines[0]["body"]["messages"][0]["content"], "p0")
        self.assertNotIn("max_completion_tokens", lines[0]["body"])
        self.assertTrue((self.dir / STATE_FILE).exists())

    def test_pending_then_resume_without_resubmitting(self):
        client = FakeClient(statuses=["in_progress", "completed"])
        backend = AzureBatchBackend(client)
        with self.assertRaises(BatchPending):
            run_batch("gpt-5.1", ["p0", "p1"], self.dir, backend=backend)
        answers = run_batch("gpt-5.1", ["p0", "p1"], self.dir, backend=backend)
        self.assertEqual(answers, ["answer 0", "answer 1"])
        self.assertEqual(client.created, 1)

    def test_changed_prompts_raise(self):
        backend = AzureBatchBackend(FakeClient())
        run_batch("gpt-5.1", ["p0", "p1"], self.dir, backend=backend)
        with self.assertRaises(BatchError):
            run_batch("gpt-5.1", ["p0", "other"], self.dir, backend=backend)

    def test_failed_batch_raises(self):
        backend = AzureBatchBackend(FakeClient(statuses=["expired"]))
        with self.assertRaises(BatchError):
            run_batch("gpt-5.1", ["p0"], self.dir, backend=backend)

    def test_error_line_and_missing_line_become_errors(self):
        bad = {"custom_id": "0", "error": {"message": "boom"}}
        client = FakeClient(output_lines=[bad])
        answers = run_batch(
            "gpt-5.1", ["p0", "p1"], self.dir, backend=AzureBatchBackend(client)
        )
        self.assertIsInstance(answers[0], BatchError)
        self.assertIsInstance(answers[1], BatchError)
        with self.assertRaises(BatchError):
            take(answers[0])


class BatchAnswersTest(unittest.TestCase):
    def args(self, **kw):
        parser = argparse.ArgumentParser()
        parser.add_argument("--model", default="gpt-5.1")
        add_batch_args(parser)
        return parser.parse_args([f"--{k}={v}" if v is not True else f"--{k}"
                                  for k, v in kw.items()])

    def test_off_returns_none(self):
        self.assertIsNone(batch_answers(self.args(), [1], str, "unused"))

    def test_unsupported_model(self):
        with self.assertRaises(NotImplementedError):
            batch_answers(self.args(batch=True, model="sonnet"), [1], str, "x")

    def test_prompt_error_is_returned_in_place(self):
        def build(sample):
            if sample == 1:
                raise ValueError("bad sample")
            return f"p{sample}"

        with tempfile.TemporaryDirectory() as tmp:
            client = FakeClient()
            result = batch_answers(
                self.args(batch=True), [0, 1, 2], build, tmp,
                backend=AzureBatchBackend(client),
            )
        self.assertEqual(result[0], "answer 0")
        self.assertIsInstance(result[1], ValueError)
        self.assertEqual(result[2], "answer 1")

    def test_pending_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = FakeClient(statuses=["in_progress"])
            with self.assertRaises(SystemExit) as cm:
                batch_answers(
                    self.args(batch=True), [0], str, tmp,
                    backend=AzureBatchBackend(client),
                )
        self.assertEqual(cm.exception.code, 0)


class SeedAndDeploymentTest(unittest.TestCase):
    def test_batch_body_has_no_seed_by_default(self):
        with mock.patch.dict(os.environ, {"AZURE_SEED": ""}):
            self.assertNotIn("seed", batch_body("p"))

    def test_batch_body_sends_seed(self):
        with mock.patch.dict(os.environ, {"AZURE_SEED": "42"}):
            self.assertEqual(batch_body("p")["seed"], 42)

    def test_deployment_per_model(self):
        from evaluation.api_call import _azure_deployment
        env = {
            "AZURE_DEPLOYMENT_GPT_5_1": "dep-5.1",
            "AZURE_DEPLOYMENT_GPT_5_4_MINI": "dep-mini",
        }
        with mock.patch.dict(os.environ, env):
            self.assertEqual(_azure_deployment("gpt-5.4-mini"), "dep-mini")
            self.assertEqual(_azure_deployment("gpt-5.1"), "dep-5.1")
            self.assertEqual(_azure_deployment("gpt-4o"), "dep-5.1")


if __name__ == "__main__":
    unittest.main()
