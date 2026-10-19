import importlib.util,concurrent.futures
from pathlib import Path
p=Path(__file__).with_name('run_corpus.py');spec=importlib.util.spec_from_file_location('corpus',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda row:m.call(row,'ocrmypdf3'),m.rows))
