from datetime import datetime, timedelta
from main.appointments.utils import generate_time_slots

def test_generate_time_slots_simple_opening_no_breaks():
    """Test with simple opening hours and no breaks."""
    opening_hours = [["09:00", "12:00"]]  # Correct format
    break_hours = []
    interval_minutes = 30

    slots = generate_time_slots(opening_hours, break_hours, interval_minutes)
    assert slots == [
        ["09:00", "09:30"], ["09:30", "10:00"], ["10:00", "10:30"],
        ["10:30", "11:00"], ["11:00", "11:30"], ["11:30", "12:00"]
    ]

def test_generate_time_slots_with_break():
    """Test with a single break."""
    opening_hours = [["09:00", "17:00"]]  # Correct format
    break_hours = [["15:00", "15:30"]]   # Correct format
    interval_minutes = 15

    slots = generate_time_slots(opening_hours, break_hours, interval_minutes)
    assert slots == [
        ["09:00", "09:15"], ["09:15", "09:30"], ["09:30", "09:45"], ["09:45", "10:00"],
        ["10:00", "10:15"], ["10:15", "10:30"], ["10:30", "10:45"], ["10:45", "11:00"],
        ["11:00", "11:15"], ["11:15", "11:30"], ["11:30", "11:45"], ["11:45", "12:00"],
        ["12:00", "12:15"], ["12:15", "12:30"], ["12:30", "12:45"], ["12:45", "13:00"],
        ["13:00", "13:15"], ["13:15", "13:30"], ["13:30", "13:45"], ["13:45", "14:00"],
        ["14:00", "14:15"], ["14:15", "14:30"], ["14:30", "14:45"], ["14:45", "15:00"],
        ["15:30", "15:45"], ["15:45", "16:00"], ["16:00", "16:15"], ["16:15", "16:30"],
        ["16:30", "16:45"], ["16:45", "17:00"]
    ]

def test_generate_time_slots_break_overlapping_opening():
    """Test when a break fully overlaps a part of the opening range."""
    opening_hours = [["09:00", "12:00"]]  # Correct format
    break_hours = [["09:30", "10:30"]]   # Correct format
    interval_minutes = 30

    slots = generate_time_slots(opening_hours, break_hours, interval_minutes)
    assert slots == [
        ["09:00", "09:30"], ["10:30", "11:00"], ["11:00", "11:30"], ["11:30", "12:00"]
    ]

def test_generate_time_slots_no_valid_slots():
    """Test when no valid time slots are available due to breaks."""
    opening_hours = [["09:00", "10:00"]]  # Correct format
    break_hours = [["09:00", "10:00"]]   # Entire range is a break
    interval_minutes = 15

    slots = generate_time_slots(opening_hours, break_hours, interval_minutes)
    assert slots == []

def test_generate_time_slots_partial_interval_fit():
    """Test when the last interval does not fully fit within opening hours."""
    opening_hours = [["10:00", "10:40"]]  # Correct format
    break_hours = []
    interval_minutes = 15

    slots = generate_time_slots(opening_hours, break_hours, interval_minutes)
    assert slots == [["10:00", "10:15"], ["10:15", "10:30"]]

def test_generate_time_slots_break_with_small_intervals():
    """Test with small intervals and overlapping breaks."""
    opening_hours = [["09:00", "12:00"]]  # Correct format
    break_hours = [["09:15", "09:45"], ["11:00", "11:15"]]  # Correct format
    interval_minutes = 15

    slots = generate_time_slots(opening_hours, break_hours, interval_minutes)
    assert slots == [
        ["09:00", "09:15"], ["09:45", "10:00"], ["10:00", "10:15"], ["10:15", "10:30"],
        ["10:30", "10:45"], ["10:45", "11:00"], ["11:15", "11:30"], ["11:30", "11:45"],
        ["11:45", "12:00"]
    ]

def test_generate_time_slots_complex_case():
    """Test a complex case with irregular breaks."""
    opening_hours = [["09:10", "17:10"]]  # Correct format
    break_hours = [["09:40", "10:15"], ["11:45", "12:15"], ["14:00", "14:30"]]  # Correct format
    interval_minutes = 25

    slots = generate_time_slots(opening_hours, break_hours, interval_minutes)

    # Adjust the expected slots to match the correct sequence considering breaks
    expected_slots = [
        ["09:10", "09:35"], ["10:15", "10:40"], ["10:40", "11:05"], ["11:05", "11:30"],
        ["12:15", "12:40"], ["12:40", "13:05"], ["13:05", "13:30"], ["13:30", "13:55"],
        ["14:30", "14:55"], ["14:55", "15:20"], ["15:20", "15:45"], ["15:45", "16:10"],
        ["16:10", "16:35"], ['16:35', '17:00']
    ]

    assert slots == expected_slots, f"Expected {expected_slots}, but got {slots}"


def test_generate_time_slots_multiple_breaks_overlapping_entire_day():
    """Test when multiple breaks span across the entire day, leaving only a small window for valid slots."""
    opening_hours = [["09:00", "17:00"]]
    break_hours = [["09:15", "12:00"], ["12:30", "14:00"], ["15:00", "17:00"]]  # Breaks overlap with most of the day
    interval_minutes = 30

    slots = generate_time_slots(opening_hours, break_hours, interval_minutes)
    assert slots == [['12:00', '12:30'], ['14:00', '14:30'], ['14:30', '15:00']], f"Expected [['12:00', '12:30']], but got {slots}"

def test_generate_time_slots_intervals_dont_fit_evenly():
    """Test when the intervals don't perfectly fit within the opening hours."""
    opening_hours = [["09:00", "17:00"]]
    break_hours = []
    interval_minutes = 70  # Interval of 70 minutes to test uneven fitting

    slots = generate_time_slots(opening_hours, break_hours, interval_minutes)
    assert slots == [
        ["09:00", "10:10"], ["10:10", "11:20"], ["11:20", "12:30"], ["12:30", "13:40"],
        ["13:40", "14:50"], ["14:50", "16:00"]
    ], f"Expected a list of slots with 70-minute intervals, but got {slots}"

def test_generate_time_slots_no_valid_slots_due_to_breaks():
    """Test when breaks completely overlap the opening hours, leaving no valid slots."""
    opening_hours = [["09:00", "17:00"]]
    break_hours = [["09:00", "17:00"]]  # Entire range is a break
    interval_minutes = 30

    slots = generate_time_slots(opening_hours, break_hours, interval_minutes)
    assert slots == [], f"Expected an empty list, but got {slots}"

def test_generate_time_slots_multiple_short_breaks():
    """Test multiple short breaks scattered throughout the day."""
    opening_hours = [["09:00", "17:00"]]
    break_hours = [["10:00", "10:15"], ["12:00", "12:15"], ["14:30", "14:45"], ["16:00", "16:15"]]
    interval_minutes = 30

    slots = generate_time_slots(opening_hours, break_hours, interval_minutes)
    assert slots == [
        ["09:00", "09:30"], ["09:30", "10:00"], ["10:15", "10:45"], ["10:45", "11:15"],
        ["11:15", "11:45"], ["12:15", "12:45"], ["12:45", "13:15"],
        ["13:15", "13:45"], ["13:45", "14:15"], ["14:45", "15:15"],
        ["15:15", "15:45"], ["16:15", "16:45"]
    ], f"Expected a list of valid slots with breaks, but got {slots}"

def test_generate_time_slots_tight_time_range_small_intervals():
    """Test with a very tight time range and small intervals."""
    opening_hours = [["09:00", "09:30"]]  # Only half an hour
    break_hours = []
    interval_minutes = 5  # Small intervals

    slots = generate_time_slots(opening_hours, break_hours, interval_minutes)
    assert slots == [
        ["09:00", "09:05"], ["09:05", "09:10"], ["09:10", "09:15"], ["09:15", "09:20"],
        ["09:20", "09:25"], ["09:25", "09:30"]
    ], f"Expected a list of 5-minute intervals, but got {slots}"


def test_generate_time_slots_two_minute_intervals():
    """Test with very small 2-minute intervals."""
    opening_hours = [["09:00", "09:10"]]  # Only 10 minutes
    break_hours = [["09:02", "09:04"]]  # Small break in the middle
    interval_minutes = 2

    slots = generate_time_slots(opening_hours, break_hours, interval_minutes)
    assert slots == [
        ["09:00", "09:02"], ["09:04", "09:06"], ["09:06", "09:08"], ["09:08", "09:10"]
    ], f"Expected slots with 2-minute intervals around the break, but got {slots}"


def test_generate_time_slots_two_minute_intervals_with_overlap():
    """Test 2-minute intervals with overlapping breaks."""
    opening_hours = [["09:00", "10:00"]]
    break_hours = [["09:10", "09:20"], ["09:15", "09:25"], ["09:40", "09:50"]]  # Overlapping breaks
    interval_minutes = 2

    slots = generate_time_slots(opening_hours, break_hours, interval_minutes)
    assert slots == [
        ["09:00", "09:02"], ["09:02", "09:04"], ["09:04", "09:06"], ["09:06", "09:08"],
        ["09:08", "09:10"], ["09:25", "09:27"], ["09:27", "09:29"], ["09:29", "09:31"],
        ["09:31", "09:33"], ["09:33", "09:35"], ["09:35", "09:37"], ["09:37", "09:39"],
        ["09:50", "09:52"], ["09:52", "09:54"], ["09:54", "09:56"],
        ["09:56", "09:58"], ["09:58", "10:00"]
    ], f"Expected slots with 2-minute intervals accounting for overlapping breaks, but got {slots}"

def test_generate_time_slots_mixed_granular_and_large_intervals():
    """Test with mixed 2-minute and large 60-minute intervals in a complex opening."""
    opening_hours = [["09:00", "18:00"]]
    break_hours = [["11:00", "13:00"]]  # Large break in the middle
    interval_minutes = 2

    # Generate 2-minute intervals before the break
    slots = generate_time_slots(opening_hours, break_hours, interval_minutes)
    expected_slots = []
    current_time = datetime.strptime("09:00", "%H:%M")
    end_time = datetime.strptime("18:00", "%H:%M")

    while current_time < end_time:
        next_time = current_time + timedelta(minutes=2)
        if not any(
            datetime.strptime(start, "%H:%M") <= current_time < datetime.strptime(end, "%H:%M")
            for start, end in break_hours
        ):
            expected_slots.append([current_time.strftime("%H:%M"), next_time.strftime("%H:%M")])
        current_time = next_time

    assert slots == expected_slots, f"Expected mixed granular slots, but got {slots}"

def test_generate_time_slots_unusual_start_time():
    """Test 12-minute intervals starting at an unusual time."""
    opening_hours = [["09:07", "10:43"]]  # Unusual start time and end time
    break_hours = [["09:31", "09:55"], ["10:19", "10:27"]]  # Irregular breaks
    interval_minutes = 12

    slots = generate_time_slots(opening_hours, break_hours, interval_minutes)
    
    expected_slots = [
        ["09:07", "09:19"], ["09:19", "09:31"],  # Before first break
        ["09:55", "10:07"], ["10:07", "10:19"],  # After first break, before second
        ["10:27", "10:39"]  # After second break
    ]

    assert slots == expected_slots, f"Expected {expected_slots}, but got {slots}"
