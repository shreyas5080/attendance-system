# 🎓 Student Attendance Management System

A Flask-based web application to manage students and track attendance.

---

## 🚀 Features

* 🔐 User Authentication (Lecture & Student)
* 👨‍🏫 Lecturer Dashboard
* 👨‍🎓 Student Dashboard
* ➕ Add Students (auto-generate username & password)
* 📊 Attendance Tracking (basic)
* 🔒 Secure Password Hashing

---

## 🛠️ Tech Stack

* Python (Flask)
* MySQL
* HTML, CSS
* Werkzeug (password hashing)

---

## 📂 Project Structure

```
project/
│── main.py
│── models.py
│── DataBase.py
│── templates/
│── static/
│── .env
│── .gitignore
```

---

## ⚙️ Setup Instructions

### 1. Clone the repository

```
git clone https://github.com/shreyas5080/attendance-system.git
cd attendance-system
```

---

### 2. Create virtual environment

```
python -m venv .venv
source .venv/bin/activate   # Linux / Mac
.venv\Scripts\activate      # Windows
```

---

### 3. Install dependencies

```
pip install -r requirements.txt
```

---

### 4. Setup Database

Create database:

```
CREATE DATABASE my_database;
USE my_database;
```

Create tables:

```sql
CREATE TABLE users(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    user_name VARCHAR(100) UNIQUE,
    password VARCHAR(255),
    user_role ENUM('lecture','student'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE students(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200),
    user_name VARCHAR(100) UNIQUE,
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

---

### 5. Create `.env` file

```
SECURE_KEY=your_secret_key
```

---

### 6. Run the app

```
python main.py
```

App will run on:

```
http://127.0.0.1:5000/
```

---

## 🔑 Default Behavior

* Students are created with:

  * Auto-generated username
  * Auto-generated password
* Credentials should be shared manually or via email

---

## ⚠️ Notes

* This is a learning project
* Not production-ready yet
* Add proper validation & error handling for real use

---

## 📌 Future Improvements

* 📧 Email credentials to students
* 🔄 Password reset system
* 📈 Advanced attendance reports
* 🌐 Deployment (Render / Railway)

---

## 👨‍💻 Author

Shreyas

---

## ⭐ If you like this project

Give it a star on GitHub ⭐
