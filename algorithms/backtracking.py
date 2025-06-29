import hashlib
import random

# --- Helper Functions ---
def is_prime(n):
    if n < 2: return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0: return False
    return True

def is_even(n): return n % 2 == 0
def is_odd(n): return n % 2 != 0

def get_candidates_for_pos(pos, current_path, clues, length):
    candidates = [c for c in list(range(10)) if c not in current_path]
    for clue in clues:
        if clue == [-1, -1]:
            candidates = [c for c in candidates if is_prime(c)]
        elif len(clue) == 2:
            clue_pos, prop = clue
            if clue_pos == pos + 1:
                if prop == 0: candidates = [c for c in candidates if is_even(c)]
                elif prop == 1: candidates = [c for c in candidates if is_odd(c)]
        elif len(clue) == length:
            fixed_digit = clue[pos]
            if fixed_digit != -1:
                return [fixed_digit] if fixed_digit in candidates else []
    return candidates

# --- Solver Implementations for Different Methods ---

def _solve_method_1(clues, target_hash, length, salt, tries_counter):
    """Method 1: Optimized backtracking with pre-filtering candidates."""
    path = []
    def backtrack():
        current_pos = len(path)
        if current_pos == length:
            tries_counter["count"] += 1
            password_str = "".join(map(str, path))
            yield list(path), f"Hashing '{password_str}'...", tries_counter["count"]
            password_bytes = password_str.encode('utf-8')
            current_hash = hashlib.sha256(salt + password_bytes).hexdigest()
            if current_hash == target_hash:
                yield list(path), f"Success! Password: {password_str}", tries_counter["count"]
                return True
            return False
        
        candidates = get_candidates_for_pos(current_pos, path, clues, length)
        for num in candidates:
            path.append(num)
            yield list(path), f"Trying: {path}", tries_counter["count"]
            if (yield from backtrack()): return True
            path.pop()
        return False
    yield from backtrack()

def _solve_method_2(clues, target_hash, length, salt, tries_counter, randomize=False):
    """Method 2 & 3: Naive backtracking, trying all digits from 0-9."""
    path = []
    def is_valid(num, pos):
        if num in path: return False
        for clue in clues:
            if clue == [-1, -1]:
                if not is_prime(num): return False
            elif len(clue) == 2:
                clue_pos, prop = clue
                if clue_pos == pos + 1:
                    if prop == 0 and not is_even(num): return False
                    if prop == 1 and not is_odd(num): return False
            elif len(clue) == length:
                if clue[pos] != -1 and num != clue[pos]: return False
        return True

    def backtrack():
        current_pos = len(path)
        if current_pos == length:
            tries_counter["count"] += 1
            password_str = "".join(map(str, path))
            yield list(path), f"Hashing '{password_str}'...", tries_counter["count"]
            password_bytes = password_str.encode('utf-8')
            current_hash = hashlib.sha256(salt + password_bytes).hexdigest()
            if current_hash == target_hash:
                yield list(path), f"Success! Password: {password_str}", tries_counter["count"]
                return True
            return False

        candidate_digits = list(range(10))
        if randomize:
            random.shuffle(candidate_digits)
            
        for num in candidate_digits:
            yield list(path), f"Trying: {path}", tries_counter["count"]
            if is_valid(num, current_pos):
                path.append(num)
                if (yield from backtrack()): return True
                path.pop()
        return False
    yield from backtrack()

# --- Main Entry Point ---
def solve_puzzle_by_method(method, clues, target_hash, length, salt, tries_counter):
    """
    Selects a backtracking method to solve the puzzle.
    Now yields (path, status, tries_count).
    """
    if method == "method1":
        return _solve_method_1(clues, target_hash, length, salt, tries_counter)
    elif method == "method2":
        return _solve_method_2(clues, target_hash, length, salt, tries_counter, randomize=False)
    elif method == "method3":
        return _solve_method_2(clues, target_hash, length, salt, tries_counter, randomize=True)
    else:
        # Fallback to the best method
        return _solve_method_1(clues, target_hash, length, salt, tries_counter)

