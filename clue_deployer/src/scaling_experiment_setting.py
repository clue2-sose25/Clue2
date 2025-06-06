from enum import StrEnum

class ScalingExperimentSetting(StrEnum):
    MEMORYBOUND = "mem"
    CPUBOUND = "cpu"
    BOTH = "full"