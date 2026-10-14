# 한국어판 r01 플레이테스트

2026-10-14 사용자가 검토한 번역 1,327항목을 그대로 적용한 플레이테스트 빌드다.
승인은 [항목별 해시 기록](approval-r01.json)에 남겼다. 실제 장면에서의 문맥,
문장 연결, 퍼즐 단서와 가독성은 플레이하며 확인할 사항이다.

## 실행

`output/korean-playtest-r01.zip`을 풀면 다음 네 디스크가 있다.
게임용 세 장과 별도 저장용 한 장이다. 모두 140K DOS 순서 `.dsk`이며 ProDOS가 아니다.

| 파일 | 용도 |
| --- | --- |
| `mask-of-sun-ko-extra.dsk` | 반드시 이 디스크로 부팅. 한글 코드·폰트·상주 메시지를 초기화한다. |
| `mask-of-sun-ko-a.dsk` | 초기화 후 안내에 따라 같은 드라이브에 넣는 게임 A면. |
| `mask-of-sun-ko-b.dsk` | 게임이 B면을 요청할 때 같은 드라이브에 넣는다. |
| `mask-of-sun-ko-save.dsk` | 초기화된 빈 저장 디스크. 저장 요청에만 사용한다. |

Apple II+의 48K 메인 RAM과 slot 0의 16K Language Card, slot 6 Disk II를
사용한다. 이번 실행 검증은 MAME 0.285 `apple2p` 프로필에서 수행했다.
실제 Apple II+ 하드웨어 검증은 하지 않았다.

1. EXTRA를 드라이브 1에 넣고 부팅한다.
2. A면 안내가 나오면 같은 드라이브의 디스크를 A로 교체하고 RETURN을 누른다.
3. `OK>` 뒤의 명령은 영문으로 입력한다. `LOOK`, `INVENTORY`, `GET MAP`,
   방향 `N`, `S`, `E`, `W` 등이 원래대로 동작한다. [입력 안내](input-guide.md)를 참조한다.
4. 게임이 디스크를 요청하면 실제 매체를 교체한 다음 안내된 키를 누른다.
   저장 매체를 게임 A/B/EXTRA와 혼동하지 않는다.

`SAVE GAME` / `RESTORE GAME`에는 이 빌드 전용 저장 디스크의 작업용 복사본을
사용한다. 영문판이나 다른 한국어 빌드의 저장은 지원하지 않는다. 새 부팅 복원도
먼저 EXTRA로 초기화하고, 게임에 진입해 `RESTORE GAME`을 입력한다.
복원 후에는 저장했던 방의 A/B면을 요청한다. 배포 원본은 보관하고 복사본으로 플레이한다.

## 검증 범위

- 번역 1,327항목의 실제 메시지 풀을 디코딩해 승인 원문과 대조했다.
- 세 디스크의 모든 파일을 다시 읽어 생성 데이터와 대조했다.
- 별도 빌드의 세 디스크와 실행 자산 7개가 바이트 단위로 일치했다.
- 66명령 A→B 경로, B면 동일 세션 저장·복원 및 새 부팅 복원이 통과했다.
- 영문 명령 122개로 엔딩에 도달했다. 뱀·유령·가스·징검다리·마지막 대치를
  포함한 13개 진행 조건을 메시지 참조와 금 그릇의 실제 소지 상태로 확인했다.
  이는 해당 경로의 성공 검증이며 원판과 시간 제한 입력 창이 같은지의 비교는 아니다.
- 자연 부팅의 제목 자막을 HGR 메모리와 대조했다. 자막 셀 외 16,328바이트가
  보존되어 원본 로고와 반대 화면 페이지를 변경하지 않았다.
- 승인 게이트를 포함한 호스트 단위 검사 44개가 통과했다.

증거는 `docs/evidence/korean/approved-r01-*.json`에 있다.
시간 제한의 입력 창 비교와 전체 화면의 사람 검수는 남아 있다.
시작 화면 하단 크레딧은 디스크 안내로 전환되므로 표시 시간도 검토 대상이다.

## 문맥 검토 의견 남기기

어색한 문구가 나오면 **화면 캡처, 직전에 입력한 명령, 장소/상황, 기대한 의미**를
함께 기록하면 해당 카탈로그 항목과 조건 분기를 찾을 수 있다. 정답이 드러나는
캡처는 별도로 표시한다. 승인 문구를 고치면 해당 항목을 재검수하며 새 빌드의
저장 호환성도 다시 확인한다.

## 재빌드

원본 영문 소스 빌드가 `build/korean/english-baseline`에 준비되어 있어야 한다.
다음 출력 경로는 존재하지 않는 새 디렉터리를 사용한다.

```sh
python3 tools/korean/catalog.py check --require-approved
python3 tools/korean/startup_disk.py --approved --output build/korean/new-playtest
python3 tools/korean/startup_disk.py --approved --output build/korean/new-repeat
python3 tools/korean/verify_approved.py --media build/korean/new-playtest --repeat build/korean/new-repeat --output build/korean/new-playtest-check.json
```

현재 사용량은 런타임 1,841바이트, 한글 650글리프/5,200바이트,
상주 풀 4,089/4,096바이트, 최대 방 풀 1,013/1,024바이트다.
디스크 여유는 A 2/B 6/EXTRA 344섹터다. 문구 수정 시 메모리와 섹터 배치를 다시 검사한다.
800K ProDOS 전환이 필요해지면 사용자에게 알리고 전환 작업을 멈춘다.

글꼴은 고정한 GalmuriMono7 2.403에서 만든 `Mask Korean 7x8` 서브셋이며
[출처](../../assets/korean/font/source.json)와 [SIL OFL 1.1](../../assets/korean/font/OFL.md)을 함께 배포한다.
