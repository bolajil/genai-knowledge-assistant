"""
Fisher-Yates Shuffle Implementations
------------------------------------
This script implements different variations of the Fisher-Yates shuffle algorithm:
1. Classic Fisher-Yates (original from 1938)
2. Modern Fisher-Yates (Knuth's version, unbiased)
3. Biased version (with potential issues)
4. Lazy shuffle (simplified implementation)
"""

import random
import time
from typing import List, Any, Dict, Tuple

def classic_fisher_yates(arr: List[Any]) -> List[Any]:
    """
    Original Fisher-Yates shuffle from 1938
    This implementation uses an additional array for the result
    Time complexity: O(n²)
    """
    n = len(arr)
    result = [None] * n
    input_arr = arr.copy()
    
    for i in range(n):
        # Choose a random index from the remaining elements
        j = random.randint(0, len(input_arr) - 1)
        # Add the chosen element to the result
        result[i] = input_arr[j]
        # Remove the chosen element from the input array
        input_arr.pop(j)
    
    return result

def modern_fisher_yates(arr: List[Any]) -> List[Any]:
    """
    Modern Fisher-Yates shuffle (Knuth's algorithm)
    This is an in-place implementation, properly unbiased
    Time complexity: O(n)
    """
    n = len(arr)
    result = arr.copy()
    
    for i in range(n-1, 0, -1):
        # Choose a random index from 0 to i
        j = random.randint(0, i)
        # Swap elements at indices i and j
        result[i], result[j] = result[j], result[i]
    
    return result

def biased_shuffle(arr: List[Any]) -> List[Any]:
    """
    A biased shuffle that doesn't provide uniform distribution
    This algorithm generates all possible permutations with different probabilities
    Don't use this in production code!
    """
    n = len(arr)
    result = arr.copy()
    
    for i in range(n):
        # Incorrectly choose a random index from the entire array
        j = random.randint(0, n-1)
        # Swap elements at indices i and j
        result[i], result[j] = result[j], result[i]
    
    return result

def lazy_shuffle(arr: List[Any]) -> List[Any]:
    """
    A very simple but correct implementation using Python's built-in random.shuffle
    This uses the Fisher-Yates algorithm internally in Python's implementation
    """
    result = arr.copy()
    random.shuffle(result)
    return result

def count_permutations(shuffle_func, arr, iterations=10000):
    """
    Counts the occurrences of each permutation when shuffling
    """
    permutation_counts = {}
    
    for _ in range(iterations):
        shuffled = shuffle_func(arr)
        perm_tuple = tuple(shuffled)
        if perm_tuple in permutation_counts:
            permutation_counts[perm_tuple] += 1
        else:
            permutation_counts[perm_tuple] = 1
    
    return permutation_counts

def benchmark_shuffles():
    """
    Benchmark and compare the different shuffle implementations
    """
    # Define test arrays
    small_arr = list(range(3))
    medium_arr = list(range(10))
    large_arr = list(range(1000))
    
    # Define implementations to test
    implementations = [
        ("Classic Fisher-Yates", classic_fisher_yates),
        ("Modern Fisher-Yates", modern_fisher_yates),
        ("Biased Shuffle", biased_shuffle),
        ("Lazy Shuffle", lazy_shuffle)
    ]
    
    # Benchmark execution time
    print("\n===== Execution Time Benchmark =====")
    for name, func in implementations:
        start = time.time()
        for _ in range(100):
            func(large_arr)
        end = time.time()
        print(f"{name}: {end - start:.6f} seconds")
    
    # Test for uniformity (only for small array to keep permutations manageable)
    print("\n===== Uniformity Test (Permutations of [0, 1, 2]) =====")
    iterations = 50000
    expected = iterations / 6  # 6 possible permutations for array of length 3
    
    for name, func in implementations:
        perm_counts = count_permutations(func, small_arr, iterations)
        print(f"\n{name}:")
        print(f"Number of unique permutations: {len(perm_counts)}")
        
        # Calculate chi-square statistic
        chi_square = sum((count - expected) ** 2 / expected for count in perm_counts.values())
        print(f"Chi-square statistic: {chi_square:.2f}")
        
        # Print distribution of permutations
        print("Permutation counts:")
        for perm, count in sorted(perm_counts.items()):
            print(f"  {perm}: {count} ({count/iterations*100:.2f}%)")
    
    print("\nVisualization skipped - install matplotlib for visual comparison")

if __name__ == "__main__":
    # Example usage
    original = [1, 2, 3, 4, 5]
    
    print("Original array:", original)
    print("Classic Fisher-Yates:", classic_fisher_yates(original))
    print("Modern Fisher-Yates:", modern_fisher_yates(original))
    print("Biased Shuffle:", biased_shuffle(original))
    print("Lazy Shuffle:", lazy_shuffle(original))
    
    # Run benchmarks and uniformity tests
    benchmark_shuffles()
