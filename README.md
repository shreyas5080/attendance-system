# Student Attendance Management System

A Flask-based web application for managing students and tracking daily attendance.

## Features

- Lecturer and student login
- Lecturer dashboard with attendance summary
- Student dashboard with recent attendance records
- Student creation with generated username and password
- Daily attendance marking
- Attendance report with percentage calculation
- Secure password hashing with Werkzeug

## Tech Stack

- Python and Flask
- MySQL
- HTML, CSS, Bootstrap
- python-dotenv
- Werkzeug password hashing

## Project Structure

```text
attendance-system/
|-- main.py
|-- models.py
|-- DataBase.py
|-- templates/
|-- static/
|-- requirements.txt
|-- Procfile
|-- .gitignore
```

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/shreyas5080/attendance-system.git
cd attendance-system
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

```bash
# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
SECURE_KEY=change_this_secret_key
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_database_password
DB_NAME=my_database

# Optional, only needed for hosted databases that require SSL
DB_SSL_CA=/path/to/ca-certificate.crt
```

### 5. Setup the database

Create the database:

```sql
CREATE DATABASE my_database;
USE my_database;
```

Create the tables:

```sql
CREATE TABLE users(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    user_name VARCHAR(100) UNIQUE,
    password VARCHAR(255),
    user_role ENUM('lecturer','student'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE students(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200),
    user_id INT UNIQUE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE attendance(
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT,
    date DATE,
    status BOOLEAN DEFAULT 0,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE(student_id, date)
);
```

### 6. Run the app

```bash
python main.py
```

Open:

```text
http://127.0.0.1:5000/
```

## Notes

- Students are created with generated credentials.
- Share generated student credentials manually after creating a student.
- This is a learning project and should be hardened further before production use.

## Future Improvements

- Email credentials to students
- Password reset flow
- Advanced attendance reports
- Deployment guide for Render or Railway

## Author

Shreyas
