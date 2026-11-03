import os

import google.generativeai as genai
from dotenv import load_dotenv
from openai import OpenAI, AzureOpenAI
import anthropic

load_dotenv()

# Add your own API keys here
ANTHROPIC_API_KEY=""
GOOGLE_GEMINI_API = ""
DEEPSEEK_API = ""


def _azure_client():
    return AzureOpenAI(
        api_key=os.environ["AZURE_FOUNDRY_API_KEY"],
        azure_endpoint=os.environ["OPENAI_BASE_URL"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    )

def send_to_openai_chatgpt(content, model="gpt-4", max_tokens=100, temperature=0.7, timeout=30):
    # On Azure, `model` is the deployment name; the caller's model/temperature
    # are ignored since GPT-5.x only supports the default temperature.
    client = _azure_client()

    kwargs = {}
    if max_tokens is not None:
        kwargs["max_completion_tokens"] = max_tokens
    response = client.chat.completions.create(
        model=os.environ["AZURE_DEPLOYMENT_GPT_5_1"],
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
            # Configure the API key
    
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


