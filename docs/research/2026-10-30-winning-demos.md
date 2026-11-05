# How winning hackathon projects showed their demos

Researched 2026-10-30. The winning videos themselves could not be fetched (YouTube blocked automated access), so first-seconds timing and slide-to-product ratios are not verified. Sources are recaps, READMEs, one winner's written demo plan and organizer/judge guidance.

## Examples

| Project (event, place) | What was verifiable about the demo | Source |
|---|---|---|
| OrgLens (LlamaCon 2025, 1st) | One demo video in the README; Llama in the tagline, stack and env var | [blog](https://ai.meta.com/blog/llamacon-hackathon/), [repo](https://github.com/TheCl3m/llama-hack) |
| Llama CCTV Operator (LlamaCon, 3rd) | Five step-by-step screenshots, pipeline diagram naming Llama 4 as the detector | [repo](https://github.com/torayeff/llamacon-hackathon-2025-sf/) |
| Geo-ML (LlamaCon, Best Llama API) | Real 400-page geology report, built by a working geologist. README says Llama 4 but the default config uses another model | [repo](https://github.com/williamjsdavis/geo-lm) |
| OpenGlass (Llama 3 2024, 1st) | Real hardware on video, "<$25" cost line | [repo](https://github.com/BasedHardware/OpenGlass) |
| CrossBeam (Anthropic Opus 4.6 hackathon, 1st) | Planned pause where the agent asks the human; side-by-side with real production results; mock answers for a reproducible run | [blog](https://claude.com/blog/meet-the-winners-of-our-built-with-opus-4-6-claude-code-hackathon), [DEMO.md](https://github.com/mikeOnBreeze/cc-crossbeam/blob/main/DEMO.md) |
| TARA (same event, prize) | 3-minute flow on a named real road; "$56 dashcam vs $800,000 survey van"; cached data so it runs without a key | [repo](https://github.com/Kye256/tara-transport-assessment) |
| Jayu (Gemini API Competition, Best Overall) | Names which model does what and why (Flash controls, Pro sees) | [project](https://ai.google.dev/competition/projects/jayu) |
| Likeminds (Agno Agent Hackathon, Grand Prize) | Live URL plus video | [winners](https://www.agno.com/blog/global-agent-hackathon-winners) |

Guidance: [Devpost](https://info.devpost.com/blog/6-tips-for-making-a-hackathon-demo-video) (pitch in the first seconds, no slide decks), [lablab](https://lablab.ai/guide/how-to-win-an-ai-hackathon) (clarity over polish, product fills the middle, a demo judges can't open scores as not working), [AngelHack](https://angelhack.com/blog/10-tips-to-help-you-rock-your-next-hackathon-demo/) (side-by-side with the old process, name the model and the evaluation, explain hidden work instead of narrating clicks).

## Patterns and what Lookout changed

| Pattern | Before | Now |
|---|---|---|
| Product in the first seconds | 67 s of text cards before the product | Frame 1 is the live product on a real-shaped broken order; one-line disclosure on top |
| Planned "agent asks the human" moment | 14:40 ask shown like any other step | "Lookout pauses and asks" is its own beat on the phone |
| Proof by trace and comparison | Ledger only | Per-order trace (click any order), end-of-day "by hand vs with Lookout" card, duplicate refund refused |
| Name each model and why | Model names in one card | "How it works" band on the page with live counts; architecture section in the video |
| Reproducible demo | Fixed seed | Same, now said out loud ("same seed, same day"), and the page states that model calls are simulated |
| Concrete hook number | 15–30 min per exception | Kept; added "23 exceptions ≈ 7.7 h by hand" from the live run |

Not done: a real phone on camera and a human voiceover. Both need the seller or the team (proposal §11 already plans the real-phone WhatsApp shot). No good TTS voice is set up on this Mac without a Google Cloud login.
