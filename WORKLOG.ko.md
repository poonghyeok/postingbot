# 작업 기록

이 문서는 Posting Bot에 적용된 구현 작업을 기록합니다. 이후 작업은 최신 내용을 쉽게 찾을 수 있도록 날짜별 기록의 위쪽에 추가합니다.

## 프로젝트 개요

Posting Bot은 Gemini API로 한국어 Markdown 글을 작성하고 수정하는 Telegram 봇입니다. 사용자가 초안을 승인하면 GitHub에서 호스팅되는 Jekyll/Chirpy 블로그의 `_posts/` 디렉터리에 게시합니다.

## 2026-09-27 — 최초 구현 및 Docker 배포

### 애플리케이션 흐름

- `python-telegram-bot`과 long polling 방식으로 Telegram 봇을 구현했습니다.
- `/start`, `/suggest`, `/write`, `/revise`, `/publish`, `/cancel` 명령을 추가했습니다.
- `ALLOWED_TELEGRAM_USER_ID`로 지정한 Telegram 사용자만 명령을 사용할 수 있도록 제한했습니다.
- 현재 초안, 제목, 카테고리, 태그를 Telegram `user_data`에 저장하도록 구현했습니다.
- 글 생성, 수정 또는 게시가 실패해도 기존 초안이 유지되도록 처리했습니다.
- Gemini와 GitHub의 동기 HTTP 요청을 `asyncio.to_thread`로 워커 스레드에서 실행하여 Telegram 비동기 이벤트 루프가 멈추지 않도록 했습니다.

### Gemini 연동

- `httpx`를 사용해 Gemini `generateContent` REST API를 연동했습니다.
- 한국어 주제 추천, 글 작성, 피드백 기반 수정용 프롬프트를 추가했습니다.
- 생성 제목, 최대 2개의 카테고리, 최대 5개의 태그, Markdown 본문으로 구성된 모델 응답 형식을 정의했습니다.
- 모델 응답 형식이 불완전한 경우를 대비해 기본값이 포함된 파서를 구현했습니다.
- 기본값이 `gemini-2.5-flash`인 `GEMINI_MODEL` 설정을 추가했습니다.
- Telegram 메시지 크기 제한을 넘지 않도록 미리보기 길이를 제한했습니다.

### GitHub 및 Jekyll 게시

- Fine-grained personal access token을 사용하는 GitHub Contents API를 연동했습니다.
- 레이아웃, 제목, 날짜, 카테고리, 태그가 포함된 Chirpy 호환 Jekyll front matter를 생성하도록 했습니다.
- 게시물 시간대는 `Asia/Seoul`을 사용합니다.
- 게시물을 `_posts/YYYY-MM-DD-HHMMSS.md` 경로에 생성합니다.
- GitHub Contents API 규격에 맞게 게시물 내용을 Base64로 인코딩합니다.
- 게시 완료 후 생성된 GitHub 파일 URL을 Telegram 사용자에게 전달합니다.

### 설정 및 비밀값 관리

- 필요한 설정 변수를 안내하는 `.env.example`을 추가했습니다.
- `.env`, 가상 환경, Python 캐시, 기존 비밀 파일이 Git에 포함되지 않도록 `.gitignore` 규칙을 추가했습니다.
- 비밀값, Git 메타데이터, 개발 파일, 문서가 Docker 빌드 컨텍스트에 포함되지 않도록 `.dockerignore` 규칙을 추가했습니다.
- Compose가 `.env`의 항목을 실행 시점 환경 변수로 주입하도록 설정했습니다. `.env` 파일 자체는 이미지에 복사되지 않습니다.

필수 환경 변수:

| 변수 | 용도 |
| --- | --- |
| `GEMINI_API_KEY` | Gemini API 요청 인증 |
| `TELEGRAM_BOT_TOKEN` | Telegram 봇 인증 |
| `GITHUB_TOKEN` | GitHub Contents API 쓰기 권한 인증 |
| `GITHUB_REPOSITORY` | `owner/repository` 형식의 게시 대상 저장소 지정 |
| `GEMINI_MODEL` | 사용할 Gemini 모델 지정 |
| `ALLOWED_TELEGRAM_USER_ID` | 봇 사용자를 한 명으로 제한 |

### 컨테이너화

- `python:3.12-slim` 기반 Docker 이미지 정의를 추가했습니다.
- `requirements.txt`에 고정된 Python 의존성을 설치하도록 구성했습니다.
- Python 출력을 버퍼링하지 않고 `.pyc` 파일을 생성하지 않도록 설정했습니다.
- 컨테이너 내부에 권한이 제한된 `postingbot` 시스템 사용자를 생성하고 해당 사용자로 실행합니다.
- `.env` 주입, init 프로세스, `unless-stopped` 재시작 정책이 적용된 Docker Compose 설정을 추가했습니다.
- 멀티 아키텍처 기반 이미지를 사용하므로 AMD64 Ubuntu에서 소스 변경 없이 네이티브 빌드할 수 있습니다. 다른 아키텍처에서 교차 빌드할 때는 `docker buildx build --platform linux/amd64`를 사용할 수 있습니다.

### 문서화

- 로컬 Python 가상 환경 설치 방법을 추가했습니다.
- Docker Compose 빌드, 실행, 로그 확인, 종료 명령을 문서화했습니다.
- Telegram 명령 사용 흐름과 생성되는 Jekyll front matter 형식을 설명했습니다.

### 검증 결과

- Docker Compose를 이용해 `postingbot:local` 이미지를 정상적으로 빌드했습니다.
- `postingbot-postingbot-1` 컨테이너를 정상적으로 시작했습니다.
- 확인 시점에 컨테이너가 재시작 횟수 0으로 계속 실행 중임을 확인했습니다.
- 비밀값을 출력하지 않고 6개 설정 변수가 모두 컨테이너에 존재하는 것을 확인했습니다.
- 초기 컨테이너 로그에서 시작 오류가 없음을 확인했습니다.

### 현재 제약사항

- 초안 상태는 프로세스 메모리에만 저장되므로 봇을 재시작하면 사라집니다.
- 설정된 Telegram 사용자 한 명만 사용할 수 있습니다.
- GitHub Contents API를 통해 항상 대상 저장소의 기본 브랜치에 게시합니다.
- 아직 자동 테스트, 상태 점검(health check), 영구 데이터 저장소, CI 파이프라인이 없습니다.
- 외부 API 오류는 사용자 친화적인 Telegram 메시지로 표시하고 상세 오류는 컨테이너 출력에 기록합니다.

## 추가된 파일

| 파일 | 역할 |
| --- | --- |
| `bot.py` | Telegram 명령, Gemini 글 생성, 초안 상태, GitHub 게시 처리 |
| `requirements.txt` | 버전이 고정된 Python 런타임 의존성 |
| `.env.example` | 실제 비밀값이 없는 설정 템플릿 |
| `.gitignore` | 로컬 비밀값 및 생성 파일 제외 규칙 |
| `.dockerignore` | Docker 빌드 컨텍스트 제외 규칙 |
| `Dockerfile` | 운영용 컨테이너 이미지 정의 |
| `compose.yaml` | 로컬/서버 컨테이너 실행 및 환경 변수 주입 설정 |
| `README.md` | 설치, 운영, 사용 방법 안내 |

