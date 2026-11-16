"""Add source reference titles and chart category labels to the complete catalog."""
import argparse
import json
from pathlib import Path
import uuid

from src.day07.catalog_agent import source_reference
from src.day07.common import now,read_jsonl,sha256,write_json,write_jsonl
from src.day07.day6 import MODEL,REVISION,load_module
from src.day07.advanced_retrieval import snippets


def main():
    p=argparse.ArgumentParser()
    for flag in ('day6-root','model-path','output','qdrant'):p.add_argument('--'+flag,required=True,type=Path)
    args=p.parse_args()
    if args.output.exists() or args.qdrant.exists():raise FileExistsError('Refusing overwrite')
    rows=read_jsonl('artifacts/advanced/catalog-v6/regions.jsonl')
    categories=['Coastal/Aerosol','Blue','Green','Red','NIR','SWIR1','SWIR2','Pan','Cirrus']
    for r in rows:
        ref=source_reference(r)
        r['metadata']['source_reference']=ref
        if ref:r['text']='Original source reference: '+ref.title()+'\n'+r['text']
        if r['evidence_id']=='landsat-v5-p019-image-001':
            for item in r['curated_data']:item['Category']=categories[int(item['OLI Band'])-1]
            before=r['text'].split('\nSource-derived structured observations:',1)[0]
            r['text']=before+'\nSource-derived structured observations:\n'+json.dumps(r['curated_data'],ensure_ascii=False)
        r['metadata']['source_catalog']='v7'
    module=load_module(args.day6_root/'src/embeddings.py','catalog_v7_embed')
    embedder=module.LocalEmbedder(model_name=MODEL,revision=REVISION,model_path=str(args.model_path),device='cpu',batch_size=16)
    chunks=[]
    for r in rows:
        for i,text in enumerate(snippets(r['text'],embedder.tokenizer,size=450,overlap=48),1):
            chunks.append({k:v for k,v in r.items() if k not in ('curated_data','automatic_table_cells')}|
                          {'id':r['evidence_id']+f'#catalog7-{i:03d}','text':text})
    from qdrant_client import QdrantClient,models
    client=QdrantClient(path=str(args.qdrant))
    try:
        client.create_collection('lab7_landsat_v5',vectors_config=models.VectorParams(size=384,distance=models.Distance.COSINE))
        for start in range(0,len(chunks),64):
            batch=chunks[start:start+64];vectors=embedder.embed_documents([r['text'] for r in batch])
            client.upsert('lab7_landsat_v5',points=[models.PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL,r['id'])),vector=v,payload=r) for r,v in zip(batch,vectors)],wait=True)
            print('Indexed',min(start+64,len(chunks)),'/',len(chunks),flush=True)
    finally:client.close()
    args.output.mkdir(parents=True)
    write_jsonl(args.output/'regions.jsonl',rows);write_jsonl(args.output/'chunks.jsonl',chunks)
    write_json(args.output/'manifest.json',{'created_at':now(),'regions':len(rows),'pages':len({r['page'] for r in rows}),
        'chunks':len(chunks),'parent_catalog_sha256':sha256('artifacts/advanced/catalog-v6/regions.jsonl'),
        'builder_sha256':sha256(Path(__file__)),'benchmark_inputs_read':False,
        'policy':'Source-only reference titles and complete chart-series categories; no question-specific answers or absence assertions.',
        'source_verification':'artifacts/source-verification.json'})


if __name__=='__main__':main()
