from github import Repository, RateLimitExceededException
from logic import ymls
import traceback, time
from datetime import datetime, timedelta
from logic.repository import TRPO_Repository
from logic import event as EV

class Listener:
    def __init__(self, repo : Repository):
        self.repo = repo
        while True:
            sleep = 120
            try:
                today = datetime.now().date()
                if ymls.CONFIG['LAST_CREATED_STATISTICS'] < today:
                    ymls.CONFIG['LAST_CREATED_STATISTICS'] = today
                    trpo_repo = TRPO_Repository(repo)
                    trpo_repo.create_statistic_team(
                        repo.GITHUB.get_organization(ymls.CONFIG['ORG']).get_team_by_slug(ymls.CONFIG['TEAM']).get_members(),
                        today
                    )
                    ymls.save_config()
                
                self.process_events(repo.get_events())
                self.process_events(repo.get_issues_events())
                master = repo.get_branch('master')
                sleep = int((int(master.raw_headers['x-ratelimit-limit']) \
                    - int(master.raw_headers['x-ratelimit-remaining'])) * 0.72)
                print(f'SLEEEEEEP-->{sleep}')
                ymls.save_info()
                time.sleep(sleep)
            except:
                print(traceback.format_exc())
                print(f'SLEEEEEEP--->{sleep}')
                ymls.save_info()
                time.sleep(sleep) 

    def process_events(self, events):
        i , limit = 0, 100
        for event in events:
            if i < limit: i += 1
            else: break
            if not hasattr(event, 'repo') or event.repo is None:
                event.repo = self.repo
            EV.process(event)

            