from datetime import datetime, timedelta

def generate_time_slots(opening_hours, break_hours, interval_minutes):
    """ Will generate a list of [[start_time, end_time]], given opening hours, break hours and interval minutes.

    If the difference of time is less than the interval time, it will be ignored.
    for eg: if the opening hours is from 9 to 10 am, interval is 30 mins, and break hours is 9:30-9:45, then
            9:45-10:00 will be ignored as its less than interval time.

    Args:
        opening_hours (_type_): _description_
        break_hours (_type_): _description_
        interval_minutes (_type_): _description_
    """
    def str_to_time(time_str):
        return datetime.strptime(time_str, "%H:%M")

    def time_to_str(time_obj):
        return time_obj.strftime("%H:%M")

    # Step 1: Convert all times to datetime objects
    opening_start, opening_end = map(str_to_time, opening_hours[0])  # Corrected to handle list of lists
    break_ranges = [(str_to_time(start), str_to_time(end)) for start, end in break_hours]

    # Step 2: Calculate usable time blocks
    usable_blocks = []
    current_start = opening_start

    for break_start, break_end in sorted(break_ranges):
        if current_start < break_start:
            usable_blocks.append((current_start, break_start))
        current_start = max(current_start, break_end)
    
    if current_start < opening_end:
        usable_blocks.append((current_start, opening_end))

    # Step 3: Generate slots for each usable block
    slots = []
    for block_start, block_end in usable_blocks:
        current_time = block_start
        while current_time + timedelta(minutes=interval_minutes) <= block_end:
            slot_end_time = current_time + timedelta(minutes=interval_minutes)
            slots.append([time_to_str(current_time), time_to_str(slot_end_time)])
            current_time = slot_end_time

    return slots