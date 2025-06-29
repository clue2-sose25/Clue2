import io
import json
import os
from pathlib import Path
from typing import List, Optional
import zipfile
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from clue_deployer.src.configs.configs import ENV_CONFIG
from clue_deployer.src.logger import logger

SUT_CONFIGS_DIR = ENV_CONFIG.SUT_CONFIGS_PATH
RESULTS_DIR = ENV_CONFIG.RESULTS_PATH
CLUE_CONFIG_PATH = ENV_CONFIG.CLUE_CONFIG_PATH

router = APIRouter()

def read_svg(name, base_path):
    path = os.path.join(base_path, f"{name}.svg")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

class ResultsEntry(BaseModel):
    uuid: str
    status: str
    sut: str
    timestamp: str
    workloads: str  # comma-separated list
    variants: str   # comma-separated list
    n_iterations: int
    

def find_deepest_directories(base_path: Path) -> List[Path]:
    """Recursively find all directories that don't contain any subdirectories."""
    deepest_dirs = []
    
    def _explore_directory(current_path: Path):
        subdirs = [item for item in current_path.iterdir() if item.is_dir()]
        
        if not subdirs:
            # This directory has no subdirectories, so it's a leaf
            deepest_dirs.append(current_path)
        else:
            # This directory has subdirectories, explore them
            for subdir in subdirs:
                _explore_directory(subdir)
    
    _explore_directory(base_path)
    return deepest_dirs

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

def extract_results_entry(directory: Path) -> Optional[ResultsEntry]:
    """Extract ResultsEntry from experiment.json and status.json in a directory."""
    experiment_file = directory / "experiment.json"
    status_file = directory / "status.json"
    
    # Read both JSON files
    experiment_data = read_json_file(experiment_file)
    status_data = read_json_file(status_file)
    
    # Check if both files were successfully read
    if experiment_data is None or status_data is None:
        logger.warning(f"Missing or invalid JSON files in directory: {directory}")
        return None
    
    try:
        # Extract data from experiment.json
        uuid = experiment_data.get("id", "")
        sut = experiment_data.get("sut", "")
        n_iterations = experiment_data.get("n_iterations", 0)
        timestamp = experiment_data.get("timestamp", "")
        
        # Extract workloads (comma-separated names)
        workloads_list = experiment_data.get("workloads", [])
        workloads = ",".join([workload.get("name", "") for workload in workloads_list])
        
        # Extract variants (comma-separated names)
        variants_list = experiment_data.get("variants", [])
        variants = ",".join([variant.get("name", "") for variant in variants_list])
        
        # Extract status from status.json
        status = status_data.get("status", "")
        
        return ResultsEntry(
            uuid=uuid,
            status=status,
            sut=sut,
            timestamp=timestamp,
            workloads=workloads,
            variants=variants,
            n_iterations=n_iterations,
        )
    except Exception as e:
        logger.error(f"Error processing data from directory {directory}: {e}")
        return None

@router.get("/api/results", response_model=List[ResultsEntry])
async def list_all_results():
    """List all results by recursively searching through nested subfolders."""
    results_base_path = Path(RESULTS_DIR)
    
    # Check for results directory
    if not results_base_path.is_dir():
        logger.error(f"Results directory not found: {results_base_path}")
        raise HTTPException(status_code=404, detail=f"Results directory not found: {results_base_path}")
    
    try:
        processed_results = []
        
        # Find all deepest directories (directories without subdirectories)
        deepest_dirs = find_deepest_directories(results_base_path)
        
        for directory in deepest_dirs:
            # Try to extract ResultsEntry from this directory
            results_entry = extract_results_entry(directory)
            if results_entry:
                processed_results.append(results_entry)
            else:
                logger.debug(f"Skipping directory without valid JSON files: {directory}")
        
        return processed_results
        
    except PermissionError:
        logger.exception("Permission error while accessing results directory.")
        raise HTTPException(status_code=500, detail="Permission denied when accessing results.")
    except Exception as e:
        logger.exception("Unexpected error while retrieving results.")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while retrieving results: {str(e)}")

# @app.get("/api/results/{result_id}", response_model=Experiment)
# async def get_single_result(result_id: str):
#     """Get a single result by ID."""
#     results_base_path = Path(RESULTS_DIR)
    
#     # Check for results directory
#     if not results_base_path.is_dir():
#         logger.error(f"Results directory not found: {results_base_path}")
#         raise HTTPException(status_code=404, detail=f"Results directory not found: {results_base_path}")
    
#     try:
#         # Parse the result ID to extract components
#         # Expected format: timestamp_workload_branch_experiment_number
#         id_parts = result_id.split('_')
#         if len(id_parts) < 4:
#             raise HTTPException(status_code=400, detail="Invalid result ID format")
        
#         # Join the remaining parts back (in case workload or branch names contain underscores)
#         remaining_parts = id_parts[:-1]
        
#         # Find the result by searching through the directory structure
#         for results_dir in results_base_path.iterdir():
#             if not results_dir.is_dir():
#                 continue
                
#             timestamp = results_dir.name.strip()
            
#             for workload_dir in results_dir.iterdir():
#                 if not workload_dir.is_dir():
#                     continue
                    
#                 workload_name = workload_dir.name.strip()
                
#                 for branch_dir in workload_dir.iterdir():
#                     if not branch_dir.is_dir():
#                         continue
                        
#                     branch_name = branch_dir.name.strip()
                    
#                     # Check if this combination matches our ID
#                     expected_id = f"{timestamp}_{workload_name}_{branch_name}"
#                     if expected_id == result_id:
#                         # Verify the experiment directory exists
#                         exp_dir = branch_dir
#                         if not exp_dir.is_dir():
#                             continue
                            
#                         # Count iterations
#                         iterations_count = sum(1 for item in exp_dir.iterdir() if item.is_dir())
                        
#                         return Experiment(
#                             id=result_id,
#                             workload=workload_name,
#                             branch_name=branch_name,
#                             timestamp=timestamp,
#                             n_iterations=iterations_count
#                         )
        
#         # If we get here, the result wasn't found
#         raise HTTPException(status_code=404, detail=f"Result with ID '{result_id}' not found")
        
#     except HTTPException:
#         # Re-raise HTTP exceptions
#         raise
#     except PermissionError:
#         logger.exception("Permission error while accessing results directory.")
#         raise HTTPException(status_code=500, detail="Permission denied when accessing results.")
#     except Exception as e:
#         logger.exception(f"Unexpected error while retrieving result '{result_id}'.")
#         raise HTTPException(status_code=500, detail=f"An unexpected error occurred while retrieving result: {str(e)}")

# @app.delete("/api/results/{result_id}")
# async def delete_result(result_id: str):
#     """Delete a specific result directory."""
#     results_base_path = Path(RESULTS_DIR)

#     if not results_base_path.exists():
#         raise HTTPException(status_code=404, detail=f"Results directory {results_base_path} does not exist")

#     try:
#         # Locate the directory matching the provided ID by traversing
#         for timestamp_dir in results_base_path.iterdir():
#             if not timestamp_dir.is_dir():
#                 continue
#             timestamp = timestamp_dir.name.strip()

#             for workload_dir in timestamp_dir.iterdir():
#                 if not workload_dir.is_dir():
#                     continue
#                 workload_name = workload_dir.name.strip()

#                 for branch_dir in workload_dir.iterdir():
#                     if not branch_dir.is_dir():
#                         continue
#                     branch_name = branch_dir.name.strip()

#                     expected_id = f"{timestamp}_{workload_name}_{branch_name}"
#                     if expected_id == result_id:
#                         # Remove the branch directory and clean up parents
#                         shutil.rmtree(branch_dir)

#                         if not any(workload_dir.iterdir()):
#                             workload_dir.rmdir()
#                             if not any(timestamp_dir.iterdir()):
#                                 timestamp_dir.rmdir()

#                         return {"message": f"Result {result_id} deleted"}

#         # If we reach here, the result wasn't found
#         raise HTTPException(status_code=404, detail=f"Result with ID '{result_id}' not found")

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.exception(f"Unexpected error while deleting result '{result_id}'.")
#         raise HTTPException(status_code=500, detail=f"An unexpected error occurred while deleting result: {str(e)}")

@router.get("/api/results/assets/{result_id}")
async def get_results(result_id:str):
    results_base_path = Path(RESULTS_DIR)
    
    # Check for results directory
    if not results_base_path.is_dir():
        logger.error(f"Results directory not found: {results_base_path}")
        raise HTTPException(status_code=404, detail=f"Results directory not found: {results_base_path}")
    
    try:
        # Parse the result ID to extract components
        # Expected format: timestamp_workload_branch_experiment_number
        id_parts = result_id.split('_')
        if len(id_parts) < 4:
            raise HTTPException(status_code=400, detail="Invalid result ID format")
        
        # Join the remaining parts back (in case workload or branch names contain underscores)
        remaining_parts = id_parts[:-1]
        
        # Find the result by searching through the directory structure
        for results_dir in results_base_path.iterdir():
            if not results_dir.is_dir():
                continue
                
            timestamp = results_dir.name.strip()
            
            for workload_dir in results_dir.iterdir():
                if not workload_dir.is_dir():
                    continue
                    
                workload_name = workload_dir.name.strip()
                
                for branch_dir in workload_dir.iterdir():
                    if not branch_dir.is_dir():
                        continue
                        
                    branch_name = branch_dir.name.strip()
                    
                    # Check if this combination matches our ID
                    expected_id = f"{timestamp}_{workload_name}_{branch_name}"
                    if expected_id == result_id:
                        # Verify the experiment directory exists
                        exp_dir = branch_dir
                        if not exp_dir.is_dir():
                            continue
                        
                        exp_dir = exp_dir/"0"
                        with open(os.path.join(exp_dir, "metrics.json"), "r") as f:
                            metrics = json.load(f)

                        return {
                            "metrics": metrics,
                            "cpu_svg": read_svg("cpu_usage", exp_dir),
                            "memory_svg": read_svg("memory_usage", exp_dir),
                            "wattage_svg": read_svg("wattage_kepler", exp_dir),
                        }
        
        # If we get here, the result wasn't found
        raise HTTPException(status_code=404, detail=f"Result with ID '{result_id}' not found")
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except PermissionError:
        logger.exception("Permission error while accessing results directory.")
        raise HTTPException(status_code=500, detail="Permission denied when accessing results.")
    except Exception as e:
        logger.exception(f"Unexpected error while retrieving result '{result_id}'.")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while retrieving result: {str(e)}")

@router.get("/api/results/{result_id}/download")
async def download_results(result_id: str):
    """Download a specific result as a zip file."""
    results_base_path = Path(RESULTS_DIR)
    
    # Check for results directory
    if not results_base_path.exists():
        raise HTTPException(status_code=404, detail=f"Results directory {results_base_path} does not exist. Did you run any experiments?")
    
    try:
        # Parse the result ID to extract components
        # Expected format: timestamp_workload_branch_experiment_number
        id_parts = result_id.split('_')
        timestamp = f"{id_parts[0]}_{id_parts[1]}"
        timestamp_folder = results_base_path / timestamp
        
        logger.info(timestamp_folder)
        
        # Check if timestamp folder exists
        if not timestamp_folder.is_dir():
            raise HTTPException(status_code=404, detail=f"Timestamp folder '{timestamp}' not found")
        
        # Create zip file with the entire timestamp folder
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Include the entire timestamp folder and all its contents
            for file_path in timestamp_folder.rglob("*"):
                if file_path.is_file():
                    # Preserve the full directory structure starting from timestamp folder
                    # This creates: timestamp/workload/branch/experiment/files
                    relative_path = file_path.relative_to(timestamp_folder.parent)
                    zip_file.write(file_path, relative_path)
        
        # Prepare the buffer for reading
        zip_buffer.seek(0)
        
        # Create a descriptive filename using the timestamp
        safe_filename = f"{timestamp}.zip"
        
        # Return the zip file as a streaming response
        return StreamingResponse(
            io.BytesIO(zip_buffer.read()),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={safe_filename}"}
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except PermissionError:
        logger.exception("Permission error while accessing results directory.")
        raise HTTPException(status_code=500, detail="Permission denied when accessing results.")
    except Exception as e:
        logger.exception(f"Unexpected error while downloading result '{result_id}'.")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while downloading result: {str(e)}")
        