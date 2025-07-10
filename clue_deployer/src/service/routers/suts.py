import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import base64
import yaml

from clue_deployer.src.configs.configs import ENV_CONFIG
from clue_deployer.src.configs.sut_config import SUTConfig
from clue_deployer.src.models.sut import VariantEntry, Sut, WorkloadEntry

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
        files = [
            f
            for f in os.listdir(SUT_CONFIGS_DIR)
            if f.endswith((".yaml", ".yml"))
            and os.path.isfile(os.path.join(SUT_CONFIGS_DIR, f))
            and os.path.splitext(f)[0] != "default_sut"
        ]
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
                    raise HTTPException(status_code=500, detail=f"Invalid variant in SUT configuration file: {filename}")
                parsed_variants.append(
                    VariantEntry(name=variant.get('name'), description=variant.get('description'))
                )

            # Get workload section, default to empty list if missing
            workloads = data.get('workloads', [])
            if not isinstance(workloads, list):
                raise HTTPException(status_code=500, detail=f"Invalid SUT configuration file: {filename} has 'workloads' that is not a list")
            
            # Extract workloads with optional description
            parsed_workloads = []
            for workload in workloads:
                if not isinstance(workload, dict) or 'name' not in workload:
                    raise HTTPException(status_code=500, detail=f"Invalid workload in SUT configuration file: {filename}")
                parsed_workloads.append(
                    WorkloadEntry(name=workload.get('name'), description=workload.get('description'))
                )

            # Create Sut object and add to list
            sut = Sut(name=sut, variants=parsed_variants, workloads=parsed_workloads)
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
    

@router.get("/api/suts/raw/{sut}", response_class=PlainTextResponse)
async def get_sut_yaml(sut: str):
    """Return the raw YAML configuration for a SUT."""
    cleaned_sut = sut.strip().lower()
    sut_filename = f"{cleaned_sut}.yaml"
    sut_path = os.path.join(SUT_CONFIGS_DIR, sut_filename)
    if not os.path.isfile(sut_path):
        raise HTTPException(status_code=404, detail=f"SUT configuration not found: {sut}")
    try:
        with open(sut_path, "r") as f:
            return f.read()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read SUT configuration: {exc}")


class SutUpload(BaseModel):
    """Request model for uploading a new SUT configuration."""
    sut_config: str


@router.post("/api/suts")
async def upload_sut(req: SutUpload):
    """Upload a new SUT configuration file."""
    try:
        decoded = base64.b64decode(req.sut_config).decode()
        data = yaml.safe_load(decoded)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to decode SUT config: {exc}")

    sut_name = data.get("config", {}).get("sut")
    if not sut_name:
        raise HTTPException(status_code=400, detail="SUT name not found in configuration")
    sut_filename = f"{sut_name}.yaml"
    sut_path = os.path.join(SUT_CONFIGS_DIR, sut_filename)

    try:
        with open(sut_path, "w") as f:
            f.write(decoded)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save SUT configuration: {exc}")

    return {"message": "SUT configuration uploaded"}