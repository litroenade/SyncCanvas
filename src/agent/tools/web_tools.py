"""模块名称: web_tools
主要功能: 网页获取工具
"""

import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from src.agent.registry import registry, ToolCategory
from src.logger import get_logger

logger = get_logger(__name__)

# HTTP 客户端配置
DEFAULT_TIMEOUT = 15.0
DEFAULT_HEADERS = {
    "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


class FetchWebPageArgs(BaseModel):
    """获取网页内容的参数"""
    url: str = Field(..., description="要获取的网页 URL")
    extract_text: bool = Field(True, description="是否提取纯文本内容")
    max_length: int = Field(5000, description="返回内容的最大字符数")


def _extract_text_from_html(html: str) -> str:
    """从 HTML 中提取纯文本"""
    html = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<!--[\s\S]*?-->", "", html)
    text = re.sub(r"<[^>]+>", " ", html)
    text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_title(html: str) -> Optional[str]:
    """从 HTML 中提取标题"""
    match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _is_valid_url(url: str) -> bool:
    """验证 URL 是否有效"""
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:  # pylint: disable=broad-except
        return False


@registry.register(
    "fetch_webpage",
    "获取网页内容，支持提取纯文本。用于获取外部信息、参考资料等。",
    FetchWebPageArgs,
    category=ToolCategory.WEB,
    timeout=20.0,
)
async def fetch_webpage(
    url: str,
    extract_text: bool = True,
    max_length: int = 5000,
) -> Dict[str, Any]:
    """获取网页内容"""
    if not _is_valid_url(url):
        return {"status": "error", "message": f"无效的 URL: {url}"}

    try:
        async with httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            headers=DEFAULT_HEADERS,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                return {"status": "error", "message": f"不支持的内容类型: {content_type}"}

            html = response.text
            title = _extract_title(html)
            content = _extract_text_from_html(html) if extract_text else html

            if len(content) > max_length:
                content = content[:max_length] + "...(内容已截断)"

            logger.info("获取网页成功: %s", url, extra={"length": len(content)})

            return {
                "status": "success",
                "url": url,
                "title": title,
                "content": content,
                "content_length": len(content),
            }

    except httpx.TimeoutException:
        return {"status": "error", "message": f"请求超时: {url}"}
    except httpx.HTTPStatusError as e:
        return {"status": "error", "message": f"HTTP 错误: {e.response.status_code}"}
    except Exception as e:  # pylint: disable=broad-except
        return {"status": "error", "message": f"获取失败: {e}"}
