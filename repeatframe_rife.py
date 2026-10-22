"""One-input repeated-frame detection and Cattery RIFE repair for Nuke."""
import json
import nuke
from repeatframe_core import find_runs


def _button(node, name, label, call):
    knob = nuke.PyScript_Knob(name, label)
    node.addKnob(knob)
    knob.setValue('import repeatframe_rife as rr\nrr.%s(nuke.thisNode())' % call)


def create():
    selected = nuke.selectedNodes()
    source = selected[-1] if selected else None
    node = nuke.nodes.Group(name='RepeatFrameRIFE')
    with node:
        raw = nuke.nodes.Input(name='Source', number=0)
        output = nuke.nodes.Output(name='Output1')
        output.setInput(0, raw)
    node.addKnob(nuke.Tab_Knob('repeatframe', 'Repeat Frame RIFE'))
    for name, label, value in [('first', 'Frame range', nuke.root().firstFrame()),
                               ('last', '', nuke.root().lastFrame())]:
        knob = nuke.Int_Knob(name, label)
        node.addKnob(knob)
        knob.setValue(int(value))
        if name == 'last':
            knob.clearFlag(nuke.STARTLINE)
    _button(node, 'reset_range', 'Use input range', 'reset_range')
    knob = nuke.Double_Knob('tolerance', 'Repeat tolerance')
    node.addKnob(knob)
    knob.setRange(0, 0.01)
    knob.setValue(0)
    knob.setTooltip('Mean absolute RGB difference in the input format. 0 detects exact repeats. Increase cautiously for compressed video; real static shots can also match.')
    knob = nuke.Boolean_Knob('use_gpu', 'RIFE GPU')
    node.addKnob(knob)
    knob.setValue(True)
    knob = nuke.Int_Knob('detail', 'RIFE detail')
    node.addKnob(knob)
    knob.setValue(3)
    knob.setRange(0, 4)
    knob = nuke.Enumeration_Knob('downrez', 'RIFE resolution', ['Full', '1/2', '1/4'])
    node.addKnob(knob)
    _button(node, 'analyze', 'Analyze and build', 'analyze')
    _button(node, 'clear', 'Clear repair', 'clear')
    node.addKnob(nuke.Text_Knob('status', 'Results', 'Not analyzed. Input passes through.'))
    node.addKnob(nuke.Text_Knob('help', '',
        'One input. Keeps the first copy; fills later copies toward the next different frame.\n'
        'Frame count and other frames stay unchanged. Trailing repeats stay unchanged.\n'
        'Static holds can also match. Review the results. Reanalyze after input/settings changes.'))
    knob = nuke.String_Knob('analysis_json', '')
    node.addKnob(knob)
    knob.setVisible(False)
    if source is not None:
        node.setInput(0, source)
        reset_range(node)
    node['label'].setValue('Repeat-frame repair / one input')
    return node


def reset_range(node):
    source = node.input(0)
    if source is None:
        raise RuntimeError('Connect an input first.')
    node['first'].setValue(int(source.firstFrame()))
    node['last'].setValue(int(source.lastFrame()))


def clear(node):
    with node:
        raw, output = node.node('Source'), node.node('Output1')
        output.setInput(0, raw)
        for child in list(node.nodes()):
            if child not in (raw, output):
                nuke.delete(child)
    node['analysis_json'].setValue('')
    node['status'].setValue('Cleared. Input passes through.')


def _differences(source, first, last, progress):
    """Full-format absolute RGB difference, evaluated at the original resolution."""
    path = source.fullName().rpartition('.')[0]
    parent = nuke.toNode(path) if path else nuke.root()
    with parent:
        temporary = nuke.nodes.Group(name='__RepeatFrameAnalysis')
        temporary.setInput(0, source)
    try:
        with temporary:
            raw = nuke.nodes.Input(number=0)
            previous = nuke.nodes.TimeOffset(time_offset=1)
            previous.setInput(0, raw)
            diff = nuke.nodes.Merge2(operation='difference')
            diff.setInput(0, raw)
            diff.setInput(1, previous)
            curve = nuke.nodes.CurveTool(operation='Avg Intensities')
            curve.setInput(0, diff)
            curve['channels'].setValue('rgb')
            fmt = source.format()
            curve['ROI'].setValue([0, 0, fmt.width(), fmt.height()])
            values = {}
            for frame in range(first + 1, last + 1):
                if progress.isCancelled():
                    raise RuntimeError('Analysis cancelled; previous repair retained.')
                progress.setMessage('Comparing %d / %d' % (frame, last))
                nuke.execute(curve, frame, frame)
                values[frame] = max(abs(curve['intensitydata'].valueAt(frame, c)) for c in range(3))
                progress.setProgress(int(80 * (frame - first) / max(1, last - first)))
            return values
    finally:
        nuke.delete(temporary)


def _build(node, runs):
    """Build off to the side, then swap only when every RIFE node is ready."""
    with node:
        repair = nuke.nodes.Group(name='RepairBuild')
        repair.setInput(0, node.node('Source'))
    try:
        with repair:
            raw = nuke.nodes.Input(number=0)
            result = raw
            for index, run in enumerate(runs):
                x = index * 350
                endpoints = []
                for label in ('left', 'right'):
                    hold = nuke.nodes.FrameHold(name='%s_%d' % (label, run[label]))
                    hold['first_frame' if hold.knob('first_frame') else 'firstFrame'].setValue(run[label])
                    hold.setInput(0, raw)
                    endpoints.append(hold)
                pair = nuke.nodes.Switch(name='EndpointPair_%d' % index)
                pair.setInput(0, endpoints[0])
                pair.setInput(1, endpoints[1])
                pair['which'].setExpression('frame < 2 ? 0 : 1')
                # External Cattery RIFE stays a separate dependency.
                rife = nuke.createNode('RIFE', inpanel=False)
                rife.setInput(0, pair)
                rife['in'].setValue(1)
                rife['out'].setValue(2)
                rife['timing'].setValue('Frame')
                rife['skipKeyframes'].setValue(True)
                rife['timingFrame'].setExpression('1 + clamp((frame - %d) / %d.0, 0, 1)' %
                    (run['left'], run['right'] - run['left']))
                rife['outputFrame'].setExpression('timingFrame')
                rife['useGPU'].setValue(node['use_gpu'].value())
                rife['detail'].setValue(int(node['detail'].value()))
                rife['downrez'].setValue(int(node['downrez'].getValue()))
                patch = nuke.nodes.Switch(name='Fill_%d_%d' % (run['start'], run['end']))
                patch.setInput(0, result)
                patch.setInput(1, rife)
                patch['which'].setExpression('frame >= %d && frame <= %d' % (run['start'], run['end']))
                endpoints[0].setXYpos(x, 80)
                endpoints[1].setXYpos(x + 150, 80)
                pair.setXYpos(x, 160)
                rife.setXYpos(x, 240)
                patch.setXYpos(x, 340)
                result = patch
            output = nuke.nodes.Output()
            output.setInput(0, result)
        old = node.node('Repair')
        node.node('Output1').setInput(0, repair)
        if old is not None:
            nuke.delete(old)
        repair.setName('Repair')
    except Exception:
        nuke.delete(repair)
        raise


def analyze(node):
    source = node.input(0)
    if source is None:
        raise RuntimeError('Connect one input first.')
    first, last = int(node['first'].value()), int(node['last'].value())
    if first > last:
        raise ValueError('Frame range starts after it ends.')
    progress = nuke.ProgressTask('Repeat Frame RIFE')
    saved_frame = nuke.frame()
    saved_proxy = nuke.root()['proxy'].value()
    saved_selection = nuke.selectedNodes()
    try:
        nuke.root()['proxy'].setValue(False)
        values = _differences(source, first, last, progress)
        runs, trailing = find_runs(first, last, values, float(node['tolerance'].value()))
        if progress.isCancelled():
            raise RuntimeError('Analysis cancelled; previous repair retained.')
        progress.setMessage('Building RIFE repairs')
        _build(node, runs)
        count = sum(r['end'] - r['start'] + 1 for r in runs)
        data = dict(first=first, last=last, runs=runs, trailing=trailing, differences=values)
        node['analysis_json'].setValue(json.dumps(data))
        ranges = ', '.join('%d-%d' % (r['start'], r['end']) for r in runs)
        node['status'].setValue('%d frames / %d runs repaired. %d trailing copies unchanged.\n%s' %
                               (count, len(runs), len(trailing), ranges or 'No repeated runs.'))
        progress.setProgress(100)
    finally:
        nuke.root()['proxy'].setValue(saved_proxy)
        nuke.frame(saved_frame)
        for selected in nuke.selectedNodes():
            selected['selected'].setValue(False)
        for selected in saved_selection:
            selected['selected'].setValue(True)
        del progress
