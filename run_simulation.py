"""
AI社区模拟启动脚本

运行基于行动触发的游戏模拟：
- 角色空闲时由AI决策下一步行动
- 所有角色忙碌时自动跳过时间
- AI自主决定休息、睡觉等
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core_engine.simulation import (
    GameSimulation, SimulationConfig, create_simulation, AgentTask
)
from core_engine.environment.world import WorldConfig
from core_engine.character.agent import CharacterAgent
from api_server.database import SessionLocal, engine
from api_server import models


def get_db_session():
    """获取数据库会话"""
    return SessionLocal()


def load_ai_characters(db_session) -> list:
    """加载所有AI角色"""
    users = db_session.query(models.User).filter(models.User.is_ai == True).all()
    return users


async def on_action_start(agent: CharacterAgent, task: AgentTask):
    """行动开始回调"""
    duration = task.end_time - task.start_time
    print(f"  >> [{agent.profile.name}] 开始: {task.action_name} ({duration}分钟)")


async def on_action_end(agent: CharacterAgent, task: AgentTask):
    """行动结束回调"""
    print(f"  << [{agent.profile.name}] 完成: {task.action_name}")


async def on_time_advance(game_time, minutes_skipped):
    """时间推进回调"""
    if minutes_skipped > 0:
        print(f"  -- 时间跳跃 {minutes_skipped} 分钟 -> {game_time}")


async def run_interactive_simulation():
    """运行交互式模拟"""
    print("=" * 60)
    print("AI社区模拟器 (基于行动触发)")
    print("=" * 60)
    
    config = SimulationConfig(
        max_time_skip=480,      # 最多跳8小时
        decision_timeout=60.0,  # 决策超时60秒
        verbose=True,
        initial_day=1,
        initial_hour=8,
        initial_minute=0
    )
    
    world_config = WorldConfig(
        name="AI社区",
        map_width=500.0,
        map_height=500.0
    )
    
    simulation = create_simulation(
        config=config,
        world_config=world_config,
        db_session_factory=get_db_session
    )
    
    # 注册回调
    simulation.on_action_start(on_action_start)
    simulation.on_action_end(on_action_end)
    simulation.on_time_advance(on_time_advance)
    
    # 初始化
    db = get_db_session()
    try:
        await simulation.initialize(db)
        
        ai_users = load_ai_characters(db)
        print(f"\n找到 {len(ai_users)} 个AI角色")
        
        if not ai_users:
            print("警告: 没有找到AI角色，请先在数据库中创建 is_ai=True 的用户")
            return
        
        for i, user in enumerate(ai_users):
            initial_x = 100 + (i % 5) * 80
            initial_y = 100 + (i // 5) * 80
            await simulation.add_character(
                character_id=user.id,
                initial_x=initial_x,
                initial_y=initial_y
            )
        
    finally:
        db.close()
    
    print(f"\n模拟准备就绪，当前时间: {simulation.game_time}")
    print("\n命令:")
    print("  start  - 启动自动模拟")
    print("  stop   - 停止模拟")
    print("  pause  - 暂停")
    print("  resume - 恢复")
    print("  step   - 手动执行一步")
    print("  status - 查看状态")
    print("  quit   - 退出")
    print()
    
    simulation_task = None
    
    try:
        while True:
            try:
                cmd = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input(">>> ").strip().lower()
                )
            except EOFError:
                break
            
            if not cmd:
                continue
            
            if cmd == "start":
                if simulation_task and not simulation_task.done():
                    print("模拟已在运行中")
                else:
                    simulation_task = asyncio.create_task(simulation.start())
                    print("模拟已启动")
            
            elif cmd == "stop":
                await simulation.stop()
                print("模拟已停止")
            
            elif cmd == "pause":
                simulation.pause()
            
            elif cmd == "resume":
                simulation.resume()
            
            elif cmd == "step":
                print("\n执行一步模拟...")
                result = await simulation.step()
                print(f"时间: {result['time_before']} -> {result['time_after']}")
                if result['time_skipped'] > 0:
                    print(f"跳过: {result['time_skipped']} 分钟")
                for action in result['actions']:
                    print(f"  {action['character']}: {action['action']} ({action['duration']}分钟)")
                print()
            
            elif cmd == "status":
                status = simulation.get_status()
                print(f"\n状态: {status['state']}")
                print(f"时间: {status['game_time']}")
                print(f"天气: {status['world']['weather']}")
                print(f"温度: {status['world']['temperature']['outdoor']:.1f}°C")
                print(f"待处理任务: {status['pending_tasks']}")
                print("\n角色状态:")
                for agent in status['agents']:
                    state_str = f"{agent['current_action']}" if agent['state'] == 'busy' else 'idle'
                    print(f"  {agent['name']}: {state_str} (疲劳: {agent['fatigue']:.0f}%)")
                print()
            
            elif cmd in ["quit", "exit", "q"]:
                await simulation.stop()
                print("再见!")
                break
            
            else:
                print(f"未知命令: {cmd}")
    
    except KeyboardInterrupt:
        print("\n中断")
        await simulation.stop()


async def run_step_by_step(steps: int = 10):
    """
    手动步进模式
    
    每一步暂停，显示结果，按回车继续
    """
    print("=" * 60)
    print(f"AI社区模拟器 - 手动步进模式 ({steps}步)")
    print("=" * 60)
    
    config = SimulationConfig(verbose=True)
    simulation = create_simulation(config=config, db_session_factory=get_db_session)
    
    simulation.on_action_start(on_action_start)
    simulation.on_action_end(on_action_end)
    
    db = get_db_session()
    try:
        await simulation.initialize(db)
        
        ai_users = load_ai_characters(db)
        for i, user in enumerate(ai_users):
            await simulation.add_character(
                character_id=user.id,
                initial_x=100 + (i % 5) * 80,
                initial_y=100 + (i // 5) * 80
            )
    finally:
        db.close()
    
    print(f"\n开始时间: {simulation.game_time}")
    print("按回车执行下一步，输入 q 退出\n")
    
    for i in range(steps):
        user_input = input(f"Step {i+1}/{steps} >>> ")
        if user_input.lower() == 'q':
            break
        
        result = await simulation.step()
        print(f"  时间: {result['time_before']} -> {result['time_after']}")
        for action in result['actions']:
            print(f"  {action['character']}: {action['action']} ({action['duration']}分钟)")
        print()
    
    print(f"结束时间: {simulation.game_time}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI社区模拟器')
    parser.add_argument('--step', type=int, default=0,
                       help='手动步进模式（指定步数）')
    args = parser.parse_args()
    
    # 确保数据库表存在
    models.Base.metadata.create_all(bind=engine)
    
    # 确保保存目录存在
    os.makedirs("data/saves", exist_ok=True)
    
    if args.step > 0:
        asyncio.run(run_step_by_step(args.step))
    else:
        asyncio.run(run_interactive_simulation())


if __name__ == "__main__":
    main()
