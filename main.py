import argparse
from pipeline.orchestrator import JobOrchestrator
from pipeline.config import load_config

def main():
    parser = argparse.ArgumentParser(description=\"Autonomous Shorts Pipeline\")
    parser.add_argument(\"--job-id\", type=str, required=True)
    parser.add_argument(\"--seed-file\", type=str, required=True)
    parser.add_argument(\"--config\", type=str, default=\"config.json\")
    parser.add_argument(\"--auto-improve\", action=\"store_true\")
    parser.add_argument(\"--max-retries\", type=int, default=3)
    args = parser.parse_args()

    config = load_config(args.config)
    orchestrator = JobOrchestrator(config)
    orchestrator.run_job(
        job_id=args.job_id,
        seed_file=args.seed_file,
        auto_improve=args.auto_improve,
        max_retries=args.max_retries
    )

if __name__ == \"__main__\":
    main()
