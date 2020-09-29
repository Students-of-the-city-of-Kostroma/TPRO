from github import RateLimitExceededException
from logic import ymls
import traceback, time
from datetime import datetime, timedelta
from logic.repository import Repository
from logic import event as EV

class Listener:
    def __init__(self, repo):
        self.repo = repo
        today = datetime.now().date()
        trpo_repo = Repository(repo)
        trpo_repo.check_issues()
        if ymls.INFO.get('LAST_CREATED_STATISTICS', (datetime.now() - timedelta(days=1)).date()) < today\
        and datetime.now().hour > 2:
            ymls.INFO['LAST_CREATED_STATISTICS'] = today
            trpo_repo.create_statistic_team(
                repo.github.get_organization(ymls.CONFIG['ORG']).get_team_by_slug(ymls.CONFIG['TEAM']).get_members(),
                today
            )
        self.process_events(repo.get_events())
        self.process_events(repo.get_issues_events())

    def process_events(self, events):
        i , limit = 0, 100
        for event in events:
            if i < limit: i += 1
            else: break
            if not hasattr(event, 'repo') or event.repo is None:
                event.repo = self.repo
            EV.process(event)

            