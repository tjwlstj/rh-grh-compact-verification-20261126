# MIT 공개 해답과 로컬 해답의 선언별 비교

두 입력은 공식 Lean 4.35.0의 `leanexport`가 낸 NDJSON 3.1.0이다. `compare_exports.py`는 이를 데이터로 읽어 선언 이름과 개별 필드를 비교한다. 수학적 판정에 사용한 도구는 공식 Lean 커널과 Lake Comparator다. [공식 export 형식](https://github.com/leanprover/lean4/blob/eb6cafb7290e8bd5f2937522d8d804f58f02bafc/src/LeanExport/Basic.lean) · [커널 실행](../../evidence/comparator.json)

**209,643개 선언 전부의 이름·순서·타입이 같았다.** 209,642개 선언의 모든 필드가 일치했다. 유일한 차이는 `HCParam.HasGap.two_mul_lowestKType_sub_vacuumWeight._proof_1_4`의 `value`였다. 같은 이름을 참조하는 상위 선언과 재귀 규칙까지 이 범위에서 일치했다. MIT의 원시 표현식은 93,313,601개, 로컬은 93,313,671개다. 생성자와 재귀자를 별도 선언으로 센 수가 209,643이고, 귀납형 묶음을 한 줄로 센 선언 레코드 수는 각각 204,583이다. [전체 대조](declaration-diff.json) · [두 SQLite 인덱스 독립 조회](index-recheck.json)

| 원시 입력 | 바이트 | SHA-256 |
|---|---:|---|
| MIT `compact-solution.ndjson` | 5,172,274,528 | `ab7b4223b9bd748a1aa68bdb63afb6d6264121fc834aadba7ba3d3796c32115b` |
| 로컬 `solution-comparator.ndjson` | 5,172,278,111 | `5a4ab2e2c6db4ca5ea3bafbe76157f8db5ab520e1eaacd5a13350eafad1e96f6` |

MIT의 압축본을 공개 URL에서 받아 압축을 풀고 게시된 원시 해시와 대조했다. 로컬 쪽은 공개 릴리스에서 다시 내려받아 같은 원시 해시를 확인했다. [MIT 원본](https://math.mit.edu/~drew/shortgrh/compact-solution.ndjson.zst) · [MIT 체크섬](https://math.mit.edu/~drew/shortgrh/exports.sha256) · [MIT 파일 수신 기록](reference-receipt.json) · [로컬 재현 파일](https://github.com/tjwlstj/rh-grh-compact-verification-20261126/releases/tag/compact-replay-20261127) · [릴리스 재다운로드 검산](../../evidence/release-readback.json)

## 어떻게 같은 선언을 찾는가

각 최상위 정리의 타입과 증명값 지문도 직접 조회했다. 다섯 쌍 모두 일치했다. 이 비교에 걸린 시간은 양쪽 인덱스 생성과 전체 선언 조회를 합쳐 15분 56초였다. [다섯 정리의 타입·본문 지문 및 실행 시각](declaration-crosscheck.json)

파일 안에서 이름·우주 수준·표현식은 숫자 ID를 참조한다. 두 파일의 같은 번호가 같은 식이라는 보장은 없다. 비교기는 각 노드의 종류와 데이터를 자식 노드의 SHA-256과 조합해 새 SHA-256을 계산한다. 이름 구성 요소의 종류, 바인더 이름, 인자 순서, 우주 수준, 메타데이터, 선언 플래그와 재귀 규칙의 우변도 비교한다. 다른 선언을 부르는 표현식은 그 이름을 가리킨다. 따라서 한 보조정리의 값이 달라졌을 때, 이름만으로 그 보조정리를 호출하는 부모의 기록은 양쪽에서 같을 수 있다.

이름별로 짝을 지은 뒤 어느 쪽에만 있는 선언, 같은 이름이지만 필드가 다른 선언, 모든 필드가 일치하는 선언을 집계한다. 두 파일의 원시 SHA-256과 각 인덱스의 자기 비교도 확인한다. 여기서 ‘일치’는 이 정규화의 구조 해시가 같다는 뜻이다. Lean의 정의적 동치 판정, 최적성 판정 또는 빌드 환경에 따른 인과 분석은 별개의 검사다. [비교기](compare_exports.py)

## 재현

Python 3.11 표준 라이브러리로 실행했다. 공개 릴리스의 gzip은 동봉된 `verify_gzip.py`로 해제할 수 있다. MIT 파일은 zstd 압축을 해제한다. 당시 Windows 실행에 사용한 도구는 서명과 해시를 확인한 시스템 libarchive였다. 그 장비에서 쓴 해제 코드를 함께 보존했다. 이 코드를 재생할 경우 별도 작업 폴더에 코드와 압축본을 두어야 한다. [Windows 해제 원문](unpack_reference.py) · [릴리스 재현 명령](../../재현-명령.md)

다음은 원시 입력을 현재 디렉터리에 두고 실행하는 명령이다. `research/reference`는 이 저장소 안의 경로다. 인덱스 폴더와 결과 파일은 새 경로를 지정한다.

```sh
python -I -B -S research/reference/compare_exports.py compact-solution.ndjson solution-comparator.ndjson --left-sha ab7b4223b9bd748a1aa68bdb63afb6d6264121fc834aadba7ba3d3796c32115b --right-sha 5a4ab2e2c6db4ca5ea3bafbe76157f8db5ab520e1eaacd5a13350eafad1e96f6 --work compare-index --out declaration-diff.json
python -I -B -S research/reference/verify_indexes.py compare-index declaration-diff.json
python -I -B -S research/reference/byte_bounds.py solution-comparator.ndjson compact-solution.ndjson
python -I -B -S research/reference/window-proof.py --reference compact-solution.ndjson --local solution-comparator.ndjson --output first-difference.json
python -I -B -S research/reference/test_compare_exports.py
```

작은 A/B 해답 592개 선언의 비교에서는 `witness.value`만 바뀌었다. 또 같은 파일의 표현식 번호 14,925개를 비롯해 이름·우주 수준 번호까지 재배열했을 때 592개 선언이 모두 일치했다. 생성자의 `isUnsafe`와 재귀 규칙의 우변을 각각 바꾼 대조에서는 바꾼 두 필드가 검출됐다. [A/B 결과](control-ab.json) · [재번호화와 대조 시험](control-renumber.json) · [같은 명제의 두 증명 실험](../control/README.ko.md)

## 첫 차이를 원문에서 찾기

처음 1,609,052,714바이트가 같다. 처음 다른 레코드는 표현식 `28548217`인 함수 적용이다. 거기서 처음 만나는 이름 있는 선언은 두 파일 모두 `HCParam.HasGap.two_mul_lowestKType_sub_vacuumWeight._proof_1_4`다. 공통 구간의 이름 조각을 이어 이 이름을 복원했다. 선언 타입은 같은 공통 구간에 있는 표현식 `28545808`로, 네 개의 바인더를 지나면 등식이 나온다. 선언의 증명값 번호는 MIT `28548934`, 로컬 `28549015`다. [원시 바이트의 공통 구간](byte-bounds.json) · [이름·타입·양쪽 선언의 원문 위치](window-proof.json)

| 구간 | MIT | 로컬 | 로컬에서 늘어난 양 |
|---|---:|---:|---:|
| 처음 다른 레코드의 시작부터 해당 선언 끝까지 | 719행, 42,538바이트 | 800행, 46,664바이트 | 81행, 4,126바이트 |
| 선언이 끝난 다음부터 파일 끝까지 | 65,342,054행, 3,563,179,290바이트 | 65,342,043행, 3,563,178,747바이트 | −11행, −543바이트 |
| 두 파일 전체 | 94,888,225행 | 94,888,295행 | 70행, 3,583바이트 |

앞 구간의 행 수 차이는 함수 적용 표현식 81개다. 이 구간에 있는 MIT 표현식 718개와 로컬 표현식 799개는 각각 전부 해당 보조정리의 증명값에서 도달한다. 처음 달라진 식까지 실제 자식 참조도 복원했다. MIT에서 63단계, 로컬에서 33단계였다. 뒤 구간의 −543바이트는 남은 데이터 길이의 차이다. 이 측정은 선언별 구조 비교와 독립적으로 원시 파일의 실제 위치에서 얻었다. [바이트 위치·증명값 참조·구간 집계 코드](window-proof.py)
