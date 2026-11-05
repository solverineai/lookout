# Meta 모델 분석 — 해커톤 제공 모델과 Lookout 적용

조사일 2026-10-28 (KST). 출처는 dev.meta.ai 공식 문서와 해커톤 Discord `#faqs`. 가격·제약은 조사 시점 기준이며 바뀔 수 있다.

## 1. 해커톤이 제공하는 모델

Discord `#faqs` "Which models can I use?": Meta Model API로 **Muse Spark, Muse Wonder, Muse Image, Muse Voice Transcribe, SAM 3.1**, 오픈 웨이트로 **Muse Glimmer, Muse Spark Open**. 코딩 보조용 **Muse Code**도 제공.

지원·크레딧
- Meta Model API 크레딧 $150/인 (개별 신청, 11/4 21:00 ET까지, 카드 필수)
- Baseten $100 + 분당 2M 토큰 한도 (용도 심사, 2,000명). 해커톤용 모델 ID: `meta-models/muse-spark-open-1026`
- Modal $100 (선착순 1,000명) · Fireworks 미정
- 라이브 세션: Agents 101(10/27), Agents 102(10/28), Fireworks 추론·학습(10/30), 정오–1시 ET

## 2. 모델 목록

| 모델 (ID) | 한 줄 | 입력 → 출력 | 컨텍스트 | 가격 |
|---|---|---|---|---|
| **Muse Wonder** (`muse-wonder-1.0`, preview) | "Meta's most capable model, built for complex software engineering and long-horizon agentic work." | 텍스트·이미지·영상·오디오·PDF → 텍스트 | 1,048,576 | $4 / $20 per 1M (캐시 입력 $0.20) |
| **Muse Spark 1.3** (`muse-spark-1.3`, 신규 작업 권장) | "Meta's model for agentic and coding work" | 텍스트·이미지·영상·오디오(부분)·PDF → 텍스트 | 1,048,576 | $1.25 / $4.25 per 1M (캐시 $0.15). Contributor 모드 $0.10 / $0.20 (학습 데이터 제공 조건) |
| **Muse Image** (`muse-image-1.0`) | "Meta's image generation model line" | 텍스트·이미지 → 이미지 | — | 생성 성공 장당 $0.01 (내장 검색 포함) |
| **Muse Voice Transcribe** (`muse-voice-transcribe-1.0`) | "Meta's speech-to-text model on Meta Model API" | 오디오 → 텍스트 | — | 오디오 시간당 $0.18 |
| **SAM 3.1** (`sam-3.1`) | "Meta's segmentation model on Meta Model API" | 텍스트 프롬프트·이미지·영상 → 박스·마스크·트랙 | — | 이미지 1천 장 $2.50, 영상 1천 프레임 $0.20 (영상 요청당 최소 50프레임) |
| **Muse Glimmer** (오픈 웨이트) | "Meta's 30B open-weight multimodal model, distilled from Muse Spark and built for local and edge deployment." | 텍스트·이미지 → 텍스트 | 128K 기본 | 자체 실행 0. Together AI 호스팅 $0.35 / $1.50 |
| **Muse Spark Open** (오픈 웨이트) | "816B-parameter mixture-of-experts model with 42B active parameters" | 텍스트·이미지·오디오·영상 → 텍스트 | — | Baseten·Fireworks·Together·Groq·Nebius·Modal·OpenRouter 호스팅 |

웹 검색(search grounding)은 Wonder·Spark 공통 1천 회 $2.50 추가. API는 OpenAI SDK 호환(`base_url=https://api.meta.ai/v1`), Responses·Chat Completions·Messages 세 프로토콜.

## 3. 모델별 특장점과 제약

### Muse Wonder 1.0
- 강점: 긴 멀티스텝 에이전트 작업, 서브에이전트 위임, 병렬 도구 호출, 오류 복구. **컴퓨터 사용**(`tools=[{"type":"computer"}]`, Responses API 전용) 주 모델. PDF·영상·오디오 이해. reasoning effort `minimal`~`max`.
- 제약: preview. **"Muse Wonder and Muse Wonder Full are not currently available in South Korea, on Model API or in Muse Code."**(models 페이지 Model availability). Geographic Use Policy는 지역 통제 우회를 금지한다. Contributor 모드 없음. Wonder Full은 Muse Code 구독 전용, API 없음.
- Lookout: **한국에서 호출 불가 가능성이 높다.** 1일차에 실제 호출로 확인하고, 막히면 같은 엔드포인트·같은 요청으로 동작하는 Spark 1.3으로 대체한다(문서: "take the same requests on the same endpoints").

### Muse Spark 1.3
- 강점: 에이전트·도구 호출 주력. 병렬·스트리밍 도구 호출, 턴 간 추론 유지, 구조화 출력, **검색 그라운딩 내장**(`{"type":"web_search"}`, `url_citation` 인용과 `results` 원천 반환), PDF·이미지·영상 이해, **컴퓨터 사용도 같은 루프로 저비용 실행**. 1M 컨텍스트. Claude Agent SDK·Codex app-server 연결 공식 지원.
- 제약: 오디오 입력은 1.2 권장. 검색 그라운딩은 Chat Completions에서 불가(Responses·Messages만). 복잡한 다단계 리서치는 "less dependable" — 좁은 질문으로 나눠서.
- Lookout: 사건 추론, Grow 리서치, 리스팅 문구, 브리핑, 음성 승인 해석, (Wonder 대체) 서류 데스크·컴퓨터 사용. 사실상 주력 모델.

### Muse Image 1.0
- 강점: 생성과 편집 한 모델. Responses API로 멀티턴 수정(`previous_response_id`). 참조 이미지 URL·base64·file_id, 편집 시 1–10장 입력, 다중 이미지 합성. **스스로 웹·이미지 검색하고 코드 실행**(차트·레이아웃). 출력 webp/png/jpeg, `size`는 비율만.
- 제약: `web_search` 도구를 넘기면 오류(자체 검색). `moderation` 파라미터 미지원. 인도 지역 미제공. 정확한 픽셀 지정 불가.
- Lookout: 카탈로그 사진·광고 소재. 참조 이미지로 상품 일관성 유지.

### Muse Voice Transcribe 1.0
- 강점: 배치(`POST /v1/asr/transcribe`, WAV 16/24kHz mono 16-bit)와 실시간(WebSocket). **한국어 포함 25개 언어, 코드 스위칭**. 화자 분리, 엔드포인팅, 키워드 바이어싱(상품명·고유명사). 시간당 $0.18.
- 제약: 턴 단위 타임스탬프만. 배치 32MB·10분 한도. 음성 합성 없음. ffmpeg 변환 필요(WhatsApp 음성은 OGG/Opus).
- Lookout: WhatsApp 음성 승인·지시. 키워드에 상품명·"승인"·"보류" 등록.

### SAM 3.1
- 강점: 명사 한 마디("slipper")로 모든 해당 객체 분할. 박스·포인트 프롬프트. **영상에서 객체 식별을 유지하며 추적**(MP4/MOV, H.264/H.265). 마스크는 `@meta-sam/parser`로 래스터 디코드. Spark와 조합(Spark가 장면 해석, SAM이 마스크).
- 제약: 요청당 개념 하나. 영상 요청 최소 50프레임 과금. 영상 길이·해상도 상한은 문서에 없음(1일차 확인). 매칭 없으면 빈 출력.
- Lookout: 폰 영상 → 상품 누끼(Sell), 입고 박스 수량 세기(P3).

### Muse Glimmer (오픈 웨이트, Apache 2.0)
- 강점: 30B dense, Spark 증류, 텍스트+이미지, 128K. 로컬 에이전트 워크플로용, 단계별 추론. llama.cpp(b10353+)·Ollama(0.32.7+)·vLLM·SGLang·ExecuTorch·LM Studio 지원. 도구 호출은 채팅 템플릿으로 지원.
- 메모리: GGUF Q4_K_M 16.8GB(비전 프로젝터 포함 131K 컨텍스트에서 19.0GiB, "fits a 24 GiB card"), Q4_K_XL 19.7GB. bf16는 약 60GB 가중치·72GB VRAM.
- Mac: Ollama `muse-glimmer:30b-mlx`(MLX 엔진), SGLang MLX는 48GB+ 통합 메모리, 텍스트만. llama.cpp는 CPU/GPU 혼합 가능.
- 제약: "Don't run this model greedy"(temperature 0 금지, 기본 1.0/top_p 0.95). `<|eom|>`에서 멈추면 도구 호출이 잘림. llama.cpp에서는 reasoning을 끌 수 없음. 이미지 입력은 GGUF+프로젝터 또는 bf16만.
- Lookout: 상시 분류 파수꾼. Mac 메모리가 부족하면 Together AI 호스팅(여전히 오픈 웨이트)으로.

### Muse Spark Open (오픈 웨이트)
- 816B MoE(42B 활성). 자체 호스팅은 B300 4–8장급. Mac은 Mac Studio 512GB 두 대 이상.
- Lookout: 직접 띄우지 않음. Glimmer 폴백으로 Baseten(`meta-models/muse-spark-open-1026`) 사용 가능.

## 4. 공통 기능

| 기능 | 요지 | Lookout 사용처 |
|---|---|---|
| 파일 입력 | 인라인 50MB, 업로드 1GiB. PDF는 앞 100쪽 텍스트 + 앞 50쪽 이미지로 변환돼 함께 전달 | 세관 통지서·인보이스 PDF |
| 구조화 출력 | JSON 스키마 강제 | Action[]·Card·추출 결과 |
| 도구 호출·도구 검색 | 병렬·스트리밍, 지연 로딩 | 어댑터 호출 |
| 검색 그라운딩 | `web_search` 도구, 인용·원천 반환, `search_context_size` | Grow 리서치 |
| 컴퓨터 사용 | 스크린샷 입력 → `computer_call`(click/type/scroll/…) 출력, 29쌍 상태 없는 재생, 25MiB 이미지, 안전 확인은 하네스가 결정 | 가짜 셀러센터 조작(P3) |
| 프롬프트 캐싱 | 캐시 입력 Spark $0.15 | 시스템 프롬프트·정책 |
| Agent frameworks | Claude Agent SDK(Messages, `ANTHROPIC_BASE_URL` 호스트만, `ANTHROPIC_AUTH_TOKEN`), Codex app-server(Responses). 주 루프 Wonder, 서브 Spark 권장 | 에이전트 루프를 직접 짤지 1일차 결정 |

## 5. 모델 → Lookout (Find · Fix · Ask)

| 단계 | 기능 | 1순위 모델 | 폴백 |
|---|---|---|---|
| Find | 이벤트 상시 분류·상태 | Glimmer(로컬) | Together/Baseten 호스팅 |
| Fix | 주문 예외 해결 계획(Action[] 구조화 출력), 고객 안내문, 브리핑 | Spark 1.3 | — |
| Fix | 세관 통지서·인보이스 PDF 읽기 | **Spark 1.3** (Wonder는 한국 미제공 확인 전까지 보류) | — |
| Fix | 가짜 셀러센터 화면 조작(P3) | Spark 1.3 computer use | 제외 |
| Ask | 음성 승인 | Voice Transcribe (한국어, 키워드 바이어싱) | 버튼만 |
| 로드맵 | 영상→리스팅 | SAM 3.1 + Muse Image + Spark | 이번 제출 제외 |
| 로드맵 | 다음에 팔 것 리서치 | Spark 1.3 검색 그라운딩 | 이번 제출 제외 |

## 6. 이번 조사로 바뀌는 것

1. **Wonder 의존 제거**: 서류 데스크와 컴퓨터 사용을 Spark 1.3 기준으로 설계한다. Wonder는 1일차에 한국에서 호출되는지 확인하고, 되면 서류 데스크만 Wonder로 올린다. 지역 통제 우회는 하지 않는다.
2. **Glimmer 로컬 경로 확정**: Ollama `muse-glimmer:30b-mlx` 또는 llama.cpp Q4_K_M. 메모리 약 19GiB. Mac 통합 메모리 32GB면 가능, 16GB면 호스팅.
3. **검색 그라운딩은 Responses API**: Grow는 Responses로, 좁은 질문 여러 개로 나눠 호출하고 인용을 카드에 표시.
4. **음성 파이프라인**: WhatsApp OGG → ffmpeg → WAV 16kHz mono → 배치 전사. 키워드 바이어싱에 상품명·승인 어휘.
5. **SAM·Muse Image·검색 그라운딩은 로드맵으로**: 이번 제출은 주문 예외 처리에 집중. 비용·문서 조사는 대회 후 리스팅·리서치 기능에 쓴다.
6. **비용 추정(하루 1회 데모)**: Glimmer 0, Spark 호출 8–12회(해결 계획·PDF·브리핑·음성 파싱) 약 $0.15–0.40, Voice 1분 $0.003 → 하루 $0.5 이하. 상한 $1 유지.

## 7. 1일차 확인 항목

- [ ] 한국에서 `muse-wonder-1.0` 호출 가능 여부 (models 페이지는 미제공이라고 함)
- [ ] Glimmer: Ollama MLX로 이벤트 1건 분류 2초 이내
- [ ] Spark 1.3: 한국어 고객 안내문 품질, Action[] 구조화 출력, PDF 1장 구조화 추출
- [ ] Shopify 개발 스토어: 주소 수정·재고 조정·환불 API 쓰기 권한
- [ ] Voice: 한국어 음성 10초 전사 정확도(키워드 바이어싱 포함)
- [ ] Agent frameworks: Claude Agent SDK를 Meta API에 붙여 쓸지 vs 직접 루프

## 출처

- Models: https://dev.meta.ai/docs/models
- Overview: https://dev.meta.ai/docs/overview
- Pricing and rate limits: https://dev.meta.ai/docs/pricing-rate-limits
- Computer use: https://dev.meta.ai/docs/computer-use
- Search grounding: https://dev.meta.ai/docs/search-grounding
- File handling: https://dev.meta.ai/docs/file-handling
- Image generation: https://dev.meta.ai/docs/image-generation
- Speech to text: https://dev.meta.ai/docs/speech-to-text
- Media segmentation: https://dev.meta.ai/docs/media-segmentation · SAM overview: https://dev.meta.ai/docs/sam/overview
- Muse Glimmer: https://dev.meta.ai/docs/muse-glimmer · quantization: https://dev.meta.ai/docs/muse-glimmer/quantization · deploy: https://dev.meta.ai/docs/muse-glimmer/deploy · hardware: https://dev.meta.ai/docs/muse-glimmer/hardware-platforms
- Open-weight models: https://dev.meta.ai/docs/open-weight-models · Muse Spark Open deploy: https://dev.meta.ai/docs/muse-spark-open/deploy
- Agent frameworks: https://dev.meta.ai/docs/agent-frameworks
- Geographic Use Policy: https://dev.meta.ai/legal/geographic-use-policy
- Muse Wonder launch: https://dev.meta.ai/resources/blog/build-with-muse-wonder
- Discord `#faqs` (Cerebral Valley, 2026-10-26): 제공 모델·크레딧·Baseten 모델 ID
