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

# Build the TypeScript code
RUN npm run build

# Run the compiled code
CMD ["node", "dist/index.js"]

# Expose port 8080
EXPOSE 8080