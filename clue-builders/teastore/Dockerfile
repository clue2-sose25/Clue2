FROM python:3.13.3-alpine

# Set working directory
WORKDIR /app

# Install system dependencies (Docker CLI, Git, dos2unix, and other essentials)
RUN apk update 
RUN apk add --no-cache docker git dos2unix 
RUN rm -rf /var/cache/apk/*

# Copy all necessary files
COPY ./clue-builders/teastore/ .
# Copy configs
COPY ./clue-config.yaml .
COPY ./sut_configs/teastore.yaml .

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Set the entrypoint to run the build.py script
ENTRYPOINT ["python", "build.py"]