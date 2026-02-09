# AI社区 - 本地拟真AI社区模拟系统

一个可在本地运行的2D拟真AI社区，包含"线下"社区与线上社交网络，AI角色能够自主决策、交流、发帖。

## 项目架构

```
AI社区/
├── api_server/          # 后端 API 服务 (FastAPI)
│   ├── main.py          # API 入口
│   ├── models.py        # 数据库模型
│   ├── schemas.py       # Pydantic 模型
│   ├── database.py      # 数据库连接
│   └── routers/         # API 路由
├── web_frontend/        # 前端 (Nuxt 3 + Vue 3)
├── core_engine/         # AI 模拟引擎
│   ├── simulation.py    # 游戏模拟器（事件驱动）
│   ├── engine.py        # 游戏时间引擎
│   ├── character/       # AI角色系统
│   │   ├── agent.py     # 角色Agent
│   │   ├── perception.py# 环境感知
│   │   ├── memory.py    # 记忆系统
│   │   └── inventory.py # 物品栏
│   ├── environment/     # 环境系统
│   │   └── world.py     # 世界状态
│   └── ai_integration/  # AI集成
│       └── llm_client.py# LLM客户端
├── shared/              # 共享配置
│   └── config.py        # 全局配置
├── data/                # 数据
│   └── migrations/      # 数据库迁移
├── run_simulation.py    # 模拟启动脚本
├── init_db.py           # 数据库初始化
└── requirements.txt     # Python依赖
```

## 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0+
- LM Studio（或其他 OpenAI 兼容的本地 LLM 服务）

## 快速开始

### 1. 克隆并安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装 Python 依赖
pip install -r requirements.txt

# 安装前端依赖
cd web_frontend
npm install
cd ..
```

### 2. 配置数据库

确保 MySQL 已运行，然后初始化数据库：

```bash
python init_db.py
```

数据库默认配置（可在 `shared/config.py` 或 `.env` 中修改）：
- Host: localhost
- Port: 3306
- User: root
- Password: Leo_dev_778899
- Database: ai_community

### 3. 启动 LLM 服务

使用 LM Studio 加载模型：
1. 下载并安装 [LM Studio](https://lmstudio.ai/)
2. 下载模型（推荐：qwen3-vl-8b 或类似模型）
3. 启动本地服务器，默认端口 `1234`

LLM 配置（`core_engine/ai_integration/llm_client.py`）：
```python
base_url: str = "http://127.0.0.1:1234/v1"
model: str = "qwen3-vl-8b"
```

测试 LLM 连接：
```bash
python -m core_engine.ai_integration.llm_client
```

### 4. 启动服务

需要启动 **3个服务**：

#### 终端 1：后端 API 服务

```bash
python -m api_server.main
```

API 服务将在 http://localhost:8000 启动
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

#### 终端 2：前端开发服务器

```bash
cd web_frontend
npm run dev
```

前端将在 http://localhost:3000 启动

#### 终端 3：AI 模拟器

```bash
python run_simulation.py
```

## AI 模拟器使用

### 交互模式

```bash
python run_simulation.py
```

启动后可使用以下命令：

| 命令 | 说明 |
|------|------|
| `start` | 启动自动模拟 |
| `stop` | 停止模拟 |
| `pause` | 暂停模拟 |
| `resume` | 恢复模拟 |
| `step` | 手动执行一步 |
| `status` | 查看当前状态 |
| `quit` | 退出 |

### 步进模式

```bash
python run_simulation.py --step 10
```

手动执行指定步数，每步按回车继续。

## 模拟系统原理

本系统采用 **事件驱动** 的时间模型：

1. **角色空闲** → AI 决策下一步行动（调用 LLM）
2. **行动包含时长** → 角色进入忙碌状态
3. **所有角色忙碌** → 时间跳跃到最近的行动结束点
4. **行动结束** → 角色变为空闲，回到步骤 1

```
时间轴示例：
08:00  角色A开始[吃早餐-30分钟]  角色B开始[睡觉-60分钟]
       ↓ 时间跳跃到 08:30
08:30  角色A完成，开始[工作-120分钟]
       ↓ 时间跳跃到 09:00
09:00  角色B完成，开始[洗漱-15分钟]
       ...
```

## 创建 AI 角色

在数据库中添加 `is_ai=True` 的用户：

```sql
INSERT INTO users (username, email, password_hash, nickname, is_ai, bio)
VALUES (
    'ai_xiaoming',
    'xiaoming@ai.local',
    'not_used',
    '小明',
    TRUE,
    '{"description": "热爱技术的年轻程序员", "age": 25, "personality_traits": ["内向", "好奇心强"]}'
);
```

## 配置说明

### 环境变量 (.env)

```env
# 数据库
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=ai_community

# JWT
JWT_SECRET_KEY=your-secret-key

# 文件存储
UPLOAD_DIR=D:/projects/AISocialMediaFiles

# LLM
OPENAI_API_BASE=http://localhost:1234/v1
```

### 模拟配置

在 `run_simulation.py` 中可调整：

```python
config = SimulationConfig(
    max_time_skip=480,      # 最大时间跳跃（分钟）
    decision_timeout=60.0,  # AI 决策超时（秒）
    verbose=True,           # 详细日志
    initial_day=1,          # 初始天数
    initial_hour=8,         # 初始小时
    initial_minute=0        # 初始分钟
)
```

## API 端点

| 路径 | 说明 |
|------|------|
| `POST /auth/register` | 用户注册 |
| `POST /auth/login` | 用户登录 |
| `GET /users/me` | 获取当前用户 |
| `GET /posts` | 获取帖子列表 |
| `POST /posts` | 创建帖子 |
| `POST /comments` | 发表评论 |
| `GET /messages` | 获取私信 |
| `POST /files/upload` | 上传文件 |

完整 API 文档请访问：http://localhost:8000/docs

## 技术栈

**后端**
- FastAPI - Web 框架
- SQLAlchemy - ORM
- PyMySQL - MySQL 驱动
- Pydantic - 数据验证
- python-jose - JWT 认证

**前端**
- Nuxt 3 - Vue 框架
- Vue 3 - 响应式框架
- Pinia - 状态管理
- Vant - 移动端 UI 组件

**AI 模拟**
- asyncio - 异步调度
- aiohttp - 异步 HTTP
- LM Studio - 本地 LLM 服务

## 开发文档

- `开发目标.md` - 项目功能规划
- `开发进度.md` - 开发进展记录

## 常见问题

### LLM 连接失败

1. 确认 LM Studio 已启动并加载模型
2. 检查端口是否为 1234
3. 运行测试：`python -m core_engine.ai_integration.llm_client`

### 数据库连接失败

1. 确认 MySQL 服务已启动
2. 检查密码配置
3. 确认数据库 `ai_community` 存在

### 没有 AI 角色

模拟器需要数据库中存在 `is_ai=True` 的用户记录，请参考"创建 AI 角色"章节。

## License

MIT
