class ResultFiles:
    """
    Manages standard output filenames for a given SUT.
    """
    def __init__(self, sut: str):
        if not sut:
            raise ValueError("SUT name cannot be empty.")
        self.sut = sut

    @property
    def stats_csv(self) -> str:
        return f"{self.sut}_stats.csv"

    @property
    def failures_csv(self) -> str:
        return f"{self.sut}_failures.csv"

    @property
    def stats_history_csv(self) -> str:
        return f"{self.sut}_stats_history.csv"
    
    @property
    def report(self) -> str:
        return f"{self.sut}_report.html"