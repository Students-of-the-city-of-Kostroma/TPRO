from logic import ymls
from datetime import datetime, timedelta
import re

DB = ymls.INFO
INACTIVE_DAYS = ymls.CONFIG['INACTIVE_DAYS']

def mute(event):
    DB[event.type].append(event.id)

def issue_closed(event):
    if event.raw_data['actor']['login'] != 'YuriSilenok':
        event.issue.edit(state = 'open')
        event.issue.create_comment(
            body = 'Прежде чем закрыть задачу, \
ее нужно перевесить на преподавателя, \
с целью выставления отметки в журнал.'
        )
    mute(event)

def check_for_unreviewed_requests(event):
    pull = event.repo.get_pull(
            event.raw_data['issue']['number']
        )
    if pull.state == 'open'\
    and event.actor.login == 'YuriSilenok'\
    and len([rr for rr in pull.get_review_requests()[0] if rr.login == 'YuriSilenok']) > 0:
        not_review = {}
        for pull_scan in event.repo.get_pulls(state='open'):
            for pull_scan_review in pull_scan.get_review_requests()[0]:
                if pull.assignee.login == pull_scan_review.login:
                    for ev in pull_scan.get_issue_events():
                        if ev.raw_data['event'] == 'review_requested' \
                        and ev.raw_data['requested_reviewer']['login'] == pull.assignee.login:
                            days = (datetime.now() - timedelta(hours=3) - ev.created_at).days
                            not_review[pull_scan.number] = days
        if not_review:
            pulls_str_long = ['#' + str(k) for k, v in not_review.items() if v > INACTIVE_DAYS / 2]
            pulls_str = ['#' + str(k) for k, v in not_review.items() if v <= INACTIVE_DAYS / 2]
            if pulls_str_long:
                pulls_str_long = str(pulls_str_long)
                mess = f'У вас есть непроверенные запросы {pulls_str_long}. Пожалуйста, выполните проверку этих запросов и после этого повторно запросите проверку своего запроса'
                pull.create_review(
                    body = mess,
                    event = 'REQUEST_CHANGES'
                )
            if pulls_str:
                pulls_str = str(pulls_str)
                mess = f'У вас есть непроверенные запросы {pulls_str}. Пожалуйста, выполните проверку этих запросов и после этого повторно запросите проверку своего запроса'
                pull.create_issue_comment(
                    body = mess
                )

def check_base_and_head_branch_in_request(event):
    pull = event.repo.get_pull(
        event.raw_data['issue']['number'])
    if not(pull.raw_data['base']['ref'] == 'master'\
    and pull.raw_data['head']['ref'] == 'dev'\
    or pull.raw_data['base']['ref'] == 'dev'\
    and re.match(r'^issue-\d+$', pull.raw_data['head']['ref'])):
        mess = 'Нарушены [требования именования веток]'\
'(https://github.com/Students-of-the-city-of-Kostroma/'\
'Student-timetable/blob/dev/Docs/branches.md).'
        if not re.match(r'^(issue-\d+|dev)$', pull.raw_data['head']['ref']):
            pull.create_comment(
                f'{mess} Головная ветка не соответсвует требованиям.'
            )
        elif pull.raw_data['base']['ref'] == 'master'\
        and pull.raw_data['head']['ref'] != 'dev':
            pull.create_review(
                body = f'{mess} Слияние в ветку master возможно только из ветки dev.',
                event = 'REQUEST_CHANGES'
            )
            pull.edit(state = 'close')
        else:
            pull.create_comment(
                f'{mess} Что-то не так, но я не знаю что.'
            )
        

def review_requested(event):
    check_base_and_head_branch_in_request(event)
    check_for_unreviewed_requests(event)
    mute(event)

def unassigned(event):
    if len(event.issue.assignees) < 1:
        event.issue.edit(
            assignees = [event.assigner.login]
        )
        event.issue.create_comment(
            body = f'У каждой задачи должен быть ответсвенный'
        )
    mute(event)

def assigned(event):
    assigned_pull(event)
    if len(event.issue.assignees) > 1:
        event.issue.edit(
            assignees = [a.login for a in event.issue.assignees if a.login != 'YuriSilenok']
        )
        event.issue.create_comment(
            body = f'У одной задачи может быть только один ответсвенный'
        )
    mute(event)

def assigned_pull(event):
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
TO_STRING = ymls.CONFIG['TO_STRING']
EVENTS = {
    'IssueCommentEvent' : mute,
    'PushEvent' : mute,
    'PullRequestReviewEvent' : mute,
    'PullRequestReviewCommentEvent' : mute,
    'CreateEvent' : mute,
    'DeleteEvent' : mute,
    'PullRequestEvent' : {
        'opened' :  mute,
        'reopened' : mute,
        'closed' : mute},
    'IssuesEvent' : {
        'opened' : mute,
        'reopened' : mute,
        'closed' : issue_closed},
    'review_requested' : review_requested,
    'subscribed' : mute,
    'mentioned' : mute,
    'review_dismissed' : mute,
    'moved_columns_in_project' : mute,
    'connected' : mute,
    'assigned' : assigned,
    'unassigned' : unassigned,
    'milestoned' : mute,
    'added_to_project' : mute,
    'labeled' : mute,
    'closed' : mute,
    'unsubscribed' : mute,
    'head_ref_deleted' : mute,
    'merged' : mute,
    'referenced' : mute,
    'renamed' : mute,
    'reopened' : mute,
    'review_request_removed' : mute,
    'ready_for_review' : mute,
    'comment_deleted' : mute
}

def to_string(event):
    dt = event.created_at + timedelta(hours=3)
    result = f'{event.id} {dt} {event.type} {event.raw_data["actor"]["login"]}'
    if event.type in TO_STRING:
        for param in TO_STRING[event.type]:
            line = event.raw_data
            for key in param.split('.'):
                try:
                    key = int(key)
                except ValueError:
                    pass
                if isinstance(line, dict)\
                and key in line:
                    line = line[key]
                elif isinstance(line,list):
                    line = line[key]
                else:
                    break
            if not isinstance(line, dict):
                result += f' {line}'
    return result

def process(event):
    if not hasattr(event, 'type'):
        event.type = event.event            
    if event.type not in DB: 
        DB[event.type] = []
    if event.id not in DB[event.type]:
        print(to_string(event))
        if event.type in EVENTS:
            if isinstance(EVENTS[event.type], dict):
                if event.payload['action'] in EVENTS[event.type]:
                    EVENTS[event.type][event.payload['action']](event)
                else: 
                    print('Обработчик действия не реализован')
            else:
                EVENTS[event.type](event)
        else:
            print('Обработчик события не реализован')