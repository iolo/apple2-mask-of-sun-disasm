# 사용자 출력 경로와 통합 상태

K0/K1 조사 기록이다. 아래는 코드에서 확인한 출력 경로이며 전체 게임의 도달
가능성·레이아웃 검증이 완료됐다는 뜻은 아니다. 원본 스크립트의 출력 위치는
[추출 목록](extraction.json)의 `output_sites`, 개별 출처는 카탈로그에 있다.

[출력 감사](../evidence/korean/output-audit.json)는 소스 22개의 해시에 대해 어셈블리
출력 호출 48곳과 스크립트 리터럴 참조 1,352곳의 처리 방침을 확인한다.
[분류 원천](../../assets/korean/output-policy.json)은 각 호출을 번역·ASCII 입력·기술
안내 등으로 분류한다. 소스나 출력 호출이 바뀌면 재감사 전에는 검사가 실패한다.
원문 재직렬화는 87개 스트림 모두 원본 바이트와 일치한다.
현재 `source_inventory_complete`는 true, 실행·화면까지 포함하는
`coverage_complete`와 `runtime_coverage_complete`는 false다.

## 기존 엔진

| 출력 | 코드 진입점/경로 | 한국어 처리와 남은 작업 |
| --- | --- | --- |
| `.P` 리터럴 | `intrinsics.s: print_quoted_string` → `$0344` | 한국어 초기화가 래퍼를 설치한다. 짧은 참조는 LC 풀, 일반 ASCII는 원래 프린터로 보낸다. 합성 검증 통과. |
| 숫자 `.P` | `format_decimal` → `$0344` | 최대 5자리 ASCII와 원래 CR/세미콜론 유지. 한글 단위 결합은 호스트 미리보기로 검사. |
| 아이템 표시 | 스크립트 `!OBJL` → `.P` | 23개 표시명을 번역하고 입력 패턴은 유지. [호스트 페이지 검사](composed-layout.md)는 통과했으며 실제 페이지 전환 검증은 남음. |
| 명령 에코 `.&` | `echo_command_byte` → ROM COUT | 영문 입력 바이트 유지. 메시지 참조로 해석하지 않음. |
| 일반 프롬프트 | `interpreter.s: print_prompt_character` → ROM COUT | PARMS 길이 바이트와 `OK>` 유지. `$0344`를 거치지 않는 직접 문자 출력. |
| 질문 프롬프트 `.A` | `intrinsics.s: print_ask_prompt` → ROM COUT | 같은 PARMS 프롬프트를 사용. 답은 영문이며 비교용 `answer_text`는 번역하지 않음. |
| 입력·백스페이스·커서 | `read_command` 및 `draw_cursor_space` → COUT/`$0348` | 기존 ASCII 편집 동작 유지. 전체 통합 후 입력 회귀 필요. |
| PARMS의 네 오류 | `file_not_found`, `disk_error`, `input_without_cr`, `script_stack_overflow` → `print_engine_error` | 한국어 조건부 빌드에서 래퍼 호출로 연결. 빈 방 캐시/양 페이지/원래 추가 CR을 합성 검증. 실제 PARMS의 참조 패킹은 승인 후 진행. |
| 그림 적재 오류 | `picture_load_overflow` → `call_string_printer` → `$0344` | 카탈로그 `intrinsic:picture_load_overflow_text`. 고정 주소에 참조를 넣는 패킹과 실제 오류 발생 검증은 남음. |
| 저장 I/O 오류 | `snapshot_error` → `call_string_printer` → `$0344` | 원래 `disk_error_text`를 카탈로그에 포함. 한국어 복원 실패는 아래 독립 guard로 분리. |
| 게임 디스크 안내 | `print_game_disk_prompt` → `call_string_printer` → `$0344` | 오류/게임명 접두부/A·B면/드라이브/OK 프롬프트를 차례로 출력. 원본 위치는 행 12/열 0. 다섯 부분의 호스트 결합 검사는 통과했으며 실제 양 페이지 검증은 남음. |
| 타이틀 그림 문자 | LOGO1/LOGO2 | 별도 그림 문자 항목과 한국어 자막 계획. 합성 시험 제목은 통과했으나 실제 번역 자막의 위치 검수는 남음. |
| B면 부트·DOS 진단 | `boot-b.s`, `dos-low.s` | 한글 초기화 전의 필수 영문 기술 안내로 카탈로그에서 사유를 기록해 제외. |

`print_engine_error`의 변경은 명령어 길이를 유지한다. 네 오류 진입점과 원래
`print_script_string` 주소 `$0BF3`도 유지한다.
[46개 메시지 검사](message-runtime.md)와 [영문 바이트 비교](../evidence/korean/english-error-regression.json)가
이를 확인한다. 합성 호출은 각각의 디스크/파서 오류 발생 조건 자체를 검사하지는 않는다.

## 추가한 기술 안내

이 다섯 문자열은 `runtime:<레이블>` ID로 카탈로그에 등록했다. 소스의 `.byte`
리터럴을 직접 추출해 원래 제어 바이트와 해시를 보존한다. 초기화 안내 두 개와
복원 실패 안내 한 개는 아래 사유로 제외하고 정상 런타임의 매체 안내 두 개에는
한국어 초안을 작성했다. [제외 목록](exclusions.md)에도 사유와 출처를 함께 생성한다.
실제 런타임에 승인 번역을 적용한 것은 아니다.

| 소스/레이블 | 현재 문구 | 최종 처리 조건 |
| --- | --- | --- |
| `bootstrap.s: boot_error_text` | INSERT STARTUP DISK AND PRESS RETURN. | 런타임·LC 초기화가 실패한 경우이므로 필수 영문 기술 안내로 제외. |
| `bootstrap.s: boot_no_lc_message` | 16K LANGUAGE CARD REQUIRED. / RESET TO RESTART. | 한글을 출력할 하드웨어가 없으므로 영문 안내 유지. |
| `dispatch.s: ko_media_text` | INSERT GAME DISK A/B AND PRESS RETURN. | 상주 번역 초안 작성. 목적 매체 식별·한국어 출력 연결은 남음. |
| `save.s: ko_save_prompt` | INSERT SAVE DISK, PRESS RETURN. | 상주 번역 초안 작성. 저장 매체 삽입 중 실제 번역 출력 검증은 남음. |
| `restore-guard.inc: ko_restore_error_text` | RESTORE ERROR. RETRY: RETURN | 부분 복원 시 확장 코드가 손상될 수 있어 스냅샷 밖의 고정 ASCII 프린터 `$0BF3`와 안내를 유지하는 기술적 제외. |

복원 guard를 일반 한국어 오류 래퍼로 바꾸면 부분 복원된 `$9400` 코드를 실행할
수 있다. 이 경로의 독립성은 [중간 읽기 실패 검사](save-runtime.md)로 확인했다.
방 메시지 풀을 다시 적재할 때는 정상 초기화된 상주 안내를 사용할 수 있으므로
복원 실패 guard와 같은 제약으로 취급하지 않는다.

## 주변 출력과 동적 출력의 범위

생성한 A면 START의 `BOOT THE STARTUP DISK.`는 `generated:a_boot_notice`로
등록했다. 한글 초기화 전에 추가 부트 디스크를 요구하는 필수 영문 안내다.
CHAR GEN에 남아 있는 과거 편집기 문구 `VTOC: `와 `V-edit: `,
부트 A의 사용하지 않는 진단 `B01-00`, DOS CATALOG의 `DISK VOLUME `도
별도 제외 항목으로 기록했다. 이 다섯 항목을 포함해 총 1,388항목 중
61항목을 제외하고 1,327항목에 번역 초안이 있다.

ROM/Applesoft/모니터와 DOS 셸의 기술 진단·파일명·숫자·에코는 영어로 유지한다.
게임 원천에 포함된 고정 진단은 카탈로그에서 추적하되 ROM 전체의 현지화는
범위에 넣지 않는다. 상세 경계와 이유는 분류 원천의 `system_scope_exclusions`에 있다.

리터럴 외 `.P`는 LIBRARY와 B ROOM 50.0의 `.P TV(8)` 두 곳이다.
`.1` 43곳과 `.2` 55곳은 두 글자 선택자로 기존 매크로의 대상 네 바이트를
고쳐 이미 추출한 처리기로 분기한다. 별도의 문자열 생성기로 취급하지 않는다.
이는 모든 선택 조합의 도달 가능성이나 커서 위치를 입증하는 것은 아니다.

## 완료하지 않은 범위

계산된 매크로의 도달 가능성, 여러 블록의 문장 결합, 인벤토리 페이지 전환,
퍼즐의 입력 안내 및 실제 그림·자막 배치는 계속 검사한다.
경로가 한국어 프린터에 연결되었다는 사실만으로 그 경로의 승인 번역 패킹이나
실제 화면 검증이 끝났다고 판단하지 않는다.

재현: `python3 tools/korean/catalog.py extract` 후
`python3 tools/korean/audit_outputs.py`를 실행한다. 추출만 다시 실행하면 완료
표시는 제거되며, 핀한 소스·출력 분류와 다시 대조한 뒤에만 복구된다.
