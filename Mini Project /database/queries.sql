USE taskmate_db;
-- Upcoming/overdue status is derived at read time; evaluated and submitted tasks are not pending.
SELECT t.title,c.course_code,t.due_date,s.status,
 CASE WHEN s.status='EVALUATED' THEN 'COMPLETED' WHEN s.status='SUBMITTED' THEN 'SUBMITTED' WHEN t.due_date<CURDATE() THEN 'OVERDUE' WHEN t.due_date=CURDATE() THEN 'DUE TODAY' WHEN t.due_date<=DATE_ADD(CURDATE(),INTERVAL 7 DAY) THEN 'UPCOMING' ELSE 'PENDING' END derived_status
FROM tasks t JOIN courses c ON c.id=t.course_id JOIN submissions s ON s.task_id=t.id WHERE s.student_id=? ORDER BY t.due_date;
-- Faculty assignment and evaluation activity.
SELECT u.name,COUNT(DISTINCT t.id) tasks_created,COUNT(DISTINCT s.id) submissions_evaluated
FROM users u LEFT JOIN tasks t ON t.faculty_id=u.id LEFT JOIN submissions s ON s.evaluated_by=u.id WHERE u.role='FACULTY' GROUP BY u.id,u.name;
-- Attendance percentage by course/student.
SELECT c.course_code,u.name,COUNT(*) classes, SUM(a.attendance_status='PRESENT') present,
 ROUND(100.0*SUM(a.attendance_status='PRESENT')/NULLIF(COUNT(*),0),1) attendance_pct
FROM attendance a JOIN courses c ON c.id=a.course_id JOIN users u ON u.id=a.student_id GROUP BY c.id,u.id;
-- Course task completion (HOD report).
SELECT c.course_code,c.section,COUNT(DISTINCT t.id) tasks,COUNT(s.id) student_task_rows,
 SUM(s.status='EVALUATED') evaluated, SUM(s.status='PENDING') pending FROM courses c LEFT JOIN tasks t ON t.course_id=c.id LEFT JOIN submissions s ON s.task_id=t.id GROUP BY c.id;
