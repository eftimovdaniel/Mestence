TOTAL_SPOTS = 60

def free_spots(occupied: int) -> int:
    if occupied < 0:
        occupied = 0
    if occupied > TOTAL_SPOTS:
        return 0
    return TOTAL_SPOTS - occupied