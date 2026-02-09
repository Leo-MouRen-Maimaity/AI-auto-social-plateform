-- AI行动日志表
-- 记录AI角色的每一步行动历史

USE ai_community;

-- 行动日志表
CREATE TABLE IF NOT EXISTS action_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    character_id INT NOT NULL,
    action_type ENUM('move', 'talk', 'use_phone', 'post', 'like', 'comment', 'message', 'rest', 'sleep', 'wake_up', 'eat', 'work', 'think', 'encounter', 'other') NOT NULL,
    action_name VARCHAR(100) NOT NULL,
    description TEXT,
    location_id INT,
    target_character_id INT,
    
    -- 游戏时间相关
    game_day INT,
    game_time VARCHAR(10),
    duration INT DEFAULT 0,
    
    -- AI决策相关
    reason TEXT,
    result TEXT,
    success BOOLEAN DEFAULT TRUE,
    
    -- LLM交互记录
    input_prompt TEXT,
    llm_response TEXT,
    
    -- 额外数据
    extra_data JSON,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (character_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE SET NULL,
    FOREIGN KEY (target_character_id) REFERENCES users(id) ON DELETE SET NULL,
    
    INDEX idx_character (character_id),
    INDEX idx_created_at (created_at DESC),
    INDEX idx_character_time (character_id, created_at DESC),
    INDEX idx_game_day (game_day)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
