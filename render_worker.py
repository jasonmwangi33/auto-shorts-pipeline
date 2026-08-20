import argparse, hashlib, json, os, subprocess, sys, time, uuid
from pathlib import Path

def chunked_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024): h.update(chunk)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-index", type=int, required=True)
    parser.add_argument("--seeds-file", type=str, default="seeds.json")
    args = parser.parse_args()

    seeds = json.loads(Path(args.seeds_file).read_text(encoding="utf-8"))
    seed = seeds[args.seed_index]
    job_id = f"{seed.get('seed_id', 'seed')}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    seed["job_id"] = job_id

    context_path = Path(f"job_context_{args.seed_index}.json")
    context_path.write_text(json.dumps(seed, indent=2), encoding="utf-8")

    env = os.environ.copy()
    env["CONTENT_SEED_FILE"] = str(context_path)
    env["JOB_ID"] = job_id

    cmd = [sys.executable, "main.py", "--job-id", job_id, "--seed-file", str(context_path)]
    print(f"Running main.py: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env, check=False)
    if result.returncode != 0: sys.exit(f"main.py failed with code {result.returncode}")

    output_video = Path("output") / f"{job_id}_output.mp4"
    if not output_video.exists() or output_video.stat().st_size == 0: sys.exit("Output video missing/empty")

    qc_manifest = {
        "job_id": job_id, "seed_index": args.seed_index, "output_file": str(output_video),
        "passed": True, "sha256": chunked_sha256(output_video)
    }
    qc_path = Path("output") / f"{job_id}_qc.json"
    qc_path.write_text(json.dumps(qc_manifest, indent=2), encoding="utf-8")

if __name__ == "__main__": main()
