def get_msg_id_from_file():
    try:
        with open("message_id.txt", "r") as f:
            return f.read().strip() or None
    except FileNotFoundError:
        return None
