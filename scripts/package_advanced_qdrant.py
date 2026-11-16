"""Package the public-text advanced index after checking every stored payload."""
import argparse
from pathlib import Path
import zipfile

from src.day07.advanced_retrieval import COLLECTION
from src.day07.common import now, read_json, read_jsonl, sha256, write_json


def main():
    from qdrant_client import QdrantClient
    p=argparse.ArgumentParser()
    p.add_argument('--qdrant',required=True,type=Path); p.add_argument('--chunks',required=True,type=Path)
    p.add_argument('--index-manifest',required=True,type=Path); p.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    if args.output.exists(): raise FileExistsError(args.output)
    manifest=read_json(args.index_manifest)
    if manifest['search_chunks_sha256']!=sha256(args.chunks): raise ValueError('Search export differs from index manifest')
    rows=read_jsonl(args.chunks); expected={r['id']:r for r in rows}
    if len(expected)!=len(rows) or any(r.get('source_id')!='LSDS-1574-v5.0' or
            r.get('source')!='https://www.usgs.gov/media/files/landsat-8-data-users-handbook' for r in rows):
        raise ValueError('Unexpected or duplicate index source')
    client=QdrantClient(path=str(args.qdrant))
    try:
        names={x.name for x in client.get_collections().collections}
        if names!={COLLECTION}: raise ValueError('Snapshot contains unexpected collections')
        found={}; offset=None
        while True:
            points,offset=client.scroll(COLLECTION,offset=offset,limit=128,with_payload=True,with_vectors=False)
            for point in points:
                payload=dict(point.payload); key=payload.get('id')
                if key in found: raise ValueError('Duplicate payload ID')
                found[key]=payload
            if offset is None: break
        if found!=expected: raise ValueError('Stored Qdrant payloads do not exactly match the public search export')
    finally: client.close()
    files=[args.qdrant/'meta.json',args.qdrant/f'collection/{COLLECTION}/storage.sqlite']
    hashes={p.relative_to(args.qdrant).as_posix():sha256(p) for p in files}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.output,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for f in files: z.write(f,f.relative_to(args.qdrant).as_posix())
    if any(sha256(p)!=hashes[p.relative_to(args.qdrant).as_posix()] for p in files):
        raise ValueError('Index changed during packaging')
    import hashlib
    with zipfile.ZipFile(args.output) as z:
        if set(z.namelist())!=set(hashes) or any(hashlib.sha256(z.read(name)).hexdigest()!=digest for name,digest in hashes.items()):
            raise ValueError('Archive validation failed')
    write_json(args.output.with_suffix('.json'),{'created_at':now(),'archive':str(args.output),
               'archive_sha256':sha256(args.output),'file_sha256':hashes,'payloads_compared':len(rows),
               'search_chunks_sha256':sha256(args.chunks),'source':'USGS Landsat 8 handbook v5, extracted text/OCR and AI visual observations',
               'contents':'Only Qdrant metadata and SQLite; no PDF images, model weights or credentials.',
               'warning':'USGS page states Public Domain; third-party image rights must be checked separately.'})
    print('Packaged and checked',len(rows),'payloads')


if __name__=='__main__': main()
