from datetime import datetime, date, timedelta
from logic import ymls

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
            title = 'Статистика активности по проекту',
            body = 'Это экспериментальная задача. \n'+
                'Статистика публикуется ежедневно.'
        )
        issue.create_comment(
            f'Статистика на {today}, средний балл {sum}\n{comment}'
        )

    def get_issue_by_title_ot_create(self, title : str, body : str):
        for issue in self.repo.get_issues(state='open'):
            if issue.title == title:
                return issue
        return self.repo.create_issue(
            title = title,
            body = body,
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
        for issue in self.repo.get_issues(state='open'):
            # проверка активности для открытых задач
            if 'pull_request' not in issue.raw_data:
                # количество полных дней отсутствия активности
                issue_inactive_days = (datetime.now() - issue.updated_at + timedelta(hours=3)).days
                branch = None
                try: branch = self.repo.get_branch('issue-'+ str(issue.number))
                except: pass
                # количество дней отсутствия активности в ветке
                branch_inactive_days = None
                if branch is not None:
                    branch.commit.raw_data
                    branch_inactive_days = (datetime.now() - datetime.strptime(branch.commit.last_modified, '%a, %d %b %Y %H:%M:%S GMT')).days
                # количество дней отсуствия актвиности в связанных запросах
                pull_inactive_days= None
                request_review_teamled = []
                pull_inactive = None
                for pr in self.repo.get_pulls(state='open'):
                    for request_user in pr.get_review_requests()[0]:
                        if request_user.login == 'YuriSilenok':
                            request_review_teamled.append(pr)
                            break
                    inactive_days_now = (datetime.now() - pr.updated_at + timedelta(hours=3)).days
                    if pull_inactive_days is None or inactive_days_now < pull_inactive_days:
                        pull_inactive = pr
                        pull_inactive_days = inactive_days_now
                # минимальное количество неактивных дней
                inactive_list = [
                    issue_inactive_days,
                    branch_inactive_days,
                    pull_inactive_days]
                inactive_days = min([x for x in inactive_list if x is not None])
                # запрос на преподавателе

                # снимаем задачу
                if inactive_days > ymls.CONFIG['INACTIVE_DAYS'] and not request_review_teamled:
                    if issue.assignee.login != 'YuriSilenok':
                        mess = 'Задача с Вас снята, так как по ней давно не было активности. ' + \
                        f'Активность по основной задаче #{issue.number} составляет {issue_inactive_days} дней. ' + \
                        str('Ветка отсутствует. ' if branch_inactive_days is None else f'Активность в ветке {branch.name} составляет {branch_inactive_days} дней. ') + \
                        str('Запрос отсутствует. ' if pull_inactive is None else f'Активность по запросу #{pull_inactive.number} составляет {pull_inactive_days} дней. ') + \
                        'Нет запросов, которые должен проверить преподаватель'
                        issue.create_comment(mess)
                        issue.edit(
                            assignee = 'YuriSilenok'
                        )
                    # предупредительный выстрел
                    elif branch is not None and branch_inactive_days > ymls.CONFIG['INACTIVE_DAYS'] * 2:
                        mess = f'Ветка {branch.name} удалена'
                        self.repo.get_git_ref(f"heads/{branch}").delete()
                        issue.create_comment(mess)
