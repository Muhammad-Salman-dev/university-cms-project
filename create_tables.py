from app import create_app
from app.database import get_db

app = create_app()

# --- SQL SCRIPT FOR DATABASE RESET ---
SQL_SCRIPT = """
-- 1. DROP ALL FOREIGN KEY CONSTRAINTS
-- This dynamic SQL finds and deletes all foreign keys to prevent dependency errors when dropping tables.
DECLARE @sql NVARCHAR(MAX) = N'';
SELECT @sql += N'ALTER TABLE ' + QUOTENAME(OBJECT_SCHEMA_NAME(parent_object_id))
    + '.' + QUOTENAME(OBJECT_NAME(parent_object_id))
    + ' DROP CONSTRAINT ' + QUOTENAME(name) + ';'
FROM sys.foreign_keys;
EXEC sp_executesql @sql;

-- 2. DROP EXISTING TABLES
IF OBJECT_ID('dbo.Submissions', 'U') IS NOT NULL DROP TABLE dbo.Submissions;
IF OBJECT_ID('dbo.Assignments', 'U') IS NOT NULL DROP TABLE dbo.Assignments;
IF OBJECT_ID('dbo.Enrollments', 'U') IS NOT NULL DROP TABLE dbo.Enrollments;
IF OBJECT_ID('dbo.Courses', 'U') IS NOT NULL DROP TABLE dbo.Courses;
IF OBJECT_ID('dbo.Users', 'U') IS NOT NULL DROP TABLE dbo.Users;

-- 3. CREATE NEW TABLE STRUCTURE

-- Users Table
CREATE TABLE Users (
    user_id INT IDENTITY(1,1) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) CHECK (role IN ('Admin', 'Faculty', 'Student')) NOT NULL
);

-- Courses Table (Default Capacity: 30)
CREATE TABLE Courses (
    course_id INT IDENTITY(1,1) PRIMARY KEY,
    course_code VARCHAR(20) UNIQUE NOT NULL,
    course_name VARCHAR(100) NOT NULL,
    credits INT NOT NULL,
    room_number VARCHAR(20),
    capacity INT DEFAULT 30,
    enrolled_count INT DEFAULT 0,
    teacher_id INT,
    FOREIGN KEY (teacher_id) REFERENCES Users(user_id)
);

-- Enrollments Table
CREATE TABLE Enrollments (
    enrollment_id INT IDENTITY(1,1) PRIMARY KEY,
    student_id INT NOT NULL,
    course_id INT NOT NULL,
    grade VARCHAR(5),
    attendance_percentage FLOAT DEFAULT 0.0,
    FOREIGN KEY (student_id) REFERENCES Users(user_id),
    FOREIGN KEY (course_id) REFERENCES Courses(course_id),
    UNIQUE(student_id, course_id)
);

-- Assignments Table
CREATE TABLE Assignments (
    assignment_id INT IDENTITY(1,1) PRIMARY KEY,
    course_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    due_date DATE,
    FOREIGN KEY (course_id) REFERENCES Courses(course_id)
);

-- 4. INSERT DEFAULT SEED DATA
INSERT INTO Users (name, email, password, role) VALUES
('Super Admin', 'admin@uni.com', 'admin123', 'Admin'),
('Sir Ali', 'ali@uni.com', 'teacher123', 'Faculty'),
('Ahmed Khan', 'ahmed@uni.com', 'student123', 'Student');
"""

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        try:
            # Execute the SQL Script
            cursor.execute(SQL_SCRIPT)
            db.commit()
            print("\n🎉 SUCCESS: Database has been reset and initialized successfully.")
            print("👤 Default Users Created: Admin, Faculty, Student")
        except Exception as e:
            print(f"\n❌ Error initializing database: {e}")

if __name__ == '__main__':
    init_db()