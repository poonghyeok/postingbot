# Posting Bot

텔레그램에서 주제를 보내면 Gemini API가 한국어 Markdown 초안을 만듭니다. 피드백으로 수정한 뒤 승인한 글만 Jekyll 형식으로 GitHub 저장소의 `_posts/` 폴더에 커밋합니다.
게시물 제목은 입력한 질문을 그대로 사용하지 않고 Gemini가 글의 내용에 맞게 생성합니다.

## 준비

1. Google AI Studio에서 Gemini API 키를 발급받습니다.
2. Telegram의 `@BotFather`에서 봇을 만들고 토큰을 받습니다.
3. GitHub fine-grained personal access token을 만들고 대상 저장소의 **Contents: Read and write** 권한을 줍니다.
4. Python 3.11 이상에서 설치합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`.env.example`을 복사하고 실제 값을 입력합니다. 앱이 시작할 때 `.env`를 자동으로 읽습니다.

```bash
cp .env.example .env
```

실행:

```bash
python bot.py
```

### Docker Compose로 실행

Docker Desktop을 실행한 뒤 프로젝트 폴더에서 다음 명령을 사용합니다. `.env`는 이미지에 포함되지 않고 컨테이너 실행 시 환경 변수로 전달됩니다.

```bash
docker compose up -d --build
docker compose logs -f
```

컨테이너를 중지하려면 다음을 실행합니다.

```bash
docker compose down
```

텔레그램에서 초안을 만들고, 수정한 뒤 게시합니다.

```text
/suggest SQL Server 2019를 MMORPG 데이터 엔지니어링에 활용할 때 알아둘 주제
/write 초보자를 위한 홈카페 시작법
/revise 도입부를 짧게 하고 구체적인 사례를 추가해 줘
/publish
```

`/suggest` 결과는 Telegram에만 표시되며 현재 초안에는 영향을 주지 않습니다. 마음에 드는 주제를 복사해 `/write` 뒤에 입력합니다. 현재 초안을 버리려면 `/cancel`을 사용합니다. 초안은 서버 메모리에 저장되므로 서버를 재시작하면 사라집니다.

## GitHub Pages

대상 Chirpy 저장소에서 GitHub Pages를 활성화합니다. 봇이 게시할 때 `_posts/YYYY-MM-DD-HHMMSS.md` 파일을 만들고 제목, 카테고리, 태그가 포함된 Chirpy용 front matter를 자동 생성합니다.

```yaml
---
layout: post
title: "Azure Kusto의 Join 종류와 실전 활용법"
date: 2026-09-27 14:18:57 +0900
categories: ["Database", "Azure Data Explorer"]
tags: ["azure", "kusto", "kql", "join"]
---
```

내 숫자 ID는 Telegram의 `@userinfobot` 같은 ID 확인 봇으로 알아낼 수 있습니다.
