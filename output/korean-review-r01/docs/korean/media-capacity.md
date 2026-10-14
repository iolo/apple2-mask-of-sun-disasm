# 전체 A/B/추가 디스크 용량 검사

2026-10-14의 [호스트 할당 결과](../evidence/korean/full-media-capacity.json)는
전체 A/B 파일과 추가 초기화 디스크가 140K DOS 매체 세 장에 들어감을 확인한다.
이는 승인된 번역의 실행 디스크 완성이나 전체 게임 실행 검증을 뜻하지 않는다.

| 매체 | 파일 수 | 남는 섹터 | 남는 바이트 |
| --- | ---: | ---: | ---: |
| A | 63 | 3 | 768 |
| B | 76 | 6 | 1,536 |
| 추가 초기화 디스크 | 12 | 345 | 88,320 |

입력은 현재 초안의 스크립트/풀 패키지 크기, 조건부 한국어 interpreter/intrinsics의
조립 결과 크기, 기존 그림·폰트·기타 파일의 할당 크기다. 추가 디스크에는 부트,
1,152바이트 bootstrap, 1,818바이트 런타임, 글꼴 5,200바이트, 패딩한 상주 풀
4,096바이트와 각 자산의 16바이트 헤더, INITIAL/LIBRARY 등 중복 자산을 포함한다.
KOR2 패키지의 빌드/면 식별 헤더 24바이트를 포함한다. 기존 KOR1보다 16바이트
늘어 파일별 반올림으로 A 3/B 4섹터를 더 쓴다. 부트/런타임 증가로 추가 디스크는
1섹터를 더 쓴다. 파일별 섹터 반올림·TS-list·카탈로그·VTOC를 실제 할당기로 검사한다.

검사는 **같은 크기의 0바이트 본문**을 메모리에서 할당하고 다시 읽는다. 초안 문구를
디스크에 적용하지 않으며 디스크 이미지도 저장하지 않는다. 할당 중복, 단일
TS-list 제한, 파일별 본문 읽기, 카탈로그 섹터 수 및 VTOC 소유/여유 비트를 확인한다.
보고서에는 각 파일의 크기 근거와 실제 후보 트랙/섹터 목록을 남긴다.

## B면의 재사용 가능 영역

추가 디스크를 만드는 기본 할당기는 DOS 부트를 위해 트랙 0–2 전체를 예약한다.
하지만 원본 B는 일부 파일과 TS-list를 트랙 1–2에 둔다. 이 영역까지 예약하면
전체 B 파일은 13섹터 부족해진다. 새 검사는 원본 파일/TS-list와 VTOC 여유 영역만
회수하므로 해당 19섹터를 사용할 수 있고 6섹터가 남는다. 트랙 0과 카탈로그
트랙 17은 재사용 대상으로 허용하지 않는다. ProDOS 전환이 필요한 상황은 아니다.

이 과정에서 재사용 TS 섹터의 예전 본문이 헤더에 남는 문제가 드러났다. 할당기는
이제 TS 섹터 전체를 먼저 지우고 연결/인덱스/섹터 쌍을 작성한다. 이 회귀를 포함한
호스트 단위 검사 32개가 통과했으며 기본 할당기를 쓰는 합성 콜드 부팅도 다시
통과했다. 기존 48K/no-LC 안내와 잘못된 매체 재시도도 검사했다.

## 재현

```sh
python3 tools/korean/encoding.py
python3 tools/korean/startup_disk.py --output build/korean/capacity-startup-new
python3 tools/korean/full_media_capacity.py --startup build/korean/capacity-startup-new
python3 -m unittest discover -s tools/korean -p 'test_*.py'
```

`startup_disk.py`는 원문 및 합성 시험 문구만으로 초기화/부분 A 시험 이미지를 만든다.
`full_media_capacity.py`는 그 빌드의 자산 크기를 전체 A/B 호스트 할당에 반영한다.
채택한 현재 startup 입력은 `build/korean/full-media-validation-02/fixture/media`다.

이후 출력 원천 감사로 제외 항목 다섯 개를 추가한 카탈로그도
[현재 용량 재검사](../evidence/korean/output-audit-capacity.json)를 통과했다.
입력은 `build/korean/full-synthetic-output-audit-01`이며 A 3/B 6/추가 345섹터가
동일하게 남는다. [바이트 동등성](../evidence/korean/output-audit-media-equivalence.json)은
이 빌드가 앞서 실행 검증한 세 이미지·여섯 자산과 같음을 기록한다.
이전 실행 보고서의 카탈로그·소스 해시는 당시 값으로 보존한다.

[전체 합성 실행](full-media-runtime.md)은 실제 세 이미지, 전체 자원 적재, A→B 전환과
B면 저장/새 부팅 복원을 통과했다. 승인 번역의 UI·최종 부팅/재시작과 엔딩 검증은 남아 있다. 현재의 작은 A/B 여유를 최종 여유로 간주하지
않으며 코드·자산·번역을 바꿀 때마다 다시 검사한다. 추가 디스크를 이용한 DOS
방식으로 해결할 수 없다고 판단하여 ProDOS 전환을 권고할 때는 사용자에게 먼저 알린다.
