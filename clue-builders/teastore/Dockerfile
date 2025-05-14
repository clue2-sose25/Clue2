FROM 3.12.10-alpine3.21

# Set working directory
WORKDIR /app

# Install system dependencies (Docker CLI, Git, dos2unix, and other essentials)
RUN apt-get update && apt-get install -y \
    docker.io \
    git \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Copy the project files
COPY . .
COPY ../clue-config.yaml .
COPY ../sut_configs/teastore.yaml ./sut_configs/teastore.yaml
COPY clue-deployer ./clue-deployer
COPY teastore ./teastore
COPY workload-generator ./workload-generator
COPY clue-builders ./clue-builders

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Ensure shell scripts have correct line endings (targeting teastore/tools)
RUN find ./teastore/tools -type f -name "*.sh" -exec dos2unix {} \;

# Set the entrypoint to run the build.py script
ENTRYPOINT ["python", "build.py"]