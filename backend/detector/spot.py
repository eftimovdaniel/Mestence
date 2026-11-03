TOTAL_SPOTS = 60

def free_spots(occupied: int, total: int = TOTAL_SPOTS) -> int:
    if occupied < 0 :
        occupied = 0
    if occupied > total:
        return 0
    return total - occupied