import yaml

with open('docker-compose.yml', 'r') as f:
    compose = yaml.safe_load(f)

if 'frontend' in compose['services']:
    compose['services']['frontend']['ports'] = ['5174:5173']

with open('docker-compose.yml', 'w') as f:
    yaml.dump(compose, f, default_flow_style=False, sort_keys=False)
