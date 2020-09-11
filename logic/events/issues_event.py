from datetime import timedelta
from logic import ymls

class IssuesEvent:
    def __init__(self, event):
        self.actions = {
            'opened' : self.opened
        }
        self.event = event
        self.issue = self.event.repo.get_issue(
            self.event.payload['issue']['number']
        )
        print(
            event.id, 
            event.created_at + timedelta(hours=3), 
            event.type, 
            event.payload['issue']['number'],
            event.payload['action'],
            event.actor.login,
            event.payload['issue']['title']
        )
        ymls.check_structure(event.type, event.payload['action'])
        if event.id not in ymls.INFO[event.type][event.payload['action']]:
            if event.payload['action'] in self.actions:
                self.actions[event.payload['action']]()
                ymls.INFO[event.type][event.payload['action']].append(event.id)
            else:
                print('Обработчик не определен')
    
    def opened(self):
        if self.issue.state == 'open':
            self.check_body()
            self.check_milestone()
            self.check_assignee()
            self.check_title()
            self.check_labels()

    def check_body(self):
        if self.issue.body == '':
            self.create_comment(
                mess = 'Пожалуйста, заполните описание'
            )

    def check_milestone(self):
        if self.issue.milestone is None:
            self.create_comment(
                mess = 'Пожалуйста, добавьте веху'
            )

    def check_assignee(self):
        if self.issue.assignee is None:
            self.create_comment(
                mess = 'Пожалуйста, добавьте ответсвенного'
            )

    def check_title(self):
        if len(self.issue.title) < 10:
            self.create_comment(
                mess = 'Пожалуйста, измените заголовок на более детальный'
            )
    
    def check_labels(self):
        if not self.issue.labels:
            self.create_comment(
                mess = 'Пожалуйста, добавьте метки'
            )

    def create_comment(self, mess):
        self.issue.create_comment(mess)
        print(mess)


