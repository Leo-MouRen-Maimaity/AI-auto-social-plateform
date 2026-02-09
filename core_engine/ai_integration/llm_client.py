"""
LLM客户端模块

提供与本地LLM（LM Studio）通信的客户端，使用OpenAI兼容接口
"""

import asyncio
import json
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, AsyncGenerator
import aiohttp


@dataclass
class LLMConfig:
    """LLM配置"""
    base_url: str = "http://127.0.0.1:1234/v1"  # LM Studio默认端口
    model: str = "qwen3-vl-8b"  # 模型名称
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.9
    timeout: int = 120  # 超时时间（秒）
    
    # 重试配置
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class Message:
    """聊天消息"""
    role: str  # system, user, assistant
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    finish_reason: str = "stop"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    
    @property
    def success(self) -> bool:
        return bool(self.content)


class LLMClient:
    """
    LLM客户端
    
    支持OpenAI兼容接口，可连接LM Studio等本地LLM服务
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._session: Optional[aiohttp.ClientSession] = None
        self._connected = False
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建HTTP会话"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        """关闭客户端"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        self._connected = False
    
    async def check_connection(self) -> bool:
        """检查与LLM服务的连接"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.config.base_url}/models") as response:
                if response.status == 200:
                    self._connected = True
                    return True
        except Exception as e:
            print(f"LLM connection check failed: {e}")
        
        self._connected = False
        return False
    
    async def get_available_models(self) -> List[str]:
        """获取可用的模型列表"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.config.base_url}/models") as response:
                if response.status == 200:
                    data = await response.json()
                    return [model['id'] for model in data.get('data', [])]
        except Exception as e:
            print(f"Failed to get models: {e}")
        return []
    
    async def chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None
    ) -> LLMResponse:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数（可选，覆盖默认值）
            max_tokens: 最大token数（可选，覆盖默认值）
            stop: 停止词列表
            
        Returns:
            LLMResponse对象
        """
        payload = {
            "model": self.config.model,
            "messages": [msg.to_dict() for msg in messages],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "top_p": self.config.top_p,
        }
        
        if stop:
            payload["stop"] = stop
        
        for attempt in range(self.config.max_retries):
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self.config.base_url}/chat/completions",
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        choice = data.get('choices', [{}])[0]
                        message = choice.get('message', {})
                        usage = data.get('usage', {})
                        
                        return LLMResponse(
                            content=message.get('content', ''),
                            finish_reason=choice.get('finish_reason', 'stop'),
                            prompt_tokens=usage.get('prompt_tokens', 0),
                            completion_tokens=usage.get('completion_tokens', 0),
                            total_tokens=usage.get('total_tokens', 0),
                            model=data.get('model', self.config.model)
                        )
                    else:
                        error_text = await response.text()
                        print(f"LLM request failed (attempt {attempt + 1}): {response.status} - {error_text}")
                        
            except asyncio.TimeoutError:
                print(f"LLM request timeout (attempt {attempt + 1})")
            except Exception as e:
                print(f"LLM request error (attempt {attempt + 1}): {e}")
            
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.retry_delay)
        
        return LLMResponse(content="", finish_reason="error")
    
    async def chat_stream(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            
        Yields:
            响应文本片段
        """
        payload = {
            "model": self.config.model,
            "messages": [msg.to_dict() for msg in messages],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "top_p": self.config.top_p,
            "stream": True
        }
        
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.config.base_url}/chat/completions",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"LLM stream request failed: {response.status} - {error_text}")
                    return
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if not line or line == "data: [DONE]":
                        continue
                    
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            choice = data.get('choices', [{}])[0]
                            delta = choice.get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            print(f"LLM stream error: {e}")
    
    async def generate_with_system(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """
        使用系统提示词和用户输入生成响应
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            LLMResponse对象
        """
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]
        return await self.chat(messages, temperature, max_tokens)
    
    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3
    ) -> Optional[Dict[str, Any]]:
        """
        生成JSON格式的响应
        
        Args:
            system_prompt: 系统提示词（应包含JSON格式要求）
            user_prompt: 用户输入
            temperature: 温度参数（较低以确保格式正确）
            
        Returns:
            解析后的JSON字典，失败返回None
        """
        response = await self.generate_with_system(
            system_prompt + "\n\n请只输出JSON格式的内容，不要有其他文字。",
            user_prompt,
            temperature=temperature
        )
        
        if not response.success:
            return None
        
        # 尝试解析JSON
        content = response.content.strip()
        
        # 尝试提取JSON块
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end > start:
                content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end > start:
                content = content[start:end].strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            print(f"Content was: {content[:200]}...")
            return None


# 全局单例
_default_client: Optional[LLMClient] = None


def get_llm_client(config: Optional[LLMConfig] = None) -> LLMClient:
    """获取全局LLM客户端实例"""
    global _default_client
    
    if _default_client is None:
        _default_client = LLMClient(config)
    elif config:
        # 如果提供了新配置，更新客户端
        _default_client.config = config
    
    return _default_client


async def test_llm_connection():
    """测试LLM连接"""
    client = get_llm_client()
    
    print("Testing LLM connection...")
    connected = await client.check_connection()
    
    if connected:
        print("✓ LLM service connected!")
        models = await client.get_available_models()
        print(f"✓ Available models: {models}")
        
        # 测试简单对话
        response = await client.generate_with_system(
            "你是一个友好的助手。",
            "你好！请用一句话介绍你自己。"
        )
        
        if response.success:
            print(f"✓ Test response: {response.content}")
            print(f"  Tokens used: {response.total_tokens}")
        else:
            print("✗ Test response failed")
    else:
        print("✗ LLM service not available")
    
    await client.close()
    return connected


if __name__ == "__main__":
    asyncio.run(test_llm_connection())
