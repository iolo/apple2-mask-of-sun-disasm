# 한국어판 r01-extra-save 플레이테스트

EXTRA가 부팅과 저장을 함께 담당한다. **EXTRA+SAVE, A, B 세 장**만 사용한다.
fix1의 시작 오류와 fix2의 명확한 A/B 안내 수정도 포함한다.
[변경·검증 기록](extra-save.md)과 [문구 변경 기록](approval-r01-extra-save.json)을 참조한다.

## 실행과 저장

`output/korean-playtest-r01-extra-save.zip`에는 다음 세 디스크가 있다.
모두 140K DOS 순서 `.dsk`이며 ProDOS가 아니다.

| 파일 | 용도 |
| --- | --- |
| `mask-of-sun-ko-extra.dsk` | 부팅 + 게임 저장·복원. 쓰기 가능한 작업용 복사본을 사용한다. |
| `mask-of-sun-ko-a.dsk` | 초기화 후 같은 드라이브에 넣는 게임 A면. |
| `mask-of-sun-ko-b.dsk` | B면 요청 시 같은 드라이브에 넣는 게임 B면. |

1. EXTRA로 부팅한다.
2. “게임 디스크 A를 넣고 RETURN을 누르세요.”가 나오면 같은 1번 드라이브에 A를 넣고 RETURN을 누른다.
3. `OK>` 뒤에는 영문 명령을 입력한다. [입력 안내](input-guide.md)를 참조한다.
4. `SAVE GAME`을 입력하고 확인하면 **EXTRA를 같은 드라이브에 넣고 RETURN**을 누른다.
5. 저장 후 요청하는 게임 A 또는 B를 다시 넣는다.
6. `RESTORE GAME`도 저장할 때 사용한 EXTRA를 넣는다. 복원 후에는 안내된 A 또는 B를 넣는다.

저장한 EXTRA로 다시 부팅해도 된다. A를 넣어 게임에 진입한 다음 `RESTORE GAME`으로 불러온다.
EXTRA 한 장에는 저장 상태 하나를 보관한다. 다시 저장하면 이전 상태를 덮어쓴다.
**EXTRA를 초기화하거나 포맷하지 않는다.** 배포 ZIP은 보관하고, 저장할 작업용 EXTRA는 쓰기 보호를 해제한다.

기존 빌드와 섞지 말고 세 디스크를 함께 교체한다. 이전 빌드의 저장은 호환되지 않는다.
새 별도 저장 디스크를 만들 필요는 없다. 새로운 빌드의 EXTRA로 기존 저장 EXTRA를 덮어쓰면 저장도 사라지므로 별도 보관한다.

## 검증 범위

- MAME 0.285 Apple II+ 48K + 16K Language Card, 단일 Disk II 드라이브.
- 66명령 A→B 경로와 B면 저장·복원: 실제 부팅한 EXTRA에 저장한다.
- 저장된 EXTRA 자체로 새로 부팅하고 B면의 게임 상태와 변경된 스크립트를 복원한다.
- 저장 전후의 모든 부팅 파일, 카탈로그/VTOC, 저장 영역 밖 섹터가 동일하다.
- A/B 안내 메시지 셀의 픽셀을 실제 글리프와 대조한다. 저장·복원 안내는 EXTRA를 명시한다.
- 1,328항목의 메시지 풀과 세 디스크 파일을 대조하고, 10개 실행 산출물의 반복 빌드 바이트가 일치한다.
- 예약 영역을 가로지르는 파일 할당과 저장 쓰기 격리 검사를 포함한 호스트 검사 45개 통과.

증거는 `docs/evidence/korean/approved-r01-extra-save-*.json`에 있다.
이번 변경에서 AppleWin/GSSquared, 전체 엔딩 경로, 실제 하드웨어는 재검증하지 않았다.
이전 r01에서는 122명령 엔딩 경로가 통과했다. 실제 문맥과 전체 화면의 사람 검수,
원판과의 정밀한 시간 제한 비교는 남아 있다.

## 재빌드

원본 영문 소스 빌드가 `build/korean/english-baseline`에 준비되어 있어야 한다.
출력은 존재하지 않는 새 디렉터리를 사용한다.

```sh
python3 tools/korean/catalog.py check --require-approved
python3 tools/korean/startup_disk.py --approved --output build/korean/new-playtest
python3 tools/korean/startup_disk.py --approved --output build/korean/new-repeat
python3 tools/korean/verify_approved.py --media build/korean/new-playtest --repeat build/korean/new-repeat --approval docs/korean/approval-r01-extra-save.json --output build/korean/new-playtest-check.json
```

런타임 1,892/2,048바이트, 글꼴 650글리프/5,200바이트, 상주 풀 4,096/4,096바이트,
최대 방 풀 1,013/1,024바이트. 저장 영역 145섹터를 예약한 뒤 여유는 EXTRA 199/A 3/B 8섹터다.
800K ProDOS 전환이 필요해지면 사용자에게 알리고 전환 작업을 멈춘다.

어색한 번역은 화면 캡처, 직전 명령, 장소/상황과 기대한 의미를 함께 기록한다.
글꼴 [출처](../../assets/korean/font/source.json)와 [SIL OFL 1.1](../../assets/korean/font/OFL.md)을 함께 배포한다.
