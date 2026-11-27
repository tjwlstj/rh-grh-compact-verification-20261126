# 다섯 정리의 증명값이 실제로 참조하는 보조정리

**소스에서 다시 빌드한 Main의 다섯 정리는 모두 `HCParam.HasGap.two_mul_lowestKType_sub_vacuumWeight._proof_1_4`에 도달한다.** 원시 NDJSON 안에서 각 정리의 증명값에 나타나는 상수 참조를 다른 선언의 값으로 계속 따라가 확인했다. 다섯 정리 어디에도 이 보조정리가 직접 나타나지 않았으며, 각 정리의 타입에서 출발하면 타입과 값을 모두 열어 보아도 도달하지 않았다. [목표별 원자료](main-raw-lineage.json) · [다섯 정리의 고정 소스](https://github.com/lsernau/grh-lean/blob/72fead102f663d5c7a407964a13dc0cf9d977207/grh-compact/src/Main.lean#L4-L13)

| 최상위 정리 | 원시 NDJSON의 선언 행 | 선택한 실제 경로의 첫 참조 | 보조정리까지 연결 수 |
|---|---:|---|---:|
| `riemannHypothesis` | 94,883,554 | `New.grh` | 18 |
| `riemannZeta_eq_zero_re` | 94,883,557 | `riemannHypothesis` | 19 |
| `LFunction_ne_zero_of_half_lt_re` | 94,883,559 | `New.grh` | 18 |
| `LFunction_eq_zero_re` | 94,888,247 | `New.grh` | 18 |
| `LFunction_eq_zero_re_of_isPrimitive` | 94,888,281 | `LFunction_eq_zero_re` | 19 |

표의 길이는 재현할 수 있는 한 경로의 선언 간 연결 수다. 최단 경로를 구하지 않았다. 경로마다 마지막 연결은 부모 정리 `HCParam.HasGap.two_mul_lowestKType_sub_vacuumWeight`의 값에 있다. 부모의 선언은 29,549,378행, 보조정리를 직접 가리키는 `const`는 29,549,185행의 표현식 28,551,941이다. 보조정리 자체는 29,546,252행의 `thm`이고, 이름 인덱스는 856,794, 타입과 증명값의 표현식 인덱스는 각각 28,545,808과 28,549,015다. [부모 정리의 소스 55–60행](https://github.com/lsernau/grh-lean/blob/72fead102f663d5c7a407964a13dc0cf9d977207/grh-compact/src/Lib/DiscreteSeries/Theta/JointHarmonicUnique.lean#L55-L60)

### 어떤 수학적 단계들을 지나나

다섯 경로는 `New.grh`에서 합쳐진다. 선택한 경로는 소수 오차항을 다루는 `eventually_primeError_le_rpow`에서 `star_inequality`로, 그 증명값 안의 `Data.IndexLe` 참조에서 `Data.Θ`로 이어진다. 코드에서 `Data.Θ`는 `D.iotaAtLevel`과 행 부분공간의 포함 사상을 합성한 선형 사상이다. 이 경로는 이후 `IsJointHarmonic.howe_argument`와 최저 K-타입 부등식에 사용된 선언을 거쳐 보조정리에 이른다. 여기서 사용했다는 말의 범위는 해당 빌드가 저장한 증명항 또는 정의값 안의 참조다. [최종 부등식](https://github.com/lsernau/grh-lean/blob/72fead102f663d5c7a407964a13dc0cf9d977207/grh-compact/src/New/Main.lean#L121) · [IndexLe](https://github.com/lsernau/grh-lean/blob/72fead102f663d5c7a407964a13dc0cf9d977207/grh-compact/src/New/Endgame/ShortAndEnough.lean#L130) · [Θ 정의](https://github.com/lsernau/grh-lean/blob/72fead102f663d5c7a407964a13dc0cf9d977207/grh-compact/src/New/Rows/RowVolume.lean#L27) · [Howe 논증](https://github.com/lsernau/grh-lean/blob/72fead102f663d5c7a407964a13dc0cf9d977207/grh-compact/src/Lib/DiscreteSeries/Theta/HoweArgument.lean#L13)

### 경로의 범위와 대조군

| 선언 간 추적 범위 | 도달한 최상위 정리 |
|---|---:|
| 타입·값·재귀자 계산 규칙의 실제 표현식 | 5/5 |
| 정의·정리·불투명 선언의 값만 | 5/5 |
| 선언 타입만 | 0/5 |
| 정리·불투명 선언의 값을 닫고 타입과 일반 정의를 따라감 | 0/5 |
| 고정 Lean의 `ConstantInfo.getUsedConstantsAsSet`에 대응하는 필드 | 5/5 |

양성 대조로 `riemannZeta_eq_zero_re`의 값이 `riemannHypothesis`를 직접 참조하는 것을 검출했다. 음성 대조인 `Nat`과 `Classical.choice`에서는 보조정리로 가는 경로가 없었다. 전방 참조된 이름은 5,119개였다. 각 회차의 가정 중 파일 끝까지 읽었을 때 달라진 이름은 차례로 1개, 1개, 0개였다. 마지막 회차에서 참조된 모든 이름을 파일 안의 선언에 연결했다. [순회 규칙과 귀납형 처리](method.ko.md)

### 입력과 재현

원본은 이 PC에서 만든 `solution-comparator.ndjson` 5,172,278,111바이트이며 SHA-256은 `5a4ab2e2c6db4ca5ea3bafbe76157f8db5ab520e1eaacd5a13350eafad1e96f6`이다. 94,888,295줄에서 표현식 93,313,671개를 읽었다. 선언 레코드는 204,583개이고, 한 귀납형 레코드 안의 생성자와 재귀자까지 개별 선언으로 세면 209,643개다. 포맷은 공식 Lean 4.35.0의 NDJSON 3.1.0이다. 이 실험은 원본 파일을 데이터로 읽었다. [공개 입력 영수증](https://github.com/tjwlstj/rh-grh-compact-verification-20261126/releases/download/compact-replay-20261127/solution-pack.json)

실제 검사한 두 스크립트와 입력 검산·실행 절차는 [재현 안내](README.md)에 있다.

두 명령 모두 종료 코드 0을 반환했다. 첫 검사에서 얻은 경로의 중복을 제거하니 선언 사이의 연결이 22개였다. 두 번째 검사기는 이 22개를 하나씩 원본 행에서 다시 읽어, 선언 필드에서 해당 상수 참조까지 이어지는 자식 표현식 인덱스 총 676단계를 복원했다. 마지막 연결만 예로 들면, 부모 정리의 증명값인 표현식 28,552,133에서 자식 24단계를 따라가면 보조정리 이름을 직접 가리키는 표현식 28,551,941에 닿는다. [목표별 결과](main-raw-lineage.json) · [22개 연결의 원문 행 및 자식 인덱스](raw-edge-certificates.json) · [전체 추적기](trace_ndjson.py) · [개별 연결 검산기](verify_edges.py)

