
import time

def is_prime(n):
    """检查一个数字是否为素数"""
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

def solve_prime_puzzle():
    """
    【已实现】使用回溯法解决“3位不重复素数密码锁”问题。
    这是一个生成器函数，它会逐步(yield)返回其搜索过程，以便在UI上进行可视化。
    
    输出 (yield):
        (list, str): 一个元组，包含当前的密码尝试(current_path)和状态信息(status_text)。
    """
    
    # 规则：密码是3位，每位都是一位数（0-9）中的素数，且数字不能重复。
    # 一位数的素数有: 2, 3, 5, 7
    candidates = [2, 3, 5, 7]
    path = []
    
    def backtrack(start_index):
        # 状态文本：显示正在尝试的路径
        status_text = f"Trying: {path}"
        yield list(path), status_text
        time.sleep(0.1) # 减慢速度以便观察

        # 找到一个完整的3位密码
        if len(path) == 3:
            status_text = f"Found Solution: {path}"
            yield list(path), status_text
            # 返回True表示找到了一个解，可以停止搜索
            return True

        # 从候选数字中选择
        for i in range(len(candidates)):
            num = candidates[i]
            if num in path:
                continue # 数字已在路径中，跳过

            # 做出选择
            path.append(num)
            
            # 向下探索
            # 通过 `yield from` 将子生成器的所有产出传递出去
            if (yield from backtrack(i + 1)):
                return True # 如果子问题找到了解，直接返回

            # 撤销选择 (回溯)
            status_text = f"Backtracking from {path}"
            path.pop()
            yield list(path), status_text
            time.sleep(0.1)

    # 启动回溯过程
    yield from backtrack(0)
