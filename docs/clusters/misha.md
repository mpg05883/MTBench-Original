# Misha Cluster (Yale YCRC): SLURM Job Submission Reference

Source: https://docs.ycrc.yale.edu/clusters/misha/ (page last updated Sept 30, 2026). Re-check the page for changes.

Misha is a YCRC cluster for projects associated with the Wu Tsai Institute. Jobs are scheduled with Slurm.

## Access
- Needs a YCRC account (request at https://research.computing.yale.edu/account-request).
- Log in via SSH or the Open OnDemand web portal.
- System status / maintenance schedule: https://research.computing.yale.edu/system-status
- Help: https://help.ycrc.yale.edu/

## Submission limits
- **200 job submissions per hour** (see "Rate Limits" in YCRC's Common Job Failures page). Use job arrays (or dSQ) instead of looping `sbatch`.
- Max **4 interactive app instances** (OnDemand) at once. Closing the browser window does NOT end the job; click "Delete" under "My Interactive Apps".

## Default request values (all public partitions)
If not specified, `sbatch`/`salloc` use:

```
--time=01:00:00 --nodes=1 --ntasks=1 --cpus-per-task=1 --mem-per-cpu=5120
```

Default partition is **day**. Requests for `--cpus-per-task` and `--mem` cannot exceed one node's capacity.

**GPU jobs do not get a GPU by default.** You must request one explicitly with `--gpus`.

## Partitions

| Partition | Purpose | Max time | Per-user limits | Per-group limits |
|---|---|---|---|---|
| `day` (default) | Most batch jobs | 1-00:00:00 | 512 CPUs, 20T mem | 1024 CPUs, 37.5T mem |
| `devel` | Interactive / debugging | 06:00:00 | 10 CPUs, 70G mem | n/a listed |
| `week` | Longer CPU jobs | 7-00:00:00 | 128 CPUs, 1280G mem | 192 CPUs, 1920G mem |
| `gpu` | GPU jobs | 2-00:00:00 | 192 CPUs, 18 GPUs | 384 CPUs, 36 GPUs |
| `gpu_devel` | GPU debugging / development | 06:00:00 | 4 CPUs, 1 GPU, 32G mem | n/a listed |
| `bigmem` | High-memory jobs | 1-00:00:00 | 64 CPUs, 2T mem | n/a listed |

## Hardware

### CPU nodes
| Partition | Nodes | CPU | CPUs/node | Mem/node (GiB) |
|---|---|---|---|---|
| day | 18 | 6458 (Sapphire Rapids) | 64 | 479 |
| devel | 2 | 6458 | 64 | 479 |
| week | 6 | 6458 | 64 | 479 |
| bigmem | 2 | 6458 | 64 | 1991 |

### GPU nodes (`gpu` partition, 4 GPUs per node)
| Nodes | GPU (`--gpus` type) | vRAM/GPU | CPUs/node | Mem/node (GiB) | CPU arch |
|---|---|---|---|---|---|
| 8 | h100 | 80 GB | 48 | 975 | Emerald Rapids (6542Y) |
| 4 | h200 | 141 GB | 48 | 975 | Emerald Rapids (6542Y) |
| 4 | h100 | 80 GB | 48 | 975 | Sapphire Rapids (6442Y) |
| 2 | h100 | 80 GB | 48 | 975 | Sapphire Rapids (6458Q) |
| 3 | l40s | 48 GB | 48 | 975 | Sapphire Rapids (6442Y) |
| 4 | a40 | 48 GB | 32 | 975 | Ice Lake (6326) |
| 6 | a100 | 80 GB | 32 | 1000 | Ice Lake (6326) |

`gpu_devel` has 2 nodes with 4x A40 (48 GB) each, 32 CPUs, 975 GiB.

### Node features (for `--constraint`)
Combine `--partition` with `--constraint` to target specific nodes. Features listed on the page include:
`sapphirerapids`, `emeraldrapids`, `icelake`, `avx512`, `doubleprecision`, `common`, `gpu`, `h100`, `h200`, `l40s`, `a40`, `a100`, `a100-80g`, plus CPU model tags (`6458Q`, `6542Y`, `6442Y`, `6326`).

## Example batch scripts
These are templates built from the limits above, not copied from the page. Adjust to your job.

### CPU job
```bash
#!/bin/bash
#SBATCH --job-name=cpu_job
#SBATCH --partition=day
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem-per-cpu=5G
#SBATCH --output=logs/%x-%j.out

# module load / conda activate here
python script.py
```

### Single-GPU job
```bash
#!/bin/bash
#SBATCH --job-name=gpu_job
#SBATCH --partition=gpu
#SBATCH --gpus=h100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x-%j.out

python train.py
```

### Quick GPU debug (interactive)
```bash
salloc --partition=gpu_devel --gpus=1 --cpus-per-task=4 --mem=32G --time=02:00:00
```
`gpu_devel` caps each user at 1 GPU, 4 CPUs, 32G mem, and 6 hours.

Pick a GPU type with `--gpus=<type>:<count>`, e.g. `--gpus=a5000:2` is the page's own syntax example (note: no A5000 nodes are listed on Misha, so use h100, h200, l40s, a40, or a100).

Multi-GPU within one node: up to 4 GPUs per node (e.g. `--gpus=h100:4`). Per-user cap is 18 GPUs in `gpu`.

## Software
Software is provided through environment modules (`module avail`, `module load`). Relevant to ML work (versions as listed on the page):
- Python 3.10.8, miniconda (23.5.2, 24.3.0)
- PyTorch 2.0.1, 2.1.2, 2.3.0a0; torchvision 0.15.2, 0.16.2, 0.18.0a0
- TensorFlow 2.13.0
- CUDA 11.8.0, 12.0.0, 12.1.1, 12.2.2; cuDNN 8.8 and 8.9; NCCL 2.16.2
- dSQ 1.05 (job arrays), mpi4py 3.1.4, OpenMPI, h5py, matplotlib, networkx, git, git-lfs

The page does not give exact module names or the right CUDA/PyTorch pairing, so check `module avail` on the cluster.

## Storage

Root filesystem: `/gpfs/radev`. Check usage with `getquota` (per-user breakdown updates once daily).

| Space | Path | Quota | File count | Backups | Snapshots |
|---|---|---|---|---|---|
| home | `/gpfs/radev/home` | 125 GiB/user | 500,000 | Not yet | >= 2 days |
| project | `/gpfs/radev/project` | 1 TiB/group (up to 4 TiB on request) | 5,000,000 | No | >= 2 days |
| scratch | `/gpfs/radev/scratch` | 10 TiB/group | 15,000,000 | No | No |

**Scratch purge:** files older than **60 days** are deleted, with an email warning one week before. Artificially extending file age (e.g. touching files) is forbidden without YCRC approval. Don't keep irreplaceable data only in scratch or project (no backups).

## Notes
- The page does not mention `--account` or `--qos` requirements; check with YCRC if submissions are rejected.
- Related YCRC docs: [Run Jobs with Slurm](https://docs.ycrc.yale.edu/clusters-at-yale/job-scheduling/), [Request Compute Resources](https://docs.ycrc.yale.edu/clusters-at-yale/job-scheduling/resource-requests/), [Job Arrays (dSQ)](https://docs.ycrc.yale.edu/clusters-at-yale/job-scheduling/dsq/), [Common Job Failures](https://docs.ycrc.yale.edu/clusters-at-yale/job-scheduling/common-job-failures/), [Multi-GPU Submission Scripts](https://docs.ycrc.yale.edu/ai/miniconda-multigpu/).
