# Models

The models that the evaluation code (`src/mtbench/eval/`) can call, in `mtbench.models.api.MODELS`. Nothing is trained
or fine-tuned yet. All calls send one user message and read back the text (`get_answer`).

## Original models (ported, unchanged)

`gpt-4o`, `gpt-4o-mini`, `o1` (OpenAI API, key `OPENAI_API_KEY`), `sonnet` (Anthropic), `gemini` (Google),
`deepseek` and `r1` (SiliconFlow), and `llama` (a local `meta-llama/Meta-Llama-3.1-8B-Instruct` Hugging Face pipeline
from `load_llama_pipeline`; needs about 16 GB of GPU memory in bfloat16 and `HF_TOKEN`). These keep the original
decoding parameters (OpenAI chat default `temperature=0.7`, no seed), which is why the parity experiment does not use
them. Details are in `src/mtbench/models/api.py` and `docs/code_provenance.md`.

## Azure models (added for the refactor evaluation parity experiment)

Called through Azure AI Foundry's OpenAI-compatible endpoint with `send_to_azure` (`AZURE_MODELS` in `api.py`). The
client is `OpenAI(api_key=$AZURE_FOUNDRY_API_KEY, base_url=$OPENAI_BASE_URL)`; the `model` argument is the deployment
name.

| `MODELS` key | Deployment (env var, default) | Thinking / reasoning | Decoding |
| --- | --- | --- | --- |
| `azure-qwen3-8b` | `AZURE_DEPLOYMENT_QWEN3_8B`, `qwen3-8b` | thinking off via `chat_template_kwargs.enable_thinking=false` (unchecked) | `temperature` 0, `top_p` 1, `seed` 42, `max_tokens` 4096 |
| `azure-gpt-4o` | `AZURE_DEPLOYMENT_GPT_4O`, `gpt-4o` | none | same |
| `azure-gpt-5.1` | `AZURE_DEPLOYMENT_GPT_5_1`, `gpt-5.1-global-batch` | default reasoning effort (paper setup) | `seed` 42, `max_completion_tokens` 16384; no `temperature` or `top_p` |
| `azure-llama-3.1-8b` | `AZURE_DEPLOYMENT_LLAMA_3_1_8B`, `llama-3.1-8b-instruct` | none | `temperature` 0, `top_p` 1, `seed` 42, `max_tokens` 4096 |

- The first call of each deployment logs the deployment name and the response's `system_fingerprint`.
- Request timeouts: 120 s, and 900 s for the reasoning model.
- API calls are only best-effort deterministic (the writeup measures this by repeating 30 items per cell twice).
- `OPENAI_BASE_URL` is also read by the `openai` SDK itself, so with it set the plain OpenAI models above go to the same
  endpoint. Unset it (or use a separate `.env`) to call the OpenAI API directly.

**TODO (unconfirmed, ask the user):** the exact Azure deployment names, model versions and API version behind each row
(the defaults above are guesses); whether the Qwen3 and Llama deployments accept `seed`, `top_p` and the thinking-off
field; the reasoning effort of the GPT-5.1 deployment; the model sizes the paper used (not stated).
