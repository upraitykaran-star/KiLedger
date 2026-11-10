# Java architecture

`Main` starts Swing; `ui.auth` authenticates and routes by session role; `ui.components` renders dashboard navigation and tables. `services` performs date and input checks. `dao` owns prepared SQL and role-scoped data access. `models` are immutable records. `security.PasswordHasher` uses salted PBKDF2-HMAC-SHA256. `database.Database` loads ignored local configuration and maps common connection failures to setup guidance.

Database operations use try-with-resources. Task creation is transactional: it inserts the task, creates pending submission rows for enrolled students, logs the action, then commits. Faculty queries include faculty ownership predicates; student queries include enrollment predicates. The DAO repeats role checks for write operations.

Current UI uses simple modal dialogs for task creation/evaluation and synchronous JDBC calls. HOD can create faculty/student accounts and activate/deactivate accounts; course assignment/enrollment management still needs a dedicated screen or SQL administration. A production deployment should move JDBC calls into `SwingWorker` and add connection pooling.
