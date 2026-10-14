# 한국어판 구현 상태와 실행 절차

2026-10-14: 사용자가 r01의 번역 1,327항목을 명시적으로 승인했다.
[승인 기록](approval-r01.json)에 검수 당시 해시와 항목별 승인 해시를 기록했다.
문맥 정확성·자연스러움의 최종 판단은 실제 플레이 후 진행한다.

승인 번역을 적용한 DOS 플레이테스트 빌드를 만들었다.
[실행 안내](playtest-r01.md)를 참조한다. A/B와 추가 초기화 디스크 한 장이며
ProDOS 전환은 시작하지 않았다. 전체 PLAN 완료나 실제 하드웨어 검증을 뜻하지 않는다.

아래 합성 검증 기록은 승인 이전 단계의 결과다. 당시의 승인 0개 및 시험 문자
표시는 역사적 범위이며, 현재 승인 빌드 결과와 구분한다.

## 현재 승인 빌드

- [플레이테스트 안내](playtest-r01.md): 번역 1,327항목 승인·적용, 세 DOS 게임 디스크.
- 122명령으로 엔딩 도달, 진행 조건 13개 확인, 잘못된 메시지 참조 0개.
- B면 저장·복원과 새 부팅 복원, 제목 자막의 픽셀 보존 검사 통과.
- 세 디스크와 실행 자산 7개의 재빌드 바이트 일치, 호스트 검사 44개 통과.
- 실제 문맥·전체 화면의 사람 검수, 정밀 시간 비교, 실제 하드웨어 검증은 남아 있다.

## 승인 전 확인한 결과

- [제목 자막 연결](title-runtime.md): 원본 로고 위 빈 행에 합성 자막을 추가했다.
  실제 부팅의 전후 HGR 16KB를 대조해 자막 셀 외 16,328바이트 보존을 확인했다.
  INITIAL의 21바이트 증가로 현재 전체 매체 여유는 **A 2/B 6/추가 344섹터**다.
  런타임은 1,841바이트로 같고 A→B/B면 복원과 10개 파일의 재현도 통과했다.
  카탈로그·검수 묶음 r01은 변하지 않았으며 승인 0개로 적용 게이트는 계속 닫혀 있다.

- [native 안내·오류 연결](native-ui-runtime.md): 고정 문자열 11개를 마스킹한 상주
  풀 참조로 패킹했다. 짧아진 문구 뒤에 예전 글자가 남지 않도록 메시지 행을
  지운다. 양 HGR 페이지·역상·빈 방 캐시의 26사례와 A→B/B면 복원을 통과했다.
  이 옵션의 런타임은 1,841바이트이며 A 3/B 6/추가 345섹터 여유는 유지된다.

- [전체 합성 매체 실행](full-media-runtime.md): A 63/B 76/추가 12파일을 실제
  이미지로 만들고 전체 86자원을 Disk II/RWTS로 적재·대조했다. 66명령 경로로
  A→B를 진행한 뒤 B 방 34에서 저장·복원하고 별도 새 부팅에서도 복원했다.
  이 게임 실행은 CPU/월드 주입 없이 진행했다. 본문은 초안의 바이트 형태를
  보존한 시험 문자이며 정식 번역 적용이나 엔딩 검증은 아니다.

- 영문 소스 재빌드 A/B가 원본 디스크 해시와 일치했다.
- Apple II+ 48K 기준선과 48K + slot 0 `lang` 프로필에서 각각 opening replay의
  13개 검사가 통과했다. 기존 전체 진행·저장 기준선은
  [검증 문서](../validation.md)와 기존 `docs/evidence/` 보고서를 참조한다.
  이번 단계에서 전체 진행을 새로 실행한 것은 아니다.
- 87개 스크립트를 읽어 1,352개 출력 리터럴 참조를 추출했다. 기존 인덱스와
  참조 개수는 같지만, 새 카탈로그는 줄 끝 세미콜론을 제어 정보로 분리하고
  조건·앞뒤 문맥·원본 오프셋·파일 해시·원본 바이트를 보존한다.
  일부 출력에 low-bit 공백이 있으므로 단순 high-bit 재인코딩은 금지한다.
- 원본이 완전히 같은 A/B DEATH 파일의 3개 항목을 공유하고, PARMS 5개,
  intrinsic 8개, 부트 1개, DOS 진단 14개, 그림 제목 1개, 새 런타임 기술 안내 5개와
  생성 START/과거 편집기/주변 진단 5개를 추가해
  총 **1,388개 항목**이 있다. 이 중 공백 출력 및 초기 기술 안내 및 영문 명령 에코 등 61개는
  사유를 기록한 제외 항목이다. 1,327개에 번역 초안이 있고 승인은 0개다.
- [출력 원천 감사](output-paths.md): 소스 23개, 출력 호출 51곳과 생성 제목 참조 한 곳,
  숫자 출력 두 곳,
  매크로 선택자 98곳을 분류했다. K1의 원천 목록은 완료했으며 실행·화면 검증은
  별도로 남긴다. [재빌드 동등성](../evidence/korean/output-audit-media-equivalence.json)은
  다섯 제외 항목 추가 후에도 기존에 실행 검증한 세 이미지와 여섯 자산의 바이트가
  같음을 확인했다. 이는 native UI 연결 전의 증거다. 현재 호스트 검사는 43개이며
  새 UI의 보존·화면 검사는 위 별도 증거에 기록했다. 기존 인코딩 산출물 94개도 재현된다.
- 아이템 표시명은 `!OBJL`의 `.P` 문자열이며, 영문 입력은 별도의 명령 패턴이다.
  원래부터 분리되어 있으므로 입력 패턴을 번역하지 않는다. 용어집의 23개
  입력 키워드는 원본의 단어당 5문자 정규화 패턴과 대조했다.
  용어집은 인명·지명·문화 및 아이템 등 40개 용어, 방향 8개, 행동 20개를 포함한다.
- [그림 조사](../evidence/korean/picture-text-audit.json): 257개 native preview를
  contact sheet로 확인했다. LOGO1/LOGO2의 제목은 별도 한국어 자막 대상으로
  등록했다. 그림 속 기하·퍼즐 기호는 보존한다. 실제 게임 합성 화면 및
  자막 배치 검증은 남아 있다.
- GalmuriMono7 원천·라이선스·커밋·해시를 고정했다. 실제 원천에는 현대 한글
  11,172음절이 있다. 일부 Latin 문장부호는 8행 밖으로 내려가므로 ASCII는
  기존 PNG 글꼴과 위상 비트를 그대로 사용하고 한글을 7×8로 변환한다.
- [LC 합성 검사](../evidence/korean/lc-probe.json): 원본 렌더러의 scanline
  루틴을 이용해 양쪽 LC 뱅크와 공통 영역의 글리프를 그렸다. HGR 880바이트,
  양 페이지·역상·ROM 복귀·검사 바이트 보존 및 LC 없는 경우의 검출을 확인했다.
  `$6000` 테스트 배치는 최종 게임용 주소가 아니다. 디스크 로더, 저장 복원,
  실시간 장면 및 실제 하드웨어를 검증한 결과로 해석하지 않는다.

- [전체 초안 인코딩·배치 실험](encoding.md): 한글 글꼴 5,200바이트, 상주 풀
  4,089바이트, 최대 방별 풀 1,013바이트다. 반복 문구 공유와 파일 통합 후 A 3섹터,
  B 6섹터가 남는 호스트 배치를 확인했다. 실행 가능한 한국어 디스크의 검증은 아니다.
- [전체 세 매체 용량 검사](media-capacity.md): A 63파일/B 76파일과 추가 디스크
  12파일의 실제 섹터 할당을 0바이트 대체 본문으로 검사했다. 코드·부트·중복 자산을
  포함해 A 3/B 6/추가 345섹터가 남는다. B의 기존 트랙 1–2 파일 영역을 회수하며
  재사용 TS 헤더 초기화 문제를 수정했다. 후속 전체 합성 실행은 위 별도 증거를 참조한다.
- [호스트 화면 미리보기](layout-review.md): 개별 번역 1,327개와 연속 출력
  403조합을 검사했다. 행 12/열 0 가정에서 본문 넘침·덮어쓰기 문제는 0개다.
  실제 커서·분기·블록 간 문구 결합 검증은 남아 있다. 알약 수 결합의 초안 네 개를
  수정하고 카탈로그·인코딩·글꼴 크기를 다시 검사했다.
- [영문 입력·수수께끼 조사](input-review.md): 질문 5곳/답 비교 10곳/명령 패턴
  337곳을 목록화하고 괄호 속 입력명 51곳과 용어집 23개 입력명을 확인했다.
  첫 화면의 영문 대문자 안내와 세 수수께끼의 영문 답 안내를 추가했다.
  [플레이어용 입력 안내 초안](input-guide.md)에는 정답을 포함하지 않는다.
  69개 메시지의 보호 토큰을 검사한다. 전체 플레이의 입력 가능성 검증은 남아 있다.
- [인벤토리·매체 결합 화면](composed-layout.md): 원래 페이지 규칙을 추적한
  46개 목록 사례/141페이지와 매체 안내 6조합의 호스트 검사가 통과했다. 23개
  아이템명은 모두 한 행에 들어가며 본문이 입력 행을 침범하지 않는다.
  실제 HGR 페이지 전환·그림 보존을 검사한 결과는 아니다.

- [합성 메시지 런타임](message-runtime.md): `$9400`의 793바이트 코드로 상주/방별 풀과
  한영 혼합 출력, 참조 문자열 및 원본 숫자/에코 경로와 native 오류 진입점을 검사했다. 46개 시나리오,
  HGR 16KB 비교, LC 데이터 13,312바이트 보존이 통과했다.
- [DOS 스트리밍 로더](loader-runtime.md): 실제 DOS 부트 후 합성 파일의 main/LC
  분리 적재, 오류 및 캐시 무효화 등 26개 사례가 통과했다. dispatcher 포함 통합 코드는 1,818바이트다.
- [추가 DOS 디스크 콜드 부팅](startup-runtime.md): 실행 코드 주입 없이 5,200바이트
  글꼴과 4,096바이트 상주 풀을 읽고 한글 시험 제목을 그렸다. 잘못된 영문 디스크의
  거부/재시도, 다섯 명령을 통한 방 1–3 진행, LC 없는 경우의 중단 안내가 통과했다.
  전체 A/B 통합·나머지 시간 제한 검증은 남아 있다.
- [저장 복원 합성 검사](save-runtime.md): 방 3 저장, 방 2에서의 같은 세션 복원,
  새 부팅 복원, 호환되지 않는 저장 거부, 확장 코드가 부분 복원된 상태의 I/O
  실패/전체 재시도를 검사했다. B면 검사는 후속 전체 합성 실행에서 통과했으며 모든 게임 상태를 검사한 것은 아니다.

- [시간 제한 조기 검사](timing-runtime.md): 원래 뱀 장면을 네 출력 프로필로
  총 12회 실행했다. 무입력 창 8개는 각각 1.623072초였으며 0.10초/1.50초 후의
  SHOOT도 모두 성공했다. draft/stress의 실제 한글 경로와 폴링 중 디스크 요청 0회를
  확인했다. 유령·해골·가스·징검다리·마지막 대치 등의 전체 실행 검증은 남아 있다.

[KOR2 통합 증거](../evidence/korean/media-identity.json)의 빌드/면 식별은 본문 적재 전에 잘못된 자원을 거부한다. 이 통합 중 발견한
`$6000` 부트의 월드 플래그 침범을 `$5000` 임시 HGR 배치로 수정했다. 부트 전후
월드 2KB 보존, 시작·저장/복원·메시지·로더 및 뱀 장면 12회 실행을 재검증했다.

## 도구

먼저 원본 실행 코드 대신 소스에서 기준 바이너리와 심볼을 만든다.

```sh
python3 tools/check_tools.py --build-only
python3 tools/build.py --output build/korean/english-baseline
python3 tools/korean/catalog.py extract
python3 tools/korean/catalog.py check
python3 tools/korean/audit_outputs.py
python3 tools/korean/catalog.py export-review
python3 tools/korean/capacity.py
python3 tools/korean/font.py --catalog assets/korean/messages.json --output build/korean/draft-font
python3 tools/korean/encoding.py
python3 tools/korean/layout_preview.py
python3 tools/korean/audit_inputs.py
python3 tools/korean/audit_composed_layout.py
python3 tools/korean/full_media_capacity.py --startup build/korean/full-media-validation-02/fixture/media
python3 tools/korean/build_messages.py
python3 -m unittest discover -s tools/korean -p 'test_*.py'
```

`assets/korean/messages.json`이 번역 편집 원천이다. `extract`는 일치하는 원문
ID/해시의 기존 번역을 유지하고, 바뀌거나 사라진 원문은 `orphaned`로 보존한다.
원문 출처가 달라진 승인 항목은 draft로 돌아간다. `check`는 소스/빌드 해시와
카탈로그 출처를 대조한다. 다른 원천을 수정했다면 기준 빌드부터 다시 만든다.

`docs/korean/review.md`는 **미승인 검수 초안**이다. `ko` 열의 JSON 값만
편집하고 `python3 tools/korean/catalog.py import-review`로 반영한다. 누락·중복
ID, 원문 해시·문맥 충돌은 거부한다. 번역 변경은 기존 승인을 무효화한다.
표 반영만으로 승인되지 않으며 `check --require-approved`는 현재 실패해야 한다.
같은 명령은 [번역 제외 목록](exclusions.md)도 생성한다. 61개 제외 항목의 원문·출처와
사유를 검토할 수 있다. 새 런타임 안내 5개 중 정상 매체 안내 2개는 번역 초안이며,
한글 초기화 불가/부분 복원 실패 안내 3개는 필수 영문 기술 안내로 제외했다.
현재 검수 요청은 [검수 묶음](review-package.md)을 기준으로 한다. 원천·미리보기·보고서의
카탈로그 해시를 대조한 후 `python3 tools/korean/review_package.py --output output/korean-review-r01`로
변경 불가 스냅샷 폴더와 ZIP을 만든다. 기존 목적지는 덮어쓰지 않는다.

실제 LC 검사는 외부에서 제공한 MAME ROM을 사용한다. 출력 경로는 새 경로여야 한다.

```sh
python3 tools/korean/verify_lc.py --rompath /path/to/roms --output build/korean/lc-validation-new
python3 tools/korean/verify_messages.py --rompath /path/to/roms --output build/korean/message-validation-new
python3 tools/korean/verify_loader.py --rompath /path/to/roms --output build/korean/loader-validation-new
python3 tools/korean/verify_startup.py --rompath /path/to/roms --output build/korean/startup-validation-new
python3 tools/korean/verify_save.py --rompath /path/to/roms --output build/korean/save-validation-new
python3 tools/korean/audit_timers.py
python3 tools/korean/verify_timing.py --rompath /path/to/roms --output build/korean/timing-validation-new
python3 tools/korean/verify_full_media.py --rompath /path/to/roms --output build/korean/full-media-validation-new
python3 tools/korean/verify_full_game.py --rompath /path/to/roms --media build/korean/full-media-validation-new/fixture/media --output build/korean/full-game-validation-new
```

LC/message/loader 개별 검사는 debugger의 명령어 경계에서 합성 프로그램을 주입한다.
`verify_startup.py`와 `verify_save.py`는 실행 코드 주입 없이 자체 생성한 DOS 디스크에서
콜드 부팅한다. 저장 검사의 실패 프로필은 명시적으로 RWTS 요구 volume만 조작한다. 임의의
프레임 시점에 PC를 바꾸면 실행 중이던 6502 명령의 내부 상태가 남을 수 있어
초기 실험이 실패했다. 채택된 검사는 `--debug` 정지 상태에서 시작한다.

## 남은 주요 작업

1. 출력 호출·동적 결합·화면 분량의 경로별 검사를 마치고 전체 초안을 다듬는다.
   [출력 경로 조사](output-paths.md)에 직접 문자 출력, PARMS 오류, 기술 안내의
   처리 방침과 남은 통합을 기록했다.
   소스 출력 목록은 22개 소스/48개 호출의 감사로 완료했다. 실행·레이아웃까지
   포함하는 `coverage_complete`는 false다. 영문 입력·퍼즐 단서를
   문맥과 연결하고 전체 초안을 대상으로 글꼴·메시지 크기를 다시 계산한다.
2. 코드 여유와 실제 RAM 배치를 확정한다. 출력 참조로 축소되는 스크립트 영역,
   상주 공통 메시지, 방별 메시지, 글꼴, 인덱스, LC 전송 버퍼를 모두 포함한다.
3. 전체 합성 A/B/초기화 매체와 86자원 적재는 통과했다. 승인 후 실제 번역 UI와
   그림 자산의 버전 확인을 포함해 최종 배포 빌드로 통합한다.
4. 추가 디스크 초기화·A→B 전환·양면의 같은 세션/새 부팅 저장 복원은 합성으로 검증했다.
   엔딩까지 전체 매체 교체·시간 제한 검사를 통과시킨다. 대표 뱀 장면의
   조기 시간 검사는 통과했으며 이를 다른 장면의 증거로 일반화하지 않는다. 저장 디스크 삽입 중
   출력해야 하는 안내/오류와 글리프는 상주시켜 복원 교착을 피한다.
5. 준비한 검수 묶음에 대한 사람의 수정 의견·승인을 받는다. 변경 항목의 용량·화면을
   다시 검사하고 재검수한다. 승인 후 패치·재빌드 통합 및 엔딩/저장/시간 제한
   장면 검증을 진행한다.

## 자료

- [카탈로그](../../assets/korean/messages.json), [용어집](../../assets/korean/glossary.json)
- [추출·출력 경로 인덱스](extraction.json), [예비 용량](../evidence/korean/capacity.json)
- [폰트 출처](../../assets/korean/font/source.json), [라이선스](../../assets/korean/font/OFL.md)
- [48K opening](../evidence/korean/baseline-opening.json), [LC opening](../evidence/korean/lc-opening.json)
