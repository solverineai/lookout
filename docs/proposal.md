# Lookout 기획안

2026-10-28 · Meta Global AI Developer Hackathon 2026 · Startup track · Build for Your World
기술 설계는 [설계 스펙](superpowers/specs/2026-10-28-lookout-design.md), 모델 분석은 [meta-models.md](meta-models.md).

## 1. 한 줄

**Every store has orders that break. Lookout fixes them before customers notice.**

어느 가게에나 깨지는 주문이 있습니다. 룩아웃은 고객이 알기 전에 고칩니다.

Lookout은 소규모 온라인 셀러 옆에서 일하는 AI 동료다. **주문 예외**(order exceptions — 출고·배송이 막혀 사람이 손대야 하는 주문)를 24시간 찾아내고, 직접 손을 써서 고치고, 돈이 움직이는 결정만 셀러에게 묻는다.

용어: 영어는 업계 표준어인 **order exceptions**, 한국어는 **주문 예외**로 통일한다. "orders that break"는 한 줄 설명에만 쓴다. 근거는 §15.

## 2. 문제

모든 온라인 가게에서 매일 주문의 일부가 정상 흐름을 벗어난다. 주소·연락처 오류, 통관 정보 오류, 재고 불일치로 출고 불가, 배송 지연·분실, 고객의 취소·변경 요청. 해외에서 들여오는 셀러는 세관 보류까지 얹힌다. 업계는 이를 주문 예외라 부르고, 이를 찾아 해결하는 일을 exception management라 부른다.

주문 예외 하나에 셀러 시간 15–30분이 든다. 포장하다 말고, 셀러센터 페이지를 열고, 고객에게 전화하고, 택배사에 묻는다. 늦으면 취소, 환불, 나쁜 리뷰가 된다. 혼자 파는 사람도, 열 명이 파는 팀도 똑같이 겪는다.

## 3. 대상과 우리의 세계

- **대상**: 소규모 온라인 셀러(independent online sellers). 혼자 또는 작은 팀으로 여러 채널에 파는 사람. 1인부터 10여 명까지.
- **우리의 세계**: 호주 상품을 수입해 Naver Smart Store와 Shopify에 파는 서울의 셀러 한 명. 통관까지 겪는, 가장 어려운 경우다. 이 셀러는 실제로 있다(솔버린 고객). 이름과 데이터는 쓰지 않는다.
- **논리**: 가장 어려운 셀러를 위해 제대로 지으면 모든 소규모 셀러에게 맞는다.

테마 "Build for Your World" — "Solve a problem you know firsthand, free up time and mental space, and make something possible that wasn't before." 우리는 한 명의 주문 예외를 매일 봐 왔다. **Your world is as big as you define it.**

## 4. 우리는 세 가지를 한다 — Find, Fix, Ask

Find·Fix·Ask는 exception management의 표준 단계(identify → resolve → escalate)를 에이전트가 끝까지 수행하는 것이다.

| 단계 | 하는 일 | 핵심 Meta 모델 |
|---|---|---|
| **Find** — 찾는다 | 여러 채널의 주문·배송·통관·고객 이벤트를 24시간 분류해 주문 예외를 잡아낸다. 로컬에서 돌아 비용 0, 데이터는 기기에 | Muse Glimmer(로컬, 오픈 웨이트) |
| **Fix** — 고친다 | 원인별로 직접 처리한다. 고객에게 수정 요청과 지연 안내(고객 언어로), 주문 정보 수정, 분할 출고, 채널 간 재고 재배정, 세관 통지서를 읽고 보완 서류 초안. 셀러센터에 API가 없으면 화면을 직접 조작 | Muse Spark 1.3(추론·PDF 이해·컴퓨터 사용) |
| **Ask** — 묻는다 | 돈이 움직이는 것(환불, 보상, 재발송 비용)만 WhatsApp으로 묻는다. 버튼 또는 음성 한 마디로 승인. 나머지는 끝내고 보고한다 | Muse Voice Transcribe + 정책 게이트 |

세 단계를 받치는 **신뢰 레이어**: 정책 게이트(돈·되돌릴 수 없는 일·건강 표현), 실행 원장(모든 판단과 행동 기록), 멱등 실행, 하루 비용 상한. "맡겨 놓고 안심한다"의 근거.

Lookout은 초안만 쓰지 않는다. 어댑터를 통해 주문을 실제로 고치고, 고객에게 실제로 보내고, 재고를 실제로 옮긴다. 셀러가 보는 건 결과와 승인 요청이다.

## 5. 하루 한 바퀴로 보여 주는 이야기

| 시각 | 주문 예외 | Lookout이 한 일 |
|---|---|---|
| 09:00 | 셀러가 포장을 시작하며 WhatsApp에 "맡길게" | 감시 시작 |
| 09:40 | Shopify 주문, 주소에 동·호수 없음 | 출고 보류, 고객에게 보완 요청 발송. 10:15 답장 오자 주문 주소 수정, 보류 해제 |
| 11:05 | Naver 주문, 해당 SKU 재고 0 (Shopify 채널에 2개) | 채널 간 재고 재배정, Shopify 노출 수량 조정, 출고 가능으로 전환 |
| 14:12 | 세관 보류 통지서(PDF): 식품 검역 서류 미비 | 통지서를 읽어 부족 서류·대상 품목 추출. 영향 주문 14건 추적, 그중 통관부호 오류 3건에 수정 요청, 14건에 지연 안내(한국어), 보류분 제외 분할 출고. 취소 요청 3건의 환불은 **Ask** |
| 14:40 | — | WhatsApp 알림 한 건: "세관 보류 14건 처리 중. 환불 3건만 결정 필요." 셀러는 우체국에 있다 |
| 16:30 | 택배 추적 3일 정지 1건 | 고객에게 선제 안내. 재발송은 비용이 들어 **Ask** |
| 18:00 | — | WhatsApp 브리핑: 오늘 주문 예외 23건 → 처리 19건, 대기 4건(환불 3, 재발송 1). 고객 안내까지 평균 3분. 절약한 시간 약 6.3시간(승인 반영 후 7.3시간). 모델 비용 $0.13 |
| 18:05 | 음성 "환불은 1번이랑 2번만, 재발송은 해" | 승인 반영 → 채널(Shopify·Naver)에서 환불 2건 실행, 재발송 주문 생성, 1건 보류 유지 → 원장 |
| 이후 | 주문·문의·추적 갱신 계속 | 감시 계속. 다음 브리핑은 셀러가 정한 시각 또는 돈이 걸린 일이 생길 때 |

## 6. 증명 가능한 지표 (대시보드 카운터)

주문 예외 발견 수 / 처리 수 / 승인 대기 수 · 발견부터 고객 안내까지 시간 · 절약한 시간(건당 20분 기준) · 오늘 모델 비용 · Glimmer 분류 건수와 Spark 호출 횟수. 심사위원은 "Run 24h"를 눌러 하루가 실제 모델 호출로 처리되는 걸 본다.

## 7. 셀러에게 주는 효과 (가정, 실제 셀러로 검증 예정)

| 셀러 유형 | 지금 | Lookout |
|---|---|---|
| 1인 셀러 | 주문 예외 하루 5–10건 × 20분 = 2–3시간, 연 약 800시간 | 80% 반환, 시급 2.5만 원 기준 연 1,600만 원 상당. 늦은 처리로 잃던 주문 회수 |
| 10–15명 팀 | CS·운영 인력 2–3명이 예외 처리에 묶임, 연 1–1.5억 원 | 예외 처리 자동화로 인력 재배치, 연 0.8–1.2억 원 |
| 연 300억 매출 셀러 | 지연 안내 늦어 생기는 취소·반품, 통관 서류 오류 | 취소율·반품률 1–2%p 개선 시 3–6억 원 |

## 8. 시장 (출처 있는 것만)

- 한국 온라인쇼핑 2025년 272조 원(역대 최대), 해외직구 8.5조 원, 역직구 3.0조 원 — 국가데이터처.
- 글로벌 크로스보더 이커머스 2025년 약 1.1–1.75조 달러(2차 집계), Shopify 활성 스토어 약 480만 개(2차 집계).
- 한국 통신판매업 사업자 수는 공식 수치 미확인.

## 9. 다음 (로드맵, 영상 끝 20초)

주문 예외가 처리되면 셀러에게 시간이 남는다. 그 시간에 Lookout이 할 다음 일: 폰 영상 하나를 채널별 리스팅으로(SAM 3.1 + Muse Image), 리뷰와 수요를 읽어 다음에 팔 것을 제안(Spark 검색 그라운딩). 지금은 주문 예외, 다음은 파는 것과 키우는 것. 소싱→판매→운영을 한 시스템이 돌면 셀러는 큐레이터이자 오너가 된다.

## 10. 심사 기준과 대응

관문: 테마 적합 + Meta 모델의 의미 있는 사용. 본 심사: Impact / Use of Meta AI tooling / Technical depth and execution / Demo quality 동일 가중. 스타트업 트랙: "technical execution and whether it holds up in production". 심사 대상: 영상, 코드, 라이브 제품.

| 기준 | Lookout |
|---|---|
| 관문 | Build for Your World. Find·Fix·Ask 각각 Meta 모델 한 계열 |
| Impact | 모든 셀러가 매일 겪는 문제, 실제 셀러와 설계, 유형별 효과, 처리 건수·시간이 대시보드에 숫자로 |
| Use of Meta AI tooling | Glimmer 로컬 분류(Open Weight), Spark 추론·PDF·컴퓨터 사용·구조화 출력, Voice 전사. 각 모델을 공식 강점에 |
| Technical depth | 실제 쓰기 실행(Shopify API), 멱등 실행, 정책 게이트, 비용 상한, 원장 전체 열람, 심사위원이 직접 돌리는 "Run 24h" |
| Demo quality | 공개 첫 문장, 주문 예외 하나하나가 고쳐지는 하루, 실제 폰 WhatsApp, 11/4–8 라이브 |
| 보너스 | Best Agentic Use-Case, Best Build on Open Weight Models. Most Viral은 "포장하는 동안 고쳐져 있는" 15초 클립 |

## 11. 심사 기준이 요구하는 기획·디자인·개발

**기획 → Impact**: 모든 셀러의 문제로 시작해 한 명의 세계로 깊이 들어간다. 숫자로 말한다. 세 단계로 고정한다. 안 만든 기능을 말하지 않는다. 금지 항목(건강 조언, 기본 RAG, 단순 이미지 분석기) 근처 기능을 두지 않는다.

**디자인 → Demo quality**: 영상은 주문 예외가 들어오고 고쳐지는 장면의 연속이다. 카운터(발견/처리/대기, 안내까지 시간, 비용)가 늘 보인다. WhatsApp은 진짜 폰. "Run 24h" 버튼 하나. 영어 UI + 한국어 데이터(원문·번역 나란히). 꾸미기·브랜드 로고 없음.

**개발 → holds up in production**: 실제 쓰기(Shopify 개발 스토어)를 멱등 키로. 정책 게이트는 선언적 코드와 테스트. 원장이 중심. 비용 상한. 결정적 시나리오. 한 명령 실행. 미리 만드는 추상화 없음. 실제 셀러 계정·실제 외부 사이트 조작 없음.

## 12. 개발 도구와 팀

- 개발 도구는 자유(운영진 답변). 개발은 Claude Code로, 제품 안의 모델은 Meta 모델로.
- 팀은 승인된 참가자 1명. 조직의 다른 관리자는 저장소에 흔적을 남기지 않는다.
- 개발은 비공개 `solverineai/lookout-dev`에서, 제출 시 대회 작업만 담은 새 공개 저장소로 옮긴다.

## 13. 일정과 게이트

| 일 | 날짜 | 끝에 돌아가는 것 |
|---|---|---|
| 1 | 10/28 | 계정·크레딧, 타당성(Glimmer 속도, Spark 한국어·PDF, WhatsApp 수신, Shopify 쓰기, Wonder 한국 호출) |
| 2 | 10/29 | 시나리오 하루 1회가 Glimmer 분류로 돌고 원장에 남음 (Find) |
| 3 | 10/30 | 세관 보류 사건 → 실제 액션(안내 발송, 분할 출고) → WhatsApp 알림 → 브리핑 → 버튼 승인 → 환불 실행 (Fix·Ask) |
| 4 | 10/31 | 통지서 PDF 읽기, 음성 승인, Shopify 실제 쓰기(주소 수정·재고·환불) |
| 5 | 11/1 | 예외 유형 추가(주소 오류, 재고 불일치, 배송 지연, 취소 요청), 대시보드 "Run 24h"와 카운터 — **게이트** |
| 6 | 11/2 | 견고화(멱등·재시도·비용 상한 테스트), 호스팅, 컴퓨터 사용(가짜 셀러센터) 여유분 |
| 7 | 11/3 | README, 영상 촬영 |
| 8 | 11/4 | 영상 편집, 게시, 공개 저장소, 제출 (마감 11/5 11:00 KST) |

5일차 저녁에 세관 보류 하루가 끝까지 돌지 않으면 예외 유형을 줄인다. 영상 대본은 실제 동작하는 것만으로 쓴다.

## 14. 상금 구조

총 $1M. Startup 1–5등 $250K / $150K / $75K / $50K / $25K. 보너스: Most Viral $20K, Open Weight $10K, Community Vote $10K, Agentic $5K, Creative $5K. 트랙 상위 5팀이 11/9 결승 라이브(11/10 02:00 KST).

## 15. 용어 근거

| 우리 용어 | 업계 표준어 | 출처 |
|---|---|---|
| 주문 예외 | order exception — "transactions or order conditions that fall outside defined business rules and require review, correction, approval, or additional information before the order can proceed" | [Hyperbots 용어집](https://www.hyperbots.com/glossary/order-exceptions) |
| 예외 처리(Find·Fix·Ask) | exception management — 예외를 실시간으로 식별·알림·해결하는 체계 | [Fulfillment Hub USA](https://fulfillmenthubusa.com/real-time-exception-management-ensuring-smooth-e-commerce-order-flow/), [Fulfill.com](https://www.fulfill.com/glossary/exception-management), [Inventory Source](https://www.inventorysource.com/?p=13150) |
| 주소·연락처 오류 | address validation failure | [PayPal store-sync](https://developer.paypal.com/api/store-sync/use-cases), Amazon `INCORRECT_SHIPPING_ADDRESS` ([Buy with Prime API](https://documents.buywithprime.amazon.com/bwp-api/docs/order-objects-cancellationreasoninput)) |
| 재고 불일치 | fulfillment exception / inventory mismatch | [NetSuite](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_4817106573.html) |
| 배송 지연·정지 | delivery exception | [Cubework 용어집](https://www.item.com/glossary/delivery-exception) |
| 통관부호 오류·세관 보류 | customs hold | 택배사·통관 실무 용어 |
| 취소·변경 요청 | cancellation / order change request | Amazon·Shopify 주문 API |

Shopify·Amazon 공식 문서는 "order exception"을 분류명으로 쓰지 않지만 구성 요소(주소 검증 실패, 취소 사유 코드)는 같은 말로 부른다. 셀러 커뮤니티에서는 "problem orders", "stuck orders", "orders on hold"도 쓴다. 조사일 2026-10-28.
