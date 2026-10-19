"""Restore losslessly packaged large JSON reports for offline measurement."""
from pathlib import Path
import gzip
B=Path(__file__).resolve().parent
for p in B.rglob('*.json.gz'):
 out=p.with_suffix('')
 if not out.exists():out.write_bytes(gzip.decompress(p.read_bytes()))
