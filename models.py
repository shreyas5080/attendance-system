from werkzeug.security import generate_password_hash,check_password_hash
from DataBase import init_database
import secrets
import string

#-------GENERATING USERNAME AND PASSWORD-------
def generate_username(name, length = 4):
    user= string.ascii_lowercase + string.digits
    random_part = ''.join(secrets.choice(user) for _ in range(length))
    return f"{name.lower().replace(' ','')}@{random_part}"

def generate_password(length = 10):
    cha= string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(cha) for _ in range(length))

def generate_unique_username(cur, name):
    while True:
        username = generate_username(name)
        cur.execute("SELECT id FROM users WHERE user_name=%s", (username,))
        if not cur.fetchone():
            return username


#--------ADDING_USERS-----------
def add_user(name, username, password, role):
    conn = init_database()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE user_name=%s", (username,))
    if cur.fetchone():
        conn.close()
        return False

    hashed = generate_password_hash(password)

    cur.execute("""
        INSERT INTO users(name, user_name, password, user_role)
        VALUES(%s,%s,%s,%s)
    """, (name, username, hashed, role))

    conn.commit()
    conn.close()
    return True


#----------CHECKING_USERS-------
def check_user(username, password, role):
    conn = init_database()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, password FROM users 
        WHERE user_name=%s AND user_role=%s
    """, (username, role))

    user = cur.fetchone()
    conn.close()

    if user and check_password_hash(user[1], password):
        return user[0]  # return user_id

    return None


# ---------------- STUDENT CREATE ----------------
def add_stu(name):
    conn = init_database()
    cur = conn.cursor()

    username = generate_unique_username(cur,name).lower()
    password = generate_password()

    hashed = generate_password_hash(password)

    

    cur.execute("""
        INSERT INTO users(name, user_name, password, user_role)
        VALUES(%s,%s,%s,'student')
    """, (name, username, hashed))

    user_id = cur.lastrowid

    cur.execute("""
        INSERT INTO students(name, user_name, user_id)
        VALUES(%s,%s,%s)
    """, (name, username, user_id))

    conn.commit()
    conn.close()
    return username,password