"""Upload added/changed public files against a pinned live release inventory."""
import argparse
import json
from pathlib import Path
from release_delta import package
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--content-only', action='store_true')
    args = parser.parse_args()
    print(json.dumps(package(ROOT, json.loads(args.baseline.read_text(encoding='utf8')),
                             ROOT/'deploy-build/pelicanmap-update.tar.gz',
                             include_runtime=not args.content_only), indent=2))


if __name__ == '__main__':
    main()
