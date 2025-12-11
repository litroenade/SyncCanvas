"""模块名称: web_tools
主要功能: 网页爬取和信息检索工具

提供网页内容获取、文本提取等功能，支持 Agent 获取外部信息。
"""

import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from src.agent.core.tools import registry, ToolCategory
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


# ==================== 参数 Schema ====================

class FetchWebPageArgs(BaseModel):
    """获取网页内容的参数"""
    url: str = Field(..., description="要获取的网页 URL")
    extract_text: bool = Field(True, description="是否提取纯文本内容")
    max_length: int = Field(5000, description="返回内容的最大字符数")


class SearchWebArgs(BaseModel):
    """搜索网页的参数"""
    query: str = Field(..., description="搜索关键词")
    max_results: int = Field(5, description="返回结果数量")


# ==================== 辅助函数 ====================

def _extract_text_from_html(html: str) -> str:
    """从 HTML 中提取纯文本
    
    Args:
        html: HTML 内容
        
    Returns:
        str: 提取的纯文本
    """
    # 移除 script 和 style 标签及其内容
    html = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", html, flags=re.IGNORECASE)

    # 移除 HTML 注释
    html = re.sub(r"<!--[\s\S]*?-->", "", html)

    # 移除所有 HTML 标签
    text = re.sub(r"<[^>]+>", " ", html)

    # 解码 HTML 实体
    text = text.replace("&nbsp;", " ")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&amp;", "&")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")

    # 清理多余空白
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text


def _extract_title(html: str) -> Optional[str]:
    """从 HTML 中提取标题
    
    Args:
        html: HTML 内容
        
    Returns:
        str: 页面标题，未找到则返回 None
    """
    match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _is_valid_url(url: str) -> bool:
    """验证 URL 是否有效
    
    Args:
        url: URL 字符串
        
    Returns:
        bool: 是否有效
    """
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception: # pylint: disable=broad-except
        return False


# ==================== 工具实现 ====================

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
    """获取网页内容
    
    Args:
        url: 网页 URL
        extract_text: 是否提取纯文本
        max_length: 最大返回长度
        
    Returns:
        dict: 包含网页内容的结果
    """
    if not _is_valid_url(url):
        return {
            "status": "error",
            "message": f"无效的 URL: {url}"
        }

    try:
        async with httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            headers=DEFAULT_HEADERS,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")

            # 检查是否为 HTML 内容
            if "text/html" not in content_type and "text/plain" not in content_type:
                return {
                    "status": "error",
                    "message": f"不支持的内容类型: {content_type}"
                }

            html = response.text
            title = _extract_title(html)

            if extract_text:
                content = _extract_text_from_html(html)
            else:
                content = html

            # 截断过长的内容
            if len(content) > max_length:
                content = content[:max_length] + "...(内容已截断)"

            logger.info("获取网页成功: %s", url, extra={"length": len(content)})

            return {
                "status": "success",
                "url": url,
                "title": title,
                "content": content,
                "content_length": len(content),
                "message": f"成功获取网页内容 ({len(content)} 字符)"
            }

    except httpx.TimeoutException:
        logger.warning("获取网页超时: %s", url)
        return {
            "status": "error",
            "message": f"请求超时: {url}"
        }
    except httpx.HTTPStatusError as e:
        logger.warning("获取网页失败: %s, 状态码: %s", url, e.response.status_code)
        return {
            "status": "error",
            "message": f"HTTP 错误: {e.response.status_code}"
        }
    except Exception as e: # pylint: disable=broad-except
        logger.error("获取网页异常: %s, 错误: %s", url, e)
        return {
            "status": "error",
            "message": f"获取失败: {str(e)}"
        }


@registry.register(
    "search_web",
    "搜索网页 (模拟搜索，实际需要接入搜索 API)",
    SearchWebArgs
)
async def search_web(
    query: str,
    max_results: int = 5,
) -> Dict[str, Any]:
    """搜索网页 (占位实现)
    
    注意: 这是一个占位实现，实际使用需要接入搜索 API (如 Bing、Google 等)
    
    Args:
        query: 搜索关键词
        max_results: 返回结果数量
        
    Returns:
        dict: 搜索结果
    """
    logger.info("搜索请求: %s", query)

    # 占位实现 - 实际需要接入搜索 API
    return {
        "status": "info",
        "query": query,
        "results": [],
        "message": "搜索功能需要配置搜索 API (如 Bing Search API)。当前为占位实现。"
    }
