import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import List, Optional
import zipfile
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from clue_deployer.src.configs.configs import CONFIGS
from clue_deployer.src.logger import logger

SUT_CONFIGS_DIR = CONFIGS.env_config.SUT_CONFIGS_PATH
RESULTS_DIR = CONFIGS.env_config.RESULTS_PATH
CLUE_CONFIG_PATH = CONFIGS.env_config.CLUE_CONFIG_PATH


router = APIRouter()

def read_svg(name, base_path):
    path = os.path.join(base_path, f"{name}.svg")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

class ResultsEntry(BaseModel):
    uuid: str
    status: str
    workloads: str  # comma-separated list
    variants: str   # comma-separated list
    n_iterations: int
    sut: str
    timestamp: str
    deploy_only: bool


def read_json_file(file_path: Path) -> Optional[dict]:
    """Safely read and parse a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"JSON file not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None


def extract_results_entry(sut_dir: Path, timestamp_dir: Path) -> Optional[ResultsEntry]:
    """Extract ResultsEntry from experiment.json and status.json in timestamp directory."""
    experiment_file = timestamp_dir / "experiment.json"
    status_file = timestamp_dir / "status.json"
    
    # Read both JSON files
    experiment_data = read_json_file(experiment_file)
    status_data = read_json_file(status_file)
    
    # Check if both files were successfully read
    if experiment_data is None or status_data is None:
        logger.warning(f"Missing or invalid JSON files in directory: {timestamp_dir}")
        return None
    
    try:
        # Extract data from experiment.json
        uuid = experiment_data.get("id", "")
        sut = experiment_data.get("sut", "")
        n_iterations = experiment_data.get("n_iterations", 0)
        
        # Extract workloads (comma-separated names)
        workloads_list = experiment_data.get("workloads", [])
        workloads = ",".join([workload.get("name", "") for workload in workloads_list])
        
        # Extract variants (comma-separated names)  
        variants_list = experiment_data.get("variants", [])
        variants = ",".join([variant.get("name", "") for variant in variants_list])
        
        # Extract status from status.json
        status = status_data.get("status", "")

        # Extract if deploy only
        deploy_only = status_data.get("deploy_only", False)
        
        return ResultsEntry(
            uuid=uuid,
            status=status,
            workloads=workloads,
            variants=variants,
            n_iterations=n_iterations,
            sut=sut,
            timestamp=timestamp_dir.name,
            deploy_only=deploy_only
        )
    except Exception as e:
        logger.error(f"Error processing data from directory {timestamp_dir}: {e}")
        return None

def find_experiment_by_uuid(uuid: str, results_base_path: Path) -> Optional[dict]:
    """Find experiment data by UUID and return combined experiment.json and status.json."""
    try:
        # Iterate through SUT directories
        for sut_dir in results_base_path.iterdir():
            if not sut_dir.is_dir():
                continue
                
            # Iterate through timestamp directories within each SUT
            for timestamp_dir in sut_dir.iterdir():
                if not timestamp_dir.is_dir():
                    continue
                
                experiment_file = timestamp_dir / "experiment.json"
                status_file = timestamp_dir / "status.json"
                
                # Read experiment.json to check UUID
                experiment_data = read_json_file(experiment_file)
                if experiment_data and experiment_data.get("id") == uuid:
                    # Found the matching experiment, now read status.json
                    status_data = read_json_file(status_file)
                    if status_data:
                        # Combine both JSON files
                        combined_data = experiment_data.copy()
                        combined_data.update(status_data)
                        return combined_data
                    else:
                        # Return experiment data even if status is missing
                        return experiment_data
                        
    except Exception as e:
        logger.error(f"Error searching for UUID {uuid}: {e}")
        
    return None

@router.get("/api/results/{uuid}")
async def get_result_by_uuid(uuid: str):
    """Get a specific result by UUID, returning combined experiment.json and status.json data."""
    results_base_path = Path(RESULTS_DIR)
    
    # Check for results directory
    if not results_base_path.is_dir():
        logger.error(f"Results directory not found: {results_base_path}")
        raise HTTPException(status_code=404, detail=f"Results directory not found: {results_base_path}")
    
    try:
        # Find the experiment by UUID
        experiment_data = find_experiment_by_uuid(uuid, results_base_path)
        
        if experiment_data is None:
            raise HTTPException(status_code=404, detail=f"Experiment with UUID {uuid} not found")
            
        return experiment_data
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except PermissionError:
        logger.exception("Permission error while accessing results directory.")
        raise HTTPException(status_code=500, detail="Permission denied when accessing results.")
    except Exception as e:
        logger.exception(f"Unexpected error while retrieving experiment {uuid}.")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while retrieving experiment: {str(e)}")

@router.get("/api/results", response_model=List[ResultsEntry])
async def list_all_results():
    """List all results by reading JSON files from timestamp directories."""
    results_base_path = Path(RESULTS_DIR)
    
    # Check for results directory
    if not results_base_path.is_dir():
        logger.error(f"Results directory not found: {results_base_path}")
        raise HTTPException(status_code=404, detail=f"Results directory not found: {results_base_path}")
    
    try:
        processed_results = []
        
        # Iterate through SUT directories
        for sut_dir in results_base_path.iterdir():
            if not sut_dir.is_dir():
                logger.debug(f"Skipping non-directory entry: {sut_dir.name}")
                continue
                
            # Iterate through timestamp directories within each SUT
            for timestamp_dir in sut_dir.iterdir():
                if not timestamp_dir.is_dir():
                    logger.debug(f"Skipping non-directory entry in SUT '{sut_dir.name}': {timestamp_dir.name}")
                    continue
                
                # Try to extract ResultsEntry from this timestamp directory
                results_entry = extract_results_entry(sut_dir, timestamp_dir)
                if results_entry:
                    processed_results.append(results_entry)
                else:
                    logger.debug(f"Skipping timestamp directory without valid JSON files: {timestamp_dir}")
        
        # Sort by timestamp for consistent ordering
        processed_results.sort(key=lambda x: x.timestamp)
        return processed_results
        
    except PermissionError:
        logger.exception("Permission error while accessing results directory.")
        raise HTTPException(status_code=500, detail="Permission denied when accessing results.")
    except Exception as e:
        logger.exception("Unexpected error while retrieving results.")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while retrieving results: {str(e)}")

def find_experiment_directory_by_uuid(uuid: str, results_base_path: Path) -> Optional[Path]:
    """Find the timestamp directory containing the experiment with the given UUID."""
    try:
        # Iterate through SUT directories
        for sut_dir in results_base_path.iterdir():
            if not sut_dir.is_dir():
                continue
                
            # Iterate through timestamp directories within each SUT
            for timestamp_dir in sut_dir.iterdir():
                if not timestamp_dir.is_dir():
                    continue
                
                experiment_file = timestamp_dir / "experiment.json"
                
                # Read experiment.json to check UUID
                experiment_data = read_json_file(experiment_file)
                if experiment_data and experiment_data.get("id") == uuid:
                    return timestamp_dir
                        
    except Exception as e:
        logger.error(f"Error searching for UUID {uuid}: {e}")
        
    return None

@router.delete("/api/results/{uuid}")
async def delete_result_by_uuid(uuid: str):
    """Delete a specific experiment by UUID, removing the entire timestamp directory."""
    results_base_path = Path(RESULTS_DIR)
    
    # Check for results directory
    if not results_base_path.is_dir():
        logger.error(f"Results directory not found: {results_base_path}")
        raise HTTPException(status_code=404, detail=f"Results directory not found: {results_base_path}")
    
    try:
        # Find the experiment directory by UUID
        experiment_dir = find_experiment_directory_by_uuid(uuid, results_base_path)
        
        if experiment_dir is None:
            raise HTTPException(status_code=404, detail=f"Experiment with UUID {uuid} not found")
        
        # Delete the entire timestamp directory
        shutil.rmtree(experiment_dir)
        logger.info(f"Successfully deleted experiment {uuid} at {experiment_dir}")
        
        return {"message": f"Experiment {uuid} deleted successfully", "deleted_path": str(experiment_dir)}
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except PermissionError:
        logger.exception("Permission error while deleting experiment directory.")
        raise HTTPException(status_code=500, detail="Permission denied when deleting experiment.")
    except Exception as e:
        logger.exception(f"Unexpected error while deleting experiment {uuid}.")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while deleting experiment: {str(e)}")


def create_zip_from_directory(source_dir: Path, zip_path: Path) -> None:
    """Create a ZIP file containing all contents of the source directory."""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk through all files and directories
        for root, dirs, files in os.walk(source_dir):
            root_path = Path(root)
            
            # Add all files
            for file in files:
                file_path = root_path / file
                # Create archive path relative to source directory
                archive_path = file_path.relative_to(source_dir)
                zipf.write(file_path, archive_path)
            
            # Add empty directories
            for dir_name in dirs:
                dir_path = root_path / dir_name
                if not any(dir_path.iterdir()):  # Check if directory is empty
                    archive_path = dir_path.relative_to(source_dir)
                    # Add empty directory to zip
                    zipf.writestr(f"{archive_path}/", "")

@router.get("/api/results/{uuid}/download")
async def download_experiment_by_uuid(uuid: str):
    """Download the entire experiment directory as a ZIP file."""
    results_base_path = Path(RESULTS_DIR)
    
    # Check for results directory
    if not results_base_path.is_dir():
        logger.error(f"Results directory not found: {results_base_path}")
        raise HTTPException(status_code=404, detail=f"Results directory not found: {results_base_path}")
    
    try:
        # Find the experiment directory by UUID
        experiment_dir = find_experiment_directory_by_uuid(uuid, results_base_path)
        
        if experiment_dir is None:
            raise HTTPException(status_code=404, detail=f"Experiment with UUID {uuid} not found")
        
        # Create a temporary ZIP file
        temp_dir = Path(tempfile.gettempdir())
        zip_filename = f"experiment_{uuid}_{experiment_dir.name}.zip"
        zip_path = temp_dir / zip_filename
        
        # Create ZIP file from the experiment directory
        create_zip_from_directory(experiment_dir, zip_path)
        
        logger.info(f"Created ZIP file for experiment {uuid}: {zip_path}")
        
        # Return the ZIP file as a download
        return FileResponse(
            path=str(zip_path),
            media_type='application/zip',
            filename=zip_filename,
            background=None  # File will be automatically cleaned up by FastAPI
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except PermissionError:
        logger.exception("Permission error while accessing experiment directory.")
        raise HTTPException(status_code=500, detail="Permission denied when accessing experiment.")
    except Exception as e:
        logger.exception(f"Unexpected error while downloading experiment {uuid}.")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while downloading experiment: {str(e)}")

