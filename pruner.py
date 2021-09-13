from xml.etree import ElementTree
from datetime import datetime, timedelta

DATETIME_FORMAT = "%m/%d/%Y %H:%M:%S"

def get_pruned_attempt_ids_and_times(attempt_history, min_threshold=None, max_threshold=None) -> dict:
    attempts_to_prune = {
        "min": [],
        "max": [],
    }
    for attempt in attempt_history:
        start_time = datetime.strptime(attempt.attrib["started"], DATETIME_FORMAT)
        end_time = datetime.strptime(attempt.attrib["ended"], DATETIME_FORMAT)
        if min_threshold and end_time - start_time < timedelta(seconds=int(min_threshold)):
            attempts_to_prune["min"].append((attempt.attrib["id"], end_time-start_time))
        elif max_threshold and end_time - start_time > timedelta(seconds=int(max_threshold)):
            attempts_to_prune["max"].append((attempt.attrib["id"], end_time-start_time))

    return attempts_to_prune

def wait_and_exit(reason=None):
    if reason:
        print(f"{reason}\n")
    input("Press Enter to close script...")
    exit()

print("""
================
Livesplit Pruner
================
""")

splits_file = input("Input the splits filename to prune: ")
try:
    lss_tree = ElementTree.parse(splits_file)
    lss_root = lss_tree.getroot()
except FileNotFoundError:
    wait_and_exit("The specified splits file does not exist.")

min_threshold = input("Input the minimum length run to keep in seconds (Leave blank for no minimum): ")
max_threshold = input("Input the maximum length run to keep in seconds (Leave blank for no maximum): ")

attempt_history = lss_root.find("AttemptHistory")
try:
    trash_runs = get_pruned_attempt_ids_and_times(attempt_history, min_threshold, max_threshold)
except Exception as exc:
    wait_and_exit(exc)

trash_ids = [attempt_id for attempt_id, delta in trash_runs["min"]+trash_runs["max"]]
if len(trash_runs["min"]) + len(trash_runs["max"]) == 0:
    wait_and_exit("No runs in this file are outside the specified range.")

if len(trash_runs["min"]) + len(trash_runs["max"]) == len(attempt_history.findall("Attempt")):
    wait_and_exit("Every run in this file is outside the specified range.")

if trash_runs["min"]:
    print("\nThe following attempts are shorter than the specified minimum:")
    for attempt_id, delta in trash_runs["min"]:
        print(f"#{attempt_id}: {delta.seconds}s ")

if trash_runs["max"]:
    print("\nThe following attempts are longer than the specified minimum:")
    for attempt_id, delta in trash_runs["max"]:
        print(f"#{attempt_id}: {delta.seconds}s ")

confirmation = input("\nWould you like to prune all of these attempts? (y/n): ")
if "y" in confirmation.lower():
    print(f"\nDeleting attempts: {', '.join(trash_ids)}.\n")
else:
    wait_and_exit("\nNo changes have been made to your file.")

num_deleted = 0
new_attempt_mappings = {}
for attempt in attempt_history.findall("Attempt"):
    attempt_id = str(attempt.attrib["id"])
    if attempt_id in trash_ids:
        attempt_history.remove(attempt)
        num_deleted += 1
        continue

    if num_deleted > 0:
        new_attempt_id = str(int(attempt_id) - num_deleted)
        new_attempt_mappings[attempt_id] = new_attempt_id
        attempt.attrib["id"] = new_attempt_id

print(new_attempt_mappings)
lss_root.find("AttemptCount").text = str(len(attempt_history))

segments = lss_root.find("Segments").findall("Segment")
for segment in segments:
    segment_history = segment.find("SegmentHistory")
    for segment_time in segment_history.findall("Time"):
        segment_time_id = str(segment_time.attrib["id"])
        if segment_time_id in new_attempt_mappings:
            segment_time.attrib["id"] = new_attempt_mappings[segment_time_id]
        elif segment_time_id in trash_ids:
            segment_history.remove(segment_time)


lss_tree.write(f"pruned_{splits_file}", encoding="UTF-8", xml_declaration=True)

wait_and_exit(f"{len(trash_runs['min'])+len(trash_runs['max'])} attempts have been pruned from your splits.")

