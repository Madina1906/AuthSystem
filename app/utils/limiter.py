from datetime import datetime, timedelta

# Vaqtinchalik xotirada saqlash (Real loyihada Redis yaxshiroq)
attempts_db = {} 

def check_block(phone: str):
    if phone in attempts_db:
        data = attempts_db[phone]
        if data['count'] >= 5:
            # 10 daqiqa o'tganini tekshirish
            if datetime.now() < data['blocked_until']:
                return False
            else:
                reset(phone) # Vaqt o'tdi, blokdan ochamiz
    return True

def register_fail(phone: str):
    if phone not in attempts_db:
        attempts_db[phone] = {'count': 1, 'blocked_until': None}
    else:
        attempts_db[phone]['count'] += 1
        if attempts_db[phone]['count'] >= 5:
            attempts_db[phone]['blocked_until'] = datetime.now() + timedelta(minutes=10)

def reset(phone: str):
    if phone in attempts_db:
        del attempts_db[phone]
