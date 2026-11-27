# StudentLedgerPro Phase 4 — Accounts and permissions

## First launch
On the first launch after this update, the application asks the operator to create the first administrator account. Use a username of at least 3 characters and a password of at least 8 characters. Every subsequent launch requires authentication.

## Roles
- **admin**: view, import, add, edit, delete, and create/manage accounts through the database API.
- **editor**: view, import, add, and edit. Cannot delete.
- **viewer**: read-only access to the student database and exports.

The initial administrator is created interactively. Additional accounts can be provisioned with `StudentDatabase.create_user(username, password, role)`; valid roles are `admin`, `editor`, and `viewer`. Accounts can be disabled with `set_user_active(user_id, False)`.

## Security and audit
Passwords are salted and hashed using PBKDF2-HMAC-SHA256 (240,000 iterations). Plain-text passwords are not stored. Successful logins and student import/add/edit/delete actions are written to the SQLite `activity_log` table. Account data and activity history are stored in the same per-user application database.

## Storage
The SQLite database remains in the current per-user application data directory, not beside the executable. No network connection is required for authentication or normal database operations.
