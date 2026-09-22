current_group = None


def set_group(group: str):
    global current_group
    current_group = group


def get_group():
    return current_group