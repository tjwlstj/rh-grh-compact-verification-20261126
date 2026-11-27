# 다섯 정리의 증명에서 내부 보조정리까지

**11월 26일 축약판에서 다섯 정리의 증명은 같은 가중치 보조정리를 참조한다.** 소스에서 직접 빌드한 794개 모듈의 `Main`을 Lean 4.35.0으로 읽었다. 다섯 정리에서 출발한 최단 경로는 `New.grh`에서 합쳐지고, 이후 12번의 직접 참조를 거쳐 `HCParam.HasGap.two_mul_lowestKType_sub_vacuumWeight._proof_1_4`에 이른다. 각 단계에서 앞 정리의 실제 증명항이 다음 정리를 참조한다. 이 결론의 범위는 고정판의 이 다섯 증명항이다. [검사한 축약판 소스](https://github.com/lsernau/grh-lean/tree/72fead102f663d5c7a407964a13dc0cf9d977207/grh-compact) · [다섯 목표의 전체 커널 검사](../../evidence/comparator.out)

| 출발 정리 | 증명항에서 보조정리까지 최소 참조 수 | 첫 참조를 명제의 타입에 한정할 때 |
|---|---:|---|
| `riemannHypothesis` | 13 | 경로 없음 |
| `riemannZeta_eq_zero_re` | 14 | 경로 없음 |
| `LFunction_ne_zero_of_half_lt_re` | 13 | 경로 없음 |
| `LFunction_eq_zero_re` | 13 | 경로 없음 |
| `LFunction_eq_zero_re_of_isPrimitive` | 14 | 경로 없음 |

### 어떤 계산이 들어 있는가

보조정리는 인덱스 `r`를 하나 고정하고 두 정수값 함수가 같다고 말한다. 왼쪽은 두 인덱스의 부호가 같은지와 가중치의 대소 관계에 따라 0과 1을 더하고 뺀 함수다. 오른쪽의 `j`에서의 값은 `↑(ε r) * ↑(ε j) * (l j - l r).sign`이다. 부모 정리 `HCParam.HasGap.two_mul_lowestKType_sub_vacuumWeight`가 이 보조정리를 직접 사용한다. 해당 모듈 69개 선언의 직렬화된 타입·본문을 별도로 읽었을 때도 이 부모의 본문에서 유일한 직접 참조가 나왔다. [Lean이 표시한 타입](focus-type.txt) · [타입 구조와 직접 참조 대조](focus-type-structure.json)

### 공통 경로

아래 목록에서 각 줄의 정리는 바로 다음 줄의 정리를 증명항에서 참조한다. `riemannHypothesis`, `LFunction_ne_zero_of_half_lt_re`, `LFunction_eq_zero_re`는 첫 줄을 직접 참조한다. `riemannZeta_eq_zero_re`는 `riemannHypothesis`를, 원시 지표 정리 `LFunction_eq_zero_re_of_isPrimitive`는 `LFunction_eq_zero_re`를 한 번 거친다. 같은 길이의 후보가 여럿이면 다음 상수 이름의 사전순으로 경로 하나를 골랐다. [ID·선언 종류·간선 필드까지 기록한 모든 경로](result.json)

```text
New.grh
eventually_primeError_le_rpow
star_inequality
Data.integral_forms_long
Data.heightLe_volume_rows
Data.crude_rows
Data.gridPeriod_eq_endPeriod
exists_lift_ofAlgForm_eq_smul
IsMatch.unique
IsMatch.sign_mul_lowestKType_sub_nonneg
IsMatch.sign_mul_lowestKType_sub_nonneg._proof_1_11
HCParam.HasGap.two_mul_lowestKType_sub_vacuumWeight
HCParam.HasGap.two_mul_lowestKType_sub_vacuumWeight._proof_1_4
```

### 배포한 그래프로 검산하기

Python 3.11 이상과 표준 라이브러리만 사용한다. 이 디렉터리에서 다음을 실행한다. Windows에서는 `python`을 `py -3`으로 바꿀 수 있다.

```sh
python -I -B replay.py --check-files
python -I -B replay.py
```

첫 명령은 공개 파일을 [SHA-256 목록](SHA256SUMS)과 대조한다. 두 번째 명령은 압축 그래프에서 목적지부터 역방향 너비 우선 탐색으로 최단 경로를 재구성한다. 별도의 탐색이 각 출발점에서 정방향으로 이동해 104개 질의의 거리를 검산한다. 두 거리와 공개 결과의 경로·ID·간선 필드·공리 목록이 모두 일치해야 종료 코드 0을 반환한다. 이 고정 입력의 출력은 `graphVertices=207763`, `bidirectionalQueries=104`, `referenceMatched=true`다. [최초 독립 검산 결과](forward-verification.json)

새로 생성한 비압축 NDJSON 또는 gzip 그래프를 입력할 수 있다. 첫 명령은 원자료 SHA와 기록된 연구 결과까지 비교한다. 두 번째 명령은 다른 빌드에서 얻은 그래프의 양방향 계산 결과를 새 JSON 파일에 쓴다. 이때 `referenceMatched=false`는 기존 결과와의 대조를 요청하지 않았다는 의미다.

```sh
python -I -B replay.py --graph other/lineage-graph-v1.ndjson --expected result.json
python -I -B replay.py --graph other/lineage-graph-v1.ndjson --measure-only --output other/paths.json
```

### 직접 빌드한 Main에서 그래프 추출하기

원 실행은 네트워크 기능이 없는 Windows AppContainer에서 공식 Lean 4.35.0, 고정 Mathlib와 공식 의존성, 직접 빌드한 프로젝트 라이브러리를 사용했다. Job 상한은 15 GiB였고 피크는 11,299,364,864바이트였다. `Lineage.lean`의 직접 import는 `Main` 하나다. [실제 명령·바이너리·입력 해시 및 종료 코드](portable-receipt.json) · [Lean 완료 출력](lineage-v1.out) · [소스 빌드 절차](../../재현-명령.md)

다시 추출하려면 같은 도구·소스와 고정 의존성을 직접 준비한 격리 환경에서 [판독 코드](Lineage.lean)를 실행한다. `extract.py`는 이미 준비한 환경에서 공식 실행 파일과 읽을 라이브러리 경로를 지정하는 도우미다. 격리와 자원 한도는 실행 환경에서 설정한다. 다음은 Bash 예시다. `LEAN435`는 검증한 공식 실행 파일, `MAIN_LIB`는 직접 빌드한 `Main.olean`이 있는 디렉터리, `MATHLIB`는 고정 Mathlib 체크아웃으로 설정한다. `OUT`은 비어 있는 새 결과 디렉터리다.

```bash
deps=(--dep "$MATHLIB/.lake/build/lib/lean")
for package in plausible LeanSearchClient importGraph proofwidgets aesop Qq batteries Cli; do
  deps+=(--dep "$MATHLIB/.lake/packages/$package/.lake/build/lib/lean")
done
python -I -B extract.py --lean "$LEAN435" --library "$MAIN_LIB" "${deps[@]}" --work "$OUT" --show
python -I -B extract.py --lean "$LEAN435" --library "$MAIN_LIB" "${deps[@]}" --work "$OUT"
python -I -B replay.py --graph "$OUT/lineage-graph-v1.ndjson" --measure-only --output "$OUT/paths.json"
```

`--show`는 선택한 명령과 경로만 표시한다. 추출 시 도우미는 Lean 버전과 커밋을 확인하고 `lean -j1 --tstack=400000 Lineage.lean`을 실행한다. 이때 생기는 두 파일은 `lineage-graph-v1.ndjson`과 `lineage-needle-type.txt`다. 공개 결과의 Lean 판독 파일은 원 실행의 바이트를 보존했다. 서로 다른 빌드의 그래프·모듈 바이트 일치 여부는 각각 SHA-256으로 확인할 수 있다.

로컬 재현에 쓰인 바이트와 동일한 `JointHarmonicUnique.olean`이 있으면, 아래 명령으로 69개 선언 안의 직접 참조와 타입 객체 283개를 별도 확인한다. 이 Python 검산은 입력을 이진 데이터로 읽는다. [직렬화된 타입에서 포인터를 ID로 치환한 원문](focus-type-dag.json)

```sh
python -I -B type_dag.py --olean "$MAIN_LIB/Lib/DiscreteSeries/Theta/JointHarmonicUnique.olean"
```

### 측정 기준과 대조군

- 상수의 정확한 Lean `Name`을 숫자 ID로 바꾸고 커널의 `ConstantInfo`를 방문했다. 타입과 본문의 표현식에서 상수와 구조체 투영에 쓰인 구조 이름을 추출한다. `value? (allowOpaque := true)`로 정리·불투명 선언까지 본문을 읽는다. 조사한 207,763개 선언 중 해석되지 않은 이름과 겹치는 표시 이름은 각각 0개다. [공식 표현식 순회](https://github.com/leanprover/lean4/blob/eb6cafb7290e8bd5f2937522d8d804f58f02bafc/src/Lean/Util/FoldConsts.lean#L24-L60) · [공식 선언의 본문 필드](https://github.com/leanprover/lean4/blob/eb6cafb7290e8bd5f2937522d8d804f58f02bafc/src/Lean/Declaration.lean#L483-L488)
- 기본 그래프는 타입과 본문의 직접 참조만 따른다. 확장 그래프는 귀납형의 생성자와 상호 귀납 블록, 생성자의 귀납형, recursor의 귀납형·규칙별 생성자와 우변, 정의·정리·불투명 선언의 mutual 목록을 더한다. 어느 쪽이든 다섯 최단거리는 같다. 소스의 모듈 import는 거리 계산에 사용하지 않았다.
- 직접 참조 양성 대조는 부모 정리의 증명에서 보조정리로 가는 한 간선과 `riemannZeta_eq_zero_re`의 증명에서 `riemannHypothesis`로 가는 한 간선이었다. 음성 대조인 `Nat.add_comm`, 다섯 명제 자체의 정의, 보조정리 자체의 타입에서는 도달 경로가 없었다. 보조정리에서 같은 이름으로 돌아오는 길이 0인 경로는 타입 대조에서 제외했다.
- 각 목표에서 타입·본문으로 도달한 모든 선언을 방문해 얻은 공리는 각각 `Classical.choice`, `Quot.sound`, `propext`였다. 이는 별도로 실행한 `#print axioms` 출력과 일치한다. 경로는 표현식에서 직접 읽었다. 고정 공식 Lean 커밋의 세 소스 파일은 로컬 배포본과 GitHub 원문이 바이트 단위로 일치했다. [공리 원출력](../../evidence/source-axioms.out) · [공식 공리 수집 구현](https://github.com/leanprover/lean4/blob/eb6cafb7290e8bd5f2937522d8d804f58f02bafc/src/Lean/Util/CollectAxioms.lean) · [공식 파일별 해시](official-references.json)

| 보존한 입력 | 크기 | SHA-256 |
|---|---:|---|
| [압축 그래프](graph.ndjson.gz) | 17,542,573바이트 | `94ebaa3c0f7996e309ff078e5c51d1ab386aea2bef4535c7aabfcd50058edfff` |
| 압축 해제 NDJSON | 76,561,497바이트 | `bc289fce795875fb987520105611a1d4bc169c213bf788942b93fd58d3dec2d8` |
| [Lean 표기 타입](focus-type.txt) | 433바이트 | `2eeb7c14df996cb9bdc06d6b103a7a2978013d5652cd95eda64884168b769345` |

원 실행에서 옮긴 아홉 파일은 각각 바이트 전체를 대조했다. 공개용 판독기에서도 압축 그래프와 원시 NDJSON을 각각 다시 계산했다. [원 실행 파일별 바이트·해시](original-file-hashes.json) · [배포본으로 다시 실행한 명령과 결과](public-recheck.json)
