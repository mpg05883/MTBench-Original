"""Answer the prompts of an evaluation run through Azure's Batch API.

A batch is one file of requests that Azure finishes within 24 hours at a lower
price. `batch_answers` submits all prompts of a run, keeps the batch id in
`batch_state.json` inside the run's save folder so that running the same
command again resumes instead of paying twice, and returns one answer (or
error) per sample, in sample order.

Ported from the `mtbench.models.batch` module of the refactored MTBench repo,
trimmed to the Azure backend. Request settings match `send_to_openai_chatgpt`
(GPT-5.1 with no token limit, and a seed only when AZURE_SEED is set), so a
batch answers like the synchronous call does.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

STATE_FILE = "batch_state.json"
INPUT_FILE = "batch_input.jsonl"
BATCH_MODELS = ("gpt-4o", "gpt-4o-mini", "gpt-5.1")
DONE_STATES = {"completed"}
FAILED_STATES = {"failed", "expired", "cancelled"}


class BatchPending(RuntimeError):
    """The batch is submitted but not finished; run the same command again
    later to collect it."""


class BatchError(RuntimeError):
    """The batch failed, expired or was cancelled, or its saved state does not
    match the prompts."""


def clean_answer(text):
    """Strip an answer and remove its double quotes, as the scripts do."""
    return text.strip().replace('"', '')


def batch_body(prompt):
    """Build the `body` of one batch line.

    A batch needs a batch-type deployment, so the name comes from
    AZURE_BATCH_DEPLOYMENT_GPT_5_1 (default "gpt-5.1-global-batch").
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    deployment = (
        os.environ.get("AZURE_BATCH_DEPLOYMENT_GPT_5_1")
        or "gpt-5.1-global-batch"
    )
    body = {
        "model": deployment,
        "messages": [{"role": "user", "content": prompt}],
    }
    seed = os.environ.get("AZURE_SEED")
    if seed:
        body["seed"] = int(seed)
    return body


class AzureBatchBackend:
    """The OpenAI Batch API on the Azure Foundry endpoint."""

    def __init__(self, client=None):
        self._client = client

    @property
    def client(self):
        if self._client is None:
            from evaluation.api_call import _azure_client
            self._client = _azure_client()
        return self._client

    def submit(self, requests):
        """Upload the request lines and start the batch."""
        payload = "\n".join(json.dumps(line) for line in requests) + "\n"
        uploaded = self.client.files.create(
            file=(INPUT_FILE, payload.encode("utf-8")),
            purpose="batch",
        )
        batch = self.client.batches.create(
            input_file_id=uploaded.id,
            endpoint="/chat/completions",
            completion_window="24h",
        )
        return {"batch_id": batch.id, "input_file_id": uploaded.id}

    def poll(self, state):
        """Return the batch status and the state with its output file ids."""
        batch = self.client.batches.retrieve(state["batch_id"])
        update = {
            **state,
            "output_file_id": getattr(batch, "output_file_id", None),
            "error_file_id": getattr(batch, "error_file_id", None),
        }
        return batch.status, update

    def collect(self, state):
        """Read the output and error files into {custom_id: answer or error}."""
        results = {}
        for key in ("output_file_id", "error_file_id"):
            file_id = state.get(key)
            if not file_id:
                continue
            text = self.client.files.content(file_id).text
            for line in text.splitlines():
                if line.strip():
                    custom_id, value = _parse_line(json.loads(line))
                    results.setdefault(custom_id, value)
        return results


def _parse_line(line):
    """Turn one output line into its custom id and the answer or error."""
    custom_id = line["custom_id"]
    response = line.get("response") or {}
    if line.get("error") or response.get("status_code") != 200:
        detail = line.get("error") or response.get("body")
        return custom_id, BatchError(f"Batch request failed: {detail}")
    try:
        message = response["body"]["choices"][0]["message"]
        return custom_id, clean_answer(message["content"])
    except (KeyError, IndexError, TypeError, AttributeError) as e:
        return custom_id, BatchError(f"Unreadable batch answer: {e!r}")


def build_requests(prompts):
    """One batch line per prompt (custom id = prompt index)."""
    return [
        {
            "custom_id": str(idx),
            "method": "POST",
            "url": "/chat/completions",
            "body": batch_body(prompt),
        }
        for idx, prompt in enumerate(prompts)
    ]


def _prompt_hashes(prompts):
    return [hashlib.sha256(p.encode("utf-8")).hexdigest() for p in prompts]


def run_batch(model, prompts, work_dir, wait=False, poll_seconds=60,
              backend=None):
    """Submit the prompts as a batch, or resume the saved one, and collect the
    answers.

    Args:
        model: The model name, kept in the state to detect a changed run.
        prompts: The prompt strings.
        work_dir: Folder for `batch_state.json` and the request file. A saved
            batch there is reused, never submitted again.
        wait: Poll until the batch finishes instead of raising BatchPending.
        poll_seconds: Seconds between polls.
        backend: A backend object; defaults to AzureBatchBackend().

    Returns:
        Per prompt, in order, the cleaned answer or the error of that request.

    Raises:
        BatchPending: If the batch is not finished and `wait` is False.
        BatchError: If the batch failed or expired, or the saved batch was
            made from other prompts or another model.
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    state_path = work_dir / STATE_FILE
    hashes = _prompt_hashes(prompts)
    backend = backend or AzureBatchBackend()

    if state_path.exists():
        state = json.loads(state_path.read_text())
        if state.get("model") != model or state.get("prompts") != hashes:
            raise BatchError(
                f"{state_path} was made from other prompts or another model. "
                f"Delete it to submit a new batch."
            )
        print(f"Resuming batch {state['batch_id']}")
    else:
        requests = build_requests(prompts)
        (work_dir / INPUT_FILE).write_text(
            "\n".join(json.dumps(r) for r in requests) + "\n"
        )
        state = {**backend.submit(requests), "model": model, "prompts": hashes}
        _save_state(state, state_path)
        print(f"Submitted batch {state['batch_id']} ({len(prompts)} requests)")

    while True:
        status, state = backend.poll(state)
        state["status"] = status
        _save_state(state, state_path)
        if status in DONE_STATES:
            break
        if status in FAILED_STATES:
            raise BatchError(f"Batch {state['batch_id']} {status}.")
        if not wait:
            raise BatchPending(f"Batch {state['batch_id']} is {status}.")
        time.sleep(poll_seconds)

    collected = backend.collect(state)
    missing = BatchError("The batch has no output line for this request.")
    return [collected.get(str(idx), missing) for idx in range(len(prompts))]


def _save_state(state, path):
    with open(path, "w") as f:
        json.dump(state, f, indent=4)


def add_batch_args(parser):
    """Add `--batch`, `--wait` and `--poll-seconds` to an argument parser."""
    parser.add_argument(
        "--batch", action="store_true",
        help="Use Azure's Batch API (about half the price, up to 24 h). The "
        "first call submits and stops; run the same command again to collect "
        "the answers.",
    )
    parser.add_argument(
        "--wait", action="store_true",
        help="With --batch, poll until the batch finishes instead of "
        "stopping.",
    )
    parser.add_argument(
        "--poll-seconds", type=float, default=60,
        help="With --batch --wait, seconds between polls (default: 60).",
    )


def batch_answers(args, samples, build_prompt, save_path, backend=None):
    """Get the answer of every sample from the Batch API.

    Args:
        args: Parsed arguments with `batch`, `wait`, `poll_seconds`, `model`.
        samples: The samples of the run.
        build_prompt: Builds a sample's prompt. An exception here leaves that
            sample out of the batch and is returned in its place.
        save_path: The run's save folder (holds `batch_state.json`).
        backend: A backend object, for tests.

    Returns:
        None if `--batch` was not given. Otherwise, per sample, the cleaned
        answer or an Exception; pass each to `take`.

    Exits with status 0 (after printing a message) if the batch is not
    finished and `--wait` was not given.
    """
    if not args.batch:
        return None
    if args.model not in BATCH_MODELS:
        raise NotImplementedError(
            f"--batch supports {BATCH_MODELS}, not {args.model!r}."
        )

    prompts = []
    for sample in samples:
        try:
            prompts.append(build_prompt(sample))
        except Exception as e:
            prompts.append(e)
    ready = [i for i, p in enumerate(prompts) if isinstance(p, str)]

    try:
        answers = run_batch(
            args.model,
            [prompts[i] for i in ready],
            save_path,
            wait=args.wait,
            poll_seconds=args.poll_seconds,
            backend=backend,
        ) if ready else []
    except BatchPending as e:
        print(f"{e} Run the same command again to collect the answers.")
        sys.exit(0)

    result = list(prompts)
    for i, answer in zip(ready, answers):
        result[i] = answer
    return result


def take(item):
    """Return a batch answer, or raise it if it is an error."""
    if isinstance(item, Exception):
        raise item
    return item
