# RepeatFrame RIFE for Nuke

원본 영상 없이 **입력 하나**에서 연속 반복 프레임을 찾아 RIFE로 교체하는 Nuke 노드입니다. [FrameMatch for Nuke](https://github.com/tardis7732/FrameMatch-for-Nuke)의 원본 비교 워크플로와 별도로 사용할 수 있습니다.

## 동작

프레임 값의 나열을 예로 들면:

```text
1234456789  → 1234(4.5)56789
12344456789 → 1234(4.3333)(4.6667)56789
12346789    → 12346789  (반복이 없으므로 변경 없음)
```

첫 번째 4는 유지하고, 뒤의 중복 복사본을 첫 4와 다음 5 사이의 균등한 시점으로 보간합니다. 전체 프레임 수와 타임라인은 유지합니다. 두 복사본이면 RIFE 시점은 1/3, 2/3입니다. 위 숫자는 픽셀 값이 아니라 보간 시점을 나타냅니다.

마지막까지 같은 프레임이 반복되면 다음 정상 프레임이 없으므로 그대로 둡니다. 입력 범위 밖의 프레임과 반복으로 분류되지 않은 프레임도 그대로 통과합니다. 자동으로 누락 프레임을 추측하거나 프레임을 추가하지 않습니다.

## 설치

1. **NukeX**와 [Cattery RIFE](https://github.com/rafaelperez/RIFE-for-Nuke)를 설치합니다. `RIFE` 노드를 생성할 수 있어야 합니다. 모델은 이 저장소에 포함하지 않습니다.
2. 이 저장소를 내려받아 PowerShell에서 `./install.ps1`을 실행합니다.
3. NukeX를 다시 열고 **Tab → RepeatFrameRIFE**를 선택합니다. 메뉴에서는 **Time → RepeatFrameRIFE**입니다.

수동 설치는 `repeatframe_core.py`, `repeatframe_rife.py`, `menu.py`를 `.nuke/RepeatFrameRIFE/`에 복사하고 `.nuke/init.py`에 다음을 추가합니다:

```python
import nuke
nuke.pluginAddPath('./RepeatFrameRIFE')
```

현재 Nuke를 재시작하지 않고 등록하려면 Script Editor에서 실행합니다:

```python
import os, nuke
path = os.path.join(os.path.expanduser('~'), '.nuke', 'RepeatFrameRIFE')
nuke.pluginAddPath(path)
import repeatframe_rife
nuke.menu('Nodes').addCommand('Time/RepeatFrameRIFE', 'repeatframe_rife.create()')
```

## 사용

1. 노드 입력 하나에 영상을 연결합니다.
2. **Use input range**로 분석 범위를 가져오거나 시작·끝을 직접 지정합니다.
3. **Analyze and build**를 누릅니다. 완료되면 이 노드 출력이 보정된 영상입니다.
4. Results의 교체 범위를 확인하고 Viewer로 검토합니다. **Clear repair**는 원래 입력으로 되돌립니다.

**Repeat tolerance** 기본값은 **0.002**이며 사용자가 직접 조절할 수 있습니다. 전체 포맷 영역에서 각 RGB 채널의 평균 절대 차이를 계산한 뒤 가장 큰 채널값을 임계값과 비교합니다. 정확히 일치하는 프레임만 찾으려면 0으로 설정합니다. 임계값을 높이면 정지 장면·미세한 움직임도 반복으로 분류될 수 있습니다. 알파와 별도 AOV는 분석 대상이 아닙니다. 입력 RGB가 유한한 값을 갖고 포맷과 해상도가 일정한 단일 샷에 사용하세요.

RIFE는 RGBA를 보간하며 기존 추가 채널은 Cattery RIFE의 RGBA 모드 동작을 따릅니다. 입력·범위·임계값·RIFE 설정을 바꾼 뒤에는 다시 분석하세요. 내부 Repair 그룹은 재분석할 때 교체됩니다. 분석 취소나 빌드 실패 시 이전 보정 결과를 유지합니다.

## 검증

Windows / NukeX 17.1v1에서 반복 탐지, 실제 RIFE 추론, 원래 프레임 통과, 저장 후 다시 열기를 확인했습니다.

```text
python -m unittest discover -s tests -v
Nuke17.1.exe -ti tests/nuke_integration.py
```

RIFE 모델 및 Cattery 구현은 Rafael Silva의 [RIFE-for-Nuke](https://github.com/rafaelperez/RIFE-for-Nuke) 외부 의존성입니다. 해당 프로젝트의 라이선스와 모델 조건을 따르세요. Foundry 공식 플러그인은 아닙니다.
