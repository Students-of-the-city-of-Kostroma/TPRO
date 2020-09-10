from github import Repository, RateLimitExceededException
from logic.event import EventAction
from logic import ymls
import traceback, time

class Listener:
    def __init__(self, repo : Repository):
        while True:
            sleep = 0
            limit = 100
            i = 1
            for event in repo.get_issues_events():
                if i >= limit: break
                else: i += 1
                try:
                    sleep = int((int(event.raw_headers['x-ratelimit-limit']) \
                        - int(event.raw_headers['x-ratelimit-remaining'])) * 0.72)
                    event_event = event.raw_data['event']
                    if event_event not in ymls.INFO['issues_events']:
                        ymls.INFO['issues_events'][event_event] = []
                    if event.id not in ymls.INFO['issues_events'][event_event]:
                        event.repo = repo
                        EventAction(event)
                except ConnectionError:
                    print(traceback.format_exc())
                    print(f'SLEEEEEEP--->{sleep}')
                    ymls.save_info()
                    time.sleep(sleep)
                except RateLimitExceededException:
                    print(traceback.format_exc())
                    print(f'SLEEEEEEP--->{sleep}')
                    ymls.save_info()
                    time.sleep(sleep)
                    

            print(f'SLEEEEEEP--->{sleep}')
            ymls.save_info()
            time.sleep(sleep)
            