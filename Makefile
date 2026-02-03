deploy-docker:
	docker compose down && docker compose up -d --build && \
	sleep 5 && \
	docker compose up --build clue-webui -d \
	&& docker attach clue-deployer   