"""Download the pinned original file; never silently change source/version."""
import argparse,hashlib,json,os,tempfile
from datetime import datetime,timezone
from pathlib import Path
import requests
from .db import ROOT
URL='https://football-data.co.uk/mmz4281/2526/E0.csv'
SHA256='3e3a8352f9ada6789c508d6ca184424421fed56a30400904a4a327c583407e62'
CSV=ROOT/'data/raw/E0-2526.csv'
def verify(path):
    data=Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest()!=SHA256:raise ValueError('SHA256 khác bản đã kiểm tra. Không tự đổi nguồn; kiểm tra thay đổi nguồn trước.')
    return data
def download(target=CSV):
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():verify(target);return target
    response=requests.get(URL,timeout=(15,60),headers={'User-Agent':'PremierLeagueSQLLab/1.0 educational download'})
    response.raise_for_status();data=response.content
    if hashlib.sha256(data).hexdigest()!=SHA256:raise ValueError('File tải về không khớp SHA256 đã chốt; không công bố file.')
    fd,tmp=tempfile.mkstemp(dir=target.parent,suffix='.part')
    try:
        with os.fdopen(fd,'wb') as f:f.write(data)
        os.link(tmp,target)
    finally:Path(tmp).unlink(missing_ok=True)
    target.with_suffix('.manifest.json').write_text(json.dumps({'url':URL,'season':'2025-2026','sha256':SHA256,'downloaded_at':datetime.now(timezone.utc).isoformat(),'bytes':len(data)},indent=2),encoding='utf-8')
    return target
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',default=str(CSV));a=p.parse_args()
    try:print(download(a.out))
    except (ValueError,OSError,requests.RequestException) as e:p.exit(1,str(e)+'\nCó thể tải thủ công file gốc, rồi --input đường_dẫn_csv.\n')
if __name__=='__main__':main()
