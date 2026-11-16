from argparse import Namespace
import copy
from pathlib import Path
import unittest

from scripts.advanced_release import validate_dev_vision_reuse
from src.day07.common import read_json, sha256

ROOT=Path(__file__).resolve().parents[1]


class ReleaseGuardTests(unittest.TestCase):
    def args(self,split='dev'):
        return Namespace(split=split,
            reuse_dev_vision_code=ROOT/'artifacts/advanced/code-snapshots/a8/src/day07/multimodal_v2.py',
            config=ROOT/'configs/advanced-v2.json')

    def inputs(self):
        manifest=read_json(ROOT/'artifacts/advanced/runs/advanced-v2-dev-a8-vision/manifest.json')
        current=copy.deepcopy(manifest['hashes'])
        for path in ('src/day07/multimodal_v2.py','scripts/advanced_release.py','configs/advanced-v2.json'):
            current['repository'][path]=sha256(ROOT/path)
        return manifest,current

    def test_unchanged_complete_perception_can_be_reused_for_dev_finalizer_only(self):
        manifest,current=self.inputs()
        result=validate_dev_vision_reuse(self.args(),manifest,current)
        self.assertTrue(result['perception_ast_identical'])

    def test_test_stage_cannot_reuse_development_perception(self):
        manifest,current=self.inputs()
        with self.assertRaisesRegex(ValueError,'different release'):
            validate_dev_vision_reuse(self.args('test'),manifest,current)

    def test_model_change_forbids_development_reuse(self):
        manifest,current=self.inputs()
        current['external']['vision_model']='different-model'
        with self.assertRaisesRegex(ValueError,'same model'):
            validate_dev_vision_reuse(self.args(),manifest,current)


if __name__=='__main__':unittest.main()
