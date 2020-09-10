from github import Repository
from datetime import datetime, date, timedelta

class TRPO_Repository:

    def __init__(self, repo : Repository):
        self.repo = repo

    def create_statistic_team(self, contributers, today : date):
        today = datetime.today().date() if today is None else today
        statistic = {}
        days = 7
        dt_down = today - timedelta(days=days)
        sum = 0
        for member in contributers:
            key = f'@{member.login}'
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
        sum /= contributers.totalCount
        comment = '|User|Events|By days|Score|\n| --- | --- | --- | --- |\n'
        for key in statistic:
            score =  round(sum, 1) if key == '@YuriSilenok' else round(statistic[key]['sum'] / sum, 2)
            comment += f'|{key}|{statistic[key]["sum"]}|{statistic[key]["days"]}|{score}|\n'
        issue = self.get_issue_by_title_ot_create(
            title = 'Статистика активности по проекту',
            body = 'Это экспериментальная задача. \n'+
                'Статистика публикуется ежедневно.'
        )
        issue.create_comment(
            f'Статистика на {today}\n{comment}'
        )

    def get_issue_by_title_ot_create(self, title : str, body : str):
        for issue in self.repo.get_issues(state='open'):
            if issue.title == title:
                return issue
        return self.repo.create_issue(
            title = title,
            body = body,
            assignees = 'YuriSilenok',
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
