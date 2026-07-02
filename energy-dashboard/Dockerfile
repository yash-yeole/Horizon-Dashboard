# Build the Vite/React bundle, then serve it statically with nginx on HF's port 7860.
# The API base URL is baked in at build time from .env.production (VITE_API_BASE_URL),
# so the deployed static site calls the HORIZON backend Space.
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 7860
CMD ["nginx", "-g", "daemon off;"]
