# Presentation outline

1. Problem: academic tasks and assessment records are scattered.
2. Solution and roles: HOD, faculty, student; show least-privilege data views.
3. DBMS: ER model, keys, bridge table, constraints, and indexes.
4. Java: Swing navigation, immutable model records, DAO/service layers, JDBC.
5. Security: PBKDF2 password hashes, parameterized SQL, role checks.
6. Demo: initialize HOD; provision faculty/student and course/enrollment; faculty creates task; student submits; faculty evaluates; student checks marks; inspect attendance/report SQL.
7. Limitations and next steps: HOD provisioning screens, assessment UI, asynchronous JDBC, integration tests.

## Viva prompts

- Why use `PreparedStatement`? It binds values separately from SQL and prevents SQL injection for data values.
- Why use `enrollments`? It models the many-to-many relationship between students and courses without repeating course data.
- Why keep marks nullable? A pending/ungraded submission has no mark yet; zero is a real grade.
- Why derive overdue status? It changes as the date changes and should not require a daily database update.
- How are passwords stored? Random per-password salt and PBKDF2-HMAC-SHA256; only the derived hash is persisted.
- What does a transaction protect in task creation? The task and its generated pending submissions/log entry either all commit or roll back together.
- How does role isolation work? DAO queries constrain faculty ownership or student enrollment, and write methods validate role/ownership.
- What is a foreign key? A database constraint that prevents references to missing parent rows.
- What does `GROUP BY` do? It groups matching rows so aggregate functions can calculate counts or averages per course/person.
- What should happen when MySQL is unavailable? The app should show setup guidance rather than fabricated data.
