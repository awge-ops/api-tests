from pages.login_page import LoginPage
from pages.inventory_page import InventoryPage


def test_login_success(page, base_url):
login = LoginPage(page, base_url)
inventory = InventoryPage(page)
login.open()
login.login("standard_user", "secret_sauce")
login.wait_for_inventory()
assert inventory.is_open()


def test_login_wrong_password(page, base_url):
login = LoginPage(page, base_url)
login.open()
login.login("standard_user", "wrong_password")
error = login.get_error()
assert error != ""


def test_login_locked_out_user(page, base_url):
login = LoginPage(page, base_url)
login.open()
login.login("locked_out_user", "secret_sauce")
error = login.get_error()
assert "locked" in error.lower()