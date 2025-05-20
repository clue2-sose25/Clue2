class ResultFiles:
    """
    Manages standard output filenames for a given SUT.
    """
    def __init__(self, sut_name: str):
        if not sut_name:
            raise ValueError("SUT name cannot be empty.")
        self.sut_name = sut_name

    @property
    def stats_csv(self) -> str:
        return f"{self.sut_name}_stats.csv"

    @property
    def failures_csv(self) -> str:
        return f"{self.sut_name}_failures.csv"

    @property
    def stats_history_csv(self) -> str:
        return f"{self.sut_name}_stats_history.csv"
    
    @property
    def report(self) -> str:
        return f"{self.sut_name}_report.html"