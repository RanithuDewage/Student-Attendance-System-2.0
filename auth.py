from db import (
    init_db,
    verify_admin,
    create_admin,
    change_admin_password,
    list_admins,
)


def init_admin():
    """
    Initialize the database and ensure default admin exists.
    init_db() already seeds the default admin if none exists.
    """
    init_db()
    return True


def login_admin(username, password):
    """
    Verify admin credentials.

    Returns:
        (ok: bool, role: str | None)
    """
    return verify_admin(username, password)


def add_admin(username, password, role="operator"):
    """
    Create or update an admin account.
    """
    create_admin(username, password, role)
    return True


def update_admin_password(username, old_password, new_password):
    """
    Change admin password after verifying old password.
    """
    return change_admin_password(username, old_password, new_password)


def get_admin_list():
    """
    Return all admins.
    """
    return list_admins()