# 원시 NDJSON에서 증명 의존성을 판정한 방법

고정 Lean 4.35.0의 `leanexport Main`이 내보낸 원본을 읽는다. 다섯 최상위 정리와 보조정리의 위치는 정규화한 소스 이름을 검색해서 추정하지 않고, JSON의 이름 표에서 부모 인덱스와 문자열 조각을 이어 복원한다. `thm.name`은 해당 이름의 선언이고, `const.name`은 그 선언을 사용한 표현식이다. 선언의 `type`과 `value`는 각각 명제와 증명값의 표현식 인덱스다. [이름·인덱스 출력](https://github.com/leanprover/lean4/blob/eb6cafb7290e8bd5f2937522d8d804f58f02bafc/src/LeanExport/Basic.lean#L100-L130) · [정리 선언 출력](https://github.com/leanprover/lean4/blob/eb6cafb7290e8bd5f2937522d8d804f58f02bafc/src/LeanExport/Basic.lean#L297-L310)

### 어떤 참조를 세었나

표현식 안에서는 Lean의 `Expr.foldConsts`를 따라 함수 적용의 함수·인자, 람다·전칭의 타입·본문, let의 타입·정의값·본문, 투영의 대상, 메타데이터의 내부 표현식을 순회한다. 이름이 있는 참조는 `const.name`과 `proj.typeName` 두 곳에서 읽는다. 바인더 이름, 우주 수준의 이름, 문자열 리터럴이 정리 이름과 같은 것만으로는 참조가 되지 않는다. 내보내기가 기본 리터럴 지원을 위해 별도로 추가한 상수도 이 구문 경로에서 제외한다. [고정 Lean 순회 코드](https://github.com/leanprover/lean4/blob/eb6cafb7290e8bd5f2937522d8d804f58f02bafc/src/Lean/Util/FoldConsts.lean#L24-L45) · [표현식 내보내기와 리터럴 처리](https://github.com/leanprover/lean4/blob/eb6cafb7290e8bd5f2937522d8d804f58f02bafc/src/LeanExport/Basic.lean#L172-L245)

| 결과 필드 | 한 선언에서 다음 선언으로 이동할 수 있는 곳 |
|---|---|
| `exprTypeValueRules` | 모든 선언의 타입, 정의·정리·불투명 선언의 값, 재귀자의 계산 규칙 우변. 귀납형·생성자·재귀자는 하나의 NDJSON 행 안에서 각자 별도 선언으로 읽는다. |
| `onlyTypes` | 각 선언의 타입만. |
| `onlyBodies` | 정의·정리·불투명 선언의 값만. 값 안의 람다나 let에 적힌 타입은 그 표현식의 일부로 읽는다. |
| `theoremAndOpaqueBodiesSealed` | 모든 선언의 타입, 일반 정의의 값, 재귀자 규칙의 우변. 정리나 불투명 선언의 값으로는 들어가지 않는다. |
| `leanConstantInfoGetUsedConstantsAsSet` | 고정 Lean의 `ConstantInfo.getUsedConstantsAsSet`. 타입과 발견 가능한 값(정리·불투명 값 포함)을 읽는다. 값이 없으면 귀납형은 생성자 목록, 생성자는 자기 이름, 재귀자는 관련 귀납형 이름 목록을 사용한다. |

서로 참조하는 이름 전체를 하나의 증거로 취급하지 않는다. 예를 들어 `all`에 이름이 있거나 같은 귀납형 그룹 행에 있다는 것만으로 첫 번째 방식의 참조를 추가하지 않는다. 다섯 번째 방식에서는 공식 함수가 선택한 필드만 별도로 사용한다. [귀납형 그룹 및 재귀 규칙 형식](https://github.com/leanprover/lean4/blob/eb6cafb7290e8bd5f2937522d8d804f58f02bafc/src/LeanExport/Basic.lean#L324-L429) · [Lean의 선언 단위 함수](https://github.com/leanprover/lean4/blob/eb6cafb7290e8bd5f2937522d8d804f58f02bafc/src/Lean/Util/FoldConsts.lean#L65-L74)

### 직접 참조와 전이 참조

분석기는 표현식의 자식 인덱스가 부모보다 작다는 조건을 확인하면서, 각 표현식에 보조정리로 이어지는 실제 이름 참조가 있는지 기록한다. 선언의 역할에 따라 타입·값·재귀자 규칙의 결과를 조합한다. `directHelper`는 해당 표현식 자체 안에 보조정리 이름의 명시적 참조가 있을 때만 참이다. `policies`는 다른 선언을 거쳐도 도달하는지 나타낸다. 추적 대상 보조정리 자체는 거리가 0인 시작점이다.

아직 선언 레코드가 나오지 않은 이름을 거짓으로 계산했으면 그 가정을 기록한다. 파일 끝에서 실제 결과와 달라진 가정이 있으면, 이미 입증한 참인 값만 보존하고 처음부터 다시 읽는다. 전방 참조 가정이 더 이상 달라지지 않고 모든 사용 이름이 같은 파일의 선언에 대응해야 결과를 확정한다. 각 회차에서 원본 전체의 크기와 SHA-256도 영수증과 대조한다.

별도 `verify_edges.py`는 선언 간 도달성 계산을 사용하지 않는다. 첫 검사에서 보고한 각 연결을 하나씩 떼어 같은 원본에서 두 이름을 다시 복원하고, 선언 필드와 명시적 참조 행의 번호·이름·표현식 인덱스를 대조한다. 그 뒤 두 표현식 사이의 실제 자식 관계만 읽어 소유 표현식부터 해당 상수 참조까지의 자식 인덱스 경로를 별도로 재구성한다. 이 경로는 해당 증명항이 무엇을 참조하는지 보여 준다. 보조정리 없는 다른 수학적 증명의 가능성은 이 검사로 결정할 수 없다.

