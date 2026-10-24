"""Complete the R0 inventory without changing any frozen constant or decision."""
import ast
import hashlib
import inspect
import json
import re
from pathlib import Path
import numpy
import scipy
from scipy.optimize._lsq import trf, common, least_squares
from scipy.optimize import _numdiff
from qualification.font04.freeze_method import BASE, ROOT, digest, write


def expand():
    path=BASE/'method-freeze.json';manifest=json.loads(path.read_text());original=digest(path)
    python_paths=[BASE/name for name in ['class_metrics.py','causal.py','metrics.py','pdf_helpers.py','raw_owned_probe.py']]
    scipy_paths=[Path(inspect.getfile(module)) for module in [trf,common,_numdiff]]
    scipy_paths.append(Path(inspect.getfile(least_squares)))
    inventories=[]
    for source in python_paths+scipy_paths:
        text=source.read_text();name=str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else 'SciPy '+str(source.relative_to(Path(scipy.__file__).parent))
        values=[]
        for node in ast.walk(ast.parse(text)):
            if isinstance(node,ast.Constant) and type(node.value) in (int,float):
                values.append(dict(source=f'{name}:{node.lineno}',value=node.value,expression=text.splitlines()[node.lineno-1].strip()))
        inventories.append(dict(source=name,sha256=digest(source),numeric_literals=values))
    rust=[]
    for name in ['trace.rs','glyphs.rs','curve_fit.rs','convert.rs','units.rs','fontbuild.rs','page_pdf.rs','serialization.rs']:
        source=ROOT/'crates/scanweave-io/src'/name;lines=source.read_text().splitlines()
        rust.append(dict(source=str(source.relative_to(ROOT)),sha256=digest(source),numeric_source_lines=[dict(source=f'{source.relative_to(ROOT)}:{i}',expression=line.strip()) for i,line in enumerate(lines,1) if re.search(r'(?<![A-Za-z_])\d',line)]))
    detail=dict(schema='font04-frozen-dependency-inventory-v1',purpose='Inventory completion only; no method, constants, membership or accepted PDF changed.',
        origin_freeze_commit='5356255',original_manifest_sha256=original,reference_source_commit='3610e009b89aa3a5f97aea65af6df87477295656',
        environment=dict(numpy=numpy.__version__,scipy=scipy.__version__,float64_epsilon=float(numpy.finfo(float).eps)),
        inventory_scope='All numeric literals/lines, including inactive helpers and comments. Release call graph is specified in method-freeze.json; this inventory creates no additional gates.',
        numpy_semantics=dict(quantile='linear interpolation',argsort='default quicksort; untested pairs remain absent',erosion='default cross/4-connectivity',dilation='default cross, two iterations',hygiene_components='default cross/4-connectivity',topology='explicit 3x3/8-connectivity for ink and background',fill_holes='default cross/4-connectivity',sampling='bilinear order=1, constant=0 outside closed image; prefilter=False'),
        solver_defaults=dict(method='trf',tr_solver='exact dense SVD',x_scale=1.0,initial=[0.,0.,1.],huber_delta=.12,max_nfev=35,diff_step=.001,ftol=1e-5,xtol=1e-5,gtol=1e-5,trust_subproblem_rtol=.01,trust_subproblem_max_iter=10,theta_min=.995,source='SciPy optimize/_lsq/trf.py and common.py; complete literals below'),
        python=inventories,rust=rust,cargo_lock_sha256=digest(ROOT/'Cargo.lock'))
    write(BASE/'method-freeze-dependencies.json',detail)
    manifest['dependency_inventory']=dict(path='qualification/font04/method-freeze-dependencies.json',sha256=digest(BASE/'method-freeze-dependencies.json'),inventory_expansion_only=True,origin_freeze_commit='5356255',original_manifest_sha256=original)
    manifest['execution_order']=['snapshot and >=10 visible-draw label eligibility','source normalization and line frame','fresh source canonical traces','directed 24-nearest shortlist and bounded fits with hard checks','source-only LOO variation estimates and complete fallback floors','self fits and hard checks','weight bands and independent canonical hygiene before offers','cost-aware cover grouping at multiplier 2.0','raw-source/default/candidate owned-ink preflight and group survival','primitive retirement accounting, composite/font-variant construction','aggregate net>=0 and encoded-font non-growth guard, else default document','complete PDF emission with default CID/Tm/W/ActualText and raster representation']
    manifest['stage_order_note']='The named contract stages below are policy stages; execution_order states their actual dependency order. Canonicals are traced per source impression before grouping, never retraced from a group.'
    manifest['research_cohort_guard']='The B2 research driver requires 55 financial labels only to bind that research cohort. Product eligibility is >=10 visible draws per label for any document; no fixed label set is a release gate.'
    write(path,manifest)
    oracle_path=BASE/'reference-oracle.json';oracle=json.loads(oracle_path.read_text());oracle['method_freeze_sha256']=digest(path);write(oracle_path,oracle)


if __name__=='__main__':expand()
