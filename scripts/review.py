"""Start the owner-review demo without installing dependencies or system services."""
import argparse
import json
import sys
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mission_control.adapters import load_mock_file
from mission_control.server import make_server
from mission_control.store import connect, import_records, initialize, timestamp

REFERENCE_TIME = timestamp("2026-10-19T12:00:00Z")


def main():
    parser = argparse.ArgumentParser(description="Start the fictional Mission Control review dashboard")
    parser.add_argument("--port", type=int, default=0, help="0 chooses a free loopback port")
    args = parser.parse_args()
    output = ROOT / "output"
    output.mkdir(exist_ok=True)
    # Dedicated review data, separate from CLI walkthrough experiments.
    with closing(connect(output / "owner-review.sqlite3")) as db:
        initialize(db)
        import_records(db, load_mock_file(ROOT / "examples" / "synthetic.json"), REFERENCE_TIME)
    with make_server(output / "owner-review.sqlite3", args.port, REFERENCE_TIME, workbench=True) as server:
        url = f"http://127.0.0.1:{server.server_port}"
        (output / "review-session.json").write_text(json.dumps({"url": url, "fictional": True}, indent=2) + "\n")
        print(f"\nMission Control — fictional review demo\n{url}\n", flush=True)
        print("Open this local URL in your browser. Keep this window open; Ctrl+C stops the demo.", flush=True)
        print("Reference snapshot: 19 October 2026, 12:00 UTC. No external integrations.\n", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nReview dashboard stopped.", flush=True)


if __name__ == "__main__":
    main()
