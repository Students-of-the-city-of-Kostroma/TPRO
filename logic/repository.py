from datetime import datetime, date, timedelta
from logic import ymls
import difflib

class Repository:

    def __init__(self, repo):
        self.repo = repo

    def create_statistic_team(self, contributers, today : date):
        today = datetime.today().date() if today is None else today
        statistic = {}
        days = 7
        dt_down = today - timedelta(days=days)
        sum = 0
        for member in contributers:
            key = f'{member.name}'
            statistic[key] = {'days':[0 for _ in range(days)], 'sum':0}
            for event in member.get_events():
                if event.created_at.date() < today:
                    if event.created_at.date() >= dt_down:
                        day = (event.created_at.date() - dt_down).days
                        if event.repo == self.repo:
                            statistic[key]['days'][day] += 1
                            statistic[key]['sum'] += 1
                    else: break
            sum += statistic[key]['sum']
        sum = round(sum / contributers.totalCount, 1)
        comment = '|User|Events|By days|Score|\n| --- | --- | --- | --- |\n'
        for key in statistic:
            score =  round(statistic[key]['sum'] / sum, 2)
            comment += f'|{key}|{statistic[key]["sum"]}|{statistic[key]["days"]}|{score}|\n'
        issue = self.get_issue_by_title_ot_create(
            title = 'Статистика активности по проекту'
        )

        issue.edit(
            body = f'Статистика на {today}, средний балл {sum}\n{comment}'
        )

    def get_issue_by_title_ot_create(self, title : str):
        for issue in self.repo.get_issues(state='open'):
            if issue.title == title:
                return issue
        return self.repo.create_issue(
            title = title,
            assignees = ['YuriSilenok'],
            milestone = self.get_backlog_milestone(),
            labels = ['info']
        )

    def get_backlog_milestone(self):
        for milestone in self.repo.get_milestones():
            if milestone.title == 'Backlog':
                if milestone.state == 'closed':
                    milestone.edit(state='open')
                return milestone
        return self.repo.create_milestone(
            title = 'Backlog',
            state = 'Open',
            description = 'Веха для бэклога проекта'
        )

    def check_issues(self):
        header = f'|User|Remains|Issue|Branch|Request|\n|---|---|---|---|---|\n'
        data = []
        for issue in self.repo.get_issues(state='open'):
            # проверка активности для открытых задач
            if 'pull_request' not in issue.raw_data:
                # количество полных дней отсутствия активности
                issue_updated_at = issue.updated_at + timedelta(hours=3)
                issue_inactive_delta = datetime.now() - issue_updated_at
                issue_inactive_days = issue_inactive_delta.days
                issue_inactive_hours = int(issue_inactive_delta.seconds / 3600)
                branch = None
                try: branch = self.repo.get_branch('issue-'+ str(issue.number))
                except: pass
                # количество дней отсутствия активности в ветке
                branch_inactive_days = None
                branch_inactive_hours = None
                branch_inactive_delta = None
                branch_last_modified = None
                if branch is not None:
                    branch.commit.raw_data
                    branch_last_modified = datetime.strptime(branch.commit.last_modified, '%a, %d %b %Y %H:%M:%S GMT') + timedelta(hours=3)
                    branch_inactive_delta = datetime.now() - branch_last_modified
                    branch_inactive_days = branch_inactive_delta.days
                    branch_inactive_hours = int(branch_inactive_delta.seconds / 3600)
                # количество дней отсуствия актвиности в связанных запросах
                pull_inactive_days= None
                pull_inactive_hours = None
                pull_inactive_delta = None
                pull_inactive = None
                pull_updated_at = None
                if branch is not None:
                    # Ищем запрос связанный с веткой
                    for pr in self.repo.get_pulls(state='open'):
                        if pr.raw_data['head']['ref'] == branch.name:
                            pull_inactive = pr
                            break                
                if pull_inactive is not None:
                    pull_updated_at = pr.updated_at + timedelta(hours=3)
                    pull_inactive_delta = datetime.now() - pull_updated_at
                    pull_inactive_days = pull_inactive_delta.days
                    pull_inactive_hours = int(pull_inactive_delta.seconds / 3600)
                # минимальное количество неактивных дней
                inactive_list_delta = [
                    issue_inactive_delta,
                    branch_inactive_delta,
                    pull_inactive_delta]
                inactive_list_delta = [i for i in inactive_list_delta if i is not None]
                inactive_delta = min(inactive_list_delta, key = lambda d: d.days * 24 + int(d.seconds / 3600))
                if issue.title not in ['Текущая активность по задачам','Статистика активности по проекту']:
                    remains = timedelta(days=ymls.CONFIG['INACTIVE_DAYS']) - inactive_delta
                    data.append([
                        f'[{issue.assignee.name}](https://github.com/Students-of-the-city-of-Kostroma/Student-timetable/issues/assigned/{issue.assignee.login})',
                        f'{remains.days}д. {str(int(remains.seconds / 3600)).zfill(2)}ч.',
                        f'#{issue.number}->{issue_inactive_days}д. {issue_inactive_hours}ч.<-{issue_updated_at}',
                        f'[{branch.name}](https://github.com/Students-of-the-city-of-Kostroma/Student-timetable/commits/{branch.name})->{branch_inactive_days}д. {branch_inactive_hours}ч.<-{branch_last_modified.strftime("%Y-%m-%d %H:%M:%S")}' if branch else ' ',
                        f'#{pull_inactive.number}->{pull_inactive_days}д. {pull_inactive_hours}ч.<-{pull_updated_at.strftime("%Y-%m-%d %H:%M:%S")}' if pull_inactive else ' '
                    ])
                # снимаем задачу
                if inactive_delta.days >= ymls.CONFIG['INACTIVE_DAYS']:
                    if issue.assignee.login != 'YuriSilenok':
                        mess = 'Задача с Вас  снята, так как по ней давно не было активности. ' + \
                        f'Активность по основной задаче #{issue.number} составляет {issue_inactive_days} дней. ' + \
                        str('Ветка отсутствует. ' if branch_inactive_days is None else f'Активность в ветке {branch.name} составляет {branch_inactive_days} дней. ') + \
                        str('Запрос отсутствует. ' if pull_inactive is None else f'Активность по запросу #{pull_inactive.number} составляет {pull_inactive_days} дней. ') + \
                        'Нет запросов, которые должен проверить преподаватель'
                        issue.create_comment(mess)
                        issue.edit(
                            assignee = 'YuriSilenok'
                        )
                    # удаляем ветку
                    elif branch is not None:
                        self.repo.get_git_ref(f"heads/{branch.name}").delete()
                        issue.create_comment(f'Ветка {branch.name} удалена')
                    else:
                        issue.edit(
                            state = 'close'
                        )
        issue = self.get_issue_by_title_ot_create(
                    title='Текущая активность по задачам'
                )
        
        data = sorted(data, key=lambda row: row[1])
        body = header+'\n'.join([f'|{"|".join(row)}|' for row in data])
        if issue.body != body:
            issue.edit(
                body=body
            )
