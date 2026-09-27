import base64
import asyncio
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


load_dotenv()

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPOSITORY = os.environ["GITHUB_REPOSITORY"]  # 예: owner/blog
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
ALLOWED_TELEGRAM_USER_ID = os.environ["ALLOWED_TELEGRAM_USER_ID"]


def is_allowed(update: Update) -> bool:
    return bool(
        update.effective_user
        and str(update.effective_user.id) == ALLOWED_TELEGRAM_USER_ID
    )


def generate_text(prompt: str) -> str:
    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        headers={
            "x-goog-api-key": GEMINI_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 2048},
        },
        timeout=60,
    )
    response.raise_for_status()
    candidates = response.json().get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini가 생성 결과를 반환하지 않았습니다.")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise RuntimeError("Gemini 응답에 텍스트가 없습니다.")
    return text


def parse_generated_post(
    markdown: str,
    fallback_title: str,
    fallback_categories: list[str] | None = None,
    fallback_tags: list[str] | None = None,
) -> tuple[str, list[str], list[str], str]:
    lines = markdown.strip().splitlines()
    title = fallback_title
    categories = fallback_categories or ["General"]
    tags = fallback_tags or ["general"]

    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip() or fallback_title

    body_start = None
    for index, line in enumerate(lines):
        if line.startswith("CATEGORIES:"):
            values = [value.strip() for value in line.removeprefix("CATEGORIES:").split("|")]
            categories = [value for value in values if value][:2] or categories
        elif line.startswith("TAGS:"):
            values = [value.strip() for value in line.removeprefix("TAGS:").split("|")]
            tags = [value for value in values if value][:5] or tags
        elif line.strip() == "---BODY---":
            body_start = index + 1
            break

    if body_start is not None:
        body = "\n".join(lines[body_start:]).strip()
        if body:
            return title, categories, tags, body

    body = "\n".join(lines[1:]).strip() if lines and lines[0].startswith("# ") else markdown.strip()
    return title, categories, tags, body


def create_post(topic: str) -> tuple[str, list[str], list[str], str]:
    result = generate_text(
        "당신은 한국어 블로그 작가입니다. 정확하고 읽기 쉬운 Markdown 글을 작성하세요. "
        "짧은 소개, 소제목 3개, 결론을 포함하고 확인하지 못한 사실은 단정하지 마세요. "
        "사용자의 표현을 그대로 복사하지 말고 글에 어울리는 자연스럽고 간결한 제목을 만드세요. "
        "아래 출력 형식을 정확히 지키세요. 카테고리는 넓은 분류에서 세부 분류 순서로 2개, "
        "태그는 검색에 유용한 영문 소문자 위주로 3~5개 작성하세요. YAML front matter는 작성하지 마세요.\n\n"
        "# 자연스러운 제목\n"
        "CATEGORIES: 상위 카테고리 | 하위 카테고리\n"
        "TAGS: tag1 | tag2 | tag3\n"
        "---BODY---\n"
        "Markdown 본문\n\n"
        f"다음 주제로 800자 안팎의 블로그 글을 작성해 주세요: {topic}"
    )
    return parse_generated_post(result, topic)


def suggest_topics(request: str) -> str:
    return generate_text(
        "당신은 기술 블로그 콘텐츠 기획자입니다. 사용자의 관심 분야에 맞는 구체적이고 "
        "실무적인 한국어 포스팅 주제 10개를 추천하세요. 서로 겹치지 않게 구성하고, "
        "각 항목은 '1. 주제 — 한 문장 설명' 형식으로 작성하세요. 서론이나 맺음말 없이 "
        "번호 목록만 출력하세요.\n\n"
        f"추천 요청: {request}"
    )


def revise_post(
    title: str,
    categories: list[str],
    tags: list[str],
    draft: str,
    feedback: str,
) -> tuple[str, list[str], list[str], str]:
    result = generate_text(
        "당신은 한국어 블로그 편집자입니다. 아래 피드백을 반영해 초안을 수정하세요. "
        "피드백에서 요청하지 않은 핵심 내용은 유지하세요. 아래 출력 형식을 정확히 지키고 "
        "YAML front matter는 작성하지 마세요.\n\n"
        "# 자연스러운 제목\n"
        "CATEGORIES: 상위 카테고리 | 하위 카테고리\n"
        "TAGS: tag1 | tag2 | tag3\n"
        "---BODY---\n"
        "수정된 Markdown 본문\n\n"
        f"[현재 제목]\n{title}\n\n"
        f"[현재 카테고리]\n{' | '.join(categories)}\n\n"
        f"[현재 태그]\n{' | '.join(tags)}\n\n"
        f"[초안]\n{draft}\n\n[피드백]\n{feedback}"
    )
    return parse_generated_post(result, title, categories, tags)


def draft_message(title: str, categories: list[str], tags: list[str], draft: str) -> str:
    full_draft = (
        f"# {title}\n\n"
        f"카테고리: {' > '.join(categories)}\n"
        f"태그: {', '.join(tags)}\n\n"
        f"{draft}"
    )
    preview = full_draft if len(full_draft) <= 3300 else full_draft[:3300] + "\n\n…(이하 생략)"
    return f"{preview}\n\n수정: /revise 피드백\n게시: /publish\n취소: /cancel"


def build_jekyll_post(
    content: str,
    title: str,
    categories: list[str],
    tags: list[str],
    now: datetime,
) -> str:
    yaml_title = json.dumps(title, ensure_ascii=False)
    yaml_categories = json.dumps(categories, ensure_ascii=False)
    yaml_tags = json.dumps(tags, ensure_ascii=False)
    return (
        "---\n"
        "layout: post\n"
        f"title: {yaml_title}\n"
        f"date: {now:%Y-%m-%d %H:%M:%S %z}\n"
        f"categories: {yaml_categories}\n"
        f"tags: {yaml_tags}\n"
        "---\n\n"
        f"{content.strip()}\n"
    )


def save_to_github(
    content: str, title: str, categories: list[str], tags: list[str]
) -> str:
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    path = f"_posts/{now:%Y-%m-%d-%H%M%S}.md"
    post = build_jekyll_post(content, title, categories, tags, now)
    api_url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{path}"
    response = httpx.put(
        api_url,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={
            "message": f"Add generated post: {title}",
            "content": base64.b64encode(post.encode("utf-8")).decode("ascii"),
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["content"]["html_url"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    await update.message.reply_text(
        "/write 주제: 새 초안 작성\n"
        "/suggest 설명: 포스팅 주제 추천\n"
        "/revise 피드백: 현재 초안 수정\n"
        "/publish: GitHub에 게시\n"
        "/cancel: 현재 초안 삭제"
    )


async def suggest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    request = " ".join(context.args).strip()
    if not request:
        await update.message.reply_text(
            "예: /suggest SQL Server 2019를 MMORPG 데이터 엔지니어링에 활용할 때 알아둘 주제"
        )
        return

    status = await update.message.reply_text("주제를 추천하고 있어요…")
    try:
        suggestions = await asyncio.to_thread(suggest_topics, request)
        preview = (
            suggestions
            if len(suggestions) <= 3800
            else suggestions[:3800] + "\n\n…(이하 생략)"
        )
        await status.edit_text(
            f"{preview}\n\n마음에 드는 주제를 복사해 /write 뒤에 입력하세요."
        )
    except Exception as exc:
        print(f"Failed to suggest topics: {exc}")
        await status.edit_text("주제 추천에 실패했습니다. 실행 로그를 확인해 주세요.")


async def write(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    topic = " ".join(context.args).strip()
    if not topic:
        await update.message.reply_text("예: /write 서울에서 가을 산책하기")
        return

    status = await update.message.reply_text("글을 작성하고 있어요…")
    try:
        title, categories, tags, post = await asyncio.to_thread(create_post, topic)
        context.user_data["draft"] = post
        context.user_data["topic"] = topic
        context.user_data["title"] = title
        context.user_data["categories"] = categories
        context.user_data["tags"] = tags
        await status.edit_text(draft_message(title, categories, tags, post))
    except Exception as exc:
        print(f"Failed to create post: {exc}")
        await status.edit_text("글 작성에 실패했습니다. 실행 로그를 확인해 주세요.")


async def revise(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    draft = context.user_data.get("draft")
    title = context.user_data.get("title") or context.user_data.get("topic") or "제목 없음"
    categories = context.user_data.get("categories") or ["General"]
    tags = context.user_data.get("tags") or ["general"]
    if not draft:
        await update.message.reply_text("수정할 초안이 없습니다. 먼저 /write 주제를 입력해 주세요.")
        return
    feedback = " ".join(context.args).strip()
    if not feedback:
        await update.message.reply_text("예: /revise 도입부를 짧게 하고 사례를 추가해 줘")
        return

    status = await update.message.reply_text("피드백을 반영하고 있어요…")
    try:
        revised_title, revised_categories, revised_tags, revised = await asyncio.to_thread(
            revise_post, title, categories, tags, draft, feedback
        )
        context.user_data["draft"] = revised
        context.user_data["title"] = revised_title
        context.user_data["categories"] = revised_categories
        context.user_data["tags"] = revised_tags
        await status.edit_text(
            draft_message(revised_title, revised_categories, revised_tags, revised)
        )
    except Exception as exc:
        print(f"Failed to revise post: {exc}")
        await status.edit_text("초안 수정에 실패했습니다. 기존 초안은 유지됩니다.")


async def publish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    draft = context.user_data.get("draft")
    title = context.user_data.get("title") or context.user_data.get("topic")
    categories = context.user_data.get("categories") or ["General"]
    tags = context.user_data.get("tags") or ["general"]
    if not draft:
        await update.message.reply_text("게시할 초안이 없습니다. 먼저 /write 주제를 입력해 주세요.")
        return

    status = await update.message.reply_text("GitHub에 게시하고 있어요…")
    try:
        github_url = await asyncio.to_thread(
            save_to_github, draft, title or "제목 없음", categories, tags
        )
        context.user_data.clear()
        await status.edit_text(f"게시했습니다.\n{github_url}")
    except Exception as exc:
        print(f"Failed to publish post: {exc}")
        await status.edit_text("게시하지 못했습니다. 초안은 유지됩니다.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    if context.user_data.pop("draft", None) is None:
        await update.message.reply_text("삭제할 초안이 없습니다.")
        return
    context.user_data.pop("topic", None)
    context.user_data.pop("title", None)
    context.user_data.pop("categories", None)
    context.user_data.pop("tags", None)
    await update.message.reply_text("현재 초안을 삭제했습니다.")


def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("suggest", suggest))
    app.add_handler(CommandHandler("write", write))
    app.add_handler(CommandHandler("revise", revise))
    app.add_handler(CommandHandler("publish", publish))
    app.add_handler(CommandHandler("cancel", cancel))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
