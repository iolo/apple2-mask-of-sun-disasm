# native 안내·오류의 상주 메시지 연결

2026-10-14. `--full-synthetic --native-ui`는 실제 번역 본문을 게임에 넣지 않고
기존 native 문자열 11개를 **시험 문자로 마스킹한 상주 풀의 참조**로 연결한다.
번역 검수 묶음 r01의 문구·카탈로그 해시는 바뀌지 않았다. 승인 전 실험이며
정식 한국어판이나 모든 오류 발생 조건의 검증은 아니다.

## 구현

- PARMS의 고정 16바이트 슬롯 네 개: 파일 없음, DOS 오류, RETURN 없음, 스택 오류.
- INTRIN의 다섯 문자열: 디스크 오류, 그림 적재 오류, 디스크 작업 오류,
  게임 디스크 접두부, 드라이브/RETURN 안내.
- 추가 런타임의 게임/저장 매체 안내 두 개.

`native_ui.py`는 원문 바이트·CR·세미콜론·고정 주소를 대조한 뒤 `~hhhh[;]CR`
참조와 0 패딩을 쓴다. 본문이 방 캐시에 의존하지 않도록 상주 ID만 허용한다.
슬롯 밖의 코드·표·파일 길이·DOS 헤더는 바꾸지 않는다. ASCII 면 이름 A/B와
OK>, 초기화 전 기술 안내 및 스냅샷 밖 독립 복원 오류 안내도 유지한다.

참조로 줄어든 안내는 원래 영어 문자열의 후행 공백을 더 이상 출력하지 않는다.
그래서 `ko_clear_message_rows`가 선택된 HGR 페이지의 행 12–15에 공백 160개를
먼저 그린다. 그림이 있는 행 0–11과 반대쪽 HGR 페이지는 건드리지 않으며 A/X
문자열 포인터와 Y를 보존한다. native 디스크 안내는 고정 크기 trampoline으로
연결하고 런타임의 재시도·복원 안내도 같은 루틴을 사용한다.

기본 영문 빌드는 원본 A/B 해시와 여전히 일치한다. 이 옵션을 켠 통합 런타임은
1,841바이트(기존 1,818바이트보다 23바이트 증가)로 2KB 안에 207바이트가 남는다.
부트는 1,152바이트이며 매체 여유는 A 3/B 6/추가 345섹터로 같다.

## 검증 범위

[native UI 감사](../evidence/korean/native-ui-audit.json)는 다음을 확인한다.
전체 요약·해시·미검증 범위는 [통합 증거](../evidence/korean/native-ui-validation.json)에 있다.

- 11개 문자열 패치를 제외한 모듈 바이트 보존, 기존 native 파일 49개 보존.
- 상주 풀과 86자원 풀의 본문이 X/공백/줄바꿈/시험 한글만 포함함.
- 실제 패킹한 11개 문자열과 native A/B 안내 조합을 두 HGR 페이지에서 출력한
  26사례. 두 번째 페이지는 역상이며 방 캐시는 모든 사례에서 무효다.
- 매 호출 후 HGR 전체 16KB와 LC 13KB, 커서·스택·ROM 복귀를 대조한다.
  화면은 `$A5`로 미리 채워 후행 문자 잔존과 그림 영역/다른 페이지의 훼손을 찾는다.
- 네 PARMS 오류는 실제 interpreter 오류 진입점을 호출한다. native A/B 안내는
  실제 조합 함수를 호출한다. 다른 개별 문자열 검사는 프린터 계약 검사이며
  원래 디스크·그림 오류 조건을 일부러 발생시킨 검사가 아니다.

이 화면 실험은 debugger의 명령어 경계에서 프로그램·초기 자산을 넣는 합성
하네스다. 캡처 전의 ROM WAIT는 비디오 갱신을 기다리는 하네스 코드에만 있다.
게임 코드에 새 입력 대기나 지연을 넣지 않는다.

캡처의 줄무늬는 의도적으로 채운 `$A5` 화면이다. 메시지 글리프 셀 밖의 줄무늬가
남는 것은 그림 영역·다른 페이지·행 사이 스캔라인을 보존한 결과다.
[일반 페이지](../evidence/korean/native-ui-page0.png)와
[역상 페이지](../evidence/korean/native-ui-page1.png)는 실제 에뮬레이터 캡처이며
읽을 수 있는 한국어 번역 화면으로 취급하지 않는다.

[전체 게임 경로 재검사](../evidence/korean/native-ui-game-probe.json)는 별도다.
완전한 세 합성 디스크로 실제 부팅하고 자연 키보드·단일 드라이브 교체만 사용한다.
66명령 A→B 경로와 B 방 34의 같은 세션/새 부팅 복원을 통과했고 방 풀을 각각
67회/5회 대조했다. CPU·월드 주입 없이 실행하며 전체 엔딩·시간 제한·실제 번역
화면 검증은 남아 있다.

## 재현

```sh
python3 tools/build.py --output build/korean/english-baseline
python3 tools/korean/startup_disk.py --full-synthetic --native-ui --output build/korean/native-ui-new
python3 tools/korean/verify_native_ui.py --media build/korean/native-ui-new --output build/korean/native-ui-check-new --rompath /path/to/roms
python3 tools/korean/verify_full_game.py --media build/korean/native-ui-new --output build/korean/native-ui-game-new --rompath /path/to/roms --evidence build/korean/native-ui-game-new/evidence.json
```

검수 중인 실제 번역은 적용하지 않는다. 제목의 합성 연결은 이후
[제목 자막 실험](title-runtime.md)에서 통과했다. 실제 제목·문구의 화면과
입력 가능성, 모든 분기·시간 제한 장면·엔딩 및 최종 배포 빌드는 별도 완료 항목이다.
ProDOS 이식은 시작하지 않았으며 필요해지면 사용자 결정 전에 멈춘다.
