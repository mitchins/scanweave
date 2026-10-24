"""Replay frozen safety regressions independently of the generator."""
import json
import unittest
import numpy as np
from qualification.font04.freeze_method import BASE, ART, digest
from qualification.font04.geometry import warp
from qualification.font04.planner import hard_checks
from qualification.font04.b2prime import owned_decision


class FrozenOracleTests(unittest.TestCase):
    def test_all_regressions(self):
        fixture=json.loads((BASE/'regression-fixtures.json').read_text())
        self.assertEqual(len(fixture['cases']),23)
        for c in fixture['cases']:
            with self.subTest(source=c['source'],member=c['member']):
                a=np.array(c['reference']).reshape(64,64)
                b=warp(np.array(c['candidate']).reshape(64,64),c['parameters'])
                reasons,_=hard_checks(a,b)
                self.assertEqual(reasons,c['expected_hard_reasons'])
                self.assertTrue(reasons or any(owned_decision(x) for x in c.get('owned_components',[])))

    def test_population_and_hashes(self):
        oracle=json.loads((BASE/'reference-oracle.json').read_text())
        self.assertEqual(oracle['plan_sha256'],digest(ART/'plan.json'))
        members=oracle['members']
        self.assertEqual([r['member'] for r in members],list(range(3524)))
        self.assertEqual(sum(r['decision']=='accept' for r in members),1750)
        for i in [3013,2466,63,1450,3422,1233]:
            self.assertEqual(members[i]['decision'],'reject')
        self.assertEqual(oracle['method_freeze_sha256'],digest(BASE/'method-freeze.json'))


if __name__=='__main__': unittest.main()
