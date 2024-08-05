# Use the official Node.js 18 image
FROM node:18

# Create and change to the app directory
WORKDIR /usr/src/app

# Copy application dependency manifests to the container image.
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code to the container image.
COPY . .

# Expose port 8080
EXPOSE 8080

# Start the app with nodemon for development
CMD ["npx", "nodemon", "--exec", "npx", "ts-node", "src/index.ts"]