# Lookout — 설계 스펙 (v3, Find · Fix · Ask)

작성 2026-10-28 · Meta Global AI Developer Hackathon 2026 · **Startup track · Build for Your World**
제출 마감 2026-11-04 21:00 ET (11-05 11:00 KST) · 심사 11/4–8 · 결승 라이브 11/9 정오 ET (11/10 02:00 KST)
심사 기준(공식 Discord `#faqs`·행사 페이지): 테마 적합 + Meta 모델의 의미 있는 사용이 관문, 그 뒤 Impact / Use of Meta AI tooling / Technical depth and execution / Demo quality 동일 가중. 스타트업 트랙은 "technical execution and whether it holds up in production".
기획은 [proposal.md](../../proposal.md), 모델 분석은 [meta-models.md](../../meta-models.md).

## 1. 한 줄

**Every store has orders that break. Lookout fixes them before customers notice.**

Lookout은 소규모 온라인 셀러 옆에서 일하는 AI 동료다. 주문 예외(order exceptions, 업계 표준어 — 출고·배송이 막혀 사람이 손대야 하는 주문)를 24시간 찾아내고(Find), 어댑터를 통해 직접 고치고(Fix), 돈이 움직이는 결정만 WhatsApp으로 묻는다(Ask).

## 2. 대상과 세계

- 대상: 소규모 온라인 셀러(independent online sellers). 혼자 또는 작은 팀, 여러 채널.
- 우리의 세계(데모): 호주 상품을 수입해 Naver Smart Store와 Shopify에 파는 서울의 셀러 한 명. 통관까지 겪는 가장 어려운 경우. 실제 셀러(솔버린 고객)가 모델이지만 이름·데이터는 쓰지 않고 데모 스토어는 가상이다.
- 테마: Build for Your World. "Your world is as big as you define it."

## 3. 범위

포함
- 주문 예외 5유형: 주소·연락처 오류(address validation failure), 통관 정보(개인통관고유부호) 오류·세관 보류(customs hold), 재고 불일치(inventory mismatch), 배송 지연·정지(delivery exception), 취소·변경 요청(cancellation / change request). 용어 근거는 proposal §15.
- Find: 채널·통관·배송·고객 이벤트 상시 분류 (Glimmer 로컬).
- Fix: 유형별 실제 액션 — 고객 메시지 발송(수정 요청·지연 안내), 주문 정보 수정, 출고 보류·해제, 분할 출고, 채널 간 재고 재배정, 세관 통지서 PDF 읽고 보완 서류 초안, (P3) 가짜 셀러센터 화면 조작.
- Ask: 정책 게이트, WhatsApp 알림·브리핑·버튼 승인, 음성 승인, 승인 후 실행(환불·재발송).
- 신뢰 레이어: 실행 원장, 멱등 실행, 하루 비용 상한.
- 어댑터: Shopify(개발 스토어, 실제 읽기·쓰기), Naver(합성, 쓰기도 합성 상태 변경), Customs(합성 + 통지서 PDF 샘플), Carrier(합성 추적), Customer messaging(WhatsApp 또는 합성 채널 메시지).
- 심사위원용 웹 대시보드: "Run 24h", 타임라인, 카운터, 원장, WhatsApp 미러.

제외(이번 제출)
- 리스팅 생성(SAM·Muse Image), 트렌드 리서치(검색 그라운딩) — 로드맵. CS 지식 기반 답변(Basic RAG 근접). 실제 셀러 계정 연결. 실제 외부 사이트 컴퓨터 사용. 건강·효능·성분 관련 모든 생성. Muse Wonder(한국 미제공, 1일차 확인 후 가능하면 PDF 읽기에만).

## 4. Find · Fix · Ask

| 단계 | 구성요소 | 모델 | 우선순위 |
|---|---|---|---|
| Find | Sentinel: Event → Triage(normal / exception:<type> / ignore, 근거 한 줄) | Glimmer(로컬) | P0 |
| Fix | Resolver: Exception + 관련 Event → Plan(Action[], 각각 reversible·amount·rationale) | Spark 1.3 구조화 출력 | P0 |
| Fix | Document reader: 세관 통지서·인보이스 PDF → 구조화 추출(품목·수량·부족 서류) | Spark 1.3 PDF 이해 (가능하면 Wonder) | P0 |
| Fix | Executor: 승인·자동 Action을 어댑터로 실행, 멱등 키, 결과 검증 | — | P0 |
| Fix | Screen operator: 가짜 셀러센터(저장소 내 정적 페이지)에 송장 입력 | Spark 1.3 computer use | P3 |
| Ask | Policy gate: Action → auto / approval / blocked | — | P0 |
| Ask | Messenger: WhatsApp 알림·브리핑·버튼·webhook | — | P0 |
| Ask | Voice: 음성 메시지 → 전사 → 결정 파싱 | Voice Transcribe + Spark | P1 |
| 신뢰 | Ledger, 비용 상한, 결정적 시나리오 | — | P0 |

### 유형별 Fix 플레이북 (v1)

| 유형 | 자동(Fix) | 승인(Ask) |
|---|---|---|
| 주소·연락처 오류 | 출고 보류, 고객에게 보완 요청, 답장 반영해 주문 수정, 보류 해제 | — |
| 통관부호 오류 | 출고 보류, 수정 요청, 반영 | — |
| 세관 보류 | 통지서 읽기, 영향 주문 추적, 지연 안내, 보류분 제외 분할 출고, 보완 서류 초안 | 취소 요청에 대한 환불 |
| 재고 불일치 | 채널 간 재배정, 노출 수량 조정, 출고 가능 전환 | 재고 없을 때 환불·대체 제안 |
| 배송 지연·정지 | 선제 안내, 택배사 조회 요청 | 재발송(비용) |
| 취소·변경 요청 | 출고 전이면 보류, 변경 반영 | 환불, 부분 환불 |

### 정책 게이트 규칙 (v1)
1. 돈이 나가는 것(refund, reship, compensation, 가격 변경)은 항상 approval.
2. 되돌릴 수 없는 것 중 고객 메시지 발송과 주문 정보 수정은 **auto**(플레이북 범위 안, 템플릿 기반, 원장 기록). 출고 변경은 auto. 리스팅 게시는 approval.
3. 건강·효능·성분 표현이 포함된 생성물은 blocked + 사람 이관.
4. 같은 idempotency_key는 두 번 실행하지 않는다. UNKNOWN은 재실행하지 않고 원장에 남긴다.
5. 하루당 모델 비용 상한(기본 $1.00). 넘으면 Spark 호출 중지, 브리핑에 표시.

"고객이 알기 전에 고친다"가 핵심이라 고객 메시지는 승인 없이 나간다. 대신 템플릿·톤·금지어 검사를 거치고 원장에 전문을 남긴다.

## 5. 하루의 흐름 (고정 시드 시나리오)

데모 모드는 하루(24시간)를 90초로 압축한다(시나리오 시계). 라이브 모드는 실시간. 같은 시드면 같은 하루.

| 시각 | 이벤트 | Find | Fix | Ask |
|---|---|---|---|---|
| 09:00 | 셀러 "맡길게" | 감시 시작 | | |
| 09:40 | Shopify 주문 #1042 주소에 동·호수 없음 | exception:address | 출고 보류, 고객에게 보완 요청 발송 | |
| 10:15 | 고객 답장 "302동 1104호" | | 주문 주소 수정(Shopify 쓰기), 보류 해제 | |
| 11:05 | Naver 주문, SKU-SLP-M 재고 0, Shopify에 2 | exception:stock | 재배정, Shopify 수량 1로 조정, 출고 가능 | |
| 09:00–14:11 | 주문 6, 문의 4, 추적 갱신 n | 전부 normal. Spark 호출 0회 | | |
| 14:12 | 세관 보류 통지서 PDF(식품 검역 서류 미비) | exception:customs | 통지서 읽기 → 부족 서류·품목. 영향 주문 14건, 통관부호 오류 3건 수정 요청, 지연 안내 14건(한국어), 분할 출고, 보완 서류 초안 | 취소 요청 3건 환불 → 대기 |
| 14:40 | | | | WhatsApp 알림 1건: 처리 중 요약 + "환불 3건 결정 필요" |
| 16:30 | 택배 추적 3일 정지 #1017 | exception:carrier | 선제 안내, 택배사 조회 요청 | 재발송 → 대기 |
| 18:00 | | | | WhatsApp 브리핑: 23건 발견 → 19건 처리 → 4건 대기. 안내까지 평균 3분. 절약 6.3시간. 비용 $0.13 (데모 서비스 계산값) |
| 18:05 | 음성 "환불은 1번이랑 2번만, 재발송은 해" | | | Voice → 결정 → 채널 환불 2건 실행, 재발송 주문 생성, 1건 보류 유지 → 원장 |
| 이후 | 계속 | 계속 | | 돈이 걸린 일이 생기면 즉시 Ask |

## 6. 모델 역할·가격·폴백

| 모델 | 역할 | 가격 | 폴백 |
|---|---|---|---|
| Muse Glimmer (30B, Apache 2.0, Ollama `muse-glimmer:30b-mlx` / llama.cpp Q4_K_M ≈19GiB) | Find 분류, 상태 | 0 | Together AI Glimmer 또는 Baseten `meta-models/muse-spark-open-1026` (둘 다 오픈 웨이트) |
| Muse Spark 1.3 | Resolver, Document reader, 브리핑 문장, 음성 결정 파싱, (P3) computer use | $1.25 / $4.25 per 1M | 한국어 품질 부족 시 영어+번역 |
| Muse Wonder 1.0 | (한국에서 호출되면) Document reader | $4 / $20 per 1M | **models 페이지: 한국 미제공.** 기본 Spark. 지역 통제 우회 금지 |
| Muse Voice Transcribe | 음성 승인 (한국어, 키워드 바이어싱: 환불·재발송·승인·보류·상품명) | $0.18/시간 | 버튼 승인만 |

Agent frameworks: Meta 공식 가이드가 Claude Agent SDK·Codex app-server 연결을 다룬다. 1일차에 직접 루프 vs SDK 결정.

## 7. 구성요소와 기술 결정

단일 Python 서비스(FastAPI, uvicorn) + SQLite + 정적 HTML(htmx) 대시보드. 외부: Meta Model API(`openai` 클라이언트, base_url 교체), Ollama(OpenAI 호환), WhatsApp Cloud API(webhook 1개), Shopify Admin API.

| 구성요소 | 역할 |
|---|---|
| clock | 시나리오 시각 소유. 데모 1분=1초 |
| scenario engine | 가상 스토어·이벤트 피드·시드. 고객 답장 같은 후속 이벤트도 시나리오가 낸다 |
| adapters | shopify(실제), naver(합성), customs(합성+PDF), carrier(합성), messaging(WhatsApp/합성). 공통 인터페이스: `read_events()`, `apply(action)` |
| sentinel | Glimmer 분류 루프 |
| resolver | Spark. Exception → Plan(Action[]) 구조화 출력, 플레이북 프롬프트 |
| document reader | Spark PDF → 구조화 추출 |
| policy | 규칙 5개, 선언적 |
| approvals | 대기 Action, WhatsApp 버튼·음성 반영 |
| executor | 어댑터 `apply`, 멱등 키, 결과 검증(사후 조건 재조회), UNKNOWN 처리 |
| messenger | WhatsApp 송수신·버튼·음성 파일 |
| voice | OGG → ffmpeg WAV 16k mono → Voice Transcribe → Spark 결정 파싱 |
| ledger | append-only: 모델·도구 호출, 판단, 정책 검사, 실행, 토큰·비용·지연 |
| dashboard | "Run 24h", 타임라인, 카운터(발견/처리/대기, 안내까지 시간, 절약 시간, 비용, 분류·호출 수), 원장, WhatsApp 미러 |
| mock seller center | 저장소 내 정적 페이지(송장 입력 폼), P3 |

저장소 구조: `app/`(main, clock, scenario/, adapters/, agents/{sentinel,resolver,docreader,voice}, policy, approvals, executor, ledger, messenger, models) · `web/` · `tests/` · README · LICENSE · .env.example · Dockerfile.

### 데이터 (최소 필드)
- Event: id, run_id, source(shopify/naver/customs/carrier/customer/seller/document), kind, at, payload
- Exception: id, run_id, type(address/pccc/customs/stock/carrier/cancel), opened_at, order_ids[], cause, status(open/fixing/waiting_approval/fixed/escalated), event_ids[]
- Action: id, exception_id, type(message_customer / hold / release / update_order / split_shipment / reallocate_stock / draft_document / refund / reship / operate_screen), target, amount?, reversible, rationale, decision(auto/approval/blocked), approval(pending/approved/rejected), idempotency_key, result?, verified_at?
- Ledger: id, run_id, at, actor(glimmer/spark/voice/policy/executor/seller), kind, input_ref, output_ref, tokens, cost_usd, latency_ms

## 8. 데모·제출

- 영상 3분. 첫 문장: "Everything here was built this week; nothing pre-existing." 구조: 한 줄 → 포장 중인 셀러 → 주문 예외가 들어오고 고쳐지는 장면 4개(주소, 재고, 세관 보류+PDF, 배송 정지) → 14:40 WhatsApp 알림(실제 폰) → 18:00 브리핑·음성 승인·환불 실행 → 카운터와 원장 → 로드맵 20초(리스팅, 다음에 팔 것) → 한 문장. 안 만든 기능은 넣지 않는다.
- 심사위원: 호스팅 대시보드 "Run 24h" → 실제 모델 호출로 90초 하루. 11/4–8 가동, 크레딧 잔량 확인.
- 제출물: 공개 저장소, 영상 링크, 기여자 이름, X 게시 링크. Threads에도 게시. 커뮤니티 투표 안내 글.
- 저장소: 영어 README(한 명령 실행, 구조도, 원장 설명, Find·Fix·Ask), MIT LICENSE, 합성 데이터에 실존 정보 없음, 자산은 라이선스 확인된 것만.
- 저장소 운영: 개발은 비공개 `solverineai/lookout-dev`. 제출 시(8일차) 대회 작업만 담은 새 공개 저장소를 만들어 커밋을 옮기고 모든 커밋 날짜가 10/27 01:00 KST 이후인지 확인. 내부 문서(`docs/hackathon/`, `docs/concept/`, `docs/applications-*.md`, 규정 PDF)는 `.gitignore` 제외.
- 제출 폼: 트랙 Startup, 테마 Build for Your World, 공개 저장소, 영상, X 게시, 기여자 1명.

## 9. 효과와 시장 (피칭용, 가정 명시)

| 셀러 유형 | 지금 | Lookout |
|---|---|---|
| 1인 셀러 | 주문 예외 하루 5–10건 × 20분 = 2–3시간, 연 약 800시간 | 80% 반환, 연 1,600만 원 상당 + 잃던 주문 회수 |
| 10–15명 팀 | 예외 처리에 묶인 인력 2–3명, 연 1–1.5억 원 | 연 0.8–1.2억 원 |
| 연 300억 매출 | 취소·반품, 통관 서류 오류 | 1–2%p 개선 시 3–6억 원 |

시장: 한국 온라인쇼핑 2025년 272조 원, 해외직구 8.5조, 역직구 3.0조(국가데이터처). 글로벌 크로스보더 약 1.1–1.75조 달러, Shopify 약 480만 스토어(2차 집계). 통신판매업 사업자 수 미확인.

## 10. 일정 (오늘 포함 8일)

| 일 | 날짜 | 끝에 돌아가는 것 |
|---|---|---|
| 1 | 10/28 | 계정·크레딧(Meta·Baseten·Modal), WhatsApp 테스트 번호, Shopify 개발 스토어. 타당성: Glimmer 로컬 속도, Spark 한국어·PDF·구조화 출력, WhatsApp 한국 번호 수신, Shopify 쓰기(주소·재고·환불), Wonder 한국 호출. Agent frameworks 결정 |
| 2 | 10/29 | clock, scenario, Event·Ledger, adapters 인터페이스 + naver·customs·carrier(합성), sentinel(Glimmer) — 하루 1회가 분류되어 원장에 남음 |
| 3 | 10/30 | resolver(세관 보류 플레이북), policy, approvals, executor(합성 어댑터), messenger — 14:12 사건 → 안내 발송·분할 출고 → 14:40 알림 → 18:00 브리핑 → 버튼 승인 → 환불 실행 |
| 4 | 10/31 | document reader(PDF), voice, shopify 어댑터 실제 쓰기(주소 수정·재고·환불·재발송) |
| 5 | 11/1 | 나머지 유형(주소, 재고, 배송, 취소) 플레이북, 대시보드 "Run 24h"·카운터·원장 — **게이트** |
| 6 | 11/2 | 견고화: 멱등·재시도·UNKNOWN·비용 상한 테스트, 호스팅, (여유) 가짜 셀러센터 computer use |
| 7 | 11/3 | README, LICENSE, 영상 촬영 |
| 8 | 11/4 | 영상 편집, X·Threads 게시, 공개 저장소, 제출 |

게이트: 5일차 저녁에 세관 보류 하루가 끝까지 돌지 않으면 유형을 줄인다(세관 보류 + 주소 오류만). 영상 대본은 7일차에 실제 동작하는 것만으로 쓴다.

## 11. 심사 기준 대응

| 기준 | 대응 |
|---|---|
| 관문 | Build for Your World. Find=Glimmer, Fix=Spark, Ask=Voice+게이트 |
| Impact | 모든 셀러의 매일 문제. 실제 셀러와 설계. 처리 건수·안내 시간·절약 시간이 카운터로 |
| Use of Meta AI tooling | Glimmer 로컬(Open Weight 보너스), Spark 구조화 출력·PDF·computer use, Voice 한국어 전사 |
| Technical depth ("holds up in production") | 실제 쓰기(Shopify), 사후 조건 검증, 멱등, 정책 게이트, 비용 상한, 원장, 결정적 시나리오, 심사위원 라이브 |
| Demo quality | 주문 예외가 고쳐지는 장면의 연속, 실제 폰 WhatsApp, 라이브 가동 |
| 보너스 | Best Agentic Use-Case, Best Build on Open Weight Models, Most Viral 15초 클립 |

## 12. 규정 준수

- 모든 코드·문서는 10/27 01:00 KST 이후. 기존 코드 없음. 영상 첫 문장에 명시.
- 금지 항목 회피: 건강·효능 생성 없음, CS 지식 기반 답변 없음, 단순 이미지 분석기 없음.
- 개인정보 없음: 합성 데이터, 실제 계정 미연결, 실존 이름·주소 없음.
- 세관 보류 사유는 실제 존재하는 것만. 지식재산권 사안 제외.
- 개발 도구 자유(운영진 답변). 개발은 Claude Code, 제품 모델은 Meta. 팀 1명, 다른 관리자 흔적 없음.
- Wonder 지역 제한 우회 금지.

## 13. 리스크

| 리스크 | 대응 |
|---|---|
| Glimmer 로컬 속도·메모리(≈19GiB) | 1일차 확인, Together/Baseten 폴백 |
| Wonder 한국 미제공 | 기본 Spark. 1일차 호출 확인 |
| Spark 한국어 안내문 품질 | 1일차 확인, 템플릿+영어 생성+번역 폴백 |
| WhatsApp 한국 번호 수신·24시간 창 | 1일차 실발송, "맡길게" 선발신 |
| Shopify 쓰기 범위(환불·재고 API 권한) | 1일차 확인, 안 되면 합성 어댑터 |
| 고객 메시지 자동 발송의 오발송 | 플레이북 템플릿, 금지어 검사, 데모는 합성 고객 |
| 혼자 8일 | 5일차 게이트, 유형 축소 가능 |
| 심사 기간 크레딧 | 하루 비용 상한, 잔량 표시 |
| 결승 라이브 | 고정 시드 경로, 녹화 백업 |
