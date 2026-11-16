"""Package the public Day 6 Qdrant snapshot used by the frozen base experiment."""
from pathlib import Path
import zipfile

from src.day07.common import now, read_json, sha256, write_json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '.local/day6-qdrant'
ARCHIVE = ROOT / 'artifacts/base/qdrant-snapshot.zip'


def main():
    lock = read_json(ROOT / 'artifacts/base/freeze.json')
    for label, path in [('qdrant/meta.json', SOURCE / 'meta.json'),
                        ('qdrant/lab6_B/storage.sqlite', SOURCE / 'collection/lab6_B/storage.sqlite')]:
        if sha256(path) != lock['external_hashes'][label]:
            raise ValueError(f'{label} no longer matches the frozen snapshot')
    if ARCHIVE.exists():
        raise FileExistsError(ARCHIVE)
    files = [p for p in SOURCE.rglob('*') if p.is_file() and p.name != '.lock' and not p.is_symlink()]
    with zipfile.ZipFile(ARCHIVE, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, path.relative_to(SOURCE).as_posix())
    verify_dir = ROOT / '.local/qdrant-archive-check'
    if verify_dir.exists():
        raise FileExistsError(verify_dir)
    verify_dir.mkdir(parents=True)
    with zipfile.ZipFile(ARCHIVE) as archive:
        for info in archive.infolist():
            target = (verify_dir / info.filename).resolve()
            if not target.is_relative_to(verify_dir.resolve()):
                raise ValueError('Unsafe archive entry')
        archive.extractall(verify_dir)
    assert sha256(verify_dir / 'meta.json') == lock['external_hashes']['qdrant/meta.json']
    assert sha256(verify_dir / 'collection/lab6_B/storage.sqlite') == lock['external_hashes']['qdrant/lab6_B/storage.sqlite']
    write_json(ROOT / 'artifacts/base/qdrant-package.json', {'created_at': now(),
               'archive': 'qdrant-snapshot.zip', 'sha256': sha256(ARCHIVE),
               'included': [p.relative_to(SOURCE).as_posix() for p in sorted(files)],
               'verified_against_freeze': True,
               'contents': 'Qdrant local collections A/B over public CPython documentation and an empty storage probe; no model weights or secrets.',
               'source_license': 'CPYTHON_LICENSE.txt and CPYTHON_DOCUMENTATION_LICENSE.rst in this directory.'})
    print('Packaged frozen public-data Qdrant snapshot:', ARCHIVE, 'bytes=', ARCHIVE.stat().st_size)


if __name__ == '__main__': main()
