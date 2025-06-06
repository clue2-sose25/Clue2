class HelmReplacement():
    """
    A single object representing a helm replacement. Used to replace strings in SUT's values.yaml files.
    """
    # The old value to replace
    old_value: str
    # The new value to use
    new_value: str
    # Sub-path for replacement
    path: str = "."

    def __str__(self) -> str:
        pathString = "in whole file" if self.path == "." else f"for subpaths {self.path}"
        return f"Replacement of {self.old_value} with {self.new_value} {pathString}"