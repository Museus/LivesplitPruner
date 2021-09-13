from xml.etree import ElementTree
from datetime import datetime, timedelta

DATETIME_FORMAT = "%m/%d/%Y %H:%M:%S"

def get_pruned_attempt_ids_and_times(attempt_history, threshold) -> tuple:
    attempts_to_prune = []
    for attempt in attempt_history:
        start_time = datetime.strptime(attempt.attrib["started"], DATETIME_FORMAT)
        end_time = datetime.strptime(attempt.attrib["ended"], DATETIME_FORMAT)
        if end_time - start_time < timedelta(seconds=int(threshold)):
            attempts_to_prune.append((attempt.attrib["id"], end_time-start_time))

    return attempts_to_prune

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
    print("The specified splits file does not exist.\n")
    exit()

threshold = input("Input the minimum length run to keep (in seconds): ")
print()

attempt_history = lss_root.find("AttemptHistory")
trash_runs = get_pruned_attempt_ids_and_times(attempt_history, threshold)
trash_ids = [attempt_id for attempt_id, delta in trash_runs]
if len(trash_runs) == 0:
    print("No runs in this file are below the specified minimum.\n")
    exit()

print("\nThe following attempts are shorter than the specified minimum:")
for attempt_id, delta in trash_runs:
    print(f"#{attempt_id}: {delta.seconds}s ")

confirmation = input("\nWould you like to prune all of these attempts? (y/n): ")
if "y" in confirmation.lower():
    print(f"\nDeleting attempts: {', '.join(trash_ids)}.")
else:
    print("\nNo changes have been made to your file.")
    exit()
print()

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

lss_root.find("AttemptCount").text = str(len(attempt_history))

segments = lss_root.find("Segments")
for segment in segments.findall("Segment"):
    segment_history = segment.find("SegmentHistory")
    for segment_time in segment_history.findall("Time"):
        segment_time_id = str(segment_time.attrib["id"])
        if segment_time_id in new_attempt_mappings:
            if new_attempt_mappings[segment_time_id] == "delete":
                segment_history.remove(segment_time)
            else:
                segment_time.attrib["id"] = new_attempt_mappings[segment_time_id]

print(f"{len(trash_runs)} attempts have been pruned from your splits.\n")

lss_tree.write(f"pruned_{splits_file}", encoding="UTF-8", xml_declaration=True)
input("Press Enter to close script...")
print()