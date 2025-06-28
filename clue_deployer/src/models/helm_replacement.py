from pydantic import BaseModel
from clue_deployer.src.models.scaling_experiment_setting import ScalingExperimentSetting


class Conditions(BaseModel):
    """
    An object for a single replacement condition
    """
    autoscaling: bool = False
    autoscaling_type: str = ""

    def __str__(self) -> str:
        return f"autoscaling {self.autoscaling} (type {self.autoscaling_type})"


class HelmReplacement(BaseModel):
    """
    A single object representing a helm replacement. Used to replace strings in SUT's values.yaml files.
    """
    # The old value to replace
    old_value: str
    # The new value to use
    new_value: str
    # Conditions
    conditions: Conditions = None
    
    def should_apply(self, autoscaling: ScalingExperimentSetting) -> bool:
        """
        Check if this replacement should be applied based on current conditions
        """
        if not self.conditions:
            # No conditions means always apply
            return True
        
        # Check for autoscaling condition without type
        if self.conditions.autoscaling and (not self.conditions.autoscaling_type) and autoscaling:
            return True
        elif self.conditions.autoscaling and (self.conditions.autoscaling_type == autoscaling):
            return True
        # All conditions failed
        return False
    
    def __str__(self) -> str:
        return f"{self.old_value} with {self.new_value} with conditions {self.conditions}"