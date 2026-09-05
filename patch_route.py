import sys

with open("app/api/routes_chat.py", "r") as f:
    content = f.read()

content = content.replace(
    "except Exception as e:",
    "except Exception as e:\n        import traceback; traceback.print_exc()\n"
)

with open("app/api/routes_chat.py", "w") as f:
    f.write(content)
