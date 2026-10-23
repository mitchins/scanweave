"""Review-time checks from complete PDFs and ledgers; no P2 or B2 entry point."""
from pathlib import Path
import collections
import json
from qualification.font04.metrics import inspect,sha
from qualification.font04.b1_audit import bindings


def main():
    root=Path('qualification/font04/local');experiment=root/'financial-experimental-v2.pdf';snapshot=json.loads(Path(str(experiment)+'.font04/source.json').read_text());base=inspect(root/'financial-default.pdf');candidate=inspect(experiment);bound=bindings(snapshot,base)
    assert base['sha256']==sha(root/'financial-main.pdf')
    assert candidate['sha256']==sha(root/'financial-experimental-repeat.pdf')
    assert len([r for r in base['draws']if r['character']=='e'])==291
    assert len([r for r in candidate['draws']if r['character']=='e'])==291
    def non_e(inv):return [(r['page'],r['character'],r['program'],r['matrix'])for r in inv['draws']if r['character']!='e']
    assert non_e(base)==non_e(candidate),'Non-e visible program or placement changed'
    gid_users=collections.defaultdict(list)
    for row in base['users']:gid_users[(row['font_hash'],row['gid'])].append(row)
    other_users=[]
    for row in snapshot['rows']:
        draw=bound[row['index']];users=gid_users[(draw['font_hash'],draw['gid'])]
        if any(u['character']!='e'or u['invisible']for u in users):other_users.append(row['index'])
    # Extraction/search, qpdf and OTS are independently recorded by b1_audit.
    score=json.loads(Path('qualification/font04/checkpoint-B1.json').read_text())
    assert score['default_matches_current_main']
    for entry in score['scorecard'].values():assert all(r['returncode']==0 for r in entry['validation'].values())
    assert all(r['extraction_equal']for r in score['text_search'].values())
    assert score['text_search']['pdfium']['search_equal']
    assert sha('qualification/font04/p2-preregistration.json')=='a4f9ccd3a7e51d719946be80f7cc9a297de7ca22285e8755e5e26e415e7db466'
    review=json.loads(Path('qualification/font04/review-manifest.json').read_text());assert review['random_rejected_members']>=50
    assert review['review_pdf_sha256']==sha(review['review_pdf'])
    result=dict(default_byte_identical=True,experimental_repeat_byte_identical=True,visible_e_draws=291,non_e_programs_and_placements_identical=True,e_members_with_invisible_or_cross_label_old_program_users=other_users,retirement_frontier_requires_all_users_remapped=not other_users,P2_hash_unchanged=True,B2_started=False,review_random_rejections=review['random_rejected_members'])
    Path('qualification/font04/verification.json').write_text(json.dumps(result,indent=2));print(result)


if __name__=='__main__':main()
