import subprocess
from pathlib import Path
from typing import Optional, List, Dict


from clue_deployer.experiment import Experiment

class HelmError(Exception):
    """Base exception for Helm operations."""
    def __init__(self, message, command: List[str], return_code: Optional[int] = None, output: Optional[str] = None):
        super().__init__(message)
        self.command = command
        self.return_code = return_code
        self.output = output

    def __str__(self):
        details = f"Command: {' '.join(self.command)}\n"
        if self.return_code is not None:
            details += f"Return Code: {self.return_code}\n"
        if self.output:
            details += f"Output:\n{self.output}\n"
        return f"{super().__str__()} \nDetails:\n{details}"

class HelmInstallError(HelmError):
    """Exception for Helm install failures."""
    pass

class HelmUninstallError(HelmError):
    """Exception for Helm uninstall failures."""
    pass

class HelmClient:
    def __init__(self, helm_executable: str = "helm"):
        self.helm_executable = helm_executable
        # You could add more default configurations here if needed

    def _run_command(self, command_args: List[str], cwd: Optional[str | Path] = None) -> str:
        """Helper method to run a Helm command and return its decoded output."""
        full_command = [self.helm_executable] + command_args
        try:
            print(f"Executing Helm command: {' '.join(full_command)} {'from CWD: ' + str(cwd) if cwd else ''}")
            process_output = subprocess.check_output(full_command, cwd=cwd, stderr=subprocess.STDOUT)
            return process_output.decode("utf-8")
        except subprocess.CalledProcessError as cpe:
            output_str = cpe.output.decode("utf-8") if cpe.output else "No output captured."
            # Re-raise with a more specific error, including command and output
            raise HelmError(
                f"Helm command failed.",
                command=full_command,
                return_code=cpe.returncode,
                output=output_str
            ) from cpe
        except FileNotFoundError:
            raise HelmError(f"Helm executable '{self.helm_executable}' not found.", command=full_command)


    def install(self, release_name: str, chart_path: str | Path, namespace: str,
                values_file: Optional[str | Path] = None, set_values: Optional[Dict[str, str]] = None) -> str:
        """
        Installs a Helm chart.
        Args:
            release_name: The name for the release.
            chart_path: The path to the chart (can be a directory, tgz, or repo/chart).
                      If it's a local directory, this function assumes 'chart_path' is the CWD.
            namespace: The Kubernetes namespace to install into.
            values_file: Optional path to a custom values YAML file.
            set_values: Optional dictionary of key=value pairs to set.
        Returns:
            The output from the helm install command.
        """
        command_args = ["install", release_name, "."] 
        command_args.extend(["-n", namespace])
        command_args.extend(["--create-namespace"])

        if values_file:
            command_args.extend(["-f", str(values_file)])
        if set_values:
            for key, value in set_values.items():
                command_args.extend(["--set", f"{key}={value}"])

        # If chart_path is a local directory, we execute from within it.
        # If chart_path is like 'repo/chartname', cwd should be None.
        # This logic might need refinement based on how chart_path is used.
        # For now, assuming chart_path is the directory containing the chart.
        cwd_path = Path(chart_path) if isinstance(chart_path, str) else chart_path
        if not cwd_path.is_dir():
            # This is a simplification. Real chart_path could be repo/name.
            # For now, we assume it's a local path to the chart dir.
            raise ValueError(f"chart_path '{chart_path}' must be a directory for this simplified install method.")


        try:
            output = self._run_command(command_args, cwd=cwd_path)
            if "STATUS: deployed" not in output:
                raise HelmInstallError(
                    "Helm install command output did not confirm deployment.",
                    command=[self.helm_executable] + command_args, # Pass the full command
                    output=output
                )
            print(f"Helm chart '{release_name}' deployed successfully in namespace '{namespace}'.")
            return output
        except HelmError as e: # Catch the base HelmError from _run_command
            # Re-raise as a more specific HelmInstallError if it's not already one
            if not isinstance(e, HelmInstallError):
                raise HelmInstallError(
                    f"Helm installation failed for release '{release_name}'.",
                    command=e.command,
                    return_code=e.return_code,
                    output=e.output
                ) from e
            raise # Re-raise if it's already a HelmInstallError


    def uninstall(self, release_name: str, namespace: str) -> str:
        """Uninstalls a Helm release."""
        command_args = ["uninstall", release_name, "-n", namespace]
        try:
            output = self._run_command(command_args)
            print(f"Helm release '{release_name}' uninstalled successfully from namespace '{namespace}'.")
            return output
        except HelmError as e:
            raise HelmUninstallError(
                f"Helm uninstallation failed for release '{release_name}'.",
                command=e.command,
                return_code=e.return_code,
                output=e.output
            ) from e


    def patch_values_file(self, values_file_path: str | Path, patches: Dict[str, str]):
        """
        Patches a values.yaml file with simple string replacements.
        WARNING: This modifies the file in-place. For production, consider templating
                 or using a proper YAML library for safer modifications.
        """
        values_file_path = Path(values_file_path)
        if not values_file_path.exists():
            raise FileNotFoundError(f"Values file not found at {values_file_path}")

        print(f"Patching Helm values file: {values_file_path}")
        with open(values_file_path, "r") as f:
            content = f.read()

        original_content = content
        for placeholder, replacement in patches.items():
            print(f"  Replacing '{placeholder}' with '{replacement}'")
            content = content.replace(placeholder, replacement)

        if content != original_content:
            with open(values_file_path, "w") as f:
                f.write(content)
            print("Values file patched successfully.")
        else:
            print("No changes made to values file after applying patches.")
