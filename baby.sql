
# 测试用
DESCRIBE notifications;
-- 或者
SHOW COLUMNS FROM notifications;

SELECT id, user_id, pinned FROM notifications WHERE id = 11;

USE baby;
SHOW TABLES;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL
);

ALTER TABLE users ADD COLUMN hashed_password VARCHAR(255) NOT NULL;
ALTER TABLE users
ADD COLUMN username VARCHAR(255) UNIQUE;


# ALTER TABLE users DROP INDEX username;

CREATE TABLE device (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    rtsp_url TEXT NOT NULL,
    ip VARCHAR(45) NOT NULL,
    status ENUM('online', 'offline') NOT NULL DEFAULT 'offline',
    email VARCHAR(255) NOT NULL,
    last_active DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);


INSERT INTO device (name, email, ip, status, rtsp_url)
VALUES
    ('设备', '2@2.com', '192.168.101.52', 'online', 'rtsp://admin:sbh740911@192.168.101.52:554/stream1'),
    ('设备2', '2@2.com', '192.168.0.2', 'offline', 'rtsp://192.168.0.2:554'),
    ('设备3', '2@2.com', '192.168.0.3', 'offline', 'rtsp://192.168.0.3:554'),
    ('设备4', '2@2.com', '192.168.0.4', 'offline', 'rtsp://192.168.0.4:554');


SELECT * FROM device WHERE email = '2@2.com';



CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    device_id INT,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    pinned BOOLEAN NOT NULL DEFAULT FALSE,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (device_id) REFERENCES device(id) ON DELETE SET NULL
);

INSERT INTO notifications (user_id, device_id, level, message, timestamp, pinned, deleted)
VALUES
(9, 1, 'safe', '婴儿正在正常活动', NOW(), false, false),
(1, 1, 'warning', '婴儿趴着睡觉时间过长', NOW(), false, false),
(7, 2, 'danger', '婴儿可能跌倒了', NOW(), false, false),
(8, 2, 'warning', '婴儿坐起但姿势不稳定', NOW(), true, false),
(10, 1, 'danger', '检测到危险姿态，请立刻查看！', NOW(), true, false);
