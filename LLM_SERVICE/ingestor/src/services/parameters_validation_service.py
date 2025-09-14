from __future__ import annotations


class ParametersValidationService:
    @staticmethod
    def validate_chunking_parameters(
        chars_min: int,
        chars_target: int,
        chars_max: int,
        chars_hard_max: int,
        overlap_chars: int
    ) -> None:
        """
        Validates chunking parameters to ensure they form a rational configuration.
        
        Ensures proper ordering: chars_min < chars_target < chars_max < chars_hard_max
        Validates reasonable ranges and gaps between parameters to prevent:
        - Overlapping chunks that exceed minimum chunk size
        - Insufficient buffer zones between size thresholds
        - Parameters that would cause inefficient chunking behavior
        
        Args:
            chars_min: Minimum characters per chunk (>= 50)
            chars_target: Target characters per chunk (must exceed chars_min by >= 50)
            chars_max: Maximum characters per chunk (must exceed chars_target by >= 50)
            chars_hard_max: Hard limit for chunk size (must exceed chars_max by >= 100, <= 2000)
            overlap_chars: Character overlap between chunks (0-200, must be < chars_min)
            
        Raises:
            ValueError: If any parameter violates validation rules
        """
        if chars_min < 50:
            raise ValueError(f"chars_min must be >= 50, got {chars_min}")
        
        if chars_target <= chars_min:
            raise ValueError(f"chars_target ({chars_target}) must be > chars_min ({chars_min})")
        
        if chars_max <= chars_target:
            raise ValueError(f"chars_max ({chars_max}) must be > chars_target ({chars_target})")
        
        if chars_hard_max <= chars_max:
            raise ValueError(f"chars_hard_max ({chars_hard_max}) must be > chars_max ({chars_max})")
        
        if chars_hard_max > 2000:
            raise ValueError(f"chars_hard_max must be <= 2000, got {chars_hard_max}")
        
        if overlap_chars < 0:
            raise ValueError(f"overlap_chars must be >= 0, got {overlap_chars}")
        
        if overlap_chars > 200:
            raise ValueError(f"overlap_chars must be <= 200, got {overlap_chars}")
        
        if overlap_chars >= chars_min:
            raise ValueError(f"overlap_chars ({overlap_chars}) must be < chars_min ({chars_min})")
        
        if chars_target - chars_min < 50:
            raise ValueError(f"chars_target - chars_min must be >= 50, got {chars_target - chars_min}")
        
        if chars_max - chars_target < 50:
            raise ValueError(f"chars_max - chars_target must be >= 50, got {chars_max - chars_target}")
        
        if chars_hard_max - chars_max < 100:
            raise ValueError(f"chars_hard_max - chars_max must be >= 100, got {chars_hard_max - chars_max}")



            