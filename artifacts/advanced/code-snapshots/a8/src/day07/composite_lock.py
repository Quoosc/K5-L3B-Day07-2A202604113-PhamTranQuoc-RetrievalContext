"""Fingerprint every component in the advanced composite release candidate."""
from pathlib import Path
from .common import sha256

ROOT=Path(__file__).resolve().parents[2]
FILES=('src/day07/composite.py','src/day07/composite_lock.py','src/day07/advanced_formatting.py',
       'src/day07/spatial_ocr.py','src/day07/spectral_join.py','scripts/refine_advanced_dev.py',
       'scripts/run_composite_final.py','scripts/freeze_advanced_composite.py','requirements-lock.txt')


def composite_hashes():
    return {name:sha256(ROOT/name) for name in FILES}
