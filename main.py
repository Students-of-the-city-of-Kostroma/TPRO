from github import Github
from other import enigma
from logic.listener import Listener
from logic import ymls
import traceback, time, os, platform

TOKEN = ymls.SECRET['TOKEN']
GITHUB = Github(TOKEN)
ORG = 'Students-of-the-city-of-Kostroma'

if __name__ == '__main__':
    try:
        repo = GITHUB.get_repo(
                full_name_or_id=f'{ymls.CONFIG["ORG"]}/{ymls.CONFIG["REPO"]}'
            )
        repo.GITHUB = GITHUB
        student = Listener(repo)
    except:
        sleep = 60
        print(traceback.format_exc())
        print(f'SLEEEEEEP->{sleep}')
        time.sleep(sleep)
    if 'Windows' in platform.platform():
        os.system(r'.\rerun.bat')
    else:
        raise NotImplementedError