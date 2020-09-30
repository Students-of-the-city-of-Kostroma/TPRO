from logic import ymls
from datetime import datetime, timedelta
import re, traceback, os, csv
from github.IssueEvent import IssueEvent
from github.Issue import Issue

DB = ymls.INFO
INACTIVE_DAYS = ymls.CONFIG['INACTIVE_DAYS']
TEAM = ymls.CONFIG['TEAM']
WORK_BRANCH = r'^issue-(\d+)$'
HEAD_BRANCH = r'^(issue-\d+|dev)$'
CORRECT_BRANCH = r'^(issue-\d+|dev|master)$'
MESS_BRANCH = 'Нарушены [требования именования веток]'\
'(https://github.com/Students-of-the-city-of-Kostroma/'\
'Student-timetable/blob/dev/Docs/branches.md#issue-d).'
MESS_LABEL = 'Нарушены [требования]'\
'(https://github.com/Students-of-the-city-of-Kostroma/Student-timetable/blob/dev/Docs/labels.md) для меток.'
MESS_UT = 'Нарушены требования именования папок или файлов к [белому ящику]'\
'(https://github.com/Students-of-the-city-of-Kostroma/Student-timetable/blob/dev/Docs/White-box/README.md)'\
' или [модульным тестам]'\
'(https://github.com/Students-of-the-city-of-Kostroma/Student-timetable/blob/dev/Docs/Unit-test/README.md).'
CLASSES = '|'.join(ymls.CONFIG['ENTITIES'])
TESTS_PATH = f'^UnitTestOfTimetableOfClasses/(C|M)({CLASSES})/(Insert|Update|Delete)/'
UT_PATH = f'{TESTS_PATH}(code.png|graph.png|whiteBox.md|UnitTest.cs)$'
ENTITIES = f'^(C|M)({CLASSES})$'

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

def check_for_unreviewed_requests(pull):
    if pull.state == 'open':
        not_review = {}
        for pull_scan in pull.repo.get_pulls(state='open'):
            for pull_scan_review in pull_scan.get_review_requests()[0]:
                if pull.assignee.login == pull_scan_review.login:
                    for ev in pull_scan.get_issue_events():
                        if ev.raw_data['event'] == 'review_requested' \
                        and ('requested_reviewer' in ev.raw_data\
                        and ev.raw_data['requested_reviewer']['login'] == pull.assignee.login\
                        or 'requested_team' in ev.raw_data):
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

def check_base_and_head_branch_in_request(pull):
    if not(pull.raw_data['base']['ref'] == 'master'\
    and pull.raw_data['head']['ref'] == 'dev'\
    or pull.raw_data['base']['ref'] == 'dev'\
    and re.search(WORK_BRANCH, pull.raw_data['head']['ref'])):
        if not re.search(WORK_BRANCH, pull.raw_data['head']['ref']):
            pull.create_review(
                body = f'{MESS_BRANCH} Головная ветка {pull.raw_data["head"]["ref"]} не соответствует требованиям.',
                event = 'REQUEST_CHANGES'
            )
        elif pull.raw_data['base']['ref'] == 'master'\
        and pull.raw_data['head']['ref'] != 'dev':
            pull.create_review(
                body = f'{MESS_BRANCH} Слияние в ветку master возможно только из ветки dev.',
                event = 'REQUEST_CHANGES'
            )
            pull.edit(state = 'close')
        else:
            pull.create_issue_comment(
                f'{MESS_BRANCH} Что-то не так, но я не знаю что.'
            )
        
def check_code(pull):
    pass

def check_reviewrs(pull):
    org = pull.repo.github.get_organization(ymls.CONFIG['ORG'])
    member = org.get_team_by_slug(ymls.CONFIG['TEAM']).get_members()
    team = set([nu.login for nu in member])
    reviews = set([r.user.login for r in pull.get_reviews()])
    requests = set([nu.login for nu in pull.get_review_requests()[0]])
    author = {pull.user.login}
    unreviewers = list(team - reviews - requests - author)
    if len(unreviewers) > 0:
        pull.create_review_request(reviewers=unreviewers)

def review_requested(event):
    pull = event.repo.get_pull(event.raw_data['issue']['number'])
    pull.repo = event.repo
    review_requests = pull.get_review_requests()
    if 'YuriSilenok' in [u.login for u in review_requests[0]]\
    or 'Elite' in [t.name for t in review_requests[1]]:
        check_reviewrs(pull)
        check_white_box(pull)
        check_base_and_head_branch_in_request(pull)
        check_for_unreviewed_requests(pull)
        check_code(pull)
        check_labels(pull)        

    payload = event.raw_data.get('payload', {})
    payload['number'] = event.raw_data['issue']['number']
    event.raw_data['payload'] = payload
    pull_open(event)

def unassigned(event):
    if len(event.issue.assignees) < 1:
        event.issue.edit(
            assignees = [event.assigner.login]
        )
        event.issue.create_comment(
            body = f'У каждой задачи должен быть ответсвенный'
        )

def assigned(event):
    assigned_pull(event)
    if len(event.issue.assignees) > 1:
        event.issue.edit(
            assignee = [a.login for a in event.issue.assignees if a.login != 'YuriSilenok'][0]
        )
        event.issue.create_comment(
            body = f'У одной задачи может быть только один ответсвенный'
        )

def assigned_pull(event):
    if event.issue.pull_request is not None\
    and event.assigner.login != 'YuriSilenok'\
    and event.assignee.login == 'YuriSilenok':
        branch = event.repo.get_pull(event.issue.number).raw_data['head']['ref']
        task_number = re.search(r'.*-(.*)', branch).group(1)
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

def pull_open(event):
    pull_number = event.raw_data['payload']['number']
    pull = event.repo.get_pull(pull_number)
    re_branch = re.search(WORK_BRANCH, pull.raw_data['head']['ref'])
    if re_branch:
        if len(re_branch.regs) == 2:
            issue_number = int(re_branch[1])
            issue = event.repo.get_issue(issue_number)
            if 'YuriSilenok' == issue.assignee.login:
                pull.create_issue_comment(
                    f'Основная задача #{issue_number} назначена на преподавателя. Это значит вы не можете вести дальнейшую активность по этой задаче.')
                pull.edit(state='close')
    else:
        pull.create_issue_comment(
            f'{MESS_BRANCH} Головная ветка {pull.raw_data["head"]["ref"]} не соответствует требованиям.')
        pull.edit(state='close')


def check_white_box(pull):
    if 'Unit test' in [l.name for l in pull.labels]:
        for f in pull.get_files():
            if not re.search(UT_PATH, f.filename):
                pull.create_review(
                    body = f'Файл `{f.filename}` не соответствует требованиям. {MESS_UT}',
                    event = 'REQUEST_CHANGES')
                break


def check_label(event):
    if 'Unit test' == event.label.name:
        issue = event.repo.get_issue(event.raw_data['issue']['number'])
        entities_labels = [l.name for l in issue.labels if re.search(ENTITIES, l.name)]
        if not entities_labels:
            issue.create_comment(
                f'Не найдены сопутствующие метки для `{event.label.name}`. {MESS_LABEL}'                
            )

def check_labels(issue):
    create_comment = issue.create_comment if  isinstance(issue, Issue) else issue.create_issue_comment
    labels = set([l.name for l in issue.labels])
    if list({'Unit test'} & labels):
        entities_labels = [l.name for l in issue.labels if re.search(ENTITIES, l.name)]
        if not entities_labels:
            create_comment(
                f'Не найдены сопутствующие метки для `Unit test`. {MESS_LABEL}'
            )
    elif list({'Documentation'} & labels):
        if not list({'Methodological'} & labels):
            create_comment(
                f'Не найдены сопутствующие метки для `Documentation`. {MESS_LABEL}'
            )
    else: 
        create_comment(
            f'Классифицирующая метка не найдена. {MESS_LABEL}'
        )

def create_branch(event):
    rgx = re.search(WORK_BRANCH, event.raw_data['payload']['ref'])
    if not rgx:
        try:
            event.repo.get_git_ref(f"heads/{event.raw_data['payload']['ref']}").delete()
        except: 
            print(traceback.format_exc())
        rgx = re.search(r'\D*(\d+)\D*', event.raw_data['payload']['ref']) 
        if rgx is not None and len(rgx.regs) > 1:
            number = rgx[1]
            try:
                event.repo.get_issue(int(number)).create_comment(
                    f"{MESS_BRANCH} Созданная ветка {event.raw_data['payload']['ref']} была удалена."
                )
            except: 
                print(traceback.format_exc())
def push_event(event):
    branch_name = event.payload['ref'][11:]
    re_branch_name = re.search(CORRECT_BRANCH, branch_name)
    if re_branch_name is None:
        re_branch_name = re.search(r'\D*(\d+)\D*', branch_name)
        if re_branch_name is not None and len(re_branch_name.regs) > 1:
                try: 
                    issue = event.repo.get_issue(re_branch_name[1])
                    issue.create_comment(f'Ветка {branch_name} в которой Вы ведете активность не соответствует [требованиям]'
                    '(https://github.com/Students-of-the-city-of-Kostroma/Student-timetable/blob/dev/Docs/branches.md)')
                except: pass
    if branch_name == 'dev':
        command = 'cd ..\\Student-timetable && git checkout dev && git pull'
        print(command)
        if os.system(command) != 0:
            print(f'ERROR: {command}')
        for branch in event.repo.get_branches():
            if branch.name not in ['master', 'dev']:
                command = f'cd ..\\Student-timetable && git checkout {branch.name} && git pull && git merge dev && git push'
                print(command)
                if os.system(command) != 0:
                    print(f'ERROR: {command}')
                    command = f'cd ..\\Student-timetable && git merge --abort'
                    if os.system(command) != 0:  
                        print(f'ERROR: {command}')  

TO_STRING = ymls.CONFIG['TO_STRING']
EVENTS = {
    'IssueCommentEvent' : mute,
    'PushEvent' : push_event,
    'PullRequestReviewEvent' : mute,
    'PullRequestReviewCommentEvent' : mute,
    'CreateEvent' : create_branch,
    'DeleteEvent' : mute,
    'PullRequestEvent' : {
        'opened' :  pull_open,
        'reopened' : pull_open,
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
    'labeled' : check_label,
    'closed' : mute,
    'unsubscribed' : mute,
    'head_ref_deleted' : mute,
    'base_ref_changed' : mute,
    'merged' : mute,
    'referenced' : mute,
    'renamed' : mute,
    'reopened' : mute,
    'review_request_removed' : mute,
    'ready_for_review' : mute,
    'comment_deleted' : mute,
    'unlabeled' : mute
}

def to_string(event):
    dt = event.created_at + timedelta(hours=3)
    result = f'{event.id} {dt} {event.type} {event.raw_data["actor"]["login"]}'
    data = [event.id, dt, event.type, event.raw_data["actor"]["login"], '']
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
                data[-1] += f' {line}'
    
    rows = []
    header = ['id', 'date', 'event', 'user', 'message']
    with open('log.csv', 'w+', encoding='utf-8') as f:
        rows = [row for row in csv.reader(f) if row]
        if len(rows) == 0:
            rows.append(header)
        rows.insert(1, data)
        writer = csv.writer(f)
        writer.writerows(rows)            
        
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
                    if EVENTS[event.type][event.payload['action']] != mute:
                        mute(event)
                else: 
                    print('Обработчик действия не реализован')
            else:
                EVENTS[event.type](event)
                if EVENTS[event.type] != mute:
                        mute(event)
        else:
            print('Обработчик события не реализован')
