import os
from fastapi import APIRouter, HTTPException, logger
import yaml

from clue_deployer.src.configs.configs import ENV_CONFIG
from clue_deployer.src.configs.sut_config import SUTConfig
from clue_deployer.src.models.sut import VariantEntry, Sut

SUT_CONFIGS_DIR = ENV_CONFIG.SUT_CONFIGS_PATH
RESULTS_DIR = ENV_CONFIG.RESULTS_PATH
CLUE_CONFIG_PATH = ENV_CONFIG.CLUE_CONFIG_PATH

router = APIRouter()

@router.get("/api/suts", response_model=list[Sut])
async def list_sut():
    """
    List all SUTs with their experiments.
    """
    try:
        if not os.path.isdir(SUT_CONFIGS_DIR):
            raise HTTPException(status_code=404, detail=f"SUT configurations directory not found: {SUT_CONFIGS_DIR}")

        # Get list of YAML files in the SUT configurations directory
        files = [f for f in os.listdir(SUT_CONFIGS_DIR) if f.endswith(('.yaml', '.yml')) and os.path.isfile(os.path.join(SUT_CONFIGS_DIR, f))]
        suts = []
        for filename in files:
            # Extract SUT name from filename (without extension)
            sut = os.path.splitext(filename)[0]
            file_path = os.path.join(SUT_CONFIGS_DIR, filename)

            # Read and parse the YAML file
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)

            # Validate that the YAML content is a dictionary
            if not isinstance(data, dict):
                raise HTTPException(status_code=500, detail=f"Invalid SUT configuration file: {filename} is not a valid YAML dictionary")

            # Get variants section, default to empty list if missing
            variants = data.get('variants', [])
            if not isinstance(variants, list):
                raise HTTPException(status_code=500, detail=f"Invalid SUT configuration file: {filename} has 'variants' that is not a list")

            # Extract experiments with optional description
            parsed_variants = []
            for variant in variants:
                if not isinstance(variant, dict) or 'name' not in variant:
                    raise HTTPException(status_code=500, detail=f"Invalid experiment in SUT configuration file: {filename}")
                parsed_variants.append(
                    VariantEntry(name=variant.get('name'), description=variant.get('description'))
                )

            # Create Sut object and add to list
            sut = Sut(name=sut, variants=parsed_variants)
            suts.append(sut)

        return suts

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while listing SUTs: {str(e)}")
    
@router.get("/api/config/sut/{sut}", response_model=SUTConfig)
async def get_sut_config(sut: str):
    """Get a specific SUT configuration."""
    cleaned_sut = sut.strip().lower()
    sut_filename = f"{cleaned_sut}.yaml"
    sut_path = os.path.join(SUT_CONFIGS_DIR, sut_filename)
    if not os.path.isfile(sut_path):
        raise HTTPException(status_code=404, detail=f"SUT configuration not found: {sut}")
    try: 
        sut_config = SUTConfig.load_from_yaml(sut_path)
        return sut_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while retrieving SUT configuration: {str(e)}")
