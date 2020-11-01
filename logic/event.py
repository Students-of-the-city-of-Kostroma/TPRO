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
METHODS = 'Insert|Update|Delete'
TESTS_PATH = f'^UnitTestOfTimetableOfClasses/(C|M)({CLASSES})/({METHODS})/'
UT_PATH = f'{TESTS_PATH}(code.png|graph.png|whiteBox.md|UnitTest.cs)$'
ENTITIES = f'^(C|M)({CLASSES})$'

def mute(event):
    DB[event.type].append(event.id)

def issue_closed(event):
    if event.raw_data['actor']['login'] != 'YuriSilenok':
        event.issue.edit(state = 'open')
        create_comment(event.issue,
            'Прежде чем закрыть задачу, '
            'ее нужно перевесить на преподавателя, '
            'с целью выставления отметки в журнал.')    

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
        
def check_code(pull, file):
    content_file = pull.repo.get_contents(file.filename, pull.head.ref)
    text = content_file.decoded_content.decode('utf-8').split('\n')
    path_ns = file.filename.split('/')
    path_ns.remove(path_ns[-1])
    ns  = 'namespace ' + r'\.'.join(path_ns) + '$'
    
    state = 'using'
    graph = {
        'using' : {
            r'(\ufeff){,1}using [\w+\.]+;$': 'using',
            r'$' : 'post_using'
        },
        'post_using' : {
            r'$' : 'post_using',
            ns : 'namespace'
        },
        'namespace' : {
            r'\{$' : 'namespace_begin'
        },
        'namespace_begin' : {
            r' {4}/// <summary>$' : 'comment_start_summary_class'
        },
        'comment_start_summary_class' : {
            r' {4}/// </summary>$' : 'comment_end_summary_class',
            r' {4}///[\w+ \.]+' : 'comment_start_summary_class'
        },
        'comment_end_summary_class' : {
            r' {4}\[TestClass\]$' : 'param_test_class'
        },
        'param_test_class' : {
            r' {4}public class UT_((I|U|D)С)|('+CLASSES+r')$' : 'header_controller_test_class',
            r' {4}public class UT_M|('+CLASSES+r')$' : 'header_model_test_class'
        },
        'header_controller_test_class' : {
            r' {4}\{$' : 'begin_ref_data'
        },
        'header_model_test_class' : {
            r' {4}\{$' : 'pre_comment'
        },
        'begin_ref_data' : {
            r' {8}/// <summary>$' : 'comment_start_summary_RD',
        },
        'comment_start_summary_RD' : {
            r' {8}/// </summary>$' : 'begin_controller_test_class',
            r' {8}///[\w+ \.]+' : 'comment_start_summary_RD'
        },
        'begin_controller_test_class' : {
            r' {8}readonly RefData refData = new RefData\(\);$' : 'pre_comment'
        },
        'pre_comment' : {
            r'$' : 'pre_comment',
            r' {8}/// <summary>$' : 'comment_start_summary',
            r' {4}\}$' : 'end_class'
        },
        'comment_start_summary' : {
            r' {8}/// </summary>$' : 'comment_end_summary',
            r' {8}///[\w+ \.]+' : 'comment_start_summary'
        },
        'comment_end_summary' : {
            r' {8}\[TestMethod\]$' : 'param_method'
        },
        'param_method' : {
            r' {8}public void ((I|U|D)C)|('+CLASSES+r')_\d+\(\)$' : 'header_method'
        },
        'header_method' : {
            r' {8}\{$' : 'body_method'
        },
        'body_method' : {
            r' {12}.*' : 'body_method',
            r' {8}\}$' : 'pre_comment'
        },
        'end_class' : {
            r'\}$' : 'end_namespace'
        },
        'end_namespace' : {
            r'$' : 'end_file'
        }
    }
    messages ={
        'pre_comment' : 'Ожидается [начало комментария](https://habr.com/ru/post/41514/) `/// <summary>` или конец класса',
        'param_test_class' : 'Ожидается имя класса соответствующее [требованиям](https://github.com/Students-of-the-city-of-Kostroma/Student-timetable/blob/dev/Docs/Unit-test/README.md)'
    }
    oldLine = ''
    for indLine in range(len(text)):
        line = text[indLine]
        reg = None
        for transfer in graph[state]:
            reg = re.match(transfer, line)
            if reg:
                state = graph[state][transfer]
                break
        if reg is None:
            position = -1
            diff = file.patch.split('\n')
            for ind in range(len(diff)):
                if diff[ind].find(line) > -1:
                    position = ind
                    break
            mess = ''
            if state in messages and position > 0:
                mess = messages[state]
            else:
                indOldLine = indLine - 1
                mess = f'После строки `{oldLine}` (номер строки {indOldLine}) ожидается любое из списка`{list(graph[state])}`'+\
                    ' Нарушено [требование](https://github.com/Students-of-the-city-of-Kostroma/Student-timetable/blob/dev/Docs/Code-review/README.md) для кода.'
            if position < 1:
                pull.create_review(
                    body = f'Проблема в файле {file.filename}. \n {mess}',
                    event = 'REQUEST_CHANGES')
            else:
                pull.create_review_comment(
                    body = mess,
                    commit_id=pull.repo.get_branch(pull.head.ref).commit,
                    path=file.filename,
                    position=position
                )
            break
        oldLine = line

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
    if pull.state != 'open':
        return
    pull.repo = event.repo
    review_requests = pull.get_review_requests()
    if 'YuriSilenok' in [u.login for u in review_requests[0]]\
    or 'Elite' in [t.name for t in review_requests[1]]:
        check_reviewrs(pull)
        #check_white_box(pull)
        check_base_and_head_branch_in_request(pull)
        check_for_unreviewed_requests(pull)
        check_labels(pull)
        check_files(pull)

    payload = event.raw_data.get('payload', {})
    payload['number'] = event.raw_data['issue']['number']
    event.raw_data['payload'] = payload
    pull_open(event)

def unassigned(event):
    if len(event.issue.assignees) < 1:
        event.issue.edit(
            assignee = event.assignee.login)
        create_comment(event.issue,
            f'У каждой задачи должен быть ответсвенный')

def assigned(event):
    if len(event.issue.assignees) > 1:
        event.issue.edit(
            assignee = [a.login for a in event.issue.assignees if a.login != 'YuriSilenok'][0])
        create_comment(event.issue,
            f'У одной задачи/запроса может быть только один ответсвенный')

    if event.issue.pull_request is None:
        issue = event.issue
        if issue.state == 'close':
            issue.edit(
                assignee = [user.login for user in issue.assignees if user.login != event.raw_data['assignee']['login']])
            create_comment(event.issue,
                'Нельзя менять ответсвенного в закрытых задачах')
    else:
        pull = event.repo.get_pull(event.issue.number)
        if event.assigner.login != 'YuriSilenok'\
        and event.assignee.login == 'YuriSilenok':
            branch = event.repo.get_pull(event.issue.number).raw_data['head']['ref']
            task_number = re.search(r'.*-(.*)', branch).group(1)
            create_comment(event.issue,
                f'После того, как преподаватель '
                'провел положительную проверку запроса #{event.issue.number}, '
                'Вы должны смержить запрос. После этого перевесить основную '
                'задачу #{task_number} на преподавателя.'
            )
            event.issue.edit(
                assignees = [a.login for a in event.issue.assignees if a.login != 'YuriSilenok']
            )

def pull_open(event):
    pull_number = event.raw_data['payload']['number']
    pull = event.repo.get_pull(pull_number)
    if pull.state != 'open':
        return

    if pull.body == '':
        pull.create_issue_comment(body='Описание запроса должно содержать сведения о том, какую задачу он закрывает в случае мержа')

    re_branch = re.search(WORK_BRANCH, pull.raw_data['head']['ref'])
    if re_branch:
        if len(re_branch.regs) == 2:
            issue_number = int(re_branch[1])
            issue = event.repo.get_issue(issue_number)
            if 'YuriSilenok' == issue.assignee.login:
                pull.create_issue_comment(
                    f'Основная задача #{issue_number} назначена на преподавателя. Вы не можете вести дальнейшую активность по этому запросу.')
                pull.edit(state='close')
            if 'open' != issue.state:
                pull.create_issue_comment(
                    f'Основная задача #{issue_number} закрыта. Вы не можете вести дальнейшую активность по этому запросу.')
                pull.edit(state='close')


def check_white_box(pull):
    if 'Unit test' in [l.name for l in pull.labels]:
        for f in pull.get_files():
            if not re.search(UT_PATH, f.filename):
                pull.create_review(
                    body = f'Файл `{f.filename}` не соответствует требованиям. {MESS_UT}',
                    event = 'REQUEST_CHANGES')
                break

def add_failing_comment(old_comm, add_comm):
    if old_comm  is '':
        return add_comm
    else:
        new_comm = old_comm
        new_comm = new_comm + '\n'
        new_comm = new_comm + add_comm
        return new_comm

def check_user_story(pull, file):
    content = pull.repo.get_contents(file.filename, pull.head.ref)
    text_file = content.decoded_content.decode('utf-8').split('\n')
    
    failing_text = {
        'alien_element' : {
            r'^\t' : 'fail',

            r'^\d' : 'numbering',

            r'^\#{3}' : 'title_third_level',

            r'^\#{2}' : 'title_second_level',

            r'^\#{1}' : 'title_first_level',

            r'^\-{1}' : 'lists',
            
            r'^\W' : 'fail'
        },

        'numbering' : r'^\d+\W',

        'title_first_level' : r'^\#{1}\b[А-Я]',

        'title_second_level' : r'^\#{2}\b[А-Я]',

        'title_third_level' : r'^\#{3}\b[А-Я]',

        'lists' : r'^\-{1}\b[А-Я]',

        'fail' : r'^\W'
    }

    first = 0
    second = 0
    comments = ''

    for line in range(len(text_file)):
        ment = 'alien_element'
        reg = None

        for lenr in failing_text[ment]:
            reg = re.match( lenr, text_file[line] )
            if reg:
                ment = failing_text[ ment ][lenr]
                break
        
        if (ment is 'alien_element'):
            continue

        if ( ment is 'fail' ):
            err = re.match( failing_text[ ment ], text_file[line] ).group(0)
            comments = add_failing_comment(comments, f'В строке {line + 1} символ `{err}` не обрабатывается')
            continue

        if ( ment is 'numbering' ):
            if ( re.match(failing_text[ment], text_file[line]) ):
                err = re.match( failing_text[ ment ], text_file[line] ).group(0)
                ment = 'lists'
                comments = add_failing_comment(comments, f'В строке {line + 1} вместо символа `{err}` ожидается символ `{failing_text[ment]}`')
            continue


        if ( re.match( failing_text[ment], text_file[line] ) is None ):
            comments = add_failing_comment(comments, f'В строке {line + 1} ожидается `{failing_text[ment]}`')
            continue
        else:
            if( ment is 'title_third_level' and second == 0):
                comments = add_failing_comment(comments, f'В строке {line + 1} нарушено последовательность уровня заглавий')
                continue

            if (ment is 'title_second_level'):
                if ( first == 0 ):
                    comments = add_failing_comment(comments, f'В строке {line + 1} нарушено последовательность уровня заглавий')
                    continue
                second = second + 1

            if ( ment is 'title_first_level' ):
                first = first + 1

    pull.create_issue_comment( comments )

def check_files(pull):
    for file in pull.get_files():
        mess = None
        if file.status != 'removed':
            if re.match(r'.*UnitTest\.cs$', file.filename):
                check_code(pull, file)
            if re.match(r'/Docs/Technical/UserStories/Story-\d+/READMY.md'):
                check_user_story(pull, file)
            elif re.match(TESTS_PATH+r'(code\.png|graph\.png|whiteBox\.md|.*\.csproj)$', file.filename):
                print(f'Неизвестный файл `{file.filename}`')
            else:
                if mess is None:
                    mess = 'Обнаружены неизвестные файлы:\n'
                mess += f'- `{file.filename}`\n'
        if mess:
            pull.create_issue_comment(mess)

def check_label(event):
    if 'Unit test' == event.label.name:
        issue = event.repo.get_issue(event.raw_data['issue']['number'])
        entities_labels = [l.name for l in issue.labels if re.search(ENTITIES, l.name)]
        if not entities_labels:
            create_comment(event.issue,
                f'Не найдены сопутствующие метки для `{event.label.name}`. {MESS_LABEL}')

def create_comment(issue, comment):
    cr_comm = issue.create_comment if  isinstance(issue, Issue) else issue.create_issue_comment
    cr_comm(body=comment)


def check_labels(issue):
    labels = set([l.name for l in issue.labels])
    if list({'Unit test'} & labels):
        entities_labels = [l.name for l in issue.labels if re.search(ENTITIES, l.name)]
        if not entities_labels:
            create_comment(issue, 
                f'Не найдены сопутствующие метки для `Unit test`. {MESS_LABEL}')
    elif list({'Documentation'} & labels):
        if not list({'Methodological'} & labels):
            create_comment(issue, 
                f'Не найдены сопутствующие метки для `Documentation`. {MESS_LABEL}')
    else: 
        create_comment(issue, 
            f'Метка определяющая тип задачи не найдена. {MESS_LABEL}')

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
                create_comment(event.repo.get_issue(int(number)),
                    f"{MESS_BRANCH} Созданная ветка `{event.raw_data['payload']['ref']}` была удалена.")
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
                    create_comment(issue,
                        f'Ветка {branch_name} в которой Вы ведете активность не соответствует [требованиям]'
                        '(https://github.com/Students-of-the-city-of-Kostroma/Student-timetable/blob/dev/Docs/branches.md)')
                except: pass
    if branch_name not in ['master', 'dev']:
        command = f'cd ..\\Student-timetable && git checkout dev && git pull && git checkout {branch_name} && git pull'
        print(command)
        if os.system(command) != 0:
            print(f'ERROR: {command}')
            return
        command = f'cd ..\\Student-timetable && git merge dev && git push'
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
    'unlabeled' : mute,
    'head_ref_restored' : mute,
    'WatchEvent' : mute
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
    if os.path.exists('log.csv'):
        with open('log.csv', 'r', encoding='utf-8') as f:
            rows = [row for row in csv.reader(f) if row]
    if len(rows) == 0:
        rows.append(header)
    rows.insert(1, data)
    with open('log.csv', 'w', encoding='utf-8') as f:
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
