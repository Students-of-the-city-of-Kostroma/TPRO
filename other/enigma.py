import yaml, os, random

def generate_level():
    start, end = ord('0'), ord('z')
    data_pull = list(range(start, end))
    result = {}
    for c in data_pull.copy():
        to = data_pull.pop(random.randint(0, len(data_pull)-1))
        result[chr(c)]=chr(to)
    return result

def get_enigma():
    try: 
        with open('enigma.yml', 'r') as enigma_yml:
            return list(yaml.full_load(enigma_yml))
    except FileNotFoundError:
        data = []
        for _ in range(6):
            data.append(
                generate_level()
            )
        with open('enigma.yml', 'w') as enigma_yml:
            yaml.dump(data, enigma_yml)
        return data

def key_to_list(key):
    enigma = ENIGMA.copy()
    enigma.reverse()
    result = []
    for level in enigma:
        l = len(level)
        result.insert(0, key % l)
        key = key // l
    return result

def get_enigma_for_key_list(key_list : list):
    enigma = []
    for i_level in range(len(key_list)):
        combo_from_key = list(ENIGMA[i_level].values())
        for _ in range(key_list[i_level]):
            combo_from_key.append(combo_from_key.pop(0))
        enigma.append(
            dict(zip(list(ENIGMA[i_level].keys()), combo_from_key))
        )
    return enigma


def code_chr(ch, key):
    enigma = get_enigma_for_key_list(
        key_to_list(key)
    )
    for level_i in range(len(enigma)):
        ch = enigma[level_i][ch]
    return ch

def decode_chr(ch, key):
    enigma = get_enigma_for_key_list(
        key_to_list(key)
    )
    for level_i in range(len(enigma)-1, -1, -1):
        ch = [k for k, v in enigma[level_i].items() if v == ch][0]
    return ch

def code(line, key):
    result = ''
    for ch in line:
        result += code_chr(ch, key)
        key += 1
    return result

def decode(line, key):
    result = ''
    for ch in line:
        result += decode_chr(ch, key)
        key += 1
    return result

ENIGMA = get_enigma()
if __name__ == '__main__':
    key = random.randint(0,100000000)
    line = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    print(line)
    cod = code(line, key)
    print(cod)
    line = decode(cod, key)
    print(line)
        