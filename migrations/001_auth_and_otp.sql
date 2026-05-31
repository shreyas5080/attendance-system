ALTER TABLE users ADD COLUMN email VARCHAR(255) NULL AFTER user_name;
ALTER TABLE users ADD COLUMN auth_provider VARCHAR(30) NOT NULL DEFAULT 'password' AFTER user_role;
ALTER TABLE users ADD COLUMN oauth_subject VARCHAR(255) NULL AFTER auth_provider;
ALTER TABLE users ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT 0 AFTER oauth_subject;
ALTER TABLE users ADD COLUMN last_login_at DATETIME NULL AFTER is_verified;
ALTER TABLE users ADD UNIQUE INDEX idx_users_email_unique (email);
ALTER TABLE users ADD INDEX idx_users_oauth (auth_provider, oauth_subject);

CREATE TABLE IF NOT EXISTS otp_verifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    user_name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    otp_hash VARCHAR(255) NOT NULL,
    expires_at DATETIME NOT NULL,
    attempts INT NOT NULL DEFAULT 0,
    consumed_at DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_otp_email (email),
    INDEX idx_otp_expires_at (expires_at)
);
