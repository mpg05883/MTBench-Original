import argparse
from pathlib import Path
import json
from datetime import datetime
import sys
sys.path.append("../..")
import os
from meta_prompt import  temperature_trend_metaprompt_generation, decode_temperature_trend_prediction
from evaluation.utils import (
    save_to_json,
    calculate_acc,
    compute_temperature_trend
)
from evaluation.api_call import (
    AZURE_CHAT_MODELS,
    send_to_openai_chatgpt,
    send_to_openai_o1,
    send_to_deepseek,
    send_to_deepseek_r1,
    send_to_anthropic_claude,
    send_to_google_gemini,
    send_to_llama
)

from evaluation.subsets import dataset_files
from evaluation.batch import add_batch_args, batch_answers, take

parser = argparse.ArgumentParser()
parser.add_argument("--subset_file", help="JSON filename list from make_parity_subsets.py")
parser.add_argument(
    "--dataset_folder", type=str, default="", help=""
)
parser.add_argument(
    "--save_path", type=str, default="out-sampled", help=""
)

parser.add_argument(
    "--model",  type=str, default="gpt-4o", help=""
)
parser.add_argument(
    "--mode",
    type=str,
    default="combined",
    help="choose from timeseries_only, text_only, combined",
)
parser.add_argument("--in_days", type=int, default=7, help="Input days")
parser.add_argument("--out_days", type=int, default=1, help="Output days")
parser.add_argument("--past_future", type=str, default="past", help="past trend analysis or future trend prediction")
parser.add_argument(
    "--limit", type=int, default=None,
    help="Evaluate only the first N samples (for a quick smoke test)",
)
add_batch_args(parser)
args = parser.parse_args()

directory_path = Path(args.dataset_folder)

data_list = []

if args.model == "llama":
    import transformers
    import torch
    pipeline = transformers.pipeline(
        "text-generation",
        model="meta-llama/Meta-Llama-3.1-8B-Instruct",
        model_kwargs={"torch_dtype": torch.bfloat16},
        device_map="auto",
    )

# Loop through all JSON files in the directory
for json_file in dataset_files(directory_path, args.subset_file):
    with open(json_file, 'r') as file:
        data = json.load(file)
        
        extracted_data = {
            "filename": json_file.name,
            "input_window": data.get("input_window"),
            "output_window": data.get("output_window"),
            "text": data.get("text"),
            "input_timestamps": data.get("input_timestamps"),
        }
        data_list.append(extracted_data)

if args.limit is not None:
    data_list = data_list[:args.limit]

os.makedirs(Path(args.save_path).parent, exist_ok=True)
result_list = []
tot_samples = len(data_list)
print("Evaluating {} samples......".format(tot_samples))


def build_prompt(sample):
    return temperature_trend_metaprompt_generation(
        text=sample["text"],
        past_temperatures=sample["input_window"],
        start_datetime=sample["input_timestamps"][0],
        end_datetime=sample["input_timestamps"][-1],
        granularity="hourly",
        past_days=args.in_days,
        next_days=args.out_days,
        mode=args.mode,
        past_future=args.past_future
    )


batched = batch_answers(args, data_list, build_prompt, args.save_path)

for idx, sample in enumerate(data_list):
    filename = sample["filename"]
    output_ts = sample["output_window"]

    designed_prompt = build_prompt(sample)
    try:
        if batched is not None:
            answer = take(batched[idx])
        elif args.model in AZURE_CHAT_MODELS:
            response = send_to_openai_chatgpt(designed_prompt, model=args.model, max_tokens=None)
            answer = response.content.strip().replace('"', '')
        elif args.model == "sonnet":
            response = send_to_anthropic_claude(designed_prompt)
            answer = response.strip().replace('"', '')
        elif args.model == "llama":
            response = send_to_llama(designed_prompt, pipeline=pipeline)
            answer = response.strip().replace('"', '')
        elif args.model == "gemini":
            response = send_to_google_gemini(designed_prompt)
            answer = response.strip().replace('"', '')
        elif args.model == "deepseek":
            response = send_to_deepseek(designed_prompt)
            answer = response.strip().replace('"', '')
        elif args.model == "o1":
            response = send_to_openai_o1(designed_prompt)
            answer = response.content.strip().replace('"', '')
        elif args.model == "r1":
            response = send_to_deepseek_r1(designed_prompt)
            answer = response.content.strip().replace('"', '')
        else:
            raise NotImplementedError("This api is not supported")
        
    
        # print(answer)
        if args.past_future == "past":
            gt = compute_temperature_trend(sample["input_window"])
        else:
            gt = compute_temperature_trend(sample["input_window"],sample["output_window"])
        predict = decode_temperature_trend_prediction(answer)
        res = {
            "cnt": len(result_list),
            "filename": sample["filename"], 
            "ground_truth": gt, 
            "predict": predict,
            "answer": answer
        }
        result_list.append(res)
        accuracy = calculate_acc(result_list)
        result_list[-1]["accumulated_acc"] = accuracy
        print("{}/{}: ground_truth: {}; predicted: {}.".format(idx, tot_samples, gt, predict))

    except Exception as e:
        # Handle the exception and print the error message
        print(f"An error occurred: {type(e).__name__}: {e}")
    
    if (idx +1) % 20 == 0:
        save_to_json(result_list, save_path=f"{args.save_path}/results.json")


if result_list:
    final_acc = result_list[-1]["accumulated_acc"]
    print("Final Accuracy: {:.4f}%".format(final_acc*100))
else:
    print("No sample was answered; see the errors above.")


save_to_json(result_list, save_path=f"{args.save_path}/results.json")
print(f"Processing complete. Results saved to {args.save_path}/results.json")

