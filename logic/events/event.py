from logic import ymls
from logic.events.issue_comment_event import IssueCommentEvent
from logic.events.issues_event import IssuesEvent
from datetime import datetime, timedelta
import re

INACTIVE_DAYS = ymls.CONFIG['INACTIVE_DAYS']

class Event:
    def __init__(self, event):
        self.events = {
            'IssueCommentEvent' : IssueCommentEvent,
            'IssuesEvent' : IssuesEvent
        }
        
        '''
        self.event_issue = {
            'review_requested' :  self._review_requested,
            'closed' : self._closed,
            'subscribed' : self._mute,
            'unsubscribed' : self._mute,
            'mentioned' : self._mute,
            'moved_columns_in_project' :  self._mute,
            'added_to_project' :  self._mute,
            'milestoned' : self._mute,
            'labeled' : self._mute,
            'assigned' : self._assigned,
            'unassigned' : self._unassigned,
            'merged' : self._mute,
            'review_dismissed' : self._mute,
            'reopened' : self._mute,
            'head_ref_deleted' : self._mute,
            'referenced' : self._mute,
            'renamed' : self._mute
        }
        '''
        

        if event.type in self.events:
            self.events[event.type](event)
        else:
            print(
                event.id, 
                event.created_at + timedelta(hours=3), 
                event.type, 
                'Обработчик не определен'
            )

    def _unassigned(self, event):
        if len(event.issue.assignees) < 1:
            event.issue.edit(
                assignees = [event.assigner.login]
            )
            event.issue.create_comment(
                body = f'У каждой задачи должен быть ответсвенный'
            )
        self._mute(event)

    def _assigned(self, event):
        self._assigned_pull(event)
        if len(event.issue.assignees) > 1:
            event.issue.edit(
                assignees = [a.login for a in event.issue.assignees if a.login != 'YuriSilenok']
            )
            event.issue.create_comment(
                body = f'У одной задачи может быть только один ответсвенный'
            )
        self._mute(event)

    def _assigned_pull(self, event):
        if event.issue.pull_request is not None\
        and event.assigner.login != 'YuriSilenok'\
        and event.assignee.login == 'YuriSilenok':
            branch = event.repo.get_pull(event.issue.number).raw_data['head']['ref']
            task_number = re.match(r'.*-(.*)', branch).group(1)
            event.issue.create_comment(
                body = f'После того, как преподаватель \
провел положительную проверку запроса #{event.issue.number}, \
Вы должны смержить запрос. После этого перевесить основную \
задачу #{task_number} на преподавателя.'
            )
            assignees = [a.login for a in event.issue.assignees if a.login != 'YuriSilenok']
            event.issue.edit(
                assignees = assignees
            )

    def _closed(self, event):
        if event.issue.pull_request is None\
        and event.raw_data['actor']['login'] != 'YuriSilenok':
            event.issue.edit(state = 'open')
            event.issue.create_comment(
                body = 'Прежде чем закрыть задачу, \
ее нужно перевесить на преподавателя, \
с целью выставления отметки в журнал.'
            )
        self._mute(event)

    def _mute(self, event):
        ymls.INFO['issues_events'][event.raw_data['event']].append(event.id)
    
    def _review_requested(self, event):
        if event.issue.state != 'closed' \
        and 'requested_reviewer' in event.raw_data \
        and event.raw_data['requested_reviewer']['login'] == 'YuriSilenok'\
        and len([rr for rr in event.repo.get_pull(event.issue.number).get_review_requests()[0] if rr.login == 'YuriSilenok']) > 0:
            pull_review = event.repo.get_pull(event.issue.number)
            not_review = {}
            for pull_scan in event.repo.get_pulls(state='open'):
                for pull_scan_review in pull_scan.get_review_requests()[0]:
                    if pull_review.assignee.login == pull_scan_review.login:
                        for ev in pull_scan.get_issue_events():
                            if ev.raw_data['event'] == 'review_requested' \
                            and ev.raw_data['requested_reviewer']['login'] == pull_review.assignee.login:
                                days = (datetime.now() - timedelta(hours=3) - ev.created_at).days
                                not_review[pull_scan.number] = days
            if not_review:
                pulls_str_long = ['#' + str(k) for k, v in not_review.items() if v > INACTIVE_DAYS / 2]
                pulls_str = ['#' + str(k) for k, v in not_review.items() if v <= INACTIVE_DAYS / 2]
                if pulls_str_long:
                    pulls_str_long = str(pulls_str_long)
                    mess = f'У вас есть непроверенные запросы {pulls_str_long}. Пожалуйста, выполните проверку этих запросов и после этого повторно запросите проверку своего запроса'
                    pull_review.create_review(
                        body = mess,
                        event = 'REQUEST_CHANGES'
                    )
                if pulls_str:
                    pulls_str = str(pulls_str)
                    mess = f'У вас есть непроверенные запросы {pulls_str}. Пожалуйста, выполните проверку этих запросов и после этого повторно запросите проверку своего запроса'
                    pull_review.create_issue_comment(
                        body = mess
                    )
        self._mute(event)