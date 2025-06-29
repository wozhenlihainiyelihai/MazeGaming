import hashlib
import random

# 工具函数
def is_prime(n):
    """判断是否为质数"""
    if n < 2: return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0: return False
    return True

def is_even(n): return n % 2 == 0
def is_odd(n): return n % 2 != 0

def get_candidates_for_pos(pos, current_path, clues, length):
    """
    根据当前位置、已有路径与线索，筛选当前可选数字
    - pos: 当前数字在密码中的位置
    - current_path: 已构建的部分路径
    - clues: 所有线索
    - length: 密码总长度
    """
    # 初始候选：所有未用过的数字
    candidates = [c for c in range(10) if c not in current_path]

    for clue in clues:
        if clue == [-1, -1]:
            # 要求所有数字都是质数
            candidates = [c for c in candidates if is_prime(c)]
        elif len(clue) == 2:
            clue_pos, prop = clue
            if clue_pos == pos + 1:
                # prop 0 表示该位置为偶数，1 表示奇数
                if prop == 0:
                    candidates = [c for c in candidates if is_even(c)]
                elif prop == 1:
                    candidates = [c for c in candidates if is_odd(c)]
        elif len(clue) == length:
            # 完整密码线索，有些位是固定数字
            fixed_digit = clue[pos]
            if fixed_digit != -1:
                return [fixed_digit] if fixed_digit in candidates else []
    return candidates

# 方法一：优化回溯（先筛选候选）
def _solve_method_1(clues, target_hash, length, salt, tries_counter):
    """方法1：预处理候选数字，使用优化的回溯搜索"""
    path = []

    def backtrack():
        current_pos = len(path)
        if current_pos == length:
            tries_counter["count"] += 1
            password_str = "".join(map(str, path))
            yield list(path), f"Hashing '{password_str}'...", tries_counter["count"]
            # 比对哈希值
            password_bytes = password_str.encode('utf-8')
            current_hash = hashlib.sha256(salt + password_bytes).hexdigest()
            if current_hash == target_hash:
                yield list(path), f"Success! Password: {password_str}", tries_counter["count"]
                return True
            return False

        # 获取当前位置的可选数字
        candidates = get_candidates_for_pos(current_pos, path, clues, length)
        for num in candidates:
            path.append(num)
            yield list(path), f"Trying: {path}", tries_counter["count"]
            if (yield from backtrack()): return True
            path.pop()
        return False

    yield from backtrack()

# 方法二/三：暴力回溯（method2 固定顺序，method3 随机打乱）
def _solve_method_2(clues, target_hash, length, salt, tries_counter, randomize=False):
    """方法2/3：尝试所有0-9数字，逐个判断是否合法"""
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

# 入口函数
def solve_puzzle_by_method(method, clues, target_hash, length, salt, tries_counter):
    """
    根据指定方法启动密码破解流程
    返回生成器，逐步输出路径、状态和尝试次数
    """
    if method == "method1":
        return _solve_method_1(clues, target_hash, length, salt, tries_counter)
    elif method == "method2":
        return _solve_method_2(clues, target_hash, length, salt, tries_counter, randomize=False)
    elif method == "method3":
        return _solve_method_2(clues, target_hash, length, salt, tries_counter, randomize=True)
    else:
        # 默认使用 method1
        return _solve_method_1(clues, target_hash, length, salt, tries_counter)
