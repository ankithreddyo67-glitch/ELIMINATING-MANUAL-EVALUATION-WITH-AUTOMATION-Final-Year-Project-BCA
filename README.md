# AutoExam MySQL

This database package follows the current AutoExam SQLite schema and includes 34 SQL scripts for MySQL 8.0.16 or later. The Flask backend still uses SQLite. Running this package creates a separate schema and does not migrate existing records or switch the app connection.

## Install

From the extracted folder, open the MySQL command-line client with `mysql -u YOUR_USER -p --abort-source-on-error`. Use an account with permission to create the autoexam database, tables and views. Then enter these commands:

```sql
SOURCE 00_install.sql;
SHOW TABLES;
SOURCE 33_demo_subjects.sql;
```

The last line is optional. Scripts 01-10 create tables in foreign-key order. Scripts 11-18 create views. Run reports 19-28 and integrity checks 29-32 individually in the same client after `USE autoexam;`. Healthy integrity checks return zero rows.

Use a UTC session when storing or comparing AutoExam timestamps. Run `SET time_zone = '+00:00';` in your MySQL session. The package assumes a fresh schema for first installation. Re-running setup creates missing tables and replaces views. Existing tables are not upgraded in place.

The archive has 34 SQL scripts plus this README. SQL scripts were checked for file ordering and dependencies. Live MySQL execution requires a MySQL client and server.
