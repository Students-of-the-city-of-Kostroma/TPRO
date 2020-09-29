from github import Github
from other import enigma
from logic.listener import Listener
from logic import ymls
import traceback, time, os, platform
from datetime import datetime, timedelta

TOKEN = ymls.SECRET['TOKEN']
GITHUB = Github(TOKEN)
ORG = 'Students-of-the-city-of-Kostroma'

if __name__ == '__main__':
    sleep = 60
    master = None
    try:
        repo = GITHUB.get_repo(
                full_name_or_id=f'{ymls.CONFIG["ORG"]}/{ymls.CONFIG["REPO"]}'
            )
        repo.GITHUB = GITHUB
        student = Listener(repo)
        master = repo.get_branch('master')
        hours_left = ((datetime.fromtimestamp(int(master._headers['x-ratelimit-reset'])) - datetime.now()).seconds / 3600) * ymls.CONFIG.get('CORRECT_TIME', 1)
        requests_left = int(master._headers['x-ratelimit-remaining'])/(int(master._headers['x-ratelimit-limit']))
        sleep = int((hours_left - requests_left) * 3600)
        sleep = sleep if sleep >= 0 else 0
    except:
        ymls.CONFIG['CORRECT_TIME'] = ymls.CONFIG.get('CORRECT_TIME', 1) + 0.01
        print(traceback.format_exc())
        with open('errors.txt', 'w', encoding='utf-8') as f:
            f.write(f'{traceback.format_exc()}\n')
    finally:
        ymls.save_info()
        if master is None:
            print('master is None')
            time.sleep(600)
        else:
            now = datetime.now().strftime('%H:%M:%S')
            end_time = (datetime.now() + timedelta(seconds=sleep)).strftime('%H:%M:%S')
            print(datetime.fromtimestamp(int(master._headers['x-ratelimit-reset'])), master._headers['x-ratelimit-remaining'])
            print(f'{now}-->{sleep}-->{end_time}')
            time.sleep(sleep)
        command = 'git pull && git commit -am "' + str(ymls.CONFIG.get('CORRECT_TIME', 1)) + '" && git push'
        print(command)
        os.system(command)
        ymls.save_config()
