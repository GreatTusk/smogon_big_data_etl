import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.run_pipeline import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("google.cloud").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger("main")


def main():
    parser = argparse.ArgumentParser(description="Smogon ETL Cloud Run Job")
    parser.add_argument("--format", help="Process only this format (e.g., gen9ou)")
    parser.add_argument("--skip-discover", action="store_true", help="Skip discovery step")
    args, _ = parser.parse_known_args()

    logger.info("Starting Smogon ETL Cloud Run job")
    logger.info("PROJECT_ID=%s", os.environ.get("PROJECT_ID", ""))
    logger.info("BUCKET_NAME=%s", os.environ.get("BUCKET_NAME", ""))
    logger.info("BQ_DATASET=%s", os.environ.get("BQ_DATASET", ""))
    logger.info("RUN_ID=%s", os.environ.get("RUN_ID", "(auto)"))

    try:
        run(format_filter=args.format, skip_discover=args.skip_discover)
    except Exception as e:
        logger.exception("Pipeline failed: %s", e)
        sys.exit(1)

    logger.info("Pipeline completed successfully")
    sys.exit(0)


if __name__ == "__main__":
    main()
