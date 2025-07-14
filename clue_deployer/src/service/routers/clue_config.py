import yaml
from fastapi import APIRouter, HTTPException

import clue_deployer.src.configs.configs as configs
from clue_deployer.src.configs.clue_config import ClueConfig
from clue_deployer.src.logger import logger

router = APIRouter()

@router.get("/api/config/clue", response_model=ClueConfig)
async def get_clue_config():
    """Return the current CLUE configuration."""
    try:
        if configs.CONFIGS and configs.CONFIGS.clue_config:
            return configs.CONFIGS.clue_config
        return ClueConfig.load_from_yaml(configs.ENV_CONFIG.CLUE_CONFIG_PATH)
    except Exception as exc:
        logger.exception("Failed to load clue config")
        raise HTTPException(status_code=500, detail=str(exc))

@router.put("/api/config/clue", response_model=ClueConfig)
async def update_clue_config(new_config: ClueConfig):
    """Update and persist the CLUE configuration."""
    try:
        path = configs.ENV_CONFIG.CLUE_CONFIG_PATH
        with open(path, "w") as f:
            yaml.safe_dump({"config": new_config.model_dump()}, f)
        if configs.CONFIGS:
            configs.CONFIGS.clue_config = new_config
        configs.CLUE_CONFIG = new_config
        return new_config
    except Exception as exc:
        logger.exception("Failed to update clue config")
        raise HTTPException(status_code=500, detail=str(exc))