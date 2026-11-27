# 리만 가설·디리클레 GRH 축약판 검증 기록

2026년 11월 27일, Luke Sernau의 `grh-compact` 소스 794개를 공식 Lean 4.35.0으로 모두 컴파일했다. **직접 만든 `Main`에서 다섯 정리는 각각 `propext`, `Classical.choice`, `Quot.sound` 세 공리에 의존했다.** 전날에는 공개 빌드 캐시를 독립 검사기로 읽어 다섯 정리를 모두 수락했다. 직접 빌드한 해답에 대한 기본 Lean 커널 Comparator 판정은 대기 중이다. [직접 빌드의 공리 출력](evidence/source-axioms.out) · [캐시 독립 검사 원출력](evidence/cache-con-leche.out) · [고정 소스](https://github.com/lsernau/grh-lean/tree/72fead102f663d5c7a407964a13dc0cf9d977207/grh-compact)

| 검사 | 이 PC에서 확인한 결과 |
|---|---|
| 출처·무결성 | Git 파일 1,627개를 대조했다. MIT 목록에 실린 1,625개는 모두 일치했다. [입력 기록](evidence/source-integrity.json) |
| 정적 검사 | 증명 소스 794개에서 검사 대상 미완성 증명·추가 공리·메타 명령 패턴 일치 0건. [검사 범위](evidence/source-review.json) |
| 목표 명제 | Lean 4.35.0에서 RH와 디리클레 L함수의 우반평면·임계띠·원시 지표 정의를 각각 `rfl`로 대조했다. 직접 만든 목표 export의 SHA-256은 MIT 배포값과 일치했다. [Lean 원문](TargetEquivalence.lean) · [목표 해시](evidence/locally-built-challenge.json) |
| 공개 캐시의 다섯 정리 | 공식 `con-leche`의 검증 모드에서 증명 쪽 선언 204,580개를 수락했다. 899.203초, 종료 코드 0. 검사기의 커밋·바이너리 해시·실제 인자·정리 이름을 보존했다. [실행 기록](evidence/cache-con-leche.json) · [캐시 파일 794개의 해시](evidence/oleans.csv) |
| 음성 대조 | 미완성 목표 파일을 그대로 해답으로 넣자 기본 Comparator가 `sorryAx`를 지목하고 종료 코드 1로 거부했다. Windows 바깥쪽 격리는 네트워크 권한 없는 AppContainer를 사용했다. [영수증](evidence/five-goal-negative.json) · [오류 원문](evidence/five-goal-negative.err) |
| 소스 직접 빌드 | 11월 27일 09:44 KST에 `Main`까지 794개 모두 종료 코드 0으로 컴파일됐다. 794개 전체에서 직접 읽은 소스와 산출물의 SHA-256이 로컬 원장과 일치했다. 공개 캐시와 바이트가 같은 모듈은 645개였다. [모듈별 실측 해시](evidence/direct-build-progress.json) |
| 서로 다른 중간 증명항 | `JointHarmonicUnique`의 보조정리 하나는 두 빌드의 타입이 같고 증명항이 달랐다. 해당 정리를 양쪽에서 각각 선택해 검사하자 독립 커널이 두 번 모두 2,777개 선언을 수락했다. [양쪽 검사 결과](evidence/joint-harmonic-checks.json) |
| 직접 빌드한 다섯 정리의 공리 | `import Main` 뒤 목표별 `#print axioms` 실행이 종료 코드 0으로 끝났다. 다섯 줄 모두 같은 세 공리를 출력했다. [다섯 줄 원문](evidence/source-axioms.out) · [실행 영수증](evidence/source-axioms.json) |
| 소스 전체의 최종 판정 | 직접 빌드한 전체 해답의 export와 기본 Lean 커널 Comparator 결과는 이 시점에 대기 중이다. |

[검증 보고서](축약판-검증.md)에는 원판과의 목표 대조, 도구 버전, MIT의 별도 실행 결과가 있다. [체시의 수학 노트](체시의-수학노트.md)는 세타 리프트로 얻은 격자 부피의 두 추정이 소수합의 오차를 어떻게 제한하는지 코드에서 따라간다. [실행한 예제](ProjectWeights.lean)는 같은 합동류의 두 소수에서 실제 가중치가 각각 0과 `2 * log 258721`이 되는 것을 확인한다.

[다섯 명제 해설](다섯-명제.md)은 제타 함수의 자명한 영점, 주지표의 극점, 열린 임계띠를 각 선언이 어떻게 다루는지 정리한다. [실행 명령과 재부팅 후 재개 방법](재현-명령.md)에는 이번 검사에 사용한 인자와 같은 PC에서의 복구 방법이 있다.

이 저장소는 종료·재부팅에 대비해 검사 증거를 보관하는 공개 기록이다. GitHub에서 장시간 빌드를 실행하는 워크플로는 설정하지 않았다. 저자 소스와 MIT의 독립 교차검증 기록은 각각 고정 소스와 배포 페이지에서 받을 수 있다. [저자 소스](https://github.com/lsernau/grh-lean/tree/72fead102f663d5c7a407964a13dc0cf9d977207) · [MIT 자료](https://math.mit.edu/~drew/shortgrh/)
