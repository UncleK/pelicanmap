"""Bounded retries for transient Windows sharing errors; never delete targets."""
import time

def replace_with_retry(temporary,target):
    for attempt in range(7):
        try:
            temporary.replace(target)
            return
        except PermissionError as error:
            # Windows file watchers/scanners may briefly deny rename. Genuine
            # permission failures still propagate after a 3.15 second bound.
            if getattr(error,'winerror',None) not in {5,32} or attempt==6:
                raise
            time.sleep(0.05*(2**attempt))
