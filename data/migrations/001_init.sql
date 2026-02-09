-- AI社区数据库初始化脚本
-- 创建数据库
CREATE DATABASE IF NOT EXISTS ai_community CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ai_community;

-- 用户表 (统一AI角色和真实用户)
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255),
    nickname VARCHAR(50) NOT NULL,
    avatar_path VARCHAR(500),
    bio TEXT,
    is_ai BOOLEAN DEFAULT FALSE,
    -- AI角色专用字段
    personality TEXT,
    fatigue INT DEFAULT 100,
    current_x FLOAT DEFAULT 0,
    current_y FLOAT DEFAULT 0,
    current_location_id INT,
    inventory_weight_limit FLOAT DEFAULT 20.0,
    -- 通用字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_is_ai (is_ai)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 记忆表 (AI专用)
CREATE TABLE IF NOT EXISTS memories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    memory_type ENUM('common', 'daily', 'important', 'knowledge', 'relation') NOT NULL,
    target_user_id INT,
    content TEXT NOT NULL,
    importance INT DEFAULT 5,
    game_day INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (target_user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user_type (user_id, memory_type),
    INDEX idx_game_day (game_day)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 帖子表
CREATE TABLE IF NOT EXISTS posts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    author_id INT NOT NULL,
    content TEXT NOT NULL,
    image_path VARCHAR(500),
    likes_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_author (author_id),
    INDEX idx_created_at (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 点赞表
CREATE TABLE IF NOT EXISTS post_likes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    post_id INT NOT NULL,
    user_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_like (post_id, user_id),
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 评论表
CREATE TABLE IF NOT EXISTS comments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    post_id INT NOT NULL,
    author_id INT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_post (post_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 群聊表
CREATE TABLE IF NOT EXISTS chat_groups (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    group_type ENUM('online', 'offline') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 群成员表
CREATE TABLE IF NOT EXISTS chat_group_members (
    id INT PRIMARY KEY AUTO_INCREMENT,
    group_id INT NOT NULL,
    user_id INT NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_member (group_id, user_id),
    FOREIGN KEY (group_id) REFERENCES chat_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 消息表
CREATE TABLE IF NOT EXISTS messages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    sender_id INT NOT NULL,
    receiver_id INT,
    group_id INT,
    content TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (group_id) REFERENCES chat_groups(id) ON DELETE CASCADE,
    INDEX idx_private_chat (sender_id, receiver_id),
    INDEX idx_group_chat (group_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 地点表
CREATE TABLE IF NOT EXISTS locations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    location_type VARCHAR(50),
    x FLOAT NOT NULL,
    y FLOAT NOT NULL,
    width FLOAT DEFAULT 10,
    height FLOAT DEFAULT 10,
    description TEXT,
    INDEX idx_position (x, y)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 游戏事件表
CREATE TABLE IF NOT EXISTS game_events (
    id INT PRIMARY KEY AUTO_INCREMENT,
    event_type VARCHAR(50) NOT NULL,
    character_id INT,
    target_character_id INT,
    location_id INT,
    scheduled_time INT NOT NULL,
    duration INT DEFAULT 0,
    status ENUM('pending', 'in_progress', 'completed', 'cancelled') DEFAULT 'pending',
    data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (target_character_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE SET NULL,
    INDEX idx_scheduled (scheduled_time),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 生图队列表
CREATE TABLE IF NOT EXISTS image_gen_queue (
    id INT PRIMARY KEY AUTO_INCREMENT,
    character_id INT NOT NULL,
    prompt TEXT NOT NULL,
    reference_images JSON,
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    result_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 物品栏表
CREATE TABLE IF NOT EXISTS inventory (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    item_name VARCHAR(100) NOT NULL,
    weight FLOAT DEFAULT 0,
    quantity INT DEFAULT 1,
    properties JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 补充 users 表的外键约束（locations 表已创建）
ALTER TABLE users ADD FOREIGN KEY (current_location_id) REFERENCES locations(id) ON DELETE SET NULL;

-- 插入测试AI角色
INSERT INTO users (username, nickname, avatar_path, bio, is_ai, personality) VALUES
('ai_xiaoming', '小明', '/avatars/xiaoming.png', '一个热爱编程的AI角色', TRUE, '性格开朗，喜欢帮助他人，对技术充满热情'),
('ai_xiaohong', '小红', '/avatars/xiaohong.png', '一个喜欢艺术的AI角色', TRUE, '温柔细腻，热爱绘画和音乐，善于表达情感'),
('ai_xiaoli', '小李', '/avatars/xiaoli.png', '一个运动达人AI角色', TRUE, '活力四射，热爱户外运动，乐观向上');

-- 插入测试地点
INSERT INTO locations (name, location_type, x, y, width, height, description) VALUES
('中心广场', 'public', 0, 0, 50, 50, '社区的中心地带，是大家聚会的好地方'),
('咖啡馆', 'commercial', 100, 50, 20, 15, '一家温馨的咖啡馆，提供各种饮品'),
('图书馆', 'public', -80, 30, 30, 25, '藏书丰富的公共图书馆'),
('公园', 'public', 50, -100, 80, 60, '绿树成荫的休闲公园'),
('小明的家', 'residential', -50, -50, 15, 15, '小明的住所'),
('小红的家', 'residential', 80, -30, 15, 15, '小红的住所'),
('小李的家', 'residential', -100, 80, 15, 15, '小李的住所');

-- 插入共同记忆（世界设定）
INSERT INTO memories (user_id, memory_type, content, importance, game_day) VALUES
(1, 'common', '这是一个虚拟的AI社区，居民们在这里生活、工作、社交。社区有中心广场、咖啡馆、图书馆、公园等公共场所。居民们可以自由移动、互相交流、发布动态。', 10, 1),
(1, 'common', '社区作息：早上8点起床开始新的一天，晚上10点左右休息。疲劳值达到70以上时应该考虑休息或睡觉。', 10, 1);

-- 为每个AI角色插入重要记忆（角色背景）
INSERT INTO memories (user_id, memory_type, content, importance, game_day) VALUES
(1, 'important', '我是小明，一个热爱编程的年轻人。我喜欢在咖啡馆写代码，在图书馆看技术书籍。我性格开朗，乐于助人，希望能结交志同道合的朋友。', 10, 1),
(2, 'important', '我是小红，一个热爱艺术的女孩。我喜欢绘画和音乐，经常在公园写生或在咖啡馆听音乐。我性格温柔，善于表达情感，希望用艺术感染他人。', 10, 1),
(3, 'important', '我是小李，一个热爱运动的阳光青年。我每天都会去公园锻炼，喜欢和朋友们一起进行户外活动。我性格乐观开朗，精力充沛，希望带动大家一起运动。', 10, 1);
