import yaml

# 1. Update docker-compose.yml
with open('docker-compose.yml', 'r') as f:
    compose = yaml.safe_load(f)

if 'frontend' not in compose['services']:
    compose['services']['frontend'] = {
        'build': './frontend',
        'ports': ['5173:5173'],
        'volumes': ['./frontend:/app', '/app/node_modules'],
        'depends_on': ['app']
    }

with open('docker-compose.yml', 'w') as f:
    yaml.dump(compose, f, default_flow_style=False, sort_keys=False)

# 2. Create frontend/Dockerfile
with open('frontend/Dockerfile', 'w') as f:
    f.write('''\
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
''')

# 3. Update vite.config.ts
with open('frontend/vite.config.ts', 'w') as f:
    f.write('''\
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://app:8000',
        changeOrigin: true
      }
    },
    watch: {
      usePolling: true,
    }
  }
})
''')
