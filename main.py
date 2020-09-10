from github import Github
from other import enigma
from logic.listener import Listener
import time

TOKEN = enigma.decode('eF_:VRseMFIyha@8tI^ArexQHmX^=[S=I3o<F7m@', 0)
GITHUB = Github(TOKEN)
ORG = 'Students-of-the-city-of-Kostroma'
REPO = 'Student-timetable'


if __name__ == '__main__':
    while True:
        try:
            student = Listener(
                repo = GITHUB.get_repo(
                    full_name_or_id=f'{ORG}/{REPO}'
                )
            )
            break
        except:
            time.sleep(60)