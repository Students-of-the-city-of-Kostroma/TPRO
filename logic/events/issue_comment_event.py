from datetime import timedelta
from logic import ymls

class IssueCommentEvent:
    def __init__(self, event):
        self.actions = {
            'created': self._mute
        }
        self.event = event

        print(
            event.id, 
            event.created_at + timedelta(hours=3), 
            event.type, 
            event.payload['issue']['number'],
            event.payload['action'],
            event.actor.login,
            event.payload['comment']['body']
        )
        
        ymls.check_structure(event.type, event.payload['action'])
        if event.id not in ymls.INFO[event.type][event.payload['action']]:
            if event.payload['action'] in self.actions:
                self.actions[event.payload['action']]()
                ymls.INFO[event.type][event.payload['action']].append(event.id)
            else:
                print('Обработчик не определен')

    def _mute(self):
        pass
        


