# 같은 명제에 다른 증명항을 사용한 대조 실험

두 버전은 공통 목표 `witness`와 `result`를 모두 만족했다. 공식 Lean 4.36.0 기본 커널이 각각 증명을 수락했고, Lake Comparator는 두 번 모두 종료 코드 0을 반환했다. 두 solution 파일은 길이가 같지만 1바이트가 다르다. [실행 기록](evidence/receipt.json) · [A 표준 출력](evidence/compare-a.out) · [B 표준 출력](evidence/compare-b.out)

## 바꾼 줄

```lean
theorem witness (P : Prop) (a b : P) : P := a
```

B에서는 오른쪽의 `a`만 `b`로 바꿨다. `theorem result (P : Prop) (a b : P) : P := witness P a b`를 비롯한 나머지 원문과 모듈명 `Solution`은 같다. 두 버전 모두 Lean Core의 `Init`만 import한다. 도전 명세의 두 정리는 같은 이름과 타입을 가지며 `sorry`로 자리를 채웠다. 허용 공리는 두 검사 모두 `propext`, `Quot.sound`, `Classical.choice`였다. [A 원문](src/a/Solution.lean) · [B 원문](src/b/Solution.lean) · [목표 원문](src/challenge/Challenge.lean) · [Comparator 설정](comparator.json)

| 입력 | 바이트 | NDJSON 행 | SHA-256 |
|---|---:|---:|---|
| 공통 Challenge | 1,018,100 | 18,511 | `353f3424d46153d1b24a8144c3ca2d11b9a903bf1842499f93882af67c1a8094` |
| Solution A | 1,015,118 | 18,426 | `e48debaf4efddfa62386a473fbd0a33af0d7d4ebfbf440727063bfc4a80ca96d` |
| Solution B | 1,015,118 | 18,426 | `829f7c1871bb205113b2d0e1234350a1dd1084b833b4fb05c2366d9bf5c63570` |

Lean 4.35.0의 `leanexport`로 [같은 35개 루트](export-roots.txt)를 같은 순서로 지정했다. A와 B의 원시 파일을 바이트별로 비교하면 0부터 센 위치 6,646에서 ASCII `2`가 `1`로 바뀐다. 1부터 센 127번째 행에는 `witness`의 가장 안쪽 람다가 있다. 다음은 그 행의 원문이다. [A export](exports/a.ndjson) · [B export](exports/b.ndjson) · [목표 export](exports/challenge.ndjson)

```json
{"ie":90,"lam":{"binderInfo":"default","body":2,"name":22,"type":2}}
{"ie":90,"lam":{"binderInfo":"default","body":1,"name":22,"type":2}}
```

`body`는 식 번호를 가리킨다. 식 2는 바깥쪽으로 한 단계 떨어진 바인더를 가리키는 `bvar 1`이며 여기서는 `a`다. 식 1은 가장 가까운 바인더를 가리키는 `bvar 0`이며 여기서는 `b`다. `witness` 선언은 두 파일 모두 타입 식 89와 증명 식 92를 참조한다. `result`의 본문은 두 파일 모두 같은 이름 `witness`를 적용한다. [원시 차이와 오프셋](evidence/receipt.json)

## 공리와 증명 무관성

Lean 4.35.0에서 `#print axioms`를 실행했다. 명세의 두 자리표시자는 `sorryAx`에 의존했다. A와 B의 `witness`와 `result`는 모두 공리에 의존하지 않는다고 출력됐다. 별도 파일에서 `(P : Prop) (a b : P) : a = b`와 두 함수 본문의 동등성을 각각 `rfl`로 증명했다. 두 동등성 정리도 컴파일됐고 공리 의존성이 없었다. Lean은 같은 명제의 두 증명을 정의적으로 같게 취급한다. 이 실험은 그 성질이 허용하는 두 증명항이 서로 다르게 직렬화되는 한 사례다. RH 축약판의 두 실제 해답은 [선언별 비교](../reference/)에서 대조한다. [동등성 원문](src/equality/Equality.lean) · [정리별 실제 출력](evidence/receipt.json)

## 재현 명령

실행에는 전용 비특권 Windows AppContainer를 사용했다. 네트워크 capability는 0, 입력과 공식 도구는 읽기 전용, 각 실행의 메모리 한도는 2 GiB였다. Windows에는 Linux namespace가 없어 Comparator에 `--inadvisably-no-sandbox`를 전달했다. 두 실행 모두 이 선택을 알리는 경고를 표준 오류에 남겼다. 최초 준비 시 상대 입력 경로를 자식의 작업 폴더 기준으로 해석해 파일을 열지 못했다. 이후 절대경로로 해석한 인자로 원문을 실제 컴파일했다. [A 표준 오류](evidence/compare-a.err) · [B 표준 오류](evidence/compare-b.err) · [전체 인자와 종료 코드](evidence/receipt.json)

다음은 같은 입력을 준비하는 셸 명령이다. 이 문서가 있는 디렉터리를 기준으로 하며, `LEAN435_BIN`과 `LEAN436_BIN`에는 각각 해당 버전의 공식 도구가 있는 디렉터리를 지정한다. `repro`에는 새로 생성한 산출물을 모은다. Linux의 기본 sandbox를 지원하는 환경에서는 마지막 두 호출에 `--inadvisably-no-sandbox`를 추가할 필요가 없다. 아래 예시의 기본 호출은 Linux sandbox를 사용한다. 실제 Windows 호출에 쓰인 모든 인자는 실행 기록에 보존돼 있다. [Lean 4.35.0](https://github.com/leanprover/lean4/releases/tag/v4.35.0) · [Lean 4.36.0](https://github.com/leanprover/lean4/releases/tag/v4.36.0)

```bash
set -eu
ROOT="$PWD"
mkdir repro
mkdir -p repro/{a,b,challenge,equality,compare}
mapfile -t roots < export-roots.txt
for version in a b challenge equality; do
  case "$version" in
    a|b) module=Solution ;;
    challenge) module=Challenge ;;
    equality) module=Equality ;;
  esac
  work="$ROOT/repro/$version"
  src="$ROOT/src/$version"
  (cd "$work" && LEAN_PATH="$work" "$LEAN435_BIN/lean" -j1 \
    -R "$src" -o "$work/$module.olean" "$src/$module.lean")
  if [ "$version" != equality ]; then
    (cd "$work" && LEAN_PATH="$work" "$LEAN435_BIN/leanexport" \
      "$module" -- "${roots[@]}") > "$work/$version.ndjson"
  fi
done
for version in a b; do
  (cd "$ROOT/repro/compare" && PATH="$LEAN436_BIN:$PATH" "$LEAN436_BIN/lake" comparator \
    --config "$ROOT/comparator.json" \
    --challenge-from-export "$ROOT/repro/challenge/challenge.ndjson" \
    --solution-from-export "$ROOT/repro/$version/$version.ndjson")
done
sha256sum repro/{challenge/challenge,a/a,b/b}.ndjson
```
