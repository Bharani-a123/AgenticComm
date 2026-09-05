with open("frontend/src/App.tsx", "r") as f:
    content = f.read()
content = content.replace("{log.agent_name} -> {log.event_type}", "{log.agent_name} {'->'} {log.event_type}")
with open("frontend/src/App.tsx", "w") as f:
    f.write(content)
