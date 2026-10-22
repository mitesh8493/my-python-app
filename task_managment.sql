DROP DATABASE IF EXISTS task_management;
CREATE DATABASE task_management;
USE task_management;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    password VARCHAR(255),
    role VARCHAR(50)
);

CREATE TABLE task (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100),
    description TEXT,
    status VARCHAR(50),
    assigned_to VARCHAR(100),
    deadline DATE
);

CREATE TABLE projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    description TEXT,
    status VARCHAR(50),
    assigned_to VARCHAR(100),
    deadline DATE
);

CREATE TABLE attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_email VARCHAR(100),
    date DATE,
    status VARCHAR(20)
);

CREATE TABLE logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_email VARCHAR(100),
    action TEXT,
    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (username,email,password,role) VALUES
('Admin','admin@gmail.com','a665a45920422f9d417e4867efdc4fb8...','admin'),
('Manager','manager@gmail.com','a665a45920422f9d417e4867efdc4fb8...','manager'),
('Employee','emp@gmail.com','a665a45920422f9d417e4867efdc4fb8...','employee');
UPDATE users SET role='manager' WHERE role='project manager';
SELECT email, password FROM users;

CREATE TABLE feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_name VARCHAR(100),
    email VARCHAR(100),
    message TEXT,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

UPDATE users 
SET role='manager' 
WHERE role='project manager';

describe projects;