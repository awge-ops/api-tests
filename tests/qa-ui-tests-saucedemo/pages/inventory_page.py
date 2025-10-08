class InventoryPage:
def __init__(self, page):
self.page = page


def is_open(self):
return "/inventory.html" in self.page.url