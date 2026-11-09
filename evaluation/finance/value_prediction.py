import json
import argparse
import numpy as np
from pathlib import Path
from datetime import datetime
import sys
sys.path.append("../..")

from meta_prompt import (
    finance_bb_metaprompt_generation,
    finance_macd_metaprompt_generation,
    finance_mse_metaprompt_generation,
    parse_val_prediction_response,
)

from evaluation.api_call import (
    AZURE_CHAT_MODELS,
    send_to_openai_chatgpt,
    send_to_openai_o1,
    send_to_deepseek,
    send_to_deepseek_r1,
    send_to_anthropic_claude,
    send_to_google_gemini,
)

from evaluation.utils import (
    save_to_json,
    calculate_mape,
    format_time_difference,
    plot_series,
)

from evaluation.subsets import dataset_files
from evaluation.batch import add_batch_args, batch_answers, take

parser = argparse.ArgumentParser()
parser.add_argument("--subset_file", help="JSON filename list from make_parity_subsets.py")
parser.add_argument("--dataset_folder", type=str, required=True, help="Dataset path")
parser.add_argument("--indicator", default="macd", type=str, required=True, help="Dataset path")
parser.add_argument("--save_path", type=str, required=True, help="Results save path")
parser.add_argument("--model", type=str, default="gpt-4o", help="API model")
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

save_path = Path(args.save_path)
details_path = save_path / "output_details"
visualizations_path = save_path / "visualizations"
details_path.mkdir(parents=True, exist_ok=True)
visualizations_path.mkdir(parents=True, exist_ok=True)

data_list = []
directory_path = Path(args.dataset_folder)
for json_file in dataset_files(directory_path, args.subset_file):
    with open(json_file, "r") as file:
        data = json.load(file)
        extracted_data = {
            "filename": json_file.name,
            "input_window": data.get("input_window"),
            "output_window": data.get("output_window"),
            "text": data.get("text").get("content"),
            "input_timestamps": data.get("input_timestamps"),
            "in_macd":data.get("technical").get("in_macd"),
            "out_macd": data.get("technical").get("out_macd"),
            "in_upper_bb": data.get("technical").get("in_upper_bb"),
            "out_upper_bb": data.get("technical").get("out_upper_bb"),
        }
        data_list.append(extracted_data)

if args.limit is not None:
    data_list = data_list[:args.limit]

result_list = []
tot_samples = len(data_list)
print(f"Evaluating {tot_samples} samples...")

epoch_results = []
cumulative_mse, cumulative_mae, cumulative_rmse, cumulative_mape = [], [], [], []


def build_prompt(sample):
    """Return the prompt and the ground-truth series of a sample."""
    datetime_list = [
        datetime.fromtimestamp(s).strftime("%Y-%m-%d %H:%M:%S")
        for s in sample["input_timestamps"]
    ]
    text = sample["text"]
    input_ts = sample["input_window"]

    granularity_string = format_time_difference(
        sample["input_timestamps"][1] - sample["input_timestamps"][0]
    )
    if args.indicator == "macd":
        output_ts = sample["out_macd"]
        designed_prompt = finance_macd_metaprompt_generation(
            text=text,
            prices=input_ts,
            start_datetime=datetime_list[0],
            end_datetime=datetime_list[-1],
            pred_end_datetime=output_ts[-1],
            granularity=granularity_string,
            prediction_length=len(output_ts),
            mode=args.mode,
        )
    elif args.indicator == "bb":
        output_ts = sample["out_upper_bb"]
        designed_prompt = finance_bb_metaprompt_generation(
            text=text,
            prices=input_ts,
            start_datetime=datetime_list[0],
            end_datetime=datetime_list[-1],
            pred_end_datetime=output_ts[-1],
            granularity=granularity_string,
            prediction_length=len(output_ts),
            mode=args.mode,
        )
    elif args.indicator == "time":
        output_ts = sample["output_window"]
        designed_prompt = finance_mse_metaprompt_generation(
            text=text,
            prices=input_ts,
            start_datetime=datetime_list[0],
            end_datetime=datetime_list[-1],
            pred_end_datetime=output_ts[-1],
            granularity=granularity_string,
            prediction_length=len(output_ts),
            mode=args.mode,
        )
    return designed_prompt, output_ts


batched = batch_answers(
    args, data_list, lambda sample: build_prompt(sample)[0], args.save_path
)

for idx, sample in enumerate(data_list):

    try:
        input_ts = sample["input_window"]
        designed_prompt, output_ts = build_prompt(sample)

        if batched is not None:
            answer = take(batched[idx])
        elif args.model in AZURE_CHAT_MODELS:
            response = send_to_openai_chatgpt(designed_prompt, model=args.model, max_tokens=None)
            answer = response.content.strip().replace('"', '')
        elif args.model == "sonnet":
            response = send_to_anthropic_claude(designed_prompt)
            answer = response.strip().replace('"', '')
        elif args.model == "gemini":
            response = send_to_google_gemini(designed_prompt,)
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
        
            
        predict_ts = parse_val_prediction_response(answer)
        predict_ts_orig = predict_ts
        predict_ts = np.interp(
            np.linspace(0, 1, len(output_ts)), np.linspace(0, 1, len(predict_ts)), predict_ts
        )
        
        res = {
            "filename": sample["filename"],
            "response": answer,
            "ground_truth": output_ts,
            "predict": predict_ts.tolist(),
        }
        result_list.append(res)
        
        save_to_json(res, details_path / sample["filename"])
        
        if args.indicator == "macd":
            first_half = sample["in_macd"]
        elif args.indicator == "bb":
            first_half = sample["in_upper_bb"]
        elif args.indicator == "time":
            first_half = sample["input_window"]
        plot_series(sample["filename"], first_half, output_ts, predict_ts_orig, visualizations_path)
        
        mse = np.mean((np.array(output_ts) - np.array(predict_ts)) ** 2)
        
        
        mae = np.mean(np.abs(np.array(output_ts) - np.array(predict_ts)))
        rmse = np.sqrt(mse)
        mape = calculate_mape(output_ts, predict_ts)
        
        if args.indicator == "macd" and mse > 10:
            print(f"{sample['filename']} failed mse ", mse)
            epoch_results.append({
                "filename": sample["filename"],
                "failed": True,
                "epoch": idx + 1,
                "mse": mse,
                "mae": mae,
                "rmse": rmse,
                "mape": mape,
            })
            continue
        
        if args.indicator == "time" and mse > 100:
            print(f"{sample['filename']} failed mse ", mse)
            epoch_results.append({
                "filename": sample["filename"],
                "failed": True,
                "epoch": idx + 1,
                "mse": mse,
                "mae": mae,
                "rmse": rmse,
                "mape": mape,
            })
            continue

        if args.indicator == "bb" and mse > 100:
            print(f"{sample['filename']} failed mse ", mse)
            epoch_results.append({
                "filename": sample["filename"],
                "failed": True,
                "epoch": idx + 1,
                "mse": mse,
                "mae": mae,
                "rmse": rmse,
                "mape": mape,
            })
            continue    
        
        cumulative_mse.append(mse)
        cumulative_mae.append(mae)
        cumulative_rmse.append(rmse)
        cumulative_mape.append(mape)
        
        epoch_results.append({
            "filename": sample["filename"],
            "epoch": idx + 1,
            "mse": mse,
            "mae": mae,
            "rmse": rmse,
            "mape": mape,
            "mean_mse": np.mean(cumulative_mse),
            "mean_mae": np.mean(cumulative_mae),
            "mean_rmse": np.mean(cumulative_rmse),
            "mean_mape": np.mean(cumulative_mape),
        })
        save_to_json(epoch_results, f"{save_path}/epoch_results.json")
        print(
            "{}/{}: mse: {:.4f}, mae: {:.4f}, rmse: {:.4f}".format(
                idx, tot_samples, mse, mae, rmse
            )
        )

        
        # import pdb; pdb.set_trace()
    except Exception as e:
        print(f"Skipping {idx} due to error: {type(e).__name__}: {e}")


# Compute final statistics
summary = {
    "total_samples": len(result_list),
    "mse": np.mean(cumulative_mse),
    "mae": np.mean(cumulative_mae),
    "rmse": np.mean(cumulative_rmse),
    "mape": np.mean(cumulative_mape),
}

save_to_json(summary, f"{save_path}/final_results.json")
print(f"Processing complete. Results saved to {save_path}/final_results.json")
