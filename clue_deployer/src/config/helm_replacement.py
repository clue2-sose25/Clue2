from pydantic import BaseModel, Field

class Condition(BaseModel):
    """
    An object for a single replacement condition
    """
    autoscaling: bool = False

    def __str__(self) -> str:
        return f"autoscaling {self.autoscaling}"


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
    
    def should_apply(self, autoscaling: bool = False) -> bool:
        """
        Check if this replacement should be applied based on current conditions
        """
        if not self.conditions:
            # No conditions means always apply
            return True
        
        # Check if any condition is met
        for condition in self.conditions:
            if condition.autoscaling and autoscaling:
                return True
        
        return False
    
    def __str__(self) -> str:
        return f"{self.old_value} with {self.new_value} with conditions {self.conditions}"