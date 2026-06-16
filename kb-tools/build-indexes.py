#!/usr/bin/env python3
"""
Master Index Builder for Catholic Knowledge Base.
Orchestrates all index building steps.
"""

import sys, os, time, subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
KB_TOOLS = BASE_DIR / "kb-tools"

RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
NC = '\033[0m'


def log(msg):
    print(f"{GREEN}[BUILD]{NC} {msg}")


def warn(msg):
    print(f"{YELLOW}[WARN]{NC}  {msg}")


def run_step(name: str, script: str, args: list[str] = None) -> bool:
    """Run a build step and return success status."""
    print(f"\n{CYAN}{'─' * 60}{NC}")
    print(f"{CYAN}  Step: {name}{NC}")
    print(f"{CYAN}{'─' * 60}{NC}")

    cmd = [sys.executable, str(KB_TOOLS / script)]
    if args:
        cmd.extend(args)

    start = time.time()
    result = subprocess.run(cmd, cwd=str(BASE_DIR))
    elapsed = time.time() - start

    if result.returncode == 0:
        log(f"Completed in {elapsed:.1f}s")
        return True
    else:
        warn(f"Failed (exit code {result.returncode})")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build all KB indexes")
    parser.add_argument("--index", choices=["catalog", "chunks", "refs", "cross-refs", "topic", "embeddings", "all"],
                       default="all", help="Which index to build (default: all)")
    parser.add_argument("--skip-embeddings", action="store_true",
                       help="Skip embedding generation (requires Ollama)")
    args = parser.parse_args()

    print(f"""
{GREEN}{'=' * 60}
  Catholic Knowledge Base — Index Builder
{'=' * 60}{NC}
""")

    steps = []
    if args.index in ("all", "catalog"):
        steps.append(("Catalog", "build-catalog.py"))
    if args.index in ("all", "chunks"):
        steps.append(("Chunks", "build-chunks.py"))
    if args.index in ("all", "refs"):
        steps.append(("References", "extract-refs.py"))
    if args.index in ("all", "cross-refs"):
        steps.append(("Cross-References", "build-cross-refs.py"))
    if args.index in ("all", "topic"):
        steps.append(("Topic Index", "build-topic-index.py"))
    if args.index in ("all", "embeddings") and not args.skip_embeddings:
        steps.append(("Embeddings", "build-embeddings.py"))

    results = {}
    start_time = time.time()

    for name, script in steps:
        success = run_step(name, script)
        results[name] = success

    total_time = time.time() - start_time

    # Summary
    print(f"\n{GREEN}{'=' * 60}")
    print(f"  Build Complete — {total_time:.1f}s")
    print(f"{'=' * 60}{NC}\n")

    all_success = True
    for name, success in results.items():
        icon = f"{GREEN}✓{NC}" if success else f"{RED}✗{NC}"
        print(f"  {icon} {name}")
        if not success:
            all_success = False

    print()
    if all_success:
        log("All indexes built successfully.")
        log("Test with: python3 kb-tools/search.py --mode auto 'transubstantiation'")
    else:
        warn("Some steps failed. Check output above.")

    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
