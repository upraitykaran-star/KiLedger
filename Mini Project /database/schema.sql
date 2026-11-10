CREATE DATABASE IF NOT EXISTS taskmate_db CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE taskmate_db;
CREATE TABLE IF NOT EXISTS users (
 id BIGINT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(120) NOT NULL, email VARCHAR(190) NOT NULL UNIQUE,
 password_hash VARCHAR(255) NOT NULL, role ENUM('HOD','FACULTY','STUDENT') NOT NULL,
 department VARCHAR(120) NOT NULL, academic_year VARCHAR(20), section VARCHAR(20), is_active BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, INDEX ix_users_role_active(role,is_active)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS courses (
 id BIGINT PRIMARY KEY AUTO_INCREMENT, course_code VARCHAR(24) NOT NULL UNIQUE, course_name VARCHAR(150) NOT NULL,
 department VARCHAR(120) NOT NULL, academic_year VARCHAR(20) NOT NULL, section VARCHAR(20) NOT NULL,
 faculty_id BIGINT NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT fk_course_faculty FOREIGN KEY(faculty_id) REFERENCES users(id), INDEX ix_course_section(department,academic_year,section)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS enrollments (
 id BIGINT PRIMARY KEY AUTO_INCREMENT, student_id BIGINT NOT NULL, course_id BIGINT NOT NULL,
 enrolled_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE KEY uq_enrollment(student_id,course_id),
 CONSTRAINT fk_enrollment_student FOREIGN KEY(student_id) REFERENCES users(id), CONSTRAINT fk_enrollment_course FOREIGN KEY(course_id) REFERENCES courses(id), INDEX ix_enrollment_course(course_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS tasks (
 id BIGINT PRIMARY KEY AUTO_INCREMENT, course_id BIGINT NOT NULL, faculty_id BIGINT NOT NULL,
 title VARCHAR(180) NOT NULL, description TEXT, task_type ENUM('ASSIGNMENT','QUIZ','ASSESSMENT') NOT NULL,
 due_date DATE NOT NULL, priority ENUM('HIGH','MEDIUM','LOW') NOT NULL DEFAULT 'MEDIUM',
 max_marks DECIMAL(7,2) NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT ck_task_marks CHECK(max_marks>0), CONSTRAINT fk_task_course FOREIGN KEY(course_id) REFERENCES courses(id),
 CONSTRAINT fk_task_faculty FOREIGN KEY(faculty_id) REFERENCES users(id), INDEX ix_task_due(due_date), INDEX ix_task_course(course_id), INDEX ix_task_faculty(faculty_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS submissions (
 id BIGINT PRIMARY KEY AUTO_INCREMENT, task_id BIGINT NOT NULL, student_id BIGINT NOT NULL,
 status ENUM('PENDING','SUBMITTED','EVALUATED') NOT NULL DEFAULT 'PENDING', submitted_at DATETIME,
 marks DECIMAL(7,2), feedback TEXT, evaluated_by BIGINT, evaluated_at DATETIME,
 UNIQUE KEY uq_submission(task_id,student_id), CONSTRAINT ck_submission_marks CHECK(marks IS NULL OR marks>=0),
 CONSTRAINT fk_submission_task FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
 CONSTRAINT fk_submission_student FOREIGN KEY(student_id) REFERENCES users(id), CONSTRAINT fk_submission_evaluator FOREIGN KEY(evaluated_by) REFERENCES users(id), INDEX ix_submission_student_status(student_id,status)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS attendance (
 id BIGINT PRIMARY KEY AUTO_INCREMENT, course_id BIGINT NOT NULL, student_id BIGINT NOT NULL, class_date DATE NOT NULL,
 attendance_status ENUM('PRESENT','ABSENT') NOT NULL, marked_by BIGINT NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE KEY uq_attendance(student_id,course_id,class_date), CONSTRAINT fk_attendance_course FOREIGN KEY(course_id) REFERENCES courses(id),
 CONSTRAINT fk_attendance_student FOREIGN KEY(student_id) REFERENCES users(id), CONSTRAINT fk_attendance_marker FOREIGN KEY(marked_by) REFERENCES users(id), INDEX ix_attendance_date(course_id,class_date)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS activity_logs (
 id BIGINT PRIMARY KEY AUTO_INCREMENT, user_id BIGINT NOT NULL, action VARCHAR(40) NOT NULL,
 entity_type VARCHAR(40) NOT NULL, entity_id BIGINT, description VARCHAR(500) NOT NULL,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, CONSTRAINT fk_log_user FOREIGN KEY(user_id) REFERENCES users(id), INDEX ix_log_user_date(user_id,created_at), INDEX ix_log_entity(entity_type,entity_id)
) ENGINE=InnoDB;
