"""Seal accepted B2-prime evidence; never reads or generates P2 content."""
import ast
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
ART = BASE / 'local/financial-B2prime-cover-2.0.pdf.font04'
SOURCES = ['planner.py', 'geometry.py', 'canonical_hygiene.py', 'soft_support.py',
           'b2prime.py', 'owned_ink.py', 'composite_transport.py']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def stable(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def freeze():
    plan = json.loads((ART / 'plan.json').read_text())
    assert plan['selected'] == dict(grouping='cover', error_scale=2.0,
                                    weight_bands=True, net_retirement_rule=False)
    constants = []
    for name in SOURCES:
        source = (BASE / name).read_text()
        # Exhaustive numeric-literal inventory deliberately includes inactive research
        # helpers. Stage references below identify the release call graph.
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Constant) and type(node.value) in (int, float):
                constants.append(dict(source=f'qualification/font04/{name}:{node.lineno}',
                                      value=node.value, expression=source.splitlines()[node.lineno-1].strip()))
    stages = [
        ('snapshot', 'crates/scanweave-io/src/font04.rs:121', 'Visible draws; eligibility is >=10 visible draws of a label per document; all other draws retain default.'),
        ('eligibility', 'qualification/font04/planner.py:19', 'Safe owned source, contrast >=30; line-local a/c/e x-height, baseline and OCR center; 64x64 frame.'),
        ('weight band', 'qualification/font04/b2prime.py:57', 'floor(log(max(mass / max(1, 4-connected eroded boundary pixels), .1)) / log(1.3)); separate labels and bands.'),
        ('hygiene', 'qualification/font04/canonical_hygiene.py:12', 'Independent current-program class support; footprint, unsupported components and topology screen before offering canonical.'),
        ('cover grouping', 'qualification/font04/planner.py:124', 'Directed 24-nearest candidate shortlist; self-admission mandatory; cost-aware greedy cover, tuple tie breaks by index; >=2 members. Soft multiplier 2.0; no witness-count gate. LOO fallback: soft_support.py.'),
        ('canonical trace', 'crates/scanweave-io/src/font04.rs:76', 'Fresh native source-field trace with floor off; preserve crop frame; existing 16384 sample cap and 16-unit trace policy. Trace occurs before fitting/grouping; no group retracing.'),
        ('placement fit', 'qualification/font04/geometry.py:39', 'Bounded SciPy TRF Huber least squares; isotropic scale and translation only; original source frame inverse.'),
        ('hard checks', 'qualification/font04/planner.py:98', 'Area, extents, elongation, median EDT stroke, 8-connected ink/background topology, centroid, major-axis orientation, effective stroke, counter XOR, cross moment, .35/.65 topology.'),
        ('owned-ink veto', 'qualification/font04/b2prime.py:19', 'Raw source and default establish ownership; detached and attached significance; veto canonical/group if canonical fires or fewer than 2 survivors.'),
        ('net-retirement', 'FONT_04_PRODUCT_MISSION.md:244', 'net_retirement_rule=false; aggregate document net outlines retired >=0 and encoded font bytes <= default, otherwise emit default; report zero-credit groups separately.'),
        ('composite stub', 'qualification/font04/composite_transport.py:43', 'Round-to-even integer offsets and F2Dot14 matrix; ROUND_XY_TO_GRID | UNSCALED_COMPONENT_OFFSET. Preserve default metrics and CID/Tm/W/ActualText.'),
        ('font-variant emission', 'qualification/font04/composite_transport.py:55', 'First compatible CID map per draw; shared embedded font; keep visible and invisible owners; subset unreachable old programs.')]
    prereg = digest(BASE / 'p2-preregistration.json')
    assert prereg == 'a4f9ccd3a7e51d719946be80f7cc9a297de7ca22285e8755e5e26e415e7db466'
    write(BASE / 'method-freeze.json', dict(schema='font04-method-freeze-v1',
        contract='3610e009b89aa3a5f97aea65af6df87477295656', method='cover-2.0',
        selected=plan['selected'], class_eligibility='>=10 visible draws of a label in this document',
        p2_preregistration_sha256=prereg, p2_opened=False,
        stages=[dict(stage=s, source=p, rule=r) for s,p,r in stages],
        numeric_literal_inventory_scope='All numeric literals in listed Python sources; includes inactive comparison helpers, not additional release gates.',
        constants=sorted(constants,key=lambda r:(r['source'].split(':')[0],int(r['source'].split(':')[1]))),
        sources={name:digest(BASE/name) for name in SOURCES},
        references=dict(plan_membership_sha256=stable(sorted((a['member'],a['canonical']) for a in plan['assignments'])),
            canonical_set_sha256=stable(sorted({a['canonical'] for a in plan['assignments']})),
            emitted_bindings_sha256=digest(ART/'emitted-bindings.json'),
            plan_sha256=digest(ART/'plan.json'), output_pdf_sha256=digest(BASE/'local/financial-B2prime-cover-2.0.pdf'))))


if __name__ == '__main__':
    freeze()
