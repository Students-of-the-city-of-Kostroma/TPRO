from github import Github, RateLimitExceededException
from other import enigma
from logic.listener import Listener
from logic import ymls
import traceback, time, os, platform
from datetime import datetime, timedelta

TOKEN = ymls.SECRET['TOKEN']
GITHUB = Github(TOKEN)
ORG = 'Students-of-the-city-of-Kostroma'

if __name__ == '__main__':
    master = None
    try:
        repo = GITHUB.get_repo(
                full_name_or_id=f'{ymls.CONFIG["ORG"]}/{ymls.CONFIG["REPO"]}'
            )
        repo.github = GITHUB
        student = Listener(repo)
        master = repo.get_branch('master')
    except RateLimitExceededException:
        ymls.CONFIG['CORRECT_TIME'] = round(ymls.CONFIG.get('CORRECT_TIME', 0.0) + 0.01, 2)
        print(traceback.format_exc())
    except:
        print(traceback.format_exc())
        with open('errors.txt', 'w', encoding='utf-8') as f:
            f.write(f'{traceback.format_exc()}')
    finally:
        ymls.save_info()
        ymls.save_config()
        sleep = 120
        if master is None:
            print('master is None')
        else:
            command = 'git pull && git commit -am "' + str(ymls.CONFIG.get('CORRECT_TIME', 0.0)) + '" && git push'
            print(command)
            os.system(command)

            hours_left = ((datetime.fromtimestamp(int(master._headers['x-ratelimit-reset'])) - datetime.now()).seconds / 3600) + ymls.CONFIG.get('CORRECT_TIME', 0.0)
            requests_left = int(master._headers['x-ratelimit-remaining'])/(int(master._headers['x-ratelimit-limit']))
            sleep = int((hours_left - requests_left) * 3600)
            sleep = sleep if sleep >= 0 else 0
            print(datetime.fromtimestamp(int(master._headers['x-ratelimit-reset'])), master._headers['x-ratelimit-remaining'])
        while sleep > 3600:
            sleep -= 3600 
        now = datetime.now().strftime('%H:%M:%S')
        end_time = (datetime.now() + timedelta(seconds=sleep)).strftime('%H:%M:%S')
        print(f'{now}-->{sleep}-->{end_time}')
        time.sleep(sleep)
