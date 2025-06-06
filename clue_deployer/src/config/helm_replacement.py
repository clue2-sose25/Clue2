from pydantic import BaseModel, Field

from clue_deployer.src.scaling_experiment_setting import ScalingExperimentSetting

class Condition(BaseModel):
    """
    An object for a single replacement condition
    """
    autoscaling: str
    autoscaling_type: str

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
    conditions: list[Condition] = Field(default_factory=list)
    
    def should_apply(self, autoscaling: ScalingExperimentSetting) -> bool:
        """
        Check if this replacement should be applied based on current conditions
        """
        if not self.conditions:
            # No conditions means always apply
            return True
        
        # Check if all conditions are met
        for condition in self.conditions:
            # Check for autoscaling condition without type
            if condition.autoscaling and (not condition.autoscaling_type) and autoscaling:
                return True
            elif condition.autoscaling and (condition.autoscaling_type == autoscaling):
                return True
        # All conditions failed
        return False
    
    def __str__(self) -> str:
        return f"{self.old_value} with {self.new_value} with conditions {self.conditions}"