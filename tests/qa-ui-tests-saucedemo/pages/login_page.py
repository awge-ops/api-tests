class LoginPage:
def __init__(self, page, base_url):
self.page = page
self.base_url = base_url
self.username = page.locator("#user-name")
self.password = page.locator("#password")
self.login_button = page.locator("#login-button")
self.error = page.locator("[data-test='error']")


def open(self):
self.page.goto(self.base_url)


def login(self, username, password):
self.username.fill(username)
self.password.fill(password)
self.login_button.click()


def wait_for_inventory(self, timeout=5000):
self.page.wait_for_url("**/inventory.html", timeout=timeout)


def get_error(self):
if self.error.count():
text = self.error.text_content()
return text.strip() if text else ""
return ""