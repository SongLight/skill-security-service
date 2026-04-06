#!/usr/bin/env python3
"""
Clean skill - No security issues, for testing false positives.
"""


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


def format_result(value: float, precision: int = 2) -> str:
    """Format a numeric result with specified precision."""
    return f"{value:.{precision}f}"


def calculate_statistics(numbers: list) -> dict:
    """Calculate basic statistics for a list of numbers."""
    if not numbers:
        return {}
    
    total = sum(numbers)
    count = len(numbers)
    average = total / count
    
    sorted_nums = sorted(numbers)
    median = sorted_nums[count // 2] if count % 2 == 1 else (
        sorted_nums[count // 2 - 1] + sorted_nums[count // 2]
    ) / 2
    
    return {
        "sum": total,
        "count": count,
        "average": average,
        "median": median,
        "min": min(numbers),
        "max": max(numbers),
    }


if __name__ == "__main__":
    # Test the functions
    print("Testing clean skill...")
    print(f"5 + 3 = {add(5, 3)}")
    print(f"5 * 3 = {multiply(5, 3)}")
    print(f"Formatted: {format_result(3.14159, 2)}")
    
    stats = calculate_statistics([1, 2, 3, 4, 5])
    print(f"Statistics: {stats}")
