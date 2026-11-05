import argparse
from pathlib import Path
import json
from datetime import datetime
import sys
sys.path.append("../..")
import os
from meta_prompt import finance_classification_metaprompt_generation, parse_cls_response
from evaluation.utils import (
    save_to_json,
    calculate_acc
)
from evaluation.api_call import (
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
        if isinstance(data.get('trend').get('output_bin_label'), str) is False:
            continue
        
        extracted_data = {
            "filename": json_file.name,
            "index": int(json_file.name.split('_')[0]),
            "input_timestamps": data.get("input_timestamps"),
            "input_window": data.get("input_window"),
            "output_timestamps": data.get("output_timestamps"),
            "output_window": data.get("output_window"),
            "percentage_change": data.get('trend').get("output_percentage_change"),
            "bin_label": data.get('trend').get('output_bin_label'),
            "text": data.get("text").get("content"),
            "timestamp_ms": datetime.utcfromtimestamp(data.get("text").get("timestamp_ms", 0) / 1000) if "timestamp_ms" in data else None
        }
        data_list.append(extracted_data)

if args.limit is not None:
    data_list = data_list[:args.limit]

os.makedirs(Path(args.save_path).parent, exist_ok=True)
result_list = []
tot_samples = len(data_list)
print("Evaluating {} samples......".format(tot_samples))


def build_prompt(sample):
    datetime_list = [
        datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S') for s in sample['input_timestamps']
    ]

    text = sample['text']
    prices = sample['input_window']

    return finance_classification_metaprompt_generation(
        text=text,
        timestamps=datetime_list,
        prices=prices,
        mode=args.mode
    )


batched = batch_answers(args, data_list, build_prompt, args.save_path)

for idx, sample in enumerate(data_list):
    designed_prompt = build_prompt(sample)
    try:
        if batched is not None:
            answer = take(batched[idx])
        elif args.model in ["gpt-4o", "gpt-4o-mini", "gpt-5.1", "gpt-5.4-mini"]:
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
        gt = sample['bin_label']
        predict = parse_cls_response(answer)
        res = {
            "cnt": len(result_list),
            "filename": sample["filename"], 
            "ground_truth": gt, 
            "predict": predict,
            "answer": answer
        }
        result_list.append(res)
        acc_5way = calculate_acc(result_list)
        acc_3way = calculate_acc(
            result_list, 
            regrouped_labels={
                "<-4%": 'negtive',
                "-2% ~ -4%": 'negtive',
                "-2% ~ +2%": 'neutral',
                "+2% ~ +4%": 'positive',
                ">+4%": 'positive'
                }
            )
        result_list[-1]["accumulated_acc_5way"] = acc_5way
        result_list[-1]["accumulated_acc_3way"] = acc_3way
        print("{}/{}: ground_truth: {}; predicted: {}.".format(idx, tot_samples, gt, predict))

    except Exception as e:
        # Handle the exception and print the error message
        print(f"An error occurred: {type(e).__name__}: {e}")
    
    if (idx +1) % 20 == 0:
        save_to_json(result_list, save_path=f"{args.save_path}/results.json")


if result_list:
    final_acc_5way = result_list[-1]["accumulated_acc_5way"]
    final_acc_3way = result_list[-1]["accumulated_acc_3way"]
    print("Final results: 5-way-acc {:.4f}%, 3-way-acc {:.4f}%".format(final_acc_5way*100, final_acc_3way*100))
else:
    print("No sample was answered; see the errors above.")


save_to_json(result_list, save_path=f"{args.save_path}/results.json")
print(f"Processing complete. Results saved to {args.save_path}/results.json")

