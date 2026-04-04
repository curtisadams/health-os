import subprocess
import sys
import time

STEPS = [
    ("WHOOP",         "scripts/whoop.py"),
    ("Apple Health",  "scripts/apple_health.py"),
    ("Lose It",       "scripts/loseit.py"),
    ("Daily Summary", "scripts/summary.py"),
]


def main():
    print("=" * 60)
    print("  health-os — daily data pipeline")
    print("=" * 60)

    start = time.time()

    for i, (label, script) in enumerate(STEPS, 1):
        print(f"\n[{i}/{len(STEPS)}] {label}...\n")
        result = subprocess.run([sys.executable, script])
        if result.returncode != 0:
            print(f"\n[ERROR] {label} failed (exit {result.returncode}). Stopping.")
            sys.exit(result.returncode)

    elapsed = round(time.time() - start, 1)
    print(f"\nDone in {elapsed}s")


if __name__ == "__main__":
    main()
