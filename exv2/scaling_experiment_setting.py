from enum import Enum


class ScalingExperimentSetting(Enum):
    MEMORYBOUND = 1
    CPUBOUND = 2
    BOTH = 3

    def __str__(self) -> str:
        if self == ScalingExperimentSetting.MEMORYBOUND:
            return "mem"
        elif self == ScalingExperimentSetting.CPUBOUND:
            return "cpu"
        elif self == ScalingExperimentSetting.BOTH:
            return "full"
        else:
            return "none"


