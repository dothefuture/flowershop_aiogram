"""Cursor Cloud Agents API — дополнение описаний товаров."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re

import aiohttp
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

CURSOR_API = "https://api.cursor.com"
_TERMINAL = frozenset({"FINISHED", "ERROR", "CANCELLED", "EXPIRED"})
_POLL_INTERVAL = 2
_POLL_ATTEMPTS = 90


class AIError(Exception):
    """Ошибка Cursor AI с текстом для админа."""


def _api_key() -> str:
    return os.getenv("CURSOR_AI_API_KEY", "").strip()


def _model_id() -> str:
    return os.getenv("CURSOR_AI_MODEL", "").strip()


def _auth_headers(api_key: str, *, use_bearer: bool = True) -> dict[str, str]:
    if use_bearer:
        auth = f"Bearer {api_key}"
    else:
        token = base64.b64encode(f"{api_key}:".encode()).decode()
        auth = f"Basic {token}"
    return {
        "Authorization": auth,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _build_prompt(
    name: str, description: str, price: float, extra_hint: str
) -> str:
    hint = f"\nПожелание админа: {extra_hint}" if extra_hint else ""
    return (
        "Ты копирайтер цветочного магазина. Дополни описание букета на русском языке. "
        "Сохрани факты из текущего описания, не выдумывай состав цветов. "
        "2–4 предложения, без заголовков, без markdown, без кода.\n\n"
        f"Название: {name}\n"
        f"Цена: {price:.0f} ₽\n"
        f"Текущее описание:\n{description or '—'}{hint}\n\n"
        "Ответь только готовым текстом описания."
    )


def _parse_error(status: int, raw: str) -> str:
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return (
                data.get("message")
                or data.get("error")
                or data.get("detail")
                or raw[:400]
            )
    except json.JSONDecodeError:
        pass
    return raw[:400] or f"HTTP {status}"


def _clean_result(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[\w]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


async def _request_json(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    api_key: str,
    *,
    json_body: dict | None = None,
) -> dict:
    last_error = ""
    for use_bearer in (True, False):
        headers = _auth_headers(api_key, use_bearer=use_bearer)
        try:
            async with session.request(
                method,
                url,
                json=json_body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                raw = await resp.text()
                if resp.status == 401 and use_bearer:
                    last_error = _parse_error(resp.status, raw)
                    continue
                if resp.status >= 400:
                    raise AIError(
                        f"Cursor API HTTP {resp.status}\n{_parse_error(resp.status, raw)}"
                    )
                if not raw:
                    return {}
                data = json.loads(raw)
                return data if isinstance(data, dict) else {}
        except AIError:
            raise
        except Exception as exc:
            raise AIError(f"Сбой запроса Cursor: {exc}") from exc
    raise AIError(f"Cursor API: неверный ключ\n{last_error}")


async def _create_agent(session: aiohttp.ClientSession, api_key: str, prompt: str) -> tuple[str, str]:
    body: dict = {"prompt": {"text": prompt}}
    model = _model_id()
    if model:
        body["model"] = {"id": model}

    data = await _request_json(
        session, "POST", f"{CURSOR_API}/v1/agents", api_key, json_body=body
    )

    agent = data.get("agent")
    run = data.get("run")
    if not isinstance(agent, dict):
        raise AIError(f"Cursor: нет agent в ответе\n{json.dumps(data, ensure_ascii=False)[:300]}")

    agent_id = agent.get("id")
    run_id = (run or {}).get("id") or agent.get("latestRunId")
    if not agent_id or not run_id:
        raise AIError("Cursor: не получен id агента или запуска")

    return str(agent_id), str(run_id)


async def _poll_run(
    session: aiohttp.ClientSession,
    api_key: str,
    agent_id: str,
    run_id: str,
) -> str:
    url = f"{CURSOR_API}/v1/agents/{agent_id}/runs/{run_id}"

    for _ in range(_POLL_ATTEMPTS):
        await asyncio.sleep(_POLL_INTERVAL)
        data = await _request_json(session, "GET", url, api_key)
        status = str(data.get("status", "")).upper()

        if status == "FINISHED":
            result = data.get("result")
            if isinstance(result, str) and result.strip():
                return _clean_result(result)
            raise AIError("Cursor завершил задачу, но result пустой")

        if status in _TERMINAL:
            raise AIError(f"Cursor run: статус {status}")

    raise AIError(
        f"Cursor не ответил за {_POLL_ATTEMPTS * _POLL_INTERVAL // 60} мин. "
        "Попробуйте ещё раз."
    )


async def enhance_product_description(
    name: str,
    description: str,
    price: float,
    *,
    extra_hint: str = "",
) -> str:
    """
    Дописывает описание через Cursor Cloud Agents API.
    CURSOR_AI_API_KEY=crsr_… из Cursor Dashboard → API Keys.
    """
    api_key = _api_key()
    if not api_key:
        raise AIError(
            "Не задан CURSOR_AI_API_KEY в .env\n"
            "Ключ: Cursor Dashboard → API Keys → crsr_…"
        )
    if not api_key.startswith("crsr_"):
        raise AIError(
            "CURSOR_AI_API_KEY должен начинаться с crsr_\n"
            "Создайте ключ в Cursor Dashboard → API Keys"
        )

    prompt = _build_prompt(name, description, price, extra_hint)

    try:
        async with aiohttp.ClientSession() as session:
            agent_id, run_id = await _create_agent(session, api_key, prompt)
            logger.info("Cursor agent %s run %s started", agent_id, run_id)
            return await _poll_run(session, api_key, agent_id, run_id)
    except AIError:
        raise
    except Exception as exc:
        logger.exception("Cursor AI failed")
        raise AIError(f"Сбой Cursor AI: {exc}") from exc
