# 원시 Lean 내보내기에서 다섯 정리의 의존성 재현

**소스로 다시 빌드한 Main에서 다섯 정리 모두 같은 보조정리를 증명값을 통해 간접 참조한다.** 추적 대상은 `HCParam.HasGap.two_mul_lowestKType_sub_vacuumWeight._proof_1_4`다. 다섯 정리의 타입에서 출발하면 해당 보조정리에 도달하지 않는다. 각 경로에서 중복을 제거한 선언 간 연결 22개를 원본 JSON 행에 대조하고, 해당 상수 사용까지의 표현식 자식 경로를 각각 복원했다. [목표별 판정](results.ko.md) · [참조를 세는 규칙](method.ko.md) · [22개 연결의 검산 기록](raw-edge-certificates.json)

## 입력과 공개 근거

공개 릴리스에서 아래 세 파일을 작업 폴더에 받는다. 저장소에는 추적 코드와 결과만 들어 있다. GitHub의 릴리스 자산 목록에 표시된 압축본 및 영수증 SHA-256을 대조했다. 아래 주소는 해당 릴리스에 고정된 파일이다. [릴리스 개요](https://github.com/tjwlstj/rh-grh-compact-verification-20261126/releases/tag/compact-replay-20261127)

| 파일 | 바이트 | SHA-256 |
|---|---:|---|
| [solution-comparator.ndjson.gz](https://github.com/tjwlstj/rh-grh-compact-verification-20261126/releases/download/compact-replay-20261127/solution-comparator.ndjson.gz) | 812,911,198 | `8d5ac16126ab7a3c986cab7c3d4003c1714850221dfc8ecae89b5030307f6362` |
| [solution-pack.json](https://github.com/tjwlstj/rh-grh-compact-verification-20261126/releases/download/compact-replay-20261127/solution-pack.json) | 2,034 | `bc1c2b7bb741453af8dfdfd96621e677079eda0ec8f1e01dd4bb25e2b0ac05b0` |
| [verify_gzip.py](https://github.com/tjwlstj/rh-grh-compact-verification-20261126/releases/download/compact-replay-20261127/verify_gzip.py) | 1,841 | `9b23076f0b25c99dfe9fc9aed446e65f69a6d0b7d643c469a48992fed1fa66b8` |
| 압축을 해제한 `solution-comparator.ndjson` | 5,172,278,111 | `5a4ab2e2c6db4ca5ea3bafbe76157f8db5ab520e1eaacd5a13350eafad1e96f6` |

MIT에 게시된 compact 해답의 SHA-256은 `ab7b4223b9bd748a1aa68bdb63afb6d6264121fc834aadba7ba3d3796c32115b`다. 이 연구의 행 번호와 표현식 번호는 위 표의 5,172,278,111바이트 원시 파일에 해당한다. [MIT 원본 체크섬](https://math.mit.edu/~drew/shortgrh/exports.sha256)

## 다른 PC에서 실행

예시는 저장소 루트에서 시작한다. 내려받은 세 파일을 `replay-input` 폴더에 둔다. Python 3.11 표준 라이브러리를 사용한다. Windows에서 Python 런처를 사용하면 아래 `python`을 `py -3.11`로 바꾼다. 첫 명령은 gzip과 복원한 원본을 각각 검산한다. 둘째 명령은 새 출력 폴더에 원래 검증에 사용한 두 스크립트를 복사하고 순서대로 실행하며, 이미 복원한 NDJSON을 제자리에서 읽는다.

```sh
python -I -B replay-input/verify_gzip.py replay-input/solution-pack.json replay-input/solution-comparator.ndjson.gz --restore replay-input/solution-comparator.ndjson
python -I -B research/raw-lineage/replay.py --input replay-input/solution-comparator.ndjson --receipt replay-input/solution-pack.json --work raw-lineage-run
```

출력은 `raw-lineage-run/analysis/raw-lineage/`에 생성된다. 이미 복원된 원본이 있으면 두 번째 명령부터 실행한다. 다시 실행할 때는 새 `--work` 폴더 이름을 쓴다. 전체 원본을 순차 판독하는 동안에는 진행률이 출력되지 않는다. 두 스크립트 모두 검사한 실제 원본의 크기와 SHA-256을 결합한다. [실행기](replay.py) · [전수 추적기](trace_ndjson.py) · [연결별 독립 검산기](verify_edges.py)

| 보관한 결과 | 바이트 | 원본 Windows 실행의 SHA-256 |
|---|---:|---|
| [main-raw-lineage.json](main-raw-lineage.json) | 52,290 | `de01d90f947fd457fa6de976a34a992e34f504d95607c8cf3abd1fc96981e534` |
| [raw-edge-certificates.json](raw-edge-certificates.json) | 26,943 | `4245a52728f8def92fead1353dc75b18f1b13382eaac219529f48dc3acd957de` |

실행기는 새 JSON의 모든 판정 필드·원본 해시·참조 경로를 보관본에 대조한다. 첫 결과의 `inputFile`은 실행자가 정한 파일명이라 내용 비교에서 제외한다. OS의 줄 끝 처리나 선택한 원본 파일명이 다르면 생성한 JSON 자체의 바이트 해시는 달라질 수 있다. 실행기는 데이터 일치 여부와 파일 전체 바이트 일치 여부를 각각 출력한다. 이 디렉터리의 배포 파일 해시는 [체크섬 목록](SHA256SUMS.txt)에 있다.

