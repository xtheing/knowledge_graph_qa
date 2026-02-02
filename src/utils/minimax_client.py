"""
MiniMax API 客户端封装
"""

import os
import requests
import json
from typing import List, Dict, Optional


class MiniMaxClient:
    """MiniMax API 客户端"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY")
        self.base_url = base_url or os.getenv(
            "MINIMAX_API_BASE", "https://api.minimaxi.chat/v1"
        )
        self.model = os.getenv("MINIMAX_MODEL", "MiniMax-Text-01")

        if not self.api_key:
            raise ValueError(
                "MiniMax API Key not found. Please set MINIMAX_API_KEY environment variable."
            )

    def chat_completion(
        self, messages: List[Dict], temperature: float = 0.3, max_tokens: int = 2000
    ) -> str:
        """
        调用 MiniMax Chat Completion API

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            生成的文本
        """
        url = f"{self.base_url}/text/chatcompletion_v2"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

            # 解析响应
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                raise Exception(f"Unexpected response format: {result}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"MiniMax API request failed: {str(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Failed to parse MiniMax response: {str(e)}")

    def generate(
        self, prompt: str, temperature: float = 0.3, max_tokens: int = 2000
    ) -> str:
        """
        简化的生成接口

        Args:
            prompt: 提示文本
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            生成的文本
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat_completion(messages, temperature, max_tokens)


# 全局客户端实例
_minimax_client = None


def get_minimax_client() -> MiniMaxClient:
    """获取 MiniMax 客户端单例"""
    global _minimax_client
    if _minimax_client is None:
        _minimax_client = MiniMaxClient()
    return _minimax_client
