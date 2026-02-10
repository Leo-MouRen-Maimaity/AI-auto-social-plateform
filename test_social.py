"""
社交功能测试脚本

测试AI角色的社交能力：
- 发帖
- 浏览/点赞/评论
- 私聊
- 线下相遇
"""

import sys
import os
import asyncio

# 设置编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from api_server.database import SessionLocal, engine
from api_server.models import User, Post, Comment, Message


async def test_social_client():
    """测试社交客户端"""
    from core_engine.social.social_client import SocialClient, get_social_client
    
    print("=" * 50)
    print("测试社交客户端")
    print("=" * 50)
    
    db = SessionLocal()
    client = get_social_client(db)
    
    # 获取所有AI角色
    ai_users = client.get_ai_characters()
    print(f"\n找到 {len(ai_users)} 个AI角色:")
    for user in ai_users:
        print(f"  - {user.nickname} (ID: {user.id})")
    
    if not ai_users:
        print("没有找到AI角色，请先运行 init_db.py 初始化数据库")
        db.close()
        return False
    
    # 测试获取最新帖子
    posts = client.get_latest_posts(limit=5)
    print(f"\n最新帖子 ({len(posts)} 条):")
    for post in posts:
        print(f"  - [{post.author_name}] {post.content[:30]}... (赞:{post.likes_count})")
    
    # 测试AI发帖
    test_ai = ai_users[0]
    print(f"\n测试 {test_ai.nickname} 发帖...")
    new_post = client.create_post(
        author_id=test_ai.id,
        content="今天天气真不错，适合出门散步！#日常"
    )
    
    if new_post:
        print(f"  发帖成功! ID: {new_post.id}")
        
        # 测试另一个AI点赞
        if len(ai_users) > 1:
            other_ai = ai_users[1]
            liked = client.like_post(other_ai.id, new_post.id)
            print(f"  {other_ai.nickname} 点赞: {'成功' if liked else '失败'}")
            
            # 测试评论
            comment = client.create_comment(
                author_id=other_ai.id,
                post_id=new_post.id,
                content="确实不错呢~"
            )
            if comment:
                print(f"  {other_ai.nickname} 评论成功!")
    else:
        print("  发帖失败")
    
    db.close()
    return True


async def test_social_scheduler():
    """测试社交调度器"""
    from core_engine.social.social_scheduler import get_social_scheduler
    from core_engine.character.agent import CharacterProfile, CharacterAgent
    from core_engine.ai_integration.llm_client import get_llm_client
    
    print("\n" + "=" * 50)
    print("测试社交调度器")
    print("=" * 50)
    
    db = SessionLocal()
    
    # 检查LLM连接
    llm = get_llm_client()
    connected = await llm.check_connection()
    
    if not connected:
        print("\n警告: LLM未连接，跳过需要LLM的测试")
        print("请确保LM Studio在端口1234运行")
        db.close()
        return True
    
    print(f"\nLLM连接成功!")
    
    # 获取AI角色
    ai_user = db.query(User).filter(User.is_ai == True).first()
    if not ai_user:
        print("没有找到AI角色")
        db.close()
        return False
    
    # 创建Agent
    profile = CharacterProfile(
        id=ai_user.id,
        name=ai_user.nickname or ai_user.username,
        description=ai_user.bio or "一个友善的社区居民",
        personality_traits=["友善", "开朗"],
        speaking_style="温和亲切"
    )
    
    agent = CharacterAgent(
        profile=profile,
        llm_client=llm,
        db_session=db
    )
    
    await agent.initialize()
    print(f"\nAgent '{profile.name}' 初始化完成")
    
    # 测试浏览帖子
    scheduler = get_social_scheduler(db)
    
    print("\n测试浏览帖子...")
    results, browsing_summary = await scheduler.browse_feed(agent, max_posts=2)
    
    for r in results:
        print(f"  [{r.action_type.value}] {r.message}")
    
    print(f"\n  浏览总结: {browsing_summary}")
    
    # 测试发帖
    print("\n测试发帖...")
    post_result = await scheduler.create_post(agent, "心情不错，想发点什么")
    
    if post_result:
        print(f"  [{post_result.action_type.value}] {post_result.message}")
    
    db.close()
    return True


async def test_encounter():
    """测试线下相遇"""
    from core_engine.social.social_scheduler import get_social_scheduler
    from core_engine.character.agent import CharacterProfile, CharacterAgent
    from core_engine.ai_integration.llm_client import get_llm_client
    
    print("\n" + "=" * 50)
    print("测试线下相遇")
    print("=" * 50)
    
    db = SessionLocal()
    llm = get_llm_client()
    
    connected = await llm.check_connection()
    if not connected:
        print("LLM未连接，跳过相遇测试")
        db.close()
        return True
    
    # 获取两个AI角色
    ai_users = db.query(User).filter(User.is_ai == True).limit(2).all()
    
    if len(ai_users) < 2:
        print("需要至少2个AI角色来测试相遇")
        db.close()
        return True
    
    # 创建两个Agent
    agents = []
    for user in ai_users:
        profile = CharacterProfile(
            id=user.id,
            name=user.nickname or user.username,
            description=user.bio or "社区居民"
        )
        agent = CharacterAgent(profile=profile, llm_client=llm, db_session=db)
        await agent.initialize()
        agents.append(agent)
    
    print(f"\n{agents[0].profile.name} 和 {agents[1].profile.name} 在公园相遇...")
    
    scheduler = get_social_scheduler(db)
    results = await scheduler.handle_encounter(agents[0], agents[1], "公园")
    
    print("\n对话内容:")
    for r in results:
        speaker_id = r.data.get('speaker')
        speaker_name = agents[0].profile.name if speaker_id == agents[0].character_id else agents[1].profile.name
        content = r.data.get('content', '')
        print(f"  {speaker_name}: {content}")
    
    db.close()
    return True


async def test_private_message():
    """测试私聊功能"""
    from core_engine.social.social_client import get_social_client
    from core_engine.social.social_scheduler import get_social_scheduler
    from core_engine.character.agent import CharacterProfile, CharacterAgent
    from core_engine.ai_integration.llm_client import get_llm_client
    
    print("\n" + "=" * 50)
    print("测试私聊功能")
    print("=" * 50)
    
    db = SessionLocal()
    client = get_social_client(db)
    
    # 获取两个AI角色
    ai_users = client.get_ai_characters()
    
    if len(ai_users) < 2:
        print("需要至少2个AI角色")
        db.close()
        return True
    
    user1, user2 = ai_users[0], ai_users[1]
    
    # 先发送一条测试消息
    print(f"\n{user1.nickname} 给 {user2.nickname} 发送消息...")
    msg = client.send_message(
        sender_id=user1.id,
        receiver_id=user2.id,
        content="你好呀，最近怎么样？"
    )
    
    if msg:
        print(f"  消息发送成功: {msg.content}")
    
    # 检查未读消息
    unread = client.get_unread_messages(user2.id)
    print(f"\n{user2.nickname} 有 {len(unread)} 条未读消息")
    
    # 测试AI回复
    llm = get_llm_client()
    connected = await llm.check_connection()
    
    if connected:
        print(f"\n测试 {user2.nickname} 自动回复...")
        
        profile = CharacterProfile(
            id=user2.id,
            name=user2.nickname,
            description=user2.bio or "社区居民"
        )
        agent = CharacterAgent(profile=profile, llm_client=llm, db_session=db)
        await agent.initialize()
        
        scheduler = get_social_scheduler(db)
        results = await scheduler.check_and_reply_messages(agent)
        
        for r in results:
            print(f"  [{r.action_type.value}] {r.message}")
    
    db.close()
    return True


async def main():
    """主测试函数"""
    print("=" * 60)
    print("AI社区社交功能测试")
    print("=" * 60)
    
    try:
        # 测试社交客户端
        success = await test_social_client()
        if not success:
            print("\n社交客户端测试失败")
            return
        
        # 测试社交调度器
        await test_social_scheduler()
        
        # 测试私聊
        await test_private_message()
        
        # 测试相遇
        await test_encounter()
        
        print("\n" + "=" * 60)
        print("所有测试完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
