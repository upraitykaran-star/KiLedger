# TaskMate – Academic Task & Assessment Management System

TaskMate is a Java 17 Swing desktop mini-project using MySQL 8, JDBC, Maven, and FlatLaf. It demonstrates relational records for users, courses, enrollments, tasks, submissions, attendance, and activity.

## Implemented

- Role-aware login (HOD, faculty, student) with PBKDF2 password verification.
- Database-backed overview counts, course lists, task lists, student task submission, faculty task creation, and attendance history.
- HOD account creation/deactivation, plus faculty evaluation with marks and feedback.
- Faculty ownership/student enrollment scoping in data queries; server-side role and ownership checks on writes.
- Task creation transaction generates pending submission rows for enrolled students and logs the action.
- Task status derives overdue, due-today, submitted, evaluated, and pending from current date and stored state.
- MySQL schema, example config, first-HOD CLI initializer, connection checker, run scripts, design/presentation docs.

## Requirements

- JDK 17 (verify with `java -version` and `javac -version`)
- Maven 3.9+
- MySQL 8.0 server and command-line client

Install and start MySQL using the official installer/package for your OS. Confirm `mysql --version`; ensure the server is running before continuing. No data is dropped by the setup script.

## Database setup

From this project directory:

```sh
mysql -u root -p < database/schema.sql
```

Create a dedicated local SQL account (replace the password):

```sql
CREATE USER 'taskmate'@'localhost' IDENTIFIED BY 'choose-a-strong-password';
GRANT SELECT, INSERT, UPDATE, DELETE ON taskmate_db.* TO 'taskmate'@'localhost';
```

Copy `.env.example` to `taskmate.properties`, then edit `db.url`, `db.user`, and `db.password`. The ignored file is not committed. Environment variables `TASKMATE_DB_URL`, `TASKMATE_DB_USER`, and `TASKMATE_DB_PASSWORD` override file values.

Initialize the first HOD from a terminal (password input is hidden):

```sh
mvn -q -DskipTests package
mvn -q exec:java -Dexec.mainClass=com.taskmate.utils.InitHod
```

Then check the connection:

```sh
mvn -q exec:java -Dexec.mainClass=com.taskmate.utils.DbCheck
```

## Run

macOS/Linux: `./scripts/run.sh` (if needed: `chmod +x scripts/*.sh`). Windows: `scripts\\run.bat`. Or run `mvn clean compile exec:java`.

Course creation/faculty assignment/student enrollment and attendance marking UI are not yet exposed in the Swing screens; use SQL for these setup operations. Password hashes for any SQL-created accounts must be generated with `PasswordHasher` (do not insert plaintext). Attendance write method exists but has no form flow. There are no prebuilt demo login credentials or fake statistic values.

## Common errors

- **Cannot reach MySQL / connection refused:** start the local MySQL service, confirm its port, then retry.
- **Access denied:** verify database username/password in `taskmate.properties` and grants.
- **Unknown database / missing tables:** run `mysql -u root -p < database/schema.sql`.
- **Missing configuration:** copy `.env.example` to `taskmate.properties`, then fill credentials.
- **Java/Maven command missing:** install JDK 17 and Maven, then reopen the terminal so PATH updates apply.

## Project structure

See `docs/database-design.md`, `docs/project-architecture.md`, `docs/presentation-outline.md`, and `database/queries.sql` for ER relationships, layering, viva questions, presentation flow, and report queries.
