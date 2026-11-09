import os

from dotenv import load_dotenv
from openai import OpenAI, AzureOpenAI
import anthropic

load_dotenv()

# Add your own API keys here
ANTHROPIC_API_KEY=""
GOOGLE_GEMINI_API = ""
DEEPSEEK_API = ""


def _azure_client():
    endpoint = os.environ["OPENAI_BASE_URL"]
    # A v1 endpoint (https://<resource>.openai.azure.com/openai/v1/) takes the
    # plain OpenAI client with no api-version; AzureOpenAI would add its own
    # /openai/deployments/... path to it and get a 404.
    if endpoint.rstrip("/").endswith("/openai/v1"):
        return OpenAI(api_key=os.environ["AZURE_FOUNDRY_API_KEY"], base_url=endpoint)
    return AzureOpenAI(
        api_key=os.environ["AZURE_FOUNDRY_API_KEY"],
        azure_endpoint=os.environ["OPENAI_BASE_URL"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    )

# Model names the evaluation scripts send to `send_to_openai_chatgpt`.
AZURE_CHAT_MODELS = ("gpt-4o", "gpt-4o-mini", "gpt-5.1", "gpt-5.4-mini")

# Model name -> env var holding its Azure deployment name. Models not listed
# here fall back to the GPT-5.1 deployment.
AZURE_DEPLOYMENT_ENV = {
    "gpt-5.1": "AZURE_DEPLOYMENT_GPT_5_1",
    "gpt-5.4-mini": "AZURE_DEPLOYMENT_GPT_5_4_MINI",
}


def _azure_deployment(model):
    """Return the Azure deployment name for a model."""
    var = AZURE_DEPLOYMENT_ENV.get(model, "AZURE_DEPLOYMENT_GPT_5_1")
    return os.environ[var]


def azure_seed():
    """Return AZURE_SEED as an int, or None when it is not set."""
    value = os.environ.get("AZURE_SEED")
    return int(value) if value else None


def send_to_openai_chatgpt(content, model="gpt-4", max_tokens=100, temperature=0.7, timeout=30):
    # On Azure, `model` selects the deployment (see AZURE_DEPLOYMENT_ENV).
    # `temperature` is ignored since GPT-5.x only supports the default.
    # Set AZURE_SEED to send a seed with every request.
    client = _azure_client()

    kwargs = {}
    if max_tokens is not None:
        kwargs["max_completion_tokens"] = max_tokens
    seed = azure_seed()
    if seed is not None:
        kwargs["seed"] = seed
    response = client.chat.completions.create(
        model=_azure_deployment(model),
        messages=[{"role": "user", "content": content}],
        timeout=timeout,
        **kwargs
    )
    return response.choices[0].message

def send_to_anthropic_claude(content, model = "claude-3-5-sonnet-20241022"):
    client = anthropic.Anthropic(
        # defaults to os.environ.get("ANTHROPIC_API_KEY")
        api_key=ANTHROPIC_API_KEY,
    )
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[
            {"role": "user", "content": content}
        ]
    )
    return message.content[0].text

def send_to_google_gemini(content):
    # Imported here so the other models work without the Gemini SDK installed.
    # genai.Client is the google-genai SDK (pip install google-genai).
    from google import genai

    client = genai.Client(api_key=GOOGLE_GEMINI_API)

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=content,
    )
    return response.candidates[0].content.parts[0].text  # Extract the text output

def send_to_deepseek(content):
    client = OpenAI(api_key=DEEPSEEK_API, base_url='https://api.siliconflow.cn/v1/')
    response = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V3",
        messages=[
            {"role": "user", "content": content},
    ],
        max_tokens=4096,
        stream=False
    )

    return response.choices[0].message.content

def send_to_deepseek_r1(content):
    client = OpenAI(api_key=DEEPSEEK_API, base_url='https://api.siliconflow.cn/v1/')

    response = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-R1",
        messages=[
            {"role": "user", "content": content},
    ],
        max_tokens=4096,
        stream=False
    )

    return response.choices[0].message.content

def send_to_openai_o1(content):
    client = _azure_client()
    # Prepare the request
    response = client.chat.completions.create(
        model=os.environ["AZURE_DEPLOYMENT_GPT_5_1"],
        messages=[{"role": "user", "content": content}],
        timeout=30
    )
    return response.choices[0].message

def send_to_llama(content, pipeline = None):
    messages = [
        {"role": "user", "content": content},
    ]
    outputs = pipeline(
        messages,
        max_new_tokens=1024,
    )

    return outputs[0]["generated_text"][-1]["content"]


