"""数据库初始化脚本"""
import pymysql
import sys
import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# 数据库配置
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'Leo_dev_778899')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'ai_community')


def init_database():
    """初始化数据库"""
    # 读取SQL文件
    sql_file = os.path.join(os.path.dirname(__file__), 'data', 'migrations', '001_init.sql')
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 连接MySQL（不指定数据库）
    connection = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        charset='utf8mb4',
        autocommit=True
    )
    
    try:
        with connection.cursor() as cursor:
            # 分割SQL语句并执行
            statements = sql_content.split(';')
            for statement in statements:
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        cursor.execute(statement)
                        print(f"执行成功: {statement[:50]}...")
                    except pymysql.err.IntegrityError as e:
                        # 忽略重复数据错误
                        if e.args[0] == 1062:
                            print(f"跳过重复数据: {statement[:50]}...")
                        else:
                            raise
                    except pymysql.err.ProgrammingError as e:
                        # 忽略表已存在等错误
                        print(f"警告: {e}")
        print("\n数据库初始化完成!")
    finally:
        connection.close()


if __name__ == "__main__":
    print("开始初始化数据库...")
    print(f"MySQL: {MYSQL_HOST}:{MYSQL_PORT}")
    print(f"数据库: {MYSQL_DATABASE}")
    print()
    
    try:
        init_database()
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
