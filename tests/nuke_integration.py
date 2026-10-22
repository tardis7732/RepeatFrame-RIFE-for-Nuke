"""Run from repo root: Nuke -ti tests/nuke_integration.py"""
import os
import sys
import json
import tempfile
sys.path.insert(0, os.getcwd())
import nuke
import repeatframe_rife as rr

nuke.root()['format'].setValue(nuke.addFormat('128 128 0 0 128 128 1 RepeatTest'))
source = nuke.nodes.Constant()
source['color'].setExpression('frame <= 4 ? frame * 0.1 : frame <= 6 ? 0.4 : (frame-2)*0.1', 0)
source['color'].setExpression('frame <= 4 ? frame * 0.1 : frame <= 6 ? 0.4 : (frame-2)*0.1', 1)
source['color'].setExpression('frame <= 4 ? frame * 0.1 : frame <= 6 ? 0.4 : (frame-2)*0.1', 2)
tool = rr.create()
tool.setInput(0, source)
tool['first'].setValue(1)
tool['last'].setValue(11)
rr.analyze(tool)
data = json.loads(tool['analysis_json'].value())
assert data['runs'] == [dict(left=4, right=7, start=5, end=6)], data
assert len([x for x in tool.nodes() if x.Class() == 'Input']) == 1
repair = tool.node('Repair')
rife = next(x for x in repair.nodes() if x.Class() == 'RIFE')
assert abs(rife['timingFrame'].valueAt(5) - (1 + 1/3)) < 1e-6
assert abs(rife['timingFrame'].valueAt(6) - (1 + 2/3)) < 1e-6
for f in (1, 4, 7, 11):
    nuke.frame(f)
    assert abs(nuke.sample(tool, 'red', 64, 64) - nuke.sample(source, 'red', 64, 64)) < 1e-6
# Exercise actual RIFE inference, not just node construction.
for f, expected in [(5, .4 + .1/3), (6, .4 + .2/3)]:
    nuke.frame(f)
    value = nuke.sample(tool, 'red', 64, 64)
    print('RIFE_SAMPLE', f, value, 'expected', expected)
    assert abs(value - expected) < .035, (f, value)
path = os.path.join(tempfile.gettempdir(), 'repeatframe_roundtrip.nk')
nuke.scriptSaveAs(path, overwrite=1)
nuke.scriptClear()
nuke.scriptOpen(path)
loaded = nuke.toNode('RepeatFrameRIFE')
assert loaded is not None
nuke.frame(5)
assert abs(nuke.sample(loaded, 'red', 64, 64) - (.4 + .1/3)) < .035
rr.clear(loaded)
assert loaded.node('Repair') is None
# Exercise independent runs, a one-copy repair, leading/trailing holds,
# no-repeat input, and nested groups using real Nuke evaluation.
for sequence, expected_runs, expected_trailing in [
    ([1,2,3,4,4,5,6,7,8,9], [(4,6)], []),
    ([1,2,3,4,6,7,8,9], [], []),
    ([1,1,2,2,3,3], [(1,3),(3,5)], [6]),
    ([1,1,1], [], [2,3]),
]:
    outer = nuke.nodes.Group(name='NestedTest')
    with outer:
        constant = nuke.nodes.Constant()
        for c in range(3):
            constant['color'].setAnimated(c)
        for f, v in enumerate(sequence, 1):
            for c in range(3):
                constant['color'].setValueAt(v / 10.0, f, c)
        node = rr.create()
        node.setInput(0, constant)
        node['first'].setValue(1)
        node['last'].setValue(len(sequence))
        rr.analyze(node)
        result = json.loads(node['analysis_json'].value())
        assert [(r['left'],r['right']) for r in result['runs']] == expected_runs, result
        assert result['trailing'] == expected_trailing, result
    nuke.delete(outer)
print('REPEATFRAME_INTEGRATION_PASS')
