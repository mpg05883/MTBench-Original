# Bouchet Cluster (Yale YCRC): SLURM Job Submission Reference

Source: https://docs.ycrc.yale.edu/clusters/bouchet/ (page last updated Sept 30, 2026). Re-check the page for changes.

Bouchet is a shared-use YCRC HPC cluster for Yale researchers. It succeeds Grace and McCleary, which are being decommissioned. Jobs are scheduled with Slurm.

## Access
- Needs a YCRC account (request at https://research.computing.yale.edu/account-request).
- Log in via SSH or the Open OnDemand web portal: https://ood-bouchet.ycrc.yale.edu
- All users must follow the Bouchet Rules of Behavior.
- System status / maintenance schedule: https://research.computing.yale.edu/system-status (the node-level cluster monitor is VPN-only).
- Off-campus access requires the Yale VPN. Login hostnames are not listed on the page; see YCRC's SSH access guide.
- Help: https://help.ycrc.yale.edu/ or research.computing@yale.edu

## Submission limits
- The page does not state a submission rate limit or an interactive-app instance limit. Misha's page cites 200 submissions per hour (see "Rate Limits" in YCRC's Common Job Failures page); assume something similar and use job arrays (or dSQ) instead of looping `sbatch`.

## Default request values
If not specified, `sbatch`/`salloc` use the following. Default partition is **day**.

| Partition | Defaults |
|---|---|
| most partitions | `--time=01:00:00 --nodes=1 --ntasks=1 --cpus-per-task=1 --mem-per-cpu=5120` |
| `mpi` | `--time=01:00:00 --nodes=1 --ntasks=1 --cpus-per-task=1 --exclusive --mem=498688` |
| `agent` | `--time=01:00:00 --nodes=1 --ntasks=1 --cpus-per-task=1 --mem-per-cpu=1024` |

Requests for `--cpus-per-task` and `--mem` cannot exceed one node's capacity.

**GPU and scavenge jobs do not get a GPU by default.** You must request one explicitly with `--gpus`, e.g. `--gpus=h100:2`.

## Partitions

| Partition | Purpose | Max time | Per-user limits | Per-group limits |
|---|---|---|---|---|
| `day` (default) | Most batch jobs | 1-00:00:00 | 1500 CPUs, 20000G mem | 2400 CPUs, 24000G mem |
| `devel` | Interactive work, exploration, compile debugging | 06:00:00 | 4 CPUs, 60G mem, 2 submitted jobs | n/a listed |
| `week` | Longer CPU jobs | 7-00:00:00 | 96 CPUs, 1.50T mem | 128 CPUs, 2T mem |
| `gpu` | GPU jobs (general) | 2-00:00:00 | 32 GPUs, 12 running jobs | 32 GPUs, 16 running jobs |
| `gpu_rtx6000` | GPU jobs (RTX Pro 6000 Blackwell) | 2-00:00:00 | 16 GPUs, 16 running jobs | 24 GPUs |
| `gpu_h100` | GPU jobs (H100) | 2-00:00:00 | 32 GPUs, 12 running jobs | 32 GPUs |
| `gpu_h200` | GPU jobs (H200) | 2-00:00:00 | 16 GPUs, 6 running jobs | 32 GPUs |
| `gpu_b200` | GPU jobs (B200) | 2-00:00:00 | 16 GPUs, 6 running jobs | 32 GPUs |
| `gpu_devel` | GPU debugging / development | 06:00:00 | 12 CPUs, 2 GPUs, 256G mem, 1 running job, 1 submitted job | n/a listed |
| `bigmem` | Very high-memory jobs | 1-00:00:00 | 128 CPUs, 8000G mem | n/a listed |
| `mpi` | Tightly coupled multi-node parallel jobs | 2-00:00:00 | 48 nodes, 10 running jobs | 48 nodes |
| `agent` | Long-lived interactive coding-agent workflows | 7-00:00:00 | 2 running jobs, 1 CPU and 8G mem per job | n/a listed |
| `scavenge` | Preemptable CPU jobs | 1-00:00:00 | n/a listed | n/a listed |
| `scavenge_gpu` | Preemptable GPU jobs | 1-00:00:00 | n/a listed | n/a listed |
| `pi_co54` | Private group partition | 7-00:00:00 | n/a listed | n/a listed |

## Hardware

### CPU nodes
| Partition | Nodes | CPU (`cpumodel`) | CPUs/node | Mem/node (GiB) |
|---|---|---|---|---|
| day | 12 | turin (9575f) | 128 | 2251 |
| day | 6 | turin (9655) | 192 | 1487 |
| day | 92 | emeraldrapids (8562Y+) | 64 | 990 |
| day | 62 | cascadelake (8268) | 48 | 368 |
| devel | 1 | turin (9655) | 192 | 1487 |
| devel | 4 | emeraldrapids (8562Y+) | 64 | 990 |
| week | 14 | turin (9575f) | 128 | 2251 |
| bigmem | 4 | emeraldrapids (8562Y+) | 64 | 4014 |
| mpi | 60 | emeraldrapids (8562Y+) | 64 | 487 |
| agent | 2 | cascadelake (8268) | 48 | 368 |

`scavenge` spans the same CPU node types (26 + 7 turin, 96 + 4 + 60 emeraldrapids, 72 cascadelake).

### GPU nodes
| Partition | Nodes | GPU (`--gpus` type) | GPUs/node | vRAM/GPU (GB) | CPUs/node | Mem/node (GiB) | CPU arch |
|---|---|---|---|---|---|---|---|
| gpu | 9 | rtx_5000_ada | 4 | 32 | 48 | 479 | Emerald Rapids (6542Y) |
| gpu | 10 | l40s | 4 | 48 | 48 | 976 | Sapphire Rapids (6442Y) |
| gpu | 9 | a40 | 4 | 48 | 48 | 976 | Sapphire Rapids (6442Y) |
| gpu | 12 | a5000 | 4 | 24 | 32 | 240 | Ice Lake (6326) |
| gpu_rtx6000 | 7 | rtx_pro_6000_blackwell | 8 | 96 | 128 | 2251 | Turin (9575f) |
| gpu_h100 | 15 | h100 | 4 | 80 | 48 | 976 | Sapphire Rapids (6442Y) |
| gpu_h200 | 9 | h200 | 8 | 141 | 48 | 1995 | Emerald Rapids (6542Y) |
| gpu_b200 | 7 | b200 | 8 | 193 | 128 | 2251 | Turin (9575f) |
| gpu_devel | 1 | rtx_pro_6000_blackwell | 8 | 96 | 128 | 2251 | Turin (9575f) |
| gpu_devel | 1 | b200 | 8 | 193 | 128 | 2251 | Turin (9575f) |
| gpu_devel | 1 | h200 | 8 | 141 | 48 | 1995 | Emerald Rapids (6542Y) |
| gpu_devel | 3 | rtx_5000_ada | 4 | 32 | 48 | 479 | Emerald Rapids (6542Y) |
| gpu_devel | 1 | a40 | 4 | 48 | 48 | 976 | Sapphire Rapids (6442Y) |

`scavenge_gpu` has preemptable nodes of types rtx_pro_6000_blackwell (8), b200 (8), h200 (10), rtx_5000_ada (12), l40s (10 + 10), h100 (15), a40 (10) and a5000 (12). `pi_co54` has 10 private l40s nodes.

### Node features (for `--constraint`)
Combine `--partition` with `--constraint` to target specific nodes. Features are of the form `cpugen:<arch>`, `cpumodel:<model>`, `gpu:<type>` and `common:yes|no`, for example:
`cpugen:turin`, `cpugen:emeraldrapids`, `cpugen:sapphirerapids`, `cpugen:icelake`, `cpugen:cascadelake`, `cpumodel:9575f`, `cpumodel:9655`, `cpumodel:8562Y+`, `cpumodel:6542Y`, `cpumodel:6442Y`, `cpumodel:6326`, `gpu:h100`, `gpu:h200`, `gpu:b200`, `gpu:l40s`, `gpu:a40`, `gpu:a5000`, `gpu:rtx_5000_ada`, `gpu:rtx_pro_6000_blackwell`.

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

python script.py
```

### Single-GPU job
```bash
#!/bin/bash
#SBATCH --job-name=gpu_job
#SBATCH --partition=gpu_h100
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
`gpu_devel` caps each user at 12 CPUs, 2 GPUs, 256G mem, 1 running job, 1 submitted job, and 6 hours.

Pick a GPU type with `--gpus=<type>:<count>`, e.g. `--gpus=h100:2`. Use the matching partition (`gpu_h100`, `gpu_h200`, `gpu_b200`, `gpu_rtx6000`) or `gpu` for rtx_5000_ada, l40s, a40 and a5000. Multi-GPU within one node: up to 4 GPUs per node on h100, l40s, a40, a5000 and rtx_5000_ada nodes, 8 on h200, b200 and rtx_pro_6000_blackwell nodes.

## Software
Software is provided through environment modules (`module avail`, `module load`). The page lists a large set; the ones relevant to ML work (versions as listed):
- Python 3.10.8, miniconda 24.7.1, SciPy-bundle 2023.02, h5py 3.8.0, networkx 3.0, mpi4py 3.1.4
- CUDA 12.1.1, GCC 12.2.0, OpenMPI 4.1.4
- JupyterLab 4.0.3, git 2.38.1, nodejs 18.12.1 / 20.11.1

The page lists no PyTorch or TensorFlow module and no cuDNN/NCCL, so install ML packages in your own environment (this project uses uv). Check `module avail` on the cluster for exact module names.

## Storage

Bouchet has one filesystem, Roberts (all-flash NFS). `~/project_pi_<PI netid>` and `~/scratch_pi_<PI netid>` are shortcuts; run `mydirectories` for absolute paths.

| Space | Path | Quota | File count | Backups | Snapshots |
|---|---|---|---|---|---|
| home | `/home` | 125 GiB/user | 500,000 | Yes | >= 2 days |
| project | `/nfs/roberts/project` | 4 TiB/group | 5,000,000 | Yes | >= 2 days |
| scratch | `/nfs/roberts/scratch` | 10 TiB/group | 15,000,000 | No | No |
| pi | `/nfs/roberts/pi` | varies | varies | No | >= 2 days |

**Scratch purge:** files older than **30 days** are deleted, with an email warning one week before. Extending scratch expiration artificially requires explicit YCRC approval. Keep anything you need to retain in project or home (both are backed up), not scratch.

## Notes
- The page does not mention `--account` or `--qos` requirements; check with YCRC if submissions are rejected. Private partitions (`pi_<groupname>`) are not counted toward group Fairshare, with few exceptions.
- Related YCRC docs: [Run Jobs with Slurm](https://docs.ycrc.yale.edu/clusters-at-yale/job-scheduling/), [Request Compute Resources](https://docs.ycrc.yale.edu/clusters-at-yale/job-scheduling/resource-requests/), [Job Arrays (dSQ)](https://docs.ycrc.yale.edu/clusters-at-yale/job-scheduling/dsq/), [Common Job Failures](https://docs.ycrc.yale.edu/clusters-at-yale/job-scheduling/common-job-failures/).
