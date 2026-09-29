

import os

import json

import shutil

import time

import subprocess

import sys

import requests

from datetime import datetime, timedelta, timezone

# ============================================================

# SOZLAMALAR

# ============================================================

API_TOKEN = "TOKEN"

ADMIN_ID  = "ADMIN"

# ============================================================

TZ       = timezone(timedelta(hours=5))

BASE_URL = f"https://api.telegram.org/bot{API_TOKEN}"

DB_FILE  = "data/db.json"

RUNNING_PROCS = {}

# ============================================================

# JSON MA'LUMOTLAR BAZASI

# ============================================================

def load_db():

    try:

        with open(DB_FILE, "r", encoding="utf-8") as f:

            return json.load(f)

    except:

        return {"kunlik": [], "users": []}

def save_db(db):

    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

    with open(DB_FILE, "w", encoding="utf-8") as f:

        json.dump(db, f, ensure_ascii=False, indent=2)

def kunlik_get(useri):

    for row in load_db().get("kunlik", []):

        if row.get("useri") == useri:

            return row

    return None

def kunlik_insert(user_id, useri, turi, tokeni, vaqti, narxi, kun, avto):

    db = load_db()

    db.setdefault("kunlik", []).append({

        "user_id": user_id, "useri": useri, "turi": turi,

        "tokeni": tokeni, "vaqti": vaqti, "narxi": narxi,

        "kun": kun, "avto": avto

    })

    save_db(db)

def kunlik_update(useri, **kwargs):

    db = load_db()

    for row in db.get("kunlik", []):

        if row.get("useri") == useri:

            row.update(kwargs)

    save_db(db)

def kunlik_update_by_user_id(old_uid, new_uid):

    db = load_db()

    for row in db.get("kunlik", []):

        if row.get("user_id") == old_uid:

            row["user_id"] = new_uid

    save_db(db)

def kunlik_delete(useri):

    db = load_db()

    db["kunlik"] = [r for r in db.get("kunlik", []) if r.get("useri") != useri]

    save_db(db)

def user_exists(uid):

    return any(str(r.get("user_id")) == str(uid) for r in load_db().get("users", []))

def user_add(uid):

    db = load_db()

    db.setdefault("users", [])

    if not any(str(r.get("user_id")) == str(uid) for r in db["users"]):

        db["users"].append({"user_id": str(uid)})

        save_db(db)

# ============================================================

# TO'LOV TIZIMLARI — yordamchi funksiyalar

# ============================================================

def get_karta():

    try:

        with open("admin/karta.json", "r", encoding="utf-8") as f:

            return json.load(f)

    except:

        return None

def save_karta(data):

    os.makedirs("admin", exist_ok=True)

    with open("admin/karta.json", "w", encoding="utf-8") as f:

        json.dump(data, f, ensure_ascii=False)

def get_stars_narx():

    val = read_file("admin/stars.txt", "0")

    try:

        return int(float(val))

    except:

        return 0

def delete_karta():

    try:

        os.remove("admin/karta.json")

    except:

        pass

def delete_stars():

    try:

        os.remove("admin/stars.txt")

    except:

        pass

# ============================================================

# PROMOKOD TIZIMLARI

# ============================================================

def load_promokodlar():

    try:

        with open("admin/promokodlar.json", "r", encoding="utf-8") as f:

            return json.load(f)

    except:

        return {}

def save_promokodlar(data):

    os.makedirs("admin", exist_ok=True)

    with open("admin/promokodlar.json", "w", encoding="utf-8") as f:

        json.dump(data, f, ensure_ascii=False, indent=2)

def promokod_ishlatilganmi(kod, uid):

    try:

        with open(f"bonus/promo_{kod}.json", "r", encoding="utf-8") as f:

            ishlatganlar = json.load(f)

        return str(uid) in ishlatganlar

    except:

        return False

def promokod_ishlatildi_belgi(kod, uid):

    os.makedirs("bonus", exist_ok=True)

    try:

        with open(f"bonus/promo_{kod}.json", "r", encoding="utf-8") as f:

            ishlatganlar = json.load(f)

    except:

        ishlatganlar = []

    if str(uid) not in ishlatganlar:

        ishlatganlar.append(str(uid))

    with open(f"bonus/promo_{kod}.json", "w", encoding="utf-8") as f:

        json.dump(ishlatganlar, f)

# ============================================================

# GURUHGA ODAM QO'SHISH TIZIMI — YORDAMCHI FUNKSIYALAR

# ============================================================

def load_guruhlar():

    try:

        with open("admin/guruhlar.json", "r", encoding="utf-8") as f:

            return json.load(f)

    except:

        return {}

def save_guruhlar(data):

    os.makedirs("admin", exist_ok=True)

    with open("admin/guruhlar.json", "w", encoding="utf-8") as f:

        json.dump(data, f, ensure_ascii=False, indent=2)

def guruh_odam_qoshuvchi_uid(chat_id_g, new_member_id):

    """Guruhga yangi a'zo qo'shgan kishi UID ini topish (chat_member event da inviter yo'q,

    shuning uchun biz step fayllarda saqlaymiz)"""

    try:

        with open(f"guruh_inviter/{chat_id_g}_{new_member_id}.txt", "r", encoding="utf-8") as f:

            return f.read().strip()

    except:

        return None

def guruh_odam_qoshuvchi_saqlash(chat_id_g, new_member_id, inviter_uid):

    os.makedirs("guruh_inviter", exist_ok=True)

    with open(f"guruh_inviter/{chat_id_g}_{new_member_id}.txt", "w", encoding="utf-8") as f:

        f.write(str(inviter_uid))

# ============================================================

# PREMIUM TIZIMI

# ============================================================

def is_premium(uid):

    exp = read_file(f"premium/{uid}.txt")

    if not exp:

        return False

    try:

        exp_dt = datetime.fromisoformat(exp)

        return datetime.now(TZ) < exp_dt

    except:

        return False

def premium_qo_shish(uid, kunlar):

    os.makedirs("premium", exist_ok=True)

    exp_f = read_file(f"premium/{uid}.txt")

    try:

        base = datetime.fromisoformat(exp_f)

        if base < datetime.now(TZ):

            base = datetime.now(TZ)

    except:

        base = datetime.now(TZ)

    new_exp = base + timedelta(days=int(kunlar))

    write_file(f"premium/{uid}.txt", new_exp.isoformat())

    return new_exp

def get_premium_narx():

    val = read_file("admin/premium_narx.txt", "10000")

    try:

        return int(float(val))

    except:

        return 10000

def get_premium_kun():

    val = read_file("admin/premium_kun.txt", "30")

    try:

        return int(float(val))

    except:

        return 30

# ============================================================

# TO'LOV TARIXI TIZIMI

# ============================================================

def tarix_qoshish(uid, tur, miqdor, izoh, valyuta_loc="so'm"):

    """uid uchun to'lov tarixiga yozuv qo'shish"""

    os.makedirs("tarix", exist_ok=True)

    path = f"tarix/{uid}.json"

    try:

        with open(path, "r", encoding="utf-8") as f:

            tarix = json.load(f)

    except:

        tarix = []

    tarix.insert(0, {

        "tur": tur,

        "miqdor": miqdor,

        "izoh": izoh,

        "valyuta": valyuta_loc,

        "vaqt": datetime.now(TZ).strftime("%d.%m.%Y %H:%M")

    })

    # Oxirgi 50 ta yozuv saqlanadi

    tarix = tarix[:50]

    with open(path, "w", encoding="utf-8") as f:

        json.dump(tarix, f, ensure_ascii=False, indent=2)

def tarix_olish(uid):

    try:

        with open(f"tarix/{uid}.json", "r", encoding="utf-8") as f:

            return json.load(f)

    except:

        return []

# ============================================================

# FOYDALANUVCHI RO'YXATDAN O'TGAN VAQT

# ============================================================

def royxat_vaqt_saqlash(uid):

    path = f"baza/{uid}/reg.txt"

    if not os.path.exists(path):

        os.makedirs(f"baza/{uid}", exist_ok=True)

        write_file(path, datetime.now(TZ).strftime("%d.%m.%Y | %H:%M"))

def royxat_vaqt(uid):

    return read_file(f"baza/{uid}/reg.txt", "Noma'lum")

# ============================================================

# KIRITGAN PUL STATISTIKASI

# ============================================================

def kiritgan_pul_qoshish(uid, miqdor):

    path = f"baza/{uid}/kiritgan.txt"

    cur = 0

    try:

        cur = int(float(read_file(path, "0")))

    except:

        pass

    os.makedirs(f"baza/{uid}", exist_ok=True)

    write_file(path, str(cur + int(miqdor)))

def kiritgan_pul(uid):

    try:

        return int(float(read_file(f"baza/{uid}/kiritgan.txt", "0")))

    except:

        return 0

# ============================================================

# BOT SUBPROCESS BOSHQARUVI

# ============================================================

def get_bot_types():

    types = []

    if not os.path.exists("bot"):

        return types

    for name in os.listdir("bot"):

        if os.path.isdir(f"bot/{name}"):

            narx    = read_file(f"bot/{name}/narx.txt", "0")

            kunlik  = read_file(f"bot/{name}/kunlik.txt", "31")

            has_code = os.path.exists(f"bot/{name}/kod.py")

            types.append({"name": name, "narx": narx, "kunlik": kunlik, "has_code": has_code})

    return types

def auto_install_requirements(py_file):

    """Kod ichidagi barcha import larni o'rnatish"""

    try:

        with open(py_file, "r", encoding="utf-8") as f:

            code = f.read()

        import re as _re

        mods = set()

        for m in _re.findall(r"^import\s+([\w]+)", code, _re.MULTILINE):

            mods.add(m)

        for m in _re.findall(r"^from\s+([\w]+)", code, _re.MULTILINE):

            mods.add(m)

        stdlib = {

            "os","sys","re","json","time","math","random","datetime",

            "threading","subprocess","collections","itertools","functools",

            "pathlib","io","copy","hashlib","base64","urllib","http",

            "string","struct","socket","logging","traceback","typing",

            "shutil","tempfile","glob","signal","abc","enum","dataclasses",

            "contextlib","operator","weakref","inspect","ast","dis","gc",

            "xml","html","csv","configparser","argparse","unittest","queue",

            "asyncio","concurrent","multiprocessing","select",

        }

        pip_map = {

            "telebot":      "pyTelegramBotAPI",

            "telegram":     "python-telegram-bot==13.15",

            "aiogram":      "aiogram==2.25.2",

            "requests":     "requests",

            "aiohttp":      "aiohttp",

            "PIL":          "Pillow",

            "bs4":          "beautifulsoup4",

            "dotenv":       "python-dotenv",

            "flask":        "flask",

            "Flask":        "flask",

            "fastapi":      "fastapi",

            "sqlalchemy":   "sqlalchemy",

            "pymongo":      "pymongo",

            "redis":        "redis",

            "cv2":          "opencv-python",

            "numpy":        "numpy",

            "pandas":       "pandas",

            "httpx":        "httpx",

            "yaml":         "pyyaml",

            "pydantic":     "pydantic",

            "apscheduler":  "APScheduler",

            "schedule":     "schedule",

            "pytz":         "pytz",

            "dateutil":     "python-dateutil",

            "emoji":        "emoji",

            "qrcode":       "qrcode",

            "jwt":          "PyJWT",

        }

        for mod in mods:

            if mod in stdlib:

                continue

            pip_pkg = pip_map.get(mod, mod)

            try:

                __import__(mod)

            except ImportError:

                print(f"[INSTALL] {pip_pkg} o'rnatilmoqda...")

                subprocess.run(

                    [sys.executable, "-m", "pip", "install", pip_pkg, "-q",

                     "--break-system-packages"],

                    timeout=180, check=False

                )

    except Exception as e:

        print(f"[INSTALL] Xato: {e}")

def detect_bot_type(code):

    import re as _re

    if _re.search(r'from\s+flask|import\s+flask|Flask\s*\(', code, _re.IGNORECASE):

        return 'flask'

    if _re.search(r'from\s+aiogram|import\s+aiogram', code, _re.IGNORECASE):

        return 'aiogram'

    if _re.search(r'import\s+telebot|from\s+telebot', code, _re.IGNORECASE):

        return 'telebot'

    if _re.search(r'from\s+telegram\b|import\s+telegram\b', code, _re.IGNORECASE):

        return 'ptb'

    return 'raw'

def _convert_flask_to_polling(code, token):

    import re as _re

    route_match = _re.search(r'@app\.route[^\n]*\ndef\s+(\w+)\s*\(', code)

    webhook_func = route_match.group(1) if route_match else None

    lines = code.split('\n')

    new_lines = []

    skip_pats = [

        r'^\s*from\s+flask\b',

        r'^\s*import\s+flask\b',

        r'^\s*from\s+flask\s+import',

        r'^\s*app\s*=\s*Flask\(',

        r'^\s*@app\.',

        r'^\s*app\.run\(',

        r'^\s*def\s+set_webhook\(',

        r'^\s*set_webhook\(',

    ]

    decorator_pending = False

    for line in lines:

        if _re.match(r'^\s*@app\.', line):

            decorator_pending = True

            continue

        skip = any(_re.match(pat, line) for pat in skip_pats)

        if skip:

            decorator_pending = False

            continue

        if webhook_func and decorator_pending:

            line = _re.sub(

                rf'def\s+{webhook_func}\s*\([^)]*\)',

                'def _process_update(update)',

                line

            )

            decorator_pending = False

        line = line.replace('request.get_json()', 'update')

        line = _re.sub(r'update\s*=\s*update\b', '# update already set', line)

        line = _re.sub(r'return\s+["\']OK["\']\s*,\s*200', 'return', line)

        new_lines.append(line)

        if decorator_pending and not _re.match(r'^\s*@', line):

            decorator_pending = False

    safe_token = token.replace('"', '\\"')

    polling_wrapper = (

        '\nimport requests as _req_poll\nimport time as _time_poll\n\n'

        'def _polling_run():\n'

        '    _offset = 0\n'

        '    _base = "https://api.telegram.org/bot' + safe_token + '"\n'

        '    print("[POLLING] Bot ishga tushdi (polling rejimi)...")\n'

        '    try:\n'

        '        _req_poll.get(f"{_base}/getUpdates", params={"offset": -1}, timeout=10)\n'

        '    except:\n'

        '        pass\n'

        '    while True:\n'

        '        try:\n'

        '            _r = _req_poll.get(\n'

        '                f"{_base}/getUpdates",\n'

        '                params={"offset": _offset, "timeout": 30},\n'

        '                timeout=40\n'

        '            ).json()\n'

        '            for _u in _r.get("result", []):\n'

        '                _offset = _u["update_id"] + 1\n'

        '                try:\n'

        '                    _process_update(_u)\n'

        '                except Exception as _e:\n'

        '                    print(f"[UPDATE XATO] {_e}")\n'

        '        except Exception as _e:\n'

        '            print(f"[POLLING XATO] {_e}")\n'

        '            _time_poll.sleep(3)\n\n'

        'if __name__ == "__main__":\n'

        '    _polling_run()\n'

    )

    return '\n'.join(new_lines) + '\n' + polling_wrapper

def prepare_bot_code(code, token, owner_id):

    """

    Har qanday bot kodini universal polling botiga moslashtirish.

    Flask, aiogram, telebot, ptb, raw - barchasi qo'llab-quvvatlanadi.

    """

    import re as _re

    # ---- TOKEN va ADMIN barcha ko'rinishlarini almashtirish ----

    # = "TOKEN", = 'TOKEN', = TOKEN, API_TOKEN = "TOKEN", BOT_TOKEN = "TOKEN"

    token_patterns = [

        ('"TOKEN"',   f'"{token}"'),

        ("'TOKEN'",   f'"{token}"'),

        ('"token"',   f'"{token}"'),

        ("'token'",   f'"{token}"'),

        ('= TOKEN\n', f'= "{token}"\n'),

        ('= TOKEN\r', f'= "{token}"\r'),

        ('= TOKEN ',  f'= "{token}" '),

    ]

    admin_patterns = [

        ('"ADMIN"',   f'"{owner_id}"'),

        ("'ADMIN'",   f'"{owner_id}"'),

        ('"admin"',   f'"{owner_id}"'),

        ("'admin'",   f'"{owner_id}"'),

        ('= ADMIN\n', f'= "{owner_id}"\n'),

        ('= ADMIN\r', f'= "{owner_id}"\r'),

        ('= ADMIN ',  f'= "{owner_id}" '),

    ]

    for old, new in token_patterns:

        code = code.replace(old, new)

    for old, new in admin_patterns:

        code = code.replace(old, new)

    # Regex bilan ham bir marta o'tkazish (= "TOKEN_NOMI" ko'rinishlar uchun)

    code = _re.sub(r'(API_TOKEN\s*=\s*)["\']TOKEN["\']', rf'\g<1>"{token}"', code)

    code = _re.sub(r'(BOT_TOKEN\s*=\s*)["\']TOKEN["\']', rf'\g<1>"{token}"', code)

    code = _re.sub(r'(TOKEN\s*=\s*)["\']TOKEN["\']',     rf'\g<1>"{token}"', code)

    code = _re.sub(r'(ADMIN_ID\s*=\s*)["\']ADMIN["\']',  rf'\g<1>"{owner_id}"', code)

    code = _re.sub(r'(ADMIN\s*=\s*)["\']ADMIN["\']',     rf'\g<1>"{owner_id}"', code)

    bot_type = detect_bot_type(code)

    print(f"[PREP] Bot turi aniqlandi: {bot_type}")

    # ---- Flask / Webhook botlarni polling ga o'tkazish ----

    if bot_type == 'flask':

        print("[PREP] Flask/Webhook → Polling ga o'tkazilmoqda...")

        code = _convert_flask_to_polling(code, token)

    # ---- aiogram ----

    elif bot_type == 'aiogram':

        if 'start_webhook' in code or ('set_webhook' in code and 'start_polling' not in code):

            code = _re.sub(

                r'executor\.start_webhook\(.*?\)',

                'executor.start_polling(dp, skip_updates=True)',

                code, flags=_re.DOTALL

            )

        # aiogram v3 (asyncio based)

        if 'asyncio.run' not in code and '__main__' not in code:

            if 'Dispatcher' in code and 'Bot' in code:

                # v3 style

                if 'dp.start_polling' in code or 'await dp.start_polling' in code:

                    pass  # already has polling

                elif 'executor' in code:

                    pass  # v2 executor

                else:

                    # v3 - add asyncio main

                    code += (

                        '\n\nasync def main():\n'

                        '    await dp.start_polling(bot)\n\n'

                        'if __name__ == "__main__":\n'

                        '    import asyncio\n'

                        '    asyncio.run(main())\n'

                    )

            elif 'executor' in code or 'start_polling' in code:

                code += '\n\nif __name__ == "__main__":\n    from aiogram import executor\n    executor.start_polling(dp, skip_updates=True)\n'

        elif '__main__' not in code:

            code += '\n\nif __name__ == "__main__":\n    from aiogram import executor\n    executor.start_polling(dp, skip_updates=True)\n'

    # ---- telebot (pyTelegramBotAPI) ----

    elif bot_type == 'telebot':

        has_flask = 'app.run' in code or 'Flask(' in code

        has_webhook = 'set_webhook' in code and 'remove_webhook' not in code

        has_polling = 'bot.polling' in code or 'bot.infinity_polling' in code

        if has_flask or (has_webhook and not has_polling):

            code = _convert_flask_to_polling(code, token)

        elif not has_polling:

            code += '\n\nif __name__ == "__main__":\n    bot.infinity_polling(skip_pending=True, timeout=60)\n'

    # ---- python-telegram-bot ----

    elif bot_type == 'ptb':

        has_flask = 'app.run' in code or 'Flask(' in code

        has_webhook = 'set_webhook' in code

        has_polling = 'start_polling' in code or 'run_polling' in code

        if has_flask or (has_webhook and not has_polling):

            code = _convert_flask_to_polling(code, token)

        elif not has_polling:

            if 'Application' in code:

                # v20+ style

                code += (

                    '\n\nif __name__ == "__main__":\n'

                    '    application.run_polling(allowed_updates=Update.ALL_TYPES)\n'

                )

            elif 'Updater' in code:

                # v13 style

                code += (

                    '\n\nif __name__ == "__main__":\n'

                    '    updater.start_polling()\n'

                    '    updater.idle()\n'

                )

    # ---- Raw polling ----

    else:

        has_main = '__main__' in code

        has_loop = 'while True' in code

        has_polling_call = 'getUpdates' in code

        if not has_main and not has_loop:

            safe_token = token.replace('"', '\\"')

            code += (

                '\n\nif __name__ == "__main__":\n'

                '    import requests as _rq, time as _tm\n'

                '    _off = 0\n'

                f'    _base = "https://api.telegram.org/bot{safe_token}"\n'

                '    print("[BOT] Polling rejimida ishga tushdi...")\n'

                '    try:\n'

                '        _rq.get(f"{_base}/getUpdates", params={"offset": -1}, timeout=10)\n'

                '    except: pass\n'

                '    while True:\n'

                '        try:\n'

                '            _r = _rq.get(\n'

                '                f"{_base}/getUpdates",\n'

                '                params={"offset": _off, "timeout": 30},\n'

                '                timeout=40\n'

                '            ).json()\n'

                '            for _u in _r.get("result", []):\n'

                '                _off = _u["update_id"] + 1\n'

                '        except Exception as _e:\n'

                '            print(f"[XATO] {_e}")\n'

                '            _tm.sleep(3)\n'

            )

    return code

def start_user_bot(bot_username):

    py_file = f"bots/{bot_username}/bot.py"

    if not os.path.exists(py_file):

        print(f"[XATO] {py_file} topilmadi!")

        return False, "bot.py fayl topilmadi"

    stop_user_bot(bot_username)

    auto_install_requirements(py_file)

    try:

        log_dir = f"bots/{bot_username}"

        os.makedirs(log_dir, exist_ok=True)

        log_path = f"{log_dir}/bot.log"

        write_file(log_path, f"[{datetime.now().strftime('%H:%M:%S')}] Bot ishga tushmoqda...\n")

        log_file = open(log_path, "a", encoding="utf-8")

        proc = subprocess.Popen(

            [sys.executable, "-u", py_file],

            stdout=log_file, stderr=log_file,

            cwd=os.getcwd(),

            env=os.environ.copy()

        )

        RUNNING_PROCS[bot_username] = proc

        write_file(f"bots/{bot_username}/pid.txt", str(proc.pid))

        time.sleep(3)

        if proc.poll() is not None:

            log_file.flush()

            log_file.close()

            err_log = read_file(log_path, "Noma'lum xato")

            err_msg = err_log.strip()[-500:] if len(err_log) > 500 else err_log.strip()

            print(f"[XATO] @{bot_username} to'xtab qoldi. Log: {err_msg}")

            del RUNNING_PROCS[bot_username]

            delete_file(f"bots/{bot_username}/pid.txt")

            return False, err_msg

        print(f"[OK] @{bot_username} ishga tushdi (PID: {proc.pid})")

        return True, ""

    except Exception as e:

        print(f"[XATO] @{bot_username}: {e}")

        return False, str(e)

def stop_user_bot(bot_username):

    proc = RUNNING_PROCS.get(bot_username)

    if proc:

        try:

            proc.terminate()

            proc.wait(timeout=5)

        except:

            try:

                proc.kill()

            except:

                pass

        del RUNNING_PROCS[bot_username]

        delete_file(f"bots/{bot_username}/pid.txt")

def bot_is_running(bot_username):

    proc = RUNNING_PROCS.get(bot_username)

    if proc and proc.poll() is None:

        return True

    if proc:

        del RUNNING_PROCS[bot_username]

        delete_file(f"bots/{bot_username}/pid.txt")

    pid_file = f"bots/{bot_username}/pid.txt"

    if os.path.exists(pid_file):

        try:

            pid = int(read_file(pid_file).strip())

            os.kill(pid, 0)

            return True

        except (OSError, ValueError):

            delete_file(pid_file)

    return False

def watchdog_restart_bots():

    if not os.path.exists("bots"):

        return

    db = load_db()

    for row in db.get("kunlik", []):

        uname = row.get("useri", "")

        if not uname:

            continue

        py_file = f"bots/{uname}/bot.py"

        if not os.path.exists(py_file):

            continue

        proc = RUNNING_PROCS.get(uname)

        if proc and proc.poll() is None:

            continue

        print(f"[WATCHDOG] @{uname} to'xtagan, qayta ishga tushirilmoqda...")

        start_user_bot(uname)

def restart_all_saved_bots():

    if not os.path.exists("bots"):

        return

    db = load_db()

    started = set()

    for row in db.get("kunlik", []):

        uname = row.get("useri", "")

        if uname and os.path.exists(f"bots/{uname}/bot.py"):

            start_user_bot(uname)

            started.add(uname)

    for name in os.listdir("bots"):

        if name not in started and os.path.exists(f"bots/{name}/bot.py"):

            start_user_bot(name)

# ============================================================

# PAPKALAR

# ============================================================

for _d in ["matn","odam","pul","oplata","ban","step","bot","bots",

           "baza","tizim","admin","tugma","bonus","data","premium","guruh_inviter"]:

    os.makedirs(_d, exist_ok=True)

# ============================================================

# FAYL YORDAMCHILARI

# ============================================================

def read_file(path, default=""):

    try:

        with open(path, "r", encoding="utf-8") as f:

            return f.read()

    except:

        return default

def write_file(path, content):

    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:

        f.write(str(content))

def append_file(path, content):

    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)

    with open(path, "a", encoding="utf-8") as f:

        f.write(str(content))

def delete_file(path):

    try:

        os.remove(path)

    except:

        pass

def delete_folder(path):

    try:

        shutil.rmtree(path)

    except:

        pass

def file_exists(path):

    return os.path.exists(path)

def download_file(file_id):

    try:

        r = requests.get(f"{BASE_URL}/getFile", params={"file_id": file_id}, timeout=15).json()

        file_path = r.get("result", {}).get("file_path", "")

        if not file_path:

            return None

        content = requests.get(

            f"https://api.telegram.org/file/bot{API_TOKEN}/{file_path}", timeout=30

        ).content

        return content.decode("utf-8", errors="replace")

    except Exception as e:

        print(f"Fayl yuklab olishda xato: {e}")

        return None

# ============================================================

# BOT API

# ============================================================

def bot(method, data=None, files=None):

    if data is None:

        data = {}

    try:

        if files:

            r = requests.post(f"{BASE_URL}/{method}", data=data, files=files, timeout=30)

        else:

            r = requests.post(f"{BASE_URL}/{method}", data=data, timeout=15)

        return r.json()

    except Exception as e:

        print(f"Bot API xato: {e}")

        return {}

# ============================================================

# VAQT

# ============================================================

def now_tz():

    return datetime.now(TZ)

def soat():

    return now_tz().strftime("%H:%M")

def sana():

    return now_tz().strftime("%d.%m.%Y")

def get_bot_username():

    r = bot("getMe")

    return r.get("result", {}).get("username", "")

# ============================================================

# KANAL OBUNASI

# ============================================================

def joinchat(cid):

    kanal = read_file("admin/kanal.txt")

    if not kanal.strip():

        return True

    lines = [l for l in kanal.strip().split("\n") if l.strip()]

    keyboard = []

    uns = False

    for url_line in lines:

        url_line = url_line.strip()

        try:

            r = requests.get(f"{BASE_URL}/getchat?chat_id={url_line}", timeout=10).json()

            name = r.get("result", {}).get("title", url_line)

        except:

            name = url_line

        ret = bot("getChatMember", {"chat_id": url_line, "user_id": cid})

        stat = ret.get("result", {}).get("status", "")

        clean_url = url_line.replace("@", "")

        if stat in ("creator", "administrator", "member"):

            keyboard.append([{"text": f"✅ {name}", "url": f"https://t.me/{clean_url}"}])

        else:

            keyboard.append([{"text": f"❌ {name}", "url": f"https://t.me/{clean_url}"}])

            uns = True

    keyboard.append([{"text": "🔄 Tekshirish", "callback_data": "result"}])

    if uns:

        bot("sendMessage", {

            "chat_id": cid,

            "text": "⛔️ <b>Botdan foydalanish uchun kanallarga obuna bo'ling:</b>",

            "parse_mode": "html", "disable_web_page_preview": True,

            "reply_markup": json.dumps({"inline_keyboard": keyboard})

        })

        return False

    return True

def token_mask(t, start=15, end=32):

    try:

        return t[:start] + "*" * (len(t) - start - (len(t) - end)) + t[end:]

    except:

        return t

# ============================================================

# KLAVIATURALAR

# ============================================================

def make_panel():

    return json.dumps({"resize_keyboard": True, "keyboard": [

        [{"text": "📢 Kanallarni sozlash"}],

        [{"text": "📊 Statistika"}, {"text": "✉ Xabar Yuborish"}],

        [{"text": "⚙ Asosiy sozlamalar"}, {"text": "💳 To'lov tizimlari"}],

        [{"text": "🤖 Bot holati"}, {"text": "🤖 Botlar"}],

        [{"text": "🔎 Foydalanuvchini boshqarish"}],

        [{"text": "🎟 Promokodlar"}, {"text": "💎 Premium sozlash"}],

        [{"text": "👥 Guruhga odam qo'shish"}],

        [{"text": "👤 Adminlar ro'yxati"}],

        [{"text": "◀️ Orqaga"}]

    ]})

def make_menu():

    return json.dumps({"resize_keyboard": True, "keyboard": [

        [{"text": "➕ Yangi bot yaratish"}],

        [{"text": "🔩 Botni sozlash"}, {"text": "👔 Mening kabinetim"}],

        [{"text": "💰 Pul ishlash"}, {"text": "⚙ Sozlamalar"}],

        [{"text": "☎️ Murojaat"}],

    ]})

def make_menus():

    return json.dumps({"resize_keyboard": True, "keyboard": [

        [{"text": "➕ Yangi bot yaratish"}],

        [{"text": "🔩 Botni sozlash"}, {"text": "👔 Mening kabinetim"}],

        [{"text": "💰 Pul ishlash"}, {"text": "⚙ Sozlamalar"}],

        [{"text": "☎️ Murojaat"}],

        [{"text": "🗄 Boshqarish"}],

    ]})

def make_asosiy():

    return json.dumps({"resize_keyboard": True, "keyboard": [

        [{"text": "*️⃣ Birlamchi sozlamalar"}],

        [{"text": "🗄 Boshqarish"}],

    ]})

def make_back():

    return json.dumps({"resize_keyboard": True, "keyboard": [[{"text": "◀️ Orqaga"}]]})

def make_boshqarish():

    return json.dumps({"resize_keyboard": True, "keyboard": [[{"text": "🗄 Boshqarish"}]]})

# ============================================================

# ADMINLAR TIZIMI

# ============================================================

ADMINS_FILE = "admin/adminlar.json"

# Admin ruxsatlari ro'yxati

ADMIN_PERMS = [

    ("statistika",          "📊 Statistika"),

    ("xabar_yuborish",      "✉ Xabar Yuborish"),

    ("asosiy_sozlamalar",   "⚙ Asosiy sozlamalar"),

    ("tolov_tizimlari",     "💳 To'lov tizimlari"),

    ("bot_holati",          "🤖 Bot holati"),

    ("botlar",              "🤖 Botlar"),

    ("foydalanuvchi",       "🔎 Foydalanuvchini boshqarish"),

    ("promokodlar",         "🎟 Promokodlar"),

    ("premium_sozlash",     "💎 Premium sozlash"),

    ("guruh_odam",          "👥 Guruhga odam qo'shish"),

    ("kanallar",            "📢 Kanallarni sozlash"),

]

def load_adminlar():

    try:

        with open(ADMINS_FILE, "r", encoding="utf-8") as f:

            return json.load(f)

    except:

        return {}

def save_adminlar(data):

    os.makedirs("admin", exist_ok=True)

    with open(ADMINS_FILE, "w", encoding="utf-8") as f:

        json.dump(data, f, ensure_ascii=False, indent=2)

def is_admin(uid):

    """Foydalanuvchi admin yoki asosiy adminmi?"""

    if str(uid) == str(ADMIN_ID):

        return True

    adminlar = load_adminlar()

    return str(uid) in adminlar

def admin_has_perm(uid, perm):

    """Admin ushbu ruxsatga egami?"""

    if str(uid) == str(ADMIN_ID):

        return True

    adminlar = load_adminlar()

    a = adminlar.get(str(uid), {})

    perms = a.get("perms", {})

    return perms.get(perm, True)  # Default: ruxsat bor

def admin_add(uid, name, username, perms=None):

    adminlar = load_adminlar()

    if perms is None:

        perms = {p[0]: True for p in ADMIN_PERMS}

    adminlar[str(uid)] = {

        "name": name,

        "username": username,

        "perms": perms,

        "added": datetime.now(TZ).strftime("%d.%m.%Y %H:%M")

    }

    save_adminlar(adminlar)

def admin_remove(uid):

    adminlar = load_adminlar()

    adminlar.pop(str(uid), None)

    save_adminlar(adminlar)

def admin_update_perm(uid, perm, value):

    adminlar = load_adminlar()

    if str(uid) in adminlar:

        adminlar[str(uid)]["perms"][perm] = value

        save_adminlar(adminlar)

# ============================================================

# STANDART FAYLLAR

# ============================================================

def init_defaults():

    for path, val in [

        ("admin/valyuta.txt", "so'm"),

        ("admin/referal.txt", "500"),

        ("admin/foiz.txt",    "2"),

        ("admin/premium_narx.txt", "10000"),

        ("admin/premium_kun.txt",  "30"),

        ("admin/kunlik_bonus.txt", "1000"),

    ]:

        if not read_file(path):

            write_file(path, val)

# ================================================================

# ASOSIY UPDATE HANDLER

# ================================================================

# ============================================================

# BOT RO'YXATI — PAGINATION + 2 QATORLI GRID + PREMIUM CHEGIRMA

# ============================================================

PAGE_SIZE = 10  # Har sahifada 10 ta bot (5 qator x 2 ta)

def _send_bot_list(chat_id, page, balans, valyuta_loc, prem=False, edit=False, msg_id=None):

    """

    Bot turlarini sahifalab ko'rsatish.

    - Har sahifada 10 ta (2 qatorli grid: 5 qator x 2 ta)

    - Premium: narx 2x arzon, +40 kun bepul

    - Birinchi sahifa: faqat Keyingi

    - Oxirgi sahifa: faqat Orqaga

    - O'rtada: Orqaga + Keyingi

    """

    types = [t for t in get_bot_types() if t["has_code"]]

    if not types:

        bot("sendMessage", {"chat_id": chat_id,

            "text": "🤷 <b>Hozircha botlar mavjud emas!</b>", "parse_mode": "html"})

        return

    total  = len(types)

    pages  = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    page   = max(0, min(page, pages - 1))

    start_ = page * PAGE_SIZE

    end_   = min(start_ + PAGE_SIZE, total)

    chunk  = types[start_:end_]

    # 2 qatorli grid (2 ta yonma-yon)

    key = []

    row = []

    for t in chunk:

        asl_narx  = int(float(t["narx"]))

        cheg_narx = max(0, asl_narx // 2) if prem else asl_narx

        asl_kun   = int(float(t["kunlik"]))

        cheg_kun  = asl_kun + 40 if prem else asl_kun

        if prem and asl_narx > 0:

            label = f"🤖 {t['name']}\n💰 {cheg_narx} {valyuta_loc} | 📅 {cheg_kun} kun"

        else:

            label = f"🤖 {t['name']}\n💰 {asl_narx} {valyuta_loc} | 📅 {asl_kun} kun"

        btn = {

            "text": label,

            "callback_data": f"dots={t['narx']}={t['name']}={t['kunlik']}"

        }

        row.append(btn)

        if len(row) == 2:

            key.append(row)

            row = []

    if row:

        key.append(row)

    # Navigatsiya

    nav = []

    if page > 0:

        nav.append({"text": "◀️ Orqaga", "callback_data": f"botpage={page - 1}"})

    if page < pages - 1:

        nav.append({"text": "Keyingi ▶️", "callback_data": f"botpage={page + 1}"})

    if nav:

        key.append(nav)

    prem_note = "\n👑 <b>Premium:</b> Narxlar 2x arzon! +40 kun bepul!" if prem else ""

    sahifa_txt = f" ({page + 1}/{pages})" if pages > 1 else ""

    text = (

        f"⬇️ <b>Bot turini tanlang{sahifa_txt}:</b>\n\n"

        f"💵 <b>Balansingiz:</b> {balans} {valyuta_loc}{prem_note}"

    )

    if edit and msg_id:

        bot("editMessageText", {

            "chat_id": chat_id, "message_id": msg_id,

            "text": text, "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": key})

        })

    else:

        bot("sendMessage", {

            "chat_id": chat_id,

            "text": text, "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": key})

        })

def handle_update(upd):

    init_defaults()

    message      = upd.get("message", {})

    callback_q   = upd.get("callback_query", {})

    pre_checkout = upd.get("pre_checkout_query", {})

    # ============================================================

    # PRE-CHECKOUT QUERY (Stars to'lovi)

    # ============================================================

    if pre_checkout:

        bot("answerPreCheckoutQuery", {

            "pre_checkout_query_id": pre_checkout["id"],

            "ok": True

        })

        return

    # ============================================================

    # GURUHGA YANGI A'ZO — chat_member_updated

    # ============================================================

    chat_member_upd = upd.get("chat_member", {})

    if chat_member_upd:

        new_chat_member = chat_member_upd.get("new_chat_member", {})

        old_chat_member = chat_member_upd.get("old_chat_member", {})

        inviter = chat_member_upd.get("from", {})

        chat_g  = chat_member_upd.get("chat", {})

        chat_g_id = str(chat_g.get("id", ""))

        new_status = new_chat_member.get("status", "")

        old_status = old_chat_member.get("status", "")

        new_uid = str(new_chat_member.get("user", {}).get("id", ""))

        inviter_uid = str(inviter.get("id", ""))

        # Faqat yangi a'zo qo'shilganda (member yoki restricted holatga o'tganda)

        if new_status in ("member", "restricted") and old_status in ("left", "kicked", ""):

            guruhlar = load_guruhlar()

            if chat_g_id in guruhlar:

                narx_g = int(guruhlar[chat_g_id].get("narx", 0))

                # Inviter o'zi emas va botning o'zi emas bo'lsa

                bot_me = bot("getMe").get("result", {}).get("id", 0)

                if inviter_uid and inviter_uid != new_uid and inviter_uid != str(bot_me) and narx_g > 0:

                    # Inviter hisobiga pul qo'shish

                    _p = read_file(f"pul/{inviter_uid}.txt", "0")

                    try:

                        new_bal = int(float(_p)) + narx_g

                        write_file(f"pul/{inviter_uid}.txt", str(new_bal))

                    except:

                        new_bal = narx_g

                        write_file(f"pul/{inviter_uid}.txt", str(new_bal))

                    valyuta_loc = read_file("admin/valyuta.txt", "so'm")

                    guruh_nom = guruhlar[chat_g_id].get("nom", chat_g_id)

                    tarix_qoshish(inviter_uid, "guruh_odam", narx_g,

                                  f"Guruhga odam qo'shildi: {guruh_nom}", valyuta_loc)

                    # Inviterga shaxsiy xabar

                    bot("sendMessage", {

                        "chat_id": inviter_uid,

                        "text": (f"👥 <b>Guruhga odam qo'shdingiz!</b>\n\n"

                                 f"📌 Guruh: <b>{guruh_nom}</b>\n"

                                 f"💰 Hisobingizga <b>{narx_g} {valyuta_loc}</b> qo'shildi!\n"

                                 f"💵 Yangi balans: <b>{new_bal} {valyuta_loc}</b>"),

                        "parse_mode": "html"

                    })

        return

    # --- Message ma'lumotlari ---

    cid       = str(message.get("chat", {}).get("id", ""))

    name      = message.get("from", {}).get("first_name", "")

    familya   = message.get("from", {}).get("last_name", "") or ""

    username  = message.get("from", {}).get("username", "") or ""

    uid       = str(message.get("from", {}).get("id", ""))

    mid       = message.get("message_id", 0)

    text      = message.get("text", "") or ""

    tx        = text

    chat_id   = cid

    doc       = message.get("document") or {}

    photos    = message.get("photo") or []

    # ============================================================

    # STARS TO'LOVI MUVAFFAQIYATLI

    # ============================================================

    pay_info = message.get("successful_payment")

    if pay_info and cid:

        payload = pay_info.get("invoice_payload", "")

        stars_paid  = pay_info.get("total_amount", 0)

        valyuta_loc = read_file("admin/valyuta.txt", "so'm")

        # Premium to'lovi

        if payload.startswith("premium_"):

            prem_kun = get_premium_kun()

            exp_dt = premium_qo_shish(cid, prem_kun)

            exp_str = exp_dt.strftime("%d.%m.%Y %H:%M")

            bot("sendMessage", {

                "chat_id": cid,

                "text": (f"⭐ <b>Premium to'lov qabul qilindi!</b>\n\n"

                         f"💎 <b>Premium {prem_kun} kun</b> faollashdi!\n"

                         f"📅 Muddati: <b>{exp_str}</b> gacha"),

                "parse_mode": "html", "reply_markup": make_menu()

            })

            bot("sendMessage", {

                "chat_id": ADMIN_ID,

                "text": (f"💎 <b>Premium sotildi (Stars):</b>\n"

                         f"👤 <a href='tg://user?id={cid}'>{name} {familya}</a>\n"

                         f"⭐ Stars: {stars_paid}\n💎 {prem_kun} kun"),

                "parse_mode": "html"

            })

        else:

            # Oddiy hisob to'ldirish

            stars_narx  = get_stars_narx()

            amount_add  = stars_paid * stars_narx

            _p = read_file(f"pul/{cid}.txt", "0")

            try:

                write_file(f"pul/{cid}.txt", str(int(float(_p)) + amount_add))

            except:

                pass

            tarix_qoshish(cid, "kirim", amount_add, f"Stars orqali hisob to'ldirish ({stars_paid} ⭐)", valyuta_loc)

            kiritgan_pul_qoshish(cid, amount_add)

            bot("sendMessage", {

                "chat_id": cid,

                "text": (f"⭐ <b>Stars to'lovi qabul qilindi!</b>\n\n"

                         f"Siz <b>{stars_paid} Stars</b> to'ladingiz.\n"

                         f"Hisobingizga <b>{amount_add} {valyuta_loc}</b> qo'shildi! ✅"),

                "parse_mode": "html", "reply_markup": make_menu()

            })

            bot("sendMessage", {

                "chat_id": ADMIN_ID,

                "text": (f"⭐ <b>Stars to'lovi:</b>\n"

                         f"👤 <a href='tg://user?id={cid}'>{name} {familya}</a> ({cid})\n"

                         f"⭐ Stars: {stars_paid}\n💰 Miqdor: {amount_add} {valyuta_loc}"),

                "parse_mode": "html"

            })

        return

    # --- Callback ---

    data     = callback_q.get("data", "") or ""

    qid      = callback_q.get("id", "")

    cid2     = str((callback_q.get("message") or {}).get("chat", {}).get("id", ""))

    mid2     = (callback_q.get("message") or {}).get("message_id", 0)

    callfrid = str(callback_q.get("from", {}).get("id", ""))

    callname = callback_q.get("from", {}).get("first_name", "")

    surname  = callback_q.get("from", {}).get("last_name", "") or ""

    eff_cid = cid if cid else cid2

    # --- Step ---

    step  = read_file(f"step/{cid}.step")  if cid  else ""

    step2 = read_file(f"step/{cid2}.step") if cid2 else ""

    # --- Config ---

    valyuta  = read_file("admin/valyuta.txt", "so'm")

    referal  = read_file("admin/referal.txt", "500")

    holat    = read_file("tizim/holat.txt")

    # --- Foydalanuvchi ---

    pul     = read_file(f"pul/{cid}.txt",  "0") if cid  else "0"

    pul2    = read_file(f"pul/{cid2}.txt", "0") if cid2 else "0"

    odam    = read_file(f"odam/{cid}.dat", "0") if cid  else "0"

    odam2   = read_file(f"odam/{cid2}.dat","0") if cid2 else "0"

    ban_f   = read_file(f"ban/{cid}.txt")       if cid  else ""

    saved   = read_file("step/alijonov.txt")

    ref1 = read_file(f"step/{cid2}.txt") if cid2 else ""

    ref2 = read_file(f"step/{cid2}.id")  if cid2 else ""

    back          = make_back()

    panel         = make_panel()

    menu          = make_menu()

    menus         = make_menus()

    asosiy_kb     = make_asosiy()

    boshqarish_kb = make_boshqarish()

    bosh          = make_back()

    bot_username = get_bot_username()

    # ============================================================

    # BAN

    # ============================================================

    if text and ban_f == "ban":

        return

    if data:

        ban2 = read_file(f"ban/{cid2}.txt") if cid2 else ""

        if ban2 == "ban":

            return

    # ============================================================

    # RO'YXATGA OLISH

    # ============================================================

    if message:

        baza = read_file("azo.dat")

        if chat_id and chat_id not in baza:

            append_file("azo.dat", f"\n{chat_id}")

        user_add(chat_id)

        royxat_vaqt_saqlash(chat_id)

        if cid:

            for fpath, default in [(f"pul/{cid}.txt","0"),(f"odam/{cid}.dat","0")]:

                v = read_file(fpath, default)

                try:

                    write_file(fpath, str(int(float(v))))

                except:

                    write_file(fpath, default)

        pul  = read_file(f"pul/{cid}.txt",  "0") if cid else "0"

        odam = read_file(f"odam/{cid}.dat", "0") if cid else "0"

    # ============================================================

    # /start — REFERAL TIZIMI

    # ============================================================

    if tx.startswith("/start") and cid and joinchat(cid):

        parts = tx.split()

        if len(parts) > 1 and parts[1].startswith("ref"):

            ref_id = parts[1][3:]

            if ref_id != cid and not file_exists(f"step/{cid}.refby"):

                write_file(f"step/{cid}.refby", ref_id)

                write_file(f"step/{cid}.txt", cid)

                write_file(f"step/{cid}.id", ref_id)

        kb = menus if is_admin(cid) else menu

        prem_badge = " 💎" if is_premium(cid) else ""

        bot("sendMessage", {

            "chat_id": cid,

            "text": f"💎 <b>Salom {name}{prem_badge}!</b>\n\n@{bot_username} ga xush kelibsiz!",

            "parse_mode": "html", "reply_markup": kb

        })

        return

    # ============================================================

    # callback: result (kanal tekshirish)

    # ============================================================

    if data == "result" and cid2:

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        if joinchat(cid2):

            ref_by = read_file(f"step/{cid2}.id")

            if ref_by and ref_by != cid2:

                p2 = read_file(f"pul/{ref_by}.txt", "0")

                ref_narx = read_file("admin/referal.txt", "500")

                try:

                    new_p = int(float(p2)) + int(float(ref_narx))

                except:

                    new_p = int(float(ref_narx))

                write_file(f"pul/{ref_by}.txt", str(new_p))

                # Takliflar sonini oshirish

                _od = read_file(f"odam/{ref_by}.dat", "0")

                try:

                    write_file(f"odam/{ref_by}.dat", str(int(float(_od)) + 1))

                except:

                    pass

                valyuta_loc2 = read_file("admin/valyuta.txt", "so'm")

                tarix_qoshish(ref_by, "referal", int(float(ref_narx)), f"Referal bonus (yangi foydalanuvchi)", valyuta_loc2)

                bot("sendMessage", {"chat_id": ref_by,

                    "text": f"👥 <b>Yangi taklif!</b> Hisobingizga <b>{ref_narx} {valyuta}</b> qo'shildi! ✅",

                    "parse_mode": "html"})

                delete_file(f"step/{cid2}.txt")

                delete_file(f"step/{cid2}.id")

            bot("sendMessage", {"chat_id": cid2, "text": "✅ <b>Obunangiz tasdiqlandi.</b>",

                "parse_mode": "html", "reply_markup": menu})

        return

    # ============================================================

    # ◀️ Orqaga

    # ============================================================

    if tx == "◀️ Orqaga":

        kb = menus if is_admin(cid) else menu

        bot("sendMessage", {"chat_id": cid, "text": "<b>🖥 Asosiy menyuga qaytdingiz.</b>",

            "parse_mode": "html", "reply_markup": kb})

        delete_file(f"step/{cid}.step")

        delete_file("step/alijonov.txt")

        return

    # ============================================================

    # 👔 Mening kabinetim

    # ============================================================

    if tx == "👔 Mening kabinetim" and cid and joinchat(cid):

        royxat_vaqt_saqlash(cid)

        prem = is_premium(cid)

        prem_status = "👑 Premium" if prem else "👤 Oddiy"

        prem_exp = ""

        if prem:

            exp_raw = read_file(f"premium/{cid}.txt")

            try:

                exp_dt = datetime.fromisoformat(exp_raw)

                prem_exp = f"\n├─ 📅 <b>Tugash:</b> {exp_dt.strftime('%d.%m.%Y')}"

            except:

                pass

        reg_v = royxat_vaqt(cid)

        kirit = kiritgan_pul(cid)

        bot("sendMessage", {

            "chat_id": cid,

            "text": (f"🗄 <b>Kabinetingizga xush kelibsiz!</b>\n"

                     f"├\n"

                     f"├─ 🔍 <b>IDingiz:</b> <code>{cid}</code>\n"

                     f"├─ 💵 <b>Balansingiz:</b> {pul} {valyuta}\n"

                     f"├─ 👥 <b>Takliflaringiz soni:</b> {odam} ta\n"

                     f"├─ 👑 <b>Statusingiz:</b> {prem_status}{prem_exp}\n"

                     f"├─ ➕ <b>Kiritgan pullaringiz:</b> {kirit}.00 {valyuta}\n"

                     f"└─ 📅 <b>Ro'yxatdan o'tgansiz:</b> {reg_v}"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "💰 Pul kiritish", "callback_data": "hisob_toldirish"},

                 {"text": "📤 Pul o'tkazish", "callback_data": "pul_otkazish"}],

                [{"text": "👑 Premium", "callback_data": "premium_buy"},

                 {"text": "📜 To'lovlar tarixi", "callback_data": "tolov_tarixi"}],

            ]})

        })

        return

    if data == "kabinet" and cid2:

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        royxat_vaqt_saqlash(cid2)

        prem = is_premium(cid2)

        prem_status = "👑 Premium" if prem else "👤 Oddiy"

        prem_exp = ""

        if prem:

            exp_raw = read_file(f"premium/{cid2}.txt")

            try:

                exp_dt = datetime.fromisoformat(exp_raw)

                prem_exp = f"\n├─ 📅 <b>Tugash:</b> {exp_dt.strftime('%d.%m.%Y')}"

            except:

                pass

        reg_v = royxat_vaqt(cid2)

        kirit = kiritgan_pul(cid2)

        bot("sendMessage", {

            "chat_id": cid2,

            "text": (f"🗄 <b>Kabinetingizga xush kelibsiz!</b>\n"

                     f"├\n"

                     f"├─ 🔍 <b>IDingiz:</b> <code>{cid2}</code>\n"

                     f"├─ 💵 <b>Balansingiz:</b> {pul2} {valyuta}\n"

                     f"├─ 👥 <b>Takliflaringiz soni:</b> {odam2} ta\n"

                     f"├─ 👑 <b>Statusingiz:</b> {prem_status}{prem_exp}\n"

                     f"├─ ➕ <b>Kiritgan pullaringiz:</b> {kirit}.00 {valyuta}\n"

                     f"└─ 📅 <b>Ro'yxatdan o'tgansiz:</b> {reg_v}"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "💰 Pul kiritish", "callback_data": "hisob_toldirish"},

                 {"text": "📤 Pul o'tkazish", "callback_data": "pul_otkazish"}],

                [{"text": "👑 Premium", "callback_data": "premium_buy"},

                 {"text": "📜 To'lovlar tarixi", "callback_data": "tolov_tarixi"}],

            ]})

        })

        return

    # ============================================================

    # TO'LOVLAR TARIXI

    # ============================================================

    if data == "tolov_tarixi" and cid2:

        tarix = tarix_olish(cid2)

        if not tarix:

            bot("answerCallbackQuery", {"callback_query_id": qid,

                "text": "📭 Sizda to'lovlar tarixi topilmadi!", "show_alert": True})

            return

        txt = "📜 <b>To'lovlar tarixi</b>\n\n"

        for i, t in enumerate(tarix[:15], 1):

            tur_emoji = {"kirim": "⬆️", "chiqim": "⬇️", "o'tkazish": "📤",

                         "qabul": "📥", "bonus": "🎁", "referal": "👥",

                         "premium": "👑", "promokod": "🎟"}.get(t.get("tur",""), "💫")

            txt += (f"{tur_emoji} <b>{t.get('izoh','')}</b>\n"

                    f"   💰 {t.get('miqdor',0)} {t.get('valyuta','so\'m')} | 🕐 {t.get('vaqt','')}\n\n")

        bot("editMessageText", {

            "chat_id": cid2, "message_id": mid2,

            "text": txt, "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "◀️ Orqaga", "callback_data": "kabinet"}]

            ]})

        })

        return

    # ============================================================

    # 💰 PUL ISHLASH BO'LIMI

    # ============================================================

    if tx == "💰 Pul ishlash" and cid and joinchat(cid):

        ref_link = f"https://t.me/{bot_username}?start=ref{cid}"

        bot("sendMessage", {

            "chat_id": cid,

            "text": f"💰 <b>Pul ishlash usullarini tanlang:</b>",

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "👥 Referal tizimi", "callback_data": "referal_info"}],

                [{"text": "🎁 Kunlik bonus", "callback_data": "kunlik_bonus"}],

                [{"text": "🎟 Promokod kiritish", "callback_data": "promokod_kirish"}],

                [{"text": "👥 Guruhga odam qo'shish", "callback_data": "guruh_odam_qoshish"}],

            ]})

        })

        return

    # ============================================================

    # REFERAL INFO

    # ============================================================

    if data == "referal_info" and cid2:

        ref_link = f"https://t.me/{bot_username}?start=ref{cid2}"

        ref_narx = read_file("admin/referal.txt", "500")

        bot("editMessageText", {

            "chat_id": cid2, "message_id": mid2,

            "text": (f"👥 <b>Referal tizimi</b>\n\n"

                     f"Har bir taklif uchun: <b>{ref_narx} {valyuta}</b>\n\n"

                     f"🔗 <b>Sizning havolangiz:</b>\n"

                     f"<code>{ref_link}</code>\n\n"

                     f"📊 Jami takliflar: <b>{read_file(f'odam/{cid2}.dat', '0')} ta</b>"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "📤 Ulashish", "url": f"https://t.me/share/url?url={ref_link}&text=Bot%20foydali!"}],

                [{"text": "◀️ Orqaga", "callback_data": "pul_ishlash_menu"}],

            ]})

        })

        return

    if data == "pul_ishlash_menu" and cid2:

        bot("editMessageText", {

            "chat_id": cid2, "message_id": mid2,

            "text": "💰 <b>Pul ishlash usullarini tanlang:</b>",

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "👥 Referal tizimi", "callback_data": "referal_info"}],

                [{"text": "🎁 Kunlik bonus", "callback_data": "kunlik_bonus"}],

                [{"text": "🎟 Promokod kiritish", "callback_data": "promokod_kirish"}],

                [{"text": "👥 Guruhga odam qo'shish", "callback_data": "guruh_odam_qoshish"}],

            ]})

        })

        return

    # ============================================================

    # KUNLIK BONUS

    # ============================================================

    if data == "kunlik_bonus" and cid2:

        bonus_miqdor = read_file("admin/kunlik_bonus.txt", "1000")

        bugun = sana()

        oxirgi = read_file(f"bonus/{cid2}_kunlik.txt")

        if oxirgi == bugun:

            bot("answerCallbackQuery", {"callback_query_id": qid,

                "text": f"✅ Bugungi bonusni oldingiz! Ertaga qaytib keling.",

                "show_alert": True})

            return

        # Bonus berish

        _p = read_file(f"pul/{cid2}.txt", "0")

        try:

            write_file(f"pul/{cid2}.txt", str(int(float(_p)) + int(float(bonus_miqdor))))

        except:

            pass

        write_file(f"bonus/{cid2}_kunlik.txt", bugun)

        valyuta_loc = read_file("admin/valyuta.txt", "so'm")

        tarix_qoshish(cid2, "bonus", int(float(bonus_miqdor)), "Kunlik bonus", valyuta_loc)

        bot("editMessageText", {

            "chat_id": cid2, "message_id": mid2,

            "text": (f"🎁 <b>Kunlik bonus!</b>\n\n"

                     f"Hisobingizga <b>{bonus_miqdor} {valyuta}</b> qo'shildi! ✅\n\n"

                     f"⏰ Ertaga yana {bonus_miqdor} {valyuta} olasiz."),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "◀️ Orqaga", "callback_data": "pul_ishlash_menu"}]

            ]})

        })

        return

    # ============================================================

    # PROMOKOD KIRISH

    # ============================================================

    if data == "promokod_kirish" and cid2:

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {

            "chat_id": cid2,

            "text": "🎟 <b>Promokodni kiriting:</b>",

            "parse_mode": "html", "reply_markup": back

        })

        write_file(f"step/{cid2}.step", "promokod_kiritish")

        return

    if step == "promokod_kiritish" and cid:

        promokodlar = load_promokodlar()

        kod = tx.strip().upper()

        if kod not in promokodlar:

            bot("sendMessage", {"chat_id": cid,

                "text": "❌ <b>Promokod topilmadi!</b>", "parse_mode": "html"})

            return

        prom = promokodlar[kod]

        if prom.get("limit", 0) <= 0:

            bot("sendMessage", {"chat_id": cid,

                "text": "❌ <b>Bu promokod tugagan!</b>", "parse_mode": "html"})

            delete_file(f"step/{cid}.step")

            return

        if promokod_ishlatilganmi(kod, cid):

            bot("sendMessage", {"chat_id": cid,

                "text": "⚠️ <b>Siz bu promokodni allaqachon ishlatgansiz!</b>", "parse_mode": "html"})

            delete_file(f"step/{cid}.step")

            return

        miqdor = prom.get("miqdor", 0)

        _p = read_file(f"pul/{cid}.txt", "0")

        try:

            write_file(f"pul/{cid}.txt", str(int(float(_p)) + int(float(miqdor))))

        except:

            pass

        promokodlar[kod]["limit"] = prom["limit"] - 1

        if promokodlar[kod]["limit"] <= 0:

            del promokodlar[kod]

        save_promokodlar(promokodlar)

        promokod_ishlatildi_belgi(kod, cid)

        valyuta_loc = read_file("admin/valyuta.txt", "so'm")

        tarix_qoshish(cid, "promokod", int(float(miqdor)), f"Promokod: {kod}", valyuta_loc)

        bot("sendMessage", {

            "chat_id": cid,

            "text": (f"🎟 <b>Promokod qabul qilindi!</b>\n\n"

                     f"Hisobingizga <b>{miqdor} {valyuta}</b> qo'shildi! ✅"),

            "parse_mode": "html", "reply_markup": menu

        })

        delete_file(f"step/{cid}.step")

        return

    # ============================================================

    # 👥 GURUHGA ODAM QO'SHISH — FOYDALANUVCHI

    # ============================================================

    if data == "guruh_odam_qoshish" and cid2:

        # Qo'shilgan guruhlar ro'yxatini olish

        guruhlar = load_guruhlar()

        if not guruhlar:

            bot("editMessageText", {

                "chat_id": cid2, "message_id": mid2,

                "text": ("👥 <b>Guruhga odam qo'shish</b>\n\n"

                         "Hozircha hech qanday guruh qo'shilmagan.\n"

                         "Admin guruh qo'shishi kutilmoqda."),

                "parse_mode": "html",

                "reply_markup": json.dumps({"inline_keyboard": [

                    [{"text": "◀️ Orqaga", "callback_data": "pul_ishlash_menu"}]

                ]})

            })

            return

        # Guruhlarni ko'rsatish

        key = []

        for guruh_id, guruh_data in guruhlar.items():

            narx_g = guruh_data.get("narx", 0)

            nom_g = guruh_data.get("nom", guruh_id)

            link_g = guruh_data.get("link", "")

            key.append([{"text": f"👥 {nom_g} — {narx_g} {valyuta}/odam", "url": link_g}])

        key.append([{"text": "◀️ Orqaga", "callback_data": "pul_ishlash_menu"}])

        bot("editMessageText", {

            "chat_id": cid2, "message_id": mid2,

            "text": ("👥 <b>Guruhga odam qo'shish</b>\n\n"

                     "Quyidagi guruhlarga a'zo bo'ling va do'stlaringizni qo'shing.\n"

                     "Har bir qo'shilgan odam uchun pul olasiz!\n\n"

                     "Guruhga kiring, obuna bo'ling va bot sizni admin qiladi.\n"

                     "Keyin guruhga odam qo'sha boshlang — har biri uchun hisob to'ldiriladi!"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": key})

        })

        return

    # ============================================================

    # 👥 GURUHGA ODAM QO'SHISH — ADMIN PANEL

    # ============================================================

    if tx == "👥 Guruhga odam qo'shish" and is_admin(cid):

        guruhlar = load_guruhlar()

        soni = len(guruhlar)

        key = [

            [{"text": "➕ Guruh qo'shish", "callback_data": "admin_guruh_qoshish"}],

            [{"text": "📋 Guruhlar ro'yxati", "callback_data": "admin_guruh_royxat"}],

        ]

        if soni > 0:

            key.append([{"text": "🗑 Guruh o'chirish", "callback_data": "admin_guruh_ochirish"}])

        bot("sendMessage", {

            "chat_id": cid,

            "text": (f"👥 <b>Guruhga odam qo'shish boshqaruvi</b>\n\n"

                     f"Faol guruhlar: <b>{soni} ta</b>\n\n"

                     f"Guruhga odam qo'shish tizimi:\n"

                     f"— Foydalanuvchi guruhga kiradi va obuna bo'ladi\n"

                     f"— Bot guruhda admin bo'lishi kerak\n"

                     f"— Foydalanuvchi odam qo'shganda avtomatik pul oladi"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": key})

        })

        return

    if data == "admin_guruh_qoshish" and is_admin(cid2):

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {

            "chat_id": cid2,

            "text": ("➕ <b>Yangi guruh qo'shish</b>\n\n"

                     "<b>Qadamlar:</b>\n"

                     "1. Botni guruhga admin qiling\n"

                     "2. Guruh linkini yuboring\n\n"

                     "Guruhingizning <b>invite link</b> yoki <b>@username</b> ini yuboring:\n"

                     "<i>Misol: https://t.me/guruh_nomi yoki @guruh_nomi</i>"),

            "parse_mode": "html", "reply_markup": back

        })

        write_file(f"step/{cid2}.step", "admin_guruh_link")

        return

    if step == "admin_guruh_link" and is_admin(cid) and text:

        guruh_link = text.strip()

        # Guruh ma'lumotlarini olish

        chat_id_g = guruh_link

        if "t.me/" in guruh_link:

            chat_id_g = "@" + guruh_link.split("t.me/")[-1].strip("/").split("/")[0]

        try:

            r_chat = bot("getChat", {"chat_id": chat_id_g})

            guruh_nom = r_chat.get("result", {}).get("title", chat_id_g)

            guruh_id_real = str(r_chat.get("result", {}).get("id", ""))

            if not guruh_id_real:

                raise Exception("Guruh topilmadi")

            # Bot admin ekanligini tekshirish

            r_mem = bot("getChatMember", {"chat_id": guruh_id_real, "user_id": bot("getMe").get("result", {}).get("id", 0)})

            bot_status = r_mem.get("result", {}).get("status", "")

            if bot_status not in ("administrator", "creator"):

                bot("sendMessage", {

                    "chat_id": cid,

                    "text": ("⚠️ <b>Bot guruhda admin emas!</b>\n\n"

                             f"Guruh: <b>{guruh_nom}</b>\n\n"

                             "Avval botni guruhga admin qiling, keyin qayta yuboring."),

                    "parse_mode": "html", "reply_markup": back

                })

                return

        except Exception as e:

            bot("sendMessage", {

                "chat_id": cid,

                "text": (f"❌ <b>Guruh topilmadi!</b>\n\n"

                         f"Xato: {e}\n\n"

                         "Link to'g'riligini tekshiring va botni guruhga qo'shing."),

                "parse_mode": "html", "reply_markup": back

            })

            return

        write_file(f"step/{cid}.admin_guruh_link", guruh_link)

        write_file(f"step/{cid}.admin_guruh_id", guruh_id_real)

        write_file(f"step/{cid}.admin_guruh_nom", guruh_nom)

        bot("sendMessage", {

            "chat_id": cid,

            "text": (f"✅ <b>Guruh topildi!</b>\n\n"

                     f"👥 <b>Nom:</b> {guruh_nom}\n"

                     f"🆔 <b>ID:</b> <code>{guruh_id_real}</code>\n\n"

                     f"Endi har bir odam qo'shganda beriladigan <b>narxni kiriting</b> (so'mda):\n"

                     f"<i>Misol: 500</i>"),

            "parse_mode": "html", "reply_markup": back

        })

        write_file(f"step/{cid}.step", "admin_guruh_narx")

        return

    if step == "admin_guruh_narx" and is_admin(cid):

        if not tx.isdigit():

            bot("sendMessage", {"chat_id": cid,

                "text": "⚠️ <b>Faqat raqam kiriting!</b>", "parse_mode": "html"})

            return

        guruh_link = read_file(f"step/{cid}.admin_guruh_link")

        guruh_id_r = read_file(f"step/{cid}.admin_guruh_id")

        guruh_nom  = read_file(f"step/{cid}.admin_guruh_nom")

        narx_g = int(tx)

        guruhlar = load_guruhlar()

        guruhlar[guruh_id_r] = {

            "nom": guruh_nom,

            "link": guruh_link,

            "narx": narx_g

        }

        save_guruhlar(guruhlar)

        bot("sendMessage", {

            "chat_id": cid,

            "text": (f"✅ <b>Guruh qo'shildi!</b>\n\n"

                     f"👥 <b>Nom:</b> {guruh_nom}\n"

                     f"🆔 <b>ID:</b> <code>{guruh_id_r}</code>\n"

                     f"💰 <b>Narx:</b> {narx_g} {valyuta} / odam\n\n"

                     f"Endi foydalanuvchilar bu guruhga odam qo'shib pul ishlay oladi!"),

            "parse_mode": "html", "reply_markup": panel

        })

        delete_file(f"step/{cid}.step")

        delete_file(f"step/{cid}.admin_guruh_link")

        delete_file(f"step/{cid}.admin_guruh_id")

        delete_file(f"step/{cid}.admin_guruh_nom")

        return

    if data == "admin_guruh_royxat" and is_admin(cid2):

        guruhlar = load_guruhlar()

        if not guruhlar:

            bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

                "text": "📂 <b>Guruhlar yo'q!</b>", "parse_mode": "html",

                "reply_markup": json.dumps({"inline_keyboard": [

                    [{"text": "◀️ Orqaga", "callback_data": "admin_guruh_bosh"}]

                ]})})

            return

        txt = "👥 <b>Guruhlar ro'yxati:</b>\n\n"

        for gid, gdata in guruhlar.items():

            txt += (f"• <b>{gdata.get('nom', gid)}</b>\n"

                    f"  💰 Narx: {gdata.get('narx', 0)} {valyuta}/odam\n"

                    f"  🆔 ID: <code>{gid}</code>\n\n")

        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

            "text": txt, "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "◀️ Orqaga", "callback_data": "admin_guruh_bosh"}]

            ]})})

        return

    if data == "admin_guruh_ochirish" and is_admin(cid2):

        guruhlar = load_guruhlar()

        if not guruhlar:

            bot("answerCallbackQuery", {"callback_query_id": qid,

                "text": "Guruhlar yo'q!", "show_alert": True})

            return

        key = []

        for gid, gdata in guruhlar.items():

            key.append([{"text": f"🗑 {gdata.get('nom', gid)}", "callback_data": f"guruh_del={gid}"}])

        key.append([{"text": "◀️ Orqaga", "callback_data": "admin_guruh_bosh"}])

        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

            "text": "🗑 <b>Qaysi guruhni o'chirish?</b>", "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": key})})

        return

    if data and data.startswith("guruh_del=") and is_admin(cid2):

        gid_del = data.split("=", 1)[1]

        guruhlar = load_guruhlar()

        gnom = guruhlar.get(gid_del, {}).get("nom", gid_del)

        if gid_del in guruhlar:

            del guruhlar[gid_del]

            save_guruhlar(guruhlar)

        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

            "text": f"✅ <b>\"{gnom}\" guruh o'chirildi!</b>", "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "◀️ Orqaga", "callback_data": "admin_guruh_bosh"}]

            ]})})

        return

    if data == "admin_guruh_bosh" and is_admin(cid2):

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        guruhlar = load_guruhlar()

        soni = len(guruhlar)

        key = [

            [{"text": "➕ Guruh qo'shish", "callback_data": "admin_guruh_qoshish"}],

            [{"text": "📋 Guruhlar ro'yxati", "callback_data": "admin_guruh_royxat"}],

        ]

        if soni > 0:

            key.append([{"text": "🗑 Guruh o'chirish", "callback_data": "admin_guruh_ochirish"}])

        bot("sendMessage", {

            "chat_id": cid2,

            "text": (f"👥 <b>Guruhga odam qo'shish boshqaruvi</b>\n\n"

                     f"Faol guruhlar: <b>{soni} ta</b>"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": key})

        })

        return

    # ============================================================

    # 👥 GURUHGA YANGI A'ZO QO'SHILGANDA — chat_member event

    # ============================================================

    # ============================================================

    # ADMIN — PROMOKOD YARATISH

    # ============================================================

    if tx == "🎟 Promokodlar" and is_admin(cid):

        promokodlar = load_promokodlar()

        soni = len(promokodlar)

        bot("sendMessage", {

            "chat_id": cid,

            "text": f"🎟 <b>Promokodlar boshqaruvi</b>\n\nFaol promokodlar: <b>{soni} ta</b>",

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "➕ Yangi promokod", "callback_data": "promo_yaratish"}],

                [{"text": "📋 Ro'yxat", "callback_data": "promo_royxat"}],

                [{"text": "🗑 Barchasini o'chirish", "callback_data": "promo_tozalash"}],

            ]})

        })

        return

    if data == "promo_yaratish" and is_admin(cid2):

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {

            "chat_id": cid2,

            "text": ("➕ <b>Yangi promokod yaratish</b>\n\n"

                     "Quyidagi formatda yuboring:\n"

                     "<code>KOD MIQDOR LIMIT</code>\n\n"

                     "Misol: <code>BONUS2024 5000 50</code>\n"

                     "(KOD: BONUS2024, 5000 so'm, 50 marta ishlatiladi)"),

            "parse_mode": "html", "reply_markup": back

        })

        write_file(f"step/{cid2}.step", "promo_yaratish")

        return

    if step == "promo_yaratish" and is_admin(cid):

        parts_p = tx.strip().split()

        if len(parts_p) < 3:

            bot("sendMessage", {"chat_id": cid,

                "text": "⚠️ <b>Noto'g'ri format! Misol: BONUS2024 5000 50</b>", "parse_mode": "html"})

            return

        kod_p = parts_p[0].upper()

        try:

            miqdor_p = int(parts_p[1])

            limit_p  = int(parts_p[2])

        except:

            bot("sendMessage", {"chat_id": cid,

                "text": "⚠️ <b>Miqdor va limit raqam bo'lishi kerak!</b>", "parse_mode": "html"})

            return

        promokodlar = load_promokodlar()

        promokodlar[kod_p] = {"miqdor": miqdor_p, "limit": limit_p}

        save_promokodlar(promokodlar)

        valyuta_loc = read_file("admin/valyuta.txt", "so'm")

        # Promokod kanaliga yuborish

        promo_kanal = read_file("admin/promo_kanal.txt").strip()

        promo_msg = (

            f"🎟 <b>YANGI PROMOKOD!</b>\n\n"

            f"┌─────────────────\n"

            f"│ 🔑 Kod: <code>{kod_p}</code>\n"

            f"│ 💰 Miqdor: <b>{miqdor_p} {valyuta_loc}</b>\n"

            f"│ 🔢 Foydalanish: <b>{limit_p} marta</b>\n"

            f"└─────────────────\n\n"

            f"⚡️ Tez foydalaning, cheklangan!"

        )

        if promo_kanal:

            bot("sendMessage", {"chat_id": promo_kanal, "text": promo_msg, "parse_mode": "html"})

        bot("sendMessage", {

            "chat_id": cid,

            "text": (f"✅ <b>Promokod yaratildi!</b>\n\n"

                     f"🎟 Kod: <code>{kod_p}</code>\n"

                     f"💰 Miqdor: {miqdor_p} {valyuta_loc}\n"

                     f"🔢 Limit: {limit_p} marta"

                     + (f"\n📢 Kanalga yuborildi!" if promo_kanal else "\n⚠️ Promokod kanali sozlanmagan")),

            "parse_mode": "html", "reply_markup": panel

        })

        delete_file(f"step/{cid}.step")

        return

    if data == "promo_royxat" and is_admin(cid2):

        promokodlar = load_promokodlar()

        if not promokodlar:

            txt = "📂 <b>Promokodlar yo'q!</b>"

        else:

            txt = "<b>🎟 Promokodlar ro'yxati:</b>\n\n"

            for k, v in promokodlar.items():

                txt += f"• <code>{k}</code> — {v['miqdor']} {valyuta} | {v['limit']} qoldi\n"

        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

            "text": txt, "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "◀️ Orqaga", "callback_data": "promo_bosh"}]

            ]})})

        return

    if data == "promo_tozalash" and is_admin(cid2):

        save_promokodlar({})

        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

            "text": "✅ <b>Barcha promokodlar o'chirildi.</b>", "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "◀️ Orqaga", "callback_data": "promo_bosh"}]

            ]})})

        return

    if data == "promo_bosh" and is_admin(cid2):

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        promokodlar = load_promokodlar()

        bot("sendMessage", {

            "chat_id": cid2,

            "text": f"🎟 <b>Promokodlar boshqaruvi</b>\n\nFaol promokodlar: <b>{len(promokodlar)} ta</b>",

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "➕ Yangi promokod", "callback_data": "promo_yaratish"}],

                [{"text": "📋 Ro'yxat", "callback_data": "promo_royxat"}],

                [{"text": "🗑 Barchasini o'chirish", "callback_data": "promo_tozalash"}],

            ]})

        })

        return

    # ============================================================

    # PREMIUM — FOYDALANUVCHI UCHUN

    # ============================================================

    if data == "premium_buy" and cid2:

        prem_narx = get_premium_narx()

        prem_kun  = get_premium_kun()

        stars_n   = get_stars_narx()

        karta     = get_karta()

        pul2_int  = 0

        try:

            pul2_int = int(float(pul2))

        except:

            pass

        prem = is_premium(cid2)

        prem_badge = "✅ Aktiv" if prem else "❌ Faol emas"

        prem_exp_txt = ""

        if prem:

            exp_raw = read_file(f"premium/{cid2}.txt")

            try:

                exp_dt = datetime.fromisoformat(exp_raw)

                prem_exp_txt = f"\n├─ ⏰ <b>Tugash:</b> {exp_dt.strftime('%d.%m.%Y')}"

            except:

                pass

        # Premium info page — rasmdagi ko'rinish

        info_txt = (

            f"👑 <b>PREMIUM</b>\n"

            f"├\n"

            f"├─ 💎 <b>Status:</b> {prem_badge}{prem_exp_txt}\n"

            f"├─ 💰 <b>Narxi:</b> {prem_narx} {valyuta}\n"

            f"├─ 📅 <b>Muddat:</b> {prem_kun} kun\n"

            f"└─ ────────────────\n\n"

            f"👑 <b>PREMIUM foydalanuvchilar uchun taqdim qilinadigan imkoniyatlar va sovg'alar:</b>\n\n"

            f"— 🔥 Barcha botlar 2x arzon\n"

            f"— 🔍 Botni o'tkazish imkoniyati\n"

            f"— 💸 Pul o'tkazish imkoniyati\n"

            f"— 💯 Botlarning Bonus sifatida 40 kunlik to'lovi bepul"

        )

        key = []

        if not prem:

            if pul2_int >= prem_narx:

                key.append([{"text": f"💵 Balansdan sotib olish ({prem_narx} {valyuta})", "callback_data": "premium_balans"}])

            if stars_n:

                stars_kerak = max(1, prem_narx // stars_n)

                key.append([{"text": f"⭐ Stars bilan ({stars_kerak} Stars)", "callback_data": f"premium_stars={stars_kerak}"}])

            if karta:

                key.append([{"text": f"💳 Karta orqali to'lov", "callback_data": "premium_karta"}])

            if not key:

                key.append([{"text": "💰 Hisob to'ldirish", "callback_data": "hisob_toldirish"}])

        key.append([{"text": "◀️ Orqaga", "callback_data": "kabinet"}])

        bot("editMessageText", {

            "chat_id": cid2, "message_id": mid2,

            "text": info_txt,

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": key})

        })

        return

    if data == "premium_balans" and cid2:

        prem_narx = get_premium_narx()

        prem_kun  = get_premium_kun()

        pul2_int  = 0

        try:

            pul2_int = int(float(pul2))

        except:

            pass

        if pul2_int < prem_narx:

            bot("answerCallbackQuery", {"callback_query_id": qid,

                "text": "❌ Hisobingizda yetarli mablag' yo'q!", "show_alert": True})

            return

        write_file(f"pul/{cid2}.txt", str(pul2_int - prem_narx))

        exp_dt = premium_qo_shish(cid2, prem_kun)

        exp_str = exp_dt.strftime("%d.%m.%Y %H:%M")

        valyuta_loc = read_file("admin/valyuta.txt", "so'm")

        tarix_qoshish(cid2, "premium", prem_narx, f"Premium {prem_kun} kun sotib olindi", valyuta_loc)

        bot("editMessageText", {

            "chat_id": cid2, "message_id": mid2,

            "text": (f"💎 <b>Premium faollashdi!</b>\n\n"

                     f"📅 Muddat: <b>{prem_kun} kun</b>\n"

                     f"⏰ Tugash: <b>{exp_str}</b>\n"

                     f"💰 To'landi: <b>{prem_narx} {valyuta}</b>"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "✅ Yaxshi!", "callback_data": "kabinet"}]

            ]})

        })

        bot("sendMessage", {

            "chat_id": ADMIN_ID,

            "text": (f"💎 <b>Premium sotildi:</b>\n"

                     f"👤 <a href='tg://user?id={cid2}'>{cid2}</a>\n"

                     f"💰 {prem_narx} {valyuta}\n📅 {prem_kun} kun"),

            "parse_mode": "html"

        })

        return

    if data and data.startswith("premium_stars=") and cid2:

        stars_kerak = data.split("=")[1]

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        prem_kun = get_premium_kun()

        bot("sendInvoice", {

            "chat_id": cid2,

            "title": f"Premium {prem_kun} kun",

            "description": f"Bot Premium obunasi {prem_kun} kun",

            "payload": f"premium_{cid2}_{prem_kun}",

            "currency": "XTR",

            "prices": json.dumps([{"label": "Premium", "amount": int(stars_kerak)}]),

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": f"⭐ {stars_kerak} Stars to'lash", "pay": True}]

            ]})

        })

        return

    if data == "premium_karta" and cid2:

        karta = get_karta()

        prem_narx = get_premium_narx()

        prem_kun = get_premium_kun()

        if not karta:

            bot("answerCallbackQuery", {"callback_query_id": qid,

                "text": "Karta topilmadi!", "show_alert": True})

            return

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {

            "chat_id": cid2,

            "text": (f"💳 <b>Premium uchun karta orqali to'lov</b>\n\n"

                     f"🏦 <b>Karta nomi:</b> {karta.get('nom','')}\n"

                     f"💳 <b>Karta raqami:</b> <code>{karta.get('raqam','')}</code>\n"

                     f"👤 <b>Egasi:</b> {karta.get('egasi','')}\n"

                     f"💰 <b>Miqdor:</b> {prem_narx} {valyuta}\n\n"

                     f"📸 To'lovdan so'ng <b>chek rasmini yuboring:</b>"),

            "parse_mode": "html", "reply_markup": back

        })

        write_file(f"step/{cid2}.step", f"premium_chek={prem_narx}={prem_kun}")

        return

    if step and step.startswith("premium_chek=") and cid:

        parts_pc = step.split("=")

        prem_narx_s = parts_pc[1] if len(parts_pc) > 1 else "0"

        prem_kun_s  = parts_pc[2] if len(parts_pc) > 2 else "30"

        file_id = None

        if photos:

            file_id = photos[-1]["file_id"]

        elif doc:

            file_id = doc.get("file_id")

        if not file_id:

            bot("sendMessage", {"chat_id": cid,

                "text": "📸 <b>Iltimos, chek rasmini yuboring!</b>", "parse_mode": "html"})

            return

        user_link = f"<a href='tg://user?id={cid}'>{name} {familya}</a>"

        bot("sendPhoto", {

            "chat_id": ADMIN_ID,

            "photo": file_id,

            "caption": (f"💎 <b>Premium so'rovi (karta)</b>\n\n"

                        f"👤 {user_link} | ID: <code>{cid}</code>\n"

                        f"💰 {prem_narx_s} {valyuta} | 📅 {prem_kun_s} kun"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": f"✅ Premium berish ({prem_kun_s} kun)",

                  "callback_data": f"prem_ok={cid}={prem_kun_s}"}],

                [{"text": "❌ Rad etish", "callback_data": f"prem_rad={cid}"}]

            ]})

        })

        bot("sendMessage", {"chat_id": cid,

            "text": "✅ <b>Chekingiz qabul qilindi! Admin tekshirib Premium beради.</b>",

            "parse_mode": "html", "reply_markup": menu})

        delete_file(f"step/{cid}.step")

        return

    if data and data.startswith("prem_ok=") and is_admin(cid2):

        parts_po = data.split("=")

        _uid_p  = parts_po[1] if len(parts_po) > 1 else ""

        _kun_p  = parts_po[2] if len(parts_po) > 2 else "30"

        exp_dt = premium_qo_shish(_uid_p, int(_kun_p))

        exp_str = exp_dt.strftime("%d.%m.%Y")

        bot("editMessageCaption", {

            "chat_id": cid2, "message_id": mid2,

            "caption": f"✅ <b>Premium berildi!</b> {_uid_p} | {_kun_p} kun | {exp_str} gacha",

            "parse_mode": "html"

        })

        bot("sendMessage", {

            "chat_id": _uid_p,

            "text": (f"💎 <b>Premium faollashdi!</b>\n\n"

                     f"📅 Muddat: <b>{_kun_p} kun</b>\n"

                     f"⏰ Tugash: <b>{exp_str}</b>"),

            "parse_mode": "html", "reply_markup": make_menu()

        })

        return

    if data and data.startswith("prem_rad=") and is_admin(cid2):

        _uid_p = data.split("=")[1]

        bot("editMessageCaption", {

            "chat_id": cid2, "message_id": mid2,

            "caption": f"❌ <b>Rad etildi.</b> {_uid_p}",

            "parse_mode": "html"

        })

        bot("sendMessage", {

            "chat_id": _uid_p,

            "text": "❌ <b>Premium so'rovingiz rad etildi.</b>\n\nSabab uchun adminga murojaat qiling.",

            "parse_mode": "html", "reply_markup": make_menu()

        })

        return

    # ============================================================

    # ADMIN — PREMIUM SOZLASH

    # ============================================================

    if tx == "💎 Premium sozlash" and is_admin(cid):

        prem_narx = get_premium_narx()

        prem_kun  = get_premium_kun()

        bot("sendMessage", {

            "chat_id": cid,

            "text": (f"💎 <b>Premium sozlamalari</b>\n\n"

                     f"💰 Narx: <b>{prem_narx} {valyuta}</b>\n"

                     f"📅 Muddat: <b>{prem_kun} kun</b>"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "💰 Narxni o'zgartirish", "callback_data": "prem_narx_set"}],

                [{"text": "📅 Kunni o'zgartirish", "callback_data": "prem_kun_set"}],

                [{"text": "👤 Foydalanuvchiga premium", "callback_data": "prem_manual"}],

            ]})

        })

        return

    if data == "prem_narx_set" and is_admin(cid2):

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {"chat_id": cid2,

            "text": "💰 <b>Premium yangi narxini kiriting (so'mda):</b>",

            "parse_mode": "html", "reply_markup": back})

        write_file(f"step/{cid2}.step", "prem_narx_set")

        return

    if step == "prem_narx_set" and is_admin(cid):

        if not tx.isdigit():

            bot("sendMessage", {"chat_id": cid, "text": "⚠️ Faqat raqam!", "parse_mode": "html"})

            return

        write_file("admin/premium_narx.txt", tx)

        bot("sendMessage", {"chat_id": cid,

            "text": f"✅ <b>Premium narxi {tx} {valyuta} qilindi!</b>",

            "parse_mode": "html", "reply_markup": panel})

        delete_file(f"step/{cid}.step")

        return

    if data == "prem_kun_set" and is_admin(cid2):

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {"chat_id": cid2,

            "text": "📅 <b>Premium necha kunlik qilish (raqam):</b>",

            "parse_mode": "html", "reply_markup": back})

        write_file(f"step/{cid2}.step", "prem_kun_set")

        return

    if step == "prem_kun_set" and is_admin(cid):

        if not tx.isdigit():

            bot("sendMessage", {"chat_id": cid, "text": "⚠️ Faqat raqam!", "parse_mode": "html"})

            return

        write_file("admin/premium_kun.txt", tx)

        bot("sendMessage", {"chat_id": cid,

            "text": f"✅ <b>Premium muddati {tx} kun qilindi!</b>",

            "parse_mode": "html", "reply_markup": panel})

        delete_file(f"step/{cid}.step")

        return

    if data == "prem_manual" and is_admin(cid2):

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {"chat_id": cid2,

            "text": "👤 <b>Foydalanuvchi ID va kunni yuboring:</b>\n<code>ID KUN</code>\nMisol: <code>123456789 30</code>",

            "parse_mode": "html", "reply_markup": back})

        write_file(f"step/{cid2}.step", "prem_manual")

        return

    if step == "prem_manual" and is_admin(cid):

        parts_pm = tx.strip().split()

        if len(parts_pm) < 2 or not parts_pm[1].isdigit():

            bot("sendMessage", {"chat_id": cid,

                "text": "⚠️ <b>Format noto'g'ri! Misol: 123456789 30</b>", "parse_mode": "html"})

            return

        _uid_m = parts_pm[0]

        _kun_m = int(parts_pm[1])

        exp_dt = premium_qo_shish(_uid_m, _kun_m)

        exp_str = exp_dt.strftime("%d.%m.%Y")

        bot("sendMessage", {"chat_id": cid,

            "text": f"✅ <b>{_uid_m} ga {_kun_m} kun premium berildi! ({exp_str} gacha)</b>",

            "parse_mode": "html", "reply_markup": panel})

        bot("sendMessage", {"chat_id": _uid_m,

            "text": f"💎 <b>Sizga {_kun_m} kun Premium berildi!</b>\n📅 {exp_str} gacha",

            "parse_mode": "html"})

        delete_file(f"step/{cid}.step")

        return

    # ============================================================

    # ADMIN — KUNLIK BONUS SOZLASH

    # ============================================================

    if data == "bonus_sozlash" and is_admin(cid2):

        bonus = read_file("admin/kunlik_bonus.txt", "1000")

        bot("editMessageText", {

            "chat_id": cid2, "message_id": mid2,

            "text": f"🎁 <b>Kunlik bonus miqdori:</b> {bonus} {valyuta}",

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "✏️ O'zgartirish", "callback_data": "bonus_change"}],

                [{"text": "◀️ Orqaga", "callback_data": "boshqarish"}]

            ]})

        })

        return

    if data == "bonus_change" and is_admin(cid2):

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {"chat_id": cid2,

            "text": "🎁 <b>Yangi kunlik bonus miqdorini kiriting:</b>",

            "parse_mode": "html", "reply_markup": back})

        write_file(f"step/{cid2}.step", "bonus_change")

        return

    if step == "bonus_change" and is_admin(cid):

        if not tx.isdigit():

            bot("sendMessage", {"chat_id": cid, "text": "⚠️ Faqat raqam!", "parse_mode": "html"})

            return

        write_file("admin/kunlik_bonus.txt", tx)

        bot("sendMessage", {"chat_id": cid,

            "text": f"✅ <b>Kunlik bonus {tx} {valyuta} qilindi!</b>",

            "parse_mode": "html", "reply_markup": panel})

        delete_file(f"step/{cid}.step")

        return

    # ============================================================

    # 📤 PUL O'TKAZISH (ID orqali)

    # ============================================================

    if data == "pul_otkazish" and cid2:

        if not is_premium(cid2):

            bot("answerCallbackQuery", {"callback_query_id": qid,

                "text": "👑 Ushbu bo'lim PREMIUM foydalanuvchilar uchun!", "show_alert": True})

            bot("editMessageText", {

                "chat_id": cid2, "message_id": mid2,

                "text": ("🔒 <b>Ushbu bo'lim 👑 PREMIUM foydalanuvchilar uchun</b>\n\n"

                         "Premium obuna olib, ko'proq imkoniyatlardan foydalaning!"),

                "parse_mode": "html",

                "reply_markup": json.dumps({"inline_keyboard": [

                    [{"text": "👑 Premium olish", "callback_data": "premium_buy"}],

                    [{"text": "◀️ Orqaga", "callback_data": "kabinet"}]

                ]})

            })

            return

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {

            "chat_id": cid2,

            "text": ("📤 <b>Pul o'tkazish</b>\n\n"

                     "Qabul qiluvchining <b>Telegram ID</b> sini kiriting:\n"

                     "<i>ID ni bilish uchun /start bosib, kabinetdan ko'rish mumkin</i>"),

            "parse_mode": "html", "reply_markup": back

        })

        write_file(f"step/{cid2}.step", "otkazish_id")

        return

    # 1-qadam: ID kiritish → foydalanuvchi nomini topib ko'rsatish

    if step == "otkazish_id" and cid:

        _inp = tx.strip()

        if not _inp.isdigit():

            bot("sendMessage", {"chat_id": cid,

                "text": "⚠️ <b>Faqat raqam (Telegram ID) kiriting!</b>", "parse_mode": "html"})

            return

        target_id = _inp

        if target_id == cid:

            bot("sendMessage", {"chat_id": cid,

                "text": "⚠️ <b>O'zingizga pul o'tkaza olmaysiz!</b>", "parse_mode": "html"})

            return

        if not file_exists(f"pul/{target_id}.txt"):

            bot("sendMessage", {"chat_id": cid,

                "text": "❌ <b>Bu ID li foydalanuvchi botda topilmadi!</b>\n\nFoydalanuvchi avval botga /start bosishi kerak.",

                "parse_mode": "html"})

            return

        # Telegram dan ismini olishga harakat

        try:

            res = bot("getChat", {"chat_id": target_id})

            t_name = res.get("result", {}).get("first_name", "")

            t_last = res.get("result", {}).get("last_name", "") or ""

            t_user = res.get("result", {}).get("username", "") or ""

            full_name = f"{t_name} {t_last}".strip() or target_id

            uname_show = f" (@{t_user})" if t_user else ""

        except:

            full_name = target_id

            uname_show = ""

        write_file(f"step/{cid}.otkazish_id", target_id)

        write_file(f"step/{cid}.otkazish_name", full_name + uname_show)

        pul_cur = read_file(f"pul/{cid}.txt", "0")

        bot("sendMessage", {

            "chat_id": cid,

            "text": (f"✅ <b>Foydalanuvchi topildi!</b>\n\n"

                     f"👤 <b>Ismi:</b> {full_name}{uname_show}\n"

                     f"🆔 <b>ID:</b> <code>{target_id}</code>\n\n"

                     f"💵 <b>Sizning balansingiz:</b> {pul_cur} {valyuta}\n\n"

                     f"Qancha pul o'tkazmoqchisiz? (faqat raqam)"),

            "parse_mode": "html", "reply_markup": back

        })

        write_file(f"step/{cid}.step", "otkazish_summa")

        return

    # 2-qadam: summani kiritish → tasdiqlash oynasi

    if step == "otkazish_summa" and cid:

        _inp2 = tx.strip()

        if not _inp2.isdigit() or int(_inp2) <= 0:

            bot("sendMessage", {"chat_id": cid,

                "text": "⚠️ <b>To'g'ri miqdor kiriting (0 dan katta raqam)!</b>", "parse_mode": "html"})

            return

        summa_o  = int(_inp2)

        target_id   = read_file(f"step/{cid}.otkazish_id").strip()

        target_name = read_file(f"step/{cid}.otkazish_name").strip() or target_id

        pul_cur = 0

        try:

            pul_cur = int(float(read_file(f"pul/{cid}.txt", "0")))

        except:

            pass

        if summa_o > pul_cur:

            bot("sendMessage", {"chat_id": cid,

                "text": (f"❌ <b>Yetarli mablag' yo'q!</b>\n\n"

                         f"💵 Balansingiz: <b>{pul_cur} {valyuta}</b>\n"

                         f"💸 Kerak: <b>{summa_o} {valyuta}</b>"),

                "parse_mode": "html"})

            return

        # Tasdiqlash xabari — summa va target_id ni step faylga saqlaymiz

        write_file(f"step/{cid}.otkazish_summa", str(summa_o))

        bot("sendMessage", {

            "chat_id": cid,

            "text": (f"📤 <b>O'tkazishni tasdiqlang:</b>\n\n"

                     f"👤 <b>Qabul qiluvchi:</b> {target_name}\n"

                     f"🆔 <b>ID:</b> <code>{target_id}</code>\n"

                     f"💰 <b>O'tkazma miqdori:</b> {summa_o} {valyuta}\n"

                     f"💵 <b>O'tkazishdan so'ng balansingiz:</b> {pul_cur - summa_o} {valyuta}"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "✅ Tasdiqlash", "callback_data": "otkazish_tasdiqlash"}],

                [{"text": "❌ Bekor qilish", "callback_data": "otkazish_bekor"}]

            ]})

        })

        delete_file(f"step/{cid}.step")

        return

    # 3-qadam: Tasdiqlash bosildi → pulni o'tkazish

    if data == "otkazish_tasdiqlash" and cid2:

        target_id   = read_file(f"step/{cid2}.otkazish_id").strip()

        target_name = read_file(f"step/{cid2}.otkazish_name").strip() or target_id

        summa_str   = read_file(f"step/{cid2}.otkazish_summa").strip()

        if not target_id or not summa_str.isdigit():

            bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

                "text": "❌ <b>Xato! Qaytadan urinib ko'ring.</b>", "parse_mode": "html",

                "reply_markup": json.dumps({"inline_keyboard": [

                    [{"text": "◀️ Orqaga", "callback_data": "kabinet"}]

                ]})})

            return

        summa_ot = int(summa_str)

        # Yuboruvchi balansi yangi tekshiruv

        pul2_cur = 0

        try:

            pul2_cur = int(float(read_file(f"pul/{cid2}.txt", "0")))

        except:

            pass

        if summa_ot > pul2_cur:

            bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

                "text": (f"❌ <b>Mablag' yetarli emas!</b>\n\n"

                         f"💵 Balansingiz: {pul2_cur} {valyuta}"),

                "parse_mode": "html",

                "reply_markup": json.dumps({"inline_keyboard": [

                    [{"text": "◀️ Orqaga", "callback_data": "kabinet"}]

                ]})})

            return

        # Yuboruvchidan ayirish

        write_file(f"pul/{cid2}.txt", str(pul2_cur - summa_ot))

        # Qabul qiluvchiga qo'shish

        target_pul = 0

        try:

            target_pul = int(float(read_file(f"pul/{target_id}.txt", "0")))

        except:

            pass

        write_file(f"pul/{target_id}.txt", str(target_pul + summa_ot))

        # Tarix yozish

        valyuta_loc = read_file("admin/valyuta.txt", "so'm")

        tarix_qoshish(cid2, "chiqim", summa_ot, f"Pul o'tkazildi → {target_name} ({target_id})", valyuta_loc)

        tarix_qoshish(target_id, "qabul", summa_ot, f"Pul qabul qilindi ← ID: {cid2}", valyuta_loc)

        # Yuboruvchiga xabar

        bot("editMessageText", {

            "chat_id": cid2, "message_id": mid2,

            "text": (f"✅ <b>Pul muvaffaqiyatli o'tkazildi!</b>\n\n"

                     f"👤 <b>Qabul qiluvchi:</b> {target_name}\n"

                     f"🆔 <b>ID:</b> <code>{target_id}</code>\n"

                     f"💸 <b>O'tkazildi:</b> {summa_ot} {valyuta}\n"

                     f"💵 <b>Qolgan balans:</b> {pul2_cur - summa_ot} {valyuta}"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "◀️ Orqaga", "callback_data": "kabinet"}]

            ]})

        })

        # Qabul qiluvchiga bildirishnoma

        try:

            sender_res = bot("getChat", {"chat_id": cid2})

            s_name = sender_res.get("result", {}).get("first_name", "")

            s_last = sender_res.get("result", {}).get("last_name", "") or ""

            s_user = sender_res.get("result", {}).get("username", "") or ""

            sender_full = f"{s_name} {s_last}".strip() or str(cid2)

            sender_uname = f" (@{s_user})" if s_user else ""

        except:

            sender_full = str(cid2)

            sender_uname = ""

        bot("sendMessage", {

            "chat_id": target_id,

            "text": (f"💸 <b>Hisobingizga pul tushdi!</b>\n\n"

                     f"👤 <b>Yuboruvchi:</b> {sender_full}{sender_uname}\n"

                     f"🆔 <b>ID:</b> <code>{cid2}</code>\n"

                     f"💰 <b>Miqdor:</b> +{summa_ot} {valyuta}\n"

                     f"💵 <b>Yangi balans:</b> {target_pul + summa_ot} {valyuta}"),

            "parse_mode": "html"

        })

        # Temp fayllarni tozalash

        delete_file(f"step/{cid2}.otkazish_id")

        delete_file(f"step/{cid2}.otkazish_name")

        delete_file(f"step/{cid2}.otkazish_summa")

        return

    if data == "otkazish_bekor" and cid2:

        delete_file(f"step/{cid2}.otkazish_id")

        delete_file(f"step/{cid2}.otkazish_name")

        delete_file(f"step/{cid2}.otkazish_summa")

        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

            "text": "❌ <b>Pul o'tkazish bekor qilindi.</b>",

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "◀️ Orqaga", "callback_data": "kabinet"}]

            ]})})

        return

    # Eski otkazish_ok handler (xavfsizlik uchun saqlanadi)

    if data and data.startswith("otkazish_ok=") and cid2:

        parts_ot = data.split("=")

        target_ot = parts_ot[1] if len(parts_ot) > 1 else ""

        try:

            summa_ot = int(parts_ot[2]) if len(parts_ot) > 2 else 0

        except:

            summa_ot = 0

        if not target_ot or summa_ot <= 0:

            return

        pul2_cur = 0

        try:

            pul2_cur = int(float(read_file(f"pul/{cid2}.txt", "0")))

        except:

            pass

        if summa_ot > pul2_cur:

            bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

                "text": f"❌ <b>Mablag' yetarli emas!</b>", "parse_mode": "html",

                "reply_markup": json.dumps({"inline_keyboard": [[{"text": "◀️ Orqaga", "callback_data": "kabinet"}]]})})

            return

        write_file(f"pul/{cid2}.txt", str(pul2_cur - summa_ot))

        target_pul = 0

        try:

            target_pul = int(float(read_file(f"pul/{target_ot}.txt", "0")))

        except:

            pass

        write_file(f"pul/{target_ot}.txt", str(target_pul + summa_ot))

        valyuta_loc = read_file("admin/valyuta.txt", "so'm")

        tarix_qoshish(cid2, "chiqim", summa_ot, f"Pul o'tkazish → {target_ot}", valyuta_loc)

        tarix_qoshish(target_ot, "qabul", summa_ot, f"Pul qabul qilindi ← {cid2}", valyuta_loc)

        bot("editMessageText", {

            "chat_id": cid2, "message_id": mid2,

            "text": (f"✅ <b>Pul o'tkazildi!</b>\n\n"

                     f"🆔 Qabul qildi: <code>{target_ot}</code>\n"

                     f"💰 Miqdor: <b>{summa_ot} {valyuta}</b>"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "◀️ Orqaga", "callback_data": "kabinet"}]]})

        })

        bot("sendMessage", {

            "chat_id": target_ot,

            "text": (f"💸 <b>Hisobingizga pul tushdi!</b>\n\n"

                     f"💰 Miqdor: <b>{summa_ot} {valyuta}</b>\n"

                     f"👤 Yuboruvchi ID: <code>{cid2}</code>"),

            "parse_mode": "html"

        })

        return

    # ============================================================

    # 💳 Hisob to'ldirish (foydalanuvchi menyu tugmasi)

    # ============================================================

    if tx == "💳 Hisob to'ldirish" and cid and joinchat(cid):

        karta     = get_karta()

        stars_n   = get_stars_narx()

        if not karta and not stars_n:

            bot("sendMessage", {"chat_id": cid,

                "text": "⚠️ <b>Hozircha hech qanday to'lov tizimi ulanmagan.</b>",

                "parse_mode": "html"})

            return

        key = []

        if karta:

            key.append([{"text": f"💳 {karta.get('nom','Karta')} orqali to'lov",

                         "callback_data": "tolov_karta"}])

        if stars_n:

            key.append([{"text": f"⭐ Telegram Stars (1 ⭐ = {stars_n} {valyuta})",

                         "callback_data": "tolov_stars"}])

        bot("sendMessage", {"chat_id": cid, "text": "<b>💳 To'lov turini tanlang:</b>",

            "parse_mode": "html", "reply_markup": json.dumps({"inline_keyboard": key})})

        return

    # callback: hisob_toldirish (inline kabinetdan)

    if data == "hisob_toldirish" and cid2:

        karta   = get_karta()

        stars_n = get_stars_narx()

        if not karta and not stars_n:

            bot("answerCallbackQuery", {"callback_query_id": qid,

                "text": "Hozircha to'lov tizimlari ulanmagan!", "show_alert": True})

            return

        key = []

        if karta:

            key.append([{"text": f"💳 {karta.get('nom','Karta')} orqali to'lov",

                         "callback_data": "tolov_karta"}])

        if stars_n:

            key.append([{"text": f"⭐ Telegram Stars (1 ⭐ = {stars_n} {valyuta})",

                         "callback_data": "tolov_stars"}])

        bot("editMessageReplyMarkup", {"chat_id": cid2, "message_id": mid2,

            "reply_markup": json.dumps({"inline_keyboard": key})})

        return

    # callback: tolov_karta

    if data == "tolov_karta" and cid2:

        karta = get_karta()

        if not karta:

            bot("answerCallbackQuery", {"callback_query_id": qid,

                "text": "Karta ma'lumotlari topilmadi!", "show_alert": True})

            return

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {

            "chat_id": cid2,

            "text": (f"💳 <b>{karta.get('nom','Karta')} orqali to'lov</b>\n\n"

                     f"Hisobingizga qancha pul qo'shmoqchisiz?\n"

                     f"<i>Faqat raqam yuboring (masalan: 50000)</i>"),

            "parse_mode": "html", "reply_markup": back

        })

        write_file(f"step/{cid2}.step", "karta_summa")

        return

    if step == "karta_summa" and cid:

        if not tx.isdigit():

            bot("sendMessage", {"chat_id": cid,

                "text": "⚠️ <b>Faqat raqam kiriting!</b>", "parse_mode": "html"})

            return

        karta = get_karta()

        if not karta:

            bot("sendMessage", {"chat_id": cid, "text": "Karta topilmadi.", "parse_mode": "html"})

            delete_file(f"step/{cid}.step")

            return

        write_file(f"step/{cid}.karta_summa", tx)

        bot("sendMessage", {

            "chat_id": cid,

            "text": (f"💳 <b>To'lov ma'lumotlari:</b>\n\n"

                     f"🏦 <b>Karta nomi:</b> {karta.get('nom','')}\n"

                     f"💳 <b>Karta raqami:</b> <code>{karta.get('raqam','')}</code>\n"

                     f"👤 <b>Karta egasi:</b> {karta.get('egasi','')}\n"

                     f"💰 <b>To'lov miqdori:</b> {tx} {valyuta}\n\n"

                     f"Yuqoridagi kartaga <b>{tx} {valyuta}</b> o'tkazib,\n"

                     f"📸 <b>Chek rasmini yuboring:</b>"),

            "parse_mode": "html", "reply_markup": back

        })

        write_file(f"step/{cid}.step", "karta_chek")

        return

    if step == "karta_chek" and cid:

        summa = read_file(f"step/{cid}.karta_summa", "0")

        file_id = None

        if photos:

            file_id = photos[-1]["file_id"]

        elif doc:

            file_id = doc.get("file_id")

        if not file_id:

            bot("sendMessage", {"chat_id": cid,

                "text": "📸 <b>Iltimos, chek rasmini yuboring!</b>", "parse_mode": "html"})

            return

        user_link = f"<a href='tg://user?id={cid}'>{name} {familya}</a>"

        uname_txt = f"@{username}" if username else "username yo'q"

        bot("sendPhoto", {

            "chat_id": ADMIN_ID,

            "photo": file_id,

            "caption": (f"🔔 <b>Yangi hisob to'ldirish so'rovi</b>\n\n"

                        f"👤 <b>Foydalanuvchi:</b> {user_link}\n"

                        f"🆔 <b>ID:</b> <code>{cid}</code>\n"

                        f"📛 <b>Username:</b> {uname_txt}\n"

                        f"💰 <b>Miqdor:</b> {summa} {valyuta}\n\n"

                        f"✅ Tasdiqlash yoki ❌ Bekor qilish?"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": f"✅ Tasdiqlash (+{summa} {valyuta})",

                  "callback_data": f"tasdiqlash={cid}={summa}"}],

                [{"text": "❌ Bekor qilish",

                  "callback_data": f"bekor={cid}={summa}"}]

            ]})

        })

        bot("sendMessage", {

            "chat_id": cid,

            "text": ("✅ <b>Chekingiz qabul qilindi!</b>\n\n"

                     "Admin tekshirib, hisobingizni to'ldiradi.\n"

                     "<i>Kuting, tez orada javob keladi.</i>"),

            "parse_mode": "html", "reply_markup": menu

        })

        delete_file(f"step/{cid}.step")

        delete_file(f"step/{cid}.karta_summa")

        return

    if data and data.startswith("tasdiqlash=") and is_admin(cid2):

        parts  = data.split("=")

        _uid   = parts[1] if len(parts) > 1 else ""

        _summa = parts[2] if len(parts) > 2 else "0"

        _p = read_file(f"pul/{_uid}.txt", "0")

        try:

            write_file(f"pul/{_uid}.txt", str(int(float(_p)) + int(float(_summa))))

        except:

            pass

        valyuta_loc = read_file("admin/valyuta.txt", "so'm")

        tarix_qoshish(_uid, "kirim", int(float(_summa)), "Karta orqali hisob to'ldirish", valyuta_loc)

        kiritgan_pul_qoshish(_uid, int(float(_summa)))

        bot("editMessageCaption", {

            "chat_id": cid2, "message_id": mid2,

            "caption": f"✅ <b>Tasdiqlandi!</b> {_uid} ga {_summa} {valyuta} qo'shildi.",

            "parse_mode": "html"

        })

        bot("sendMessage", {

            "chat_id": _uid,

            "text": (f"✅ <b>To'lovingiz tasdiqlandi!</b>\n\n"

                     f"Hisobingizga <b>{_summa} {valyuta}</b> qo'shildi! 🎉"),

            "parse_mode": "html", "reply_markup": menu

        })

        return

    if data and data.startswith("bekor=") and is_admin(cid2):

        parts  = data.split("=")

        _uid   = parts[1] if len(parts) > 1 else ""

        _summa = parts[2] if len(parts) > 2 else "0"

        bot("editMessageCaption", {

            "chat_id": cid2, "message_id": mid2,

            "caption": f"❌ <b>Bekor qilindi.</b> {_uid} — {_summa} {valyuta}",

            "parse_mode": "html"

        })

        bot("sendMessage", {

            "chat_id": _uid,

            "text": ("❌ <b>To'lovingiz tasdiqlanmadi.</b>\n\n"

                     "Muammo bo'lsa admin bilan bog'laning."),

            "parse_mode": "html", "reply_markup": menu

        })

        return

    # callback: tolov_stars

    if data == "tolov_stars" and cid2:

        stars_n = get_stars_narx()

        if not stars_n:

            bot("answerCallbackQuery", {"callback_query_id": qid,

                "text": "Stars to'lov tizimi ulanmagan!", "show_alert": True})

            return

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {

            "chat_id": cid2,

            "text": (f"⭐ <b>Telegram Stars orqali to'lov</b>\n\n"

                     f"1 ⭐ = <b>{stars_n} {valyuta}</b>\n\n"

                     f"Nechta Stars bilan hisob to'ldirmoqchisiz?\n"

                     f"<i>Raqam yuboring (masalan: 10)</i>"),

            "parse_mode": "html", "reply_markup": back

        })

        write_file(f"step/{cid2}.step", "stars_son")

        return

    if step == "stars_son" and cid:

        if not tx.isdigit() or int(tx) < 1:

            bot("sendMessage", {"chat_id": cid,

                "text": "⚠️ <b>Kamida 1 ta Stars kiriting!</b>", "parse_mode": "html"})

            return

        stars_n    = get_stars_narx()

        stars_son  = int(tx)

        jami_pul   = stars_son * stars_n

        bot("sendInvoice", {

            "chat_id": cid,

            "title": "Hisob to'ldirish",

            "description": f"{stars_son} Stars → {jami_pul} {valyuta} hisob to'ldirish",

            "payload": f"stars_{cid}_{stars_son}",

            "currency": "XTR",

            "prices": json.dumps([{"label": "To'lov", "amount": stars_son}]),

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": f"⭐ {stars_son} Stars to'lash", "pay": True}]

            ]})

        })

        delete_file(f"step/{cid}.step")

        return

    # ============================================================

    # 💳 TO'LOV TIZIMLARI (Admin panel)

    # ============================================================

    if tx == "💳 To'lov tizimlari" and is_admin(cid):

        karta   = get_karta()

        stars_n = get_stars_narx()

        karta_status = f"✅ Ulangan ({karta.get('nom','')})" if karta else "❌ Ulanmagan"

        stars_status = f"✅ Ulangan (1⭐={stars_n} {valyuta})" if stars_n else "❌ Ulanmagan"

        bot("sendMessage", {

            "chat_id": cid,

            "text": (f"<b>💳 To'lov tizimlari</b>\n\n"

                     f"💳 Karta: {karta_status}\n"

                     f"⭐ Stars: {stars_status}"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "💳 Karta to'lov tizimi", "callback_data": "admin_karta"}],

                [{"text": "⭐ Stars to'lov tizimi", "callback_data": "admin_stars"}],

                [{"text": "🎁 Kunlik bonus", "callback_data": "bonus_sozlash"}],

                [{"text": "Yopish", "callback_data": "boshqarish"}]

            ]})

        })

        return

    if data == "admin_karta" and is_admin(cid2):

        karta = get_karta()

        if karta:

            bot("editMessageText", {

                "chat_id": cid2, "message_id": mid2,

                "text": (f"<b>💳 Karta ma'lumotlari:</b>\n\n"

                         f"🏦 Nomi: {karta.get('nom','')}\n"

                         f"💳 Raqami: <code>{karta.get('raqam','')}</code>\n"

                         f"👤 Egasi: {karta.get('egasi','')}"),

                "parse_mode": "html",

                "reply_markup": json.dumps({"inline_keyboard": [

                    [{"text": "✏️ O'zgartirish", "callback_data": "karta_qoshish"}],

                    [{"text": "🗑 O'chirish", "callback_data": "karta_ochirish"}],

                    [{"text": "◀️ Orqaga", "callback_data": "tolov_bosh"}]

                ]})

            })

        else:

            bot("editMessageText", {

                "chat_id": cid2, "message_id": mid2,

                "text": "<b>💳 Karta to'lov tizimi ulanmagan.</b>",

                "parse_mode": "html",

                "reply_markup": json.dumps({"inline_keyboard": [

                    [{"text": "➕ Karta qo'shish", "callback_data": "karta_qoshish"}],

                    [{"text": "◀️ Orqaga", "callback_data": "tolov_bosh"}]

                ]})

            })

        return

    if data == "karta_ochirish" and is_admin(cid2):

        delete_karta()

        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

            "text": "✅ <b>Karta o'chirildi.</b>", "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "◀️ Orqaga", "callback_data": "admin_karta"}]]})})

        return

    if data == "karta_qoshish" and is_admin(cid2):

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {

            "chat_id": cid2,

            "text": ("💳 <b>Karta qo'shish</b>\n\n"

                     "<b>1-qadam:</b> Karta nomini yuboring.\n"

                     "<i>Namuna: Uzcard, Humo, Visa...</i>"),

            "parse_mode": "html", "reply_markup": boshqarish_kb

        })

        write_file(f"step/{cid2}.step", "karta_nom")

        return

    if step == "karta_nom" and is_admin(cid) and text:

        write_file(f"step/{cid}.karta_nom", text)

        bot("sendMessage", {"chat_id": cid,

            "text": f"✅ <b>Nom: {text}</b>\n\n<b>2-qadam:</b> Karta raqamini yuboring:",

            "parse_mode": "html", "reply_markup": back})

        write_file(f"step/{cid}.step", "karta_raqam")

        return

    if step == "karta_raqam" and is_admin(cid) and text:

        write_file(f"step/{cid}.karta_raqam", text)

        bot("sendMessage", {"chat_id": cid,

            "text": f"✅ <b>Raqam: {text}</b>\n\n<b>3-qadam:</b> Karta egasining ismini yuboring:",

            "parse_mode": "html", "reply_markup": back})

        write_file(f"step/{cid}.step", "karta_egasi")

        return

    if step == "karta_egasi" and is_admin(cid) and text:

        _nom   = read_file(f"step/{cid}.karta_nom")

        _raqam = read_file(f"step/{cid}.karta_raqam")

        save_karta({"nom": _nom, "raqam": _raqam, "egasi": text})

        bot("sendMessage", {

            "chat_id": cid,

            "text": (f"✅ <b>Karta muvaffaqiyatli qo'shildi!</b>\n\n"

                     f"🏦 Nomi: {_nom}\n"

                     f"💳 Raqami: <code>{_raqam}</code>\n"

                     f"👤 Egasi: {text}"),

            "parse_mode": "html", "reply_markup": panel

        })

        delete_file(f"step/{cid}.step")

        delete_file(f"step/{cid}.karta_nom")

        delete_file(f"step/{cid}.karta_raqam")

        return

    if data == "admin_stars" and is_admin(cid2):

        stars_n = get_stars_narx()

        if stars_n:

            bot("editMessageText", {

                "chat_id": cid2, "message_id": mid2,

                "text": (f"<b>⭐ Stars to'lov tizimi</b>\n\n"

                         f"1 Stars = <b>{stars_n} {valyuta}</b>"),

                "parse_mode": "html",

                "reply_markup": json.dumps({"inline_keyboard": [

                    [{"text": "✏️ Narxni o'zgartirish", "callback_data": "stars_qoshish"}],

                    [{"text": "🗑 O'chirish", "callback_data": "stars_ochirish"}],

                    [{"text": "◀️ Orqaga", "callback_data": "tolov_bosh"}]

                ]})

            })

        else:

            bot("editMessageText", {

                "chat_id": cid2, "message_id": mid2,

                "text": "<b>⭐ Stars to'lov tizimi ulanmagan.</b>",

                "parse_mode": "html",

                "reply_markup": json.dumps({"inline_keyboard": [

                    [{"text": "➕ Stars tizimini ulash", "callback_data": "stars_qoshish"}],

                    [{"text": "◀️ Orqaga", "callback_data": "tolov_bosh"}]

                ]})

            })

        return

    if data == "stars_ochirish" and is_admin(cid2):

        delete_stars()

        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

            "text": "✅ <b>Stars tizimi o'chirildi.</b>", "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "◀️ Orqaga", "callback_data": "admin_stars"}]]})})

        return

    if data == "stars_qoshish" and is_admin(cid2):

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {

            "chat_id": cid2,

            "text": ("⭐ <b>Stars to'lov tizimi</b>\n\n"

                     "1 ta Stars uchun narxni yuboring (valyutada).\n"

                     f"<i>Namuna: 1000 (ya'ni 1 ⭐ = 1000 {valyuta})</i>"),

            "parse_mode": "html", "reply_markup": boshqarish_kb

        })

        write_file(f"step/{cid2}.step", "stars_narx_set")

        return

    if step == "stars_narx_set" and is_admin(cid):

        if not tx.isdigit():

            bot("sendMessage", {"chat_id": cid, "text": "⚠️ <b>Faqat raqam kiriting!</b>", "parse_mode": "html"})

            return

        write_file("admin/stars.txt", tx)

        bot("sendMessage", {

            "chat_id": cid,

            "text": f"✅ <b>Stars to'lov tizimi ulandi!</b>\n\n1 ⭐ = <b>{tx} {valyuta}</b>",

            "parse_mode": "html", "reply_markup": panel

        })

        delete_file(f"step/{cid}.step")

        return

    if data == "tolov_bosh" and is_admin(cid2):

        karta   = get_karta()

        stars_n = get_stars_narx()

        karta_status = f"✅ Ulangan ({karta.get('nom','')})" if karta else "❌ Ulanmagan"

        stars_status = f"✅ Ulangan (1⭐={stars_n} {valyuta})" if stars_n else "❌ Ulanmagan"

        bot("editMessageText", {

            "chat_id": cid2, "message_id": mid2,

            "text": (f"<b>💳 To'lov tizimlari</b>\n\n"

                     f"💳 Karta: {karta_status}\n"

                     f"⭐ Stars: {stars_status}"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "💳 Karta to'lov tizimi", "callback_data": "admin_karta"}],

                [{"text": "⭐ Stars to'lov tizimi", "callback_data": "admin_stars"}],

                [{"text": "🎁 Kunlik bonus", "callback_data": "bonus_sozlash"}],

                [{"text": "Yopish", "callback_data": "boshqarish"}]

            ]})

        })

        return

    # ============================================================

    # ➕ Yangi bot yaratish

    # ============================================================

    if tx == "➕ Yangi bot yaratish" and cid and joinchat(cid):

        _send_bot_list(cid, 0, pul, valyuta, is_premium(cid))

        return

    if data == "orqaga" and cid2:

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        _send_bot_list(cid2, 0, pul2, valyuta, is_premium(cid2))

        return

    if data and data.startswith("botpage=") and cid2:

        try:

            _pg = int(data.split("=")[1])

        except:

            _pg = 0

        _send_bot_list(cid2, _pg, pul2, valyuta, is_premium(cid2), edit=True, msg_id=mid2)

        return

    if data and data.lower().startswith("dots="):

        parts    = data.split("=")

        _narx_v  = parts[1] if len(parts) > 1 else "0"

        _turi_v  = parts[2] if len(parts) > 2 else ""

        _kun_v   = parts[3] if len(parts) > 3 else "31"

        _prem    = is_premium(cid2)

        try:

            _asl_narx   = int(float(_narx_v))

            _final_narx = max(0, _asl_narx // 2) if _prem else _asl_narx

            _asl_kun    = int(float(_kun_v))

            _final_kun  = _asl_kun + 40 if _prem else _asl_kun

        except:

            _asl_narx = 0; _final_narx = 0; _asl_kun = 31; _final_kun = 31

        if _prem and _asl_narx > 0:

            _narx_txt = f"<s>{_asl_narx}</s> → <b>{_final_narx} {valyuta}</b> 👑 2x arzon!"

            _kun_txt  = f"<b>{_final_kun} kun</b> <i>(+40 kun bepul 👑)</i>"

        else:

            _narx_txt = f"<b>{_asl_narx} {valyuta}</b>"

            _kun_txt  = f"<b>{_asl_kun} kun</b>"

        bot("editMessageText", {

            "chat_id": cid2, "message_id": mid2,

            "text": (f"🤖 <b>Bot turi:</b> {_turi_v}\n"

                     f"💰 <b>Narxi:</b> {_narx_txt}\n"

                     f"📅 <b>Muddat:</b> {_kun_txt}\n\n"

                     f"💵 <b>Balansingiz:</b> {pul2} {valyuta}"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "✅ Sotib olish",

                  "callback_data": f"buy={_final_narx}={_turi_v}={_final_kun}"}],

                [{"text": "◀️ Orqaga", "callback_data": "orqaga"}]

            ]})

        })

        return

    if data and data.lower().startswith("buy="):

        parts   = data.split("=")

        _narx_v = parts[1] if len(parts) > 1 else "0"

        _turi_v = parts[2] if len(parts) > 2 else ""

        _kun_v  = parts[3] if len(parts) > 3 else "31"

        try:

            _p2_int   = int(float(pul2))

            _narx_int = int(float(_narx_v))

        except:

            _p2_int = 0; _narx_int = 0

        if _p2_int >= _narx_int:

            bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

            bot("sendMessage", {"chat_id": cid2,

                "text": "🔑 <b>Botingizning tokenini yuboring.</b>\n\n<i>@BotFather dan olishingiz mumkin.</i>",

                "parse_mode": "html", "reply_markup": back})

            write_file(f"step/{cid2}.step", f"bots={_turi_v}={_narx_v}={_kun_v}")

        else:

            bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

                "text": "😞 <b>Hisobingizda yetarli mablag' yo'q.</b>",

                "parse_mode": "html",

                "reply_markup": json.dumps({"inline_keyboard": [

                    [{"text": "💳 Hisob to'ldirish", "callback_data": "hisob_toldirish"}]

                ]})})

        return

    if step and step.startswith("bots="):

        parts   = step.split("=")

        _turi_v = parts[1]

        _narx_v = int(float(parts[2])) if len(parts) > 2 else 0

        _kun_v  = parts[3] if len(parts) > 3 else "31"

        if not (tx and ":" in tx):

            bot("sendMessage", {"chat_id": cid,

                "text": "⚠️ <b>Token noto'g'ri. Qayta yuboring:</b>", "parse_mode": "html"})

            return

        msg      = bot("sendMessage", {"chat_id": cid, "text": "⏱ <b>Tekshirilmoqda...</b>", "parse_mode": "html"})

        sent_mid = msg.get("result", {}).get("message_id", mid)

        try:

            _me_res = requests.get(f"https://api.telegram.org/bot{tx}/getMe", timeout=10).json()

            _uname  = _me_res.get("result", {}).get("username", "")

        except:

            _uname = ""

        if not _uname:

            bot("editMessageText", {"chat_id": cid, "message_id": sent_mid,

                "text": "⛔️ <b>Token yaroqsiz! Qayta yuboring:</b>", "parse_mode": "html"})

            return

        shablon = read_file(f"bot/{_turi_v}/kod.py")

        if not shablon:

            bot("editMessageText", {"chat_id": cid, "message_id": sent_mid,

                "text": "\u26d4\ufe0f <b>Bot turi uchun kod topilmadi!</b>", "parse_mode": "html"})

            return

        # Universal: Flask, aiogram, telebot, polling - barchasini qollab-quvvatlash

        final_code = prepare_bot_code(shablon, tx, cid)

        # Har foydalanuvchi uchun alohida xotira papkasi

        bot_dir = f"bots/{_uname}"

        os.makedirs(bot_dir, exist_ok=True)

        os.makedirs(f"{bot_dir}/data", exist_ok=True)

        # Kod ichida DATA_DIR ni foydalanuvchi papkasiga moslashtirish

        final_code = final_code.replace('"data/"', f'"bots/{_uname}/data/"')

        final_code = final_code.replace("'data/'", f'"bots/{_uname}/data/"')

        final_code = final_code.replace('"data/db.json"', f'"bots/{_uname}/data/db.json"')

        write_file(f"{bot_dir}/bot.py", final_code)

        write_file(f"{bot_dir}/owner.txt", cid)

        write_file(f"{bot_dir}/turi.txt", _turi_v)

        append_file(f"baza/{cid}/bots.txt", f"\n{_uname}")

        append_file(f"baza/{cid}/bots2.txt", f"\n{_turi_v}")

        kunlik_insert(user_id=cid, useri=_uname, turi=_turi_v, tokeni=tx,

            vaqti=f"{sana()} | {soat()}", narxi=str(_narx_v), kun=_kun_v, avto="❌")

        _p_cur = read_file(f"pul/{cid}.txt", "0")

        try:

            write_file(f"pul/{cid}.txt", str(int(float(_p_cur)) - _narx_v))

        except:

            pass

        ok, err_msg = start_user_bot(_uname)

        if ok:

            status_text = "✅ Bot muvaffaqiyatli ishga tushdi!"

            err_block = ""

        else:

            err_lines = [l for l in err_msg.split("\n") if l.strip() and

                         ("Error" in l or "error" in l or "Traceback" in l or

                          "No module" in l or "invalid" in l or "Token" in l)]

            short_err = err_lines[-1] if err_lines else err_msg[-200:]

            err_block = f"\n\n❌ <b>Xato:</b>\n<code>{short_err}</code>"

        bot("editMessageText", {"chat_id": cid, "message_id": sent_mid,

            "text": (f"🎉 <b>@{_uname} tayyor!</b>\n\n"

                     f"🤖 <b>Tur:</b> {_turi_v}\n"

                     f"📅 <b>Muddat:</b> {_kun_v} kun\n\n{status_text}{err_block}"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "➡️ Botga o'tish", "url": f"https://t.me/{_uname}"}],

                [{"text": "◀️ Orqaga", "callback_data": "orqaga"}]

            ]})})

        delete_file(f"step/{cid}.step")

        return

    # ============================================================

    # 📢 Kanallarni sozlash

    # ============================================================

    if tx == "📢 Kanallarni sozlash" and is_admin(cid):

        pk = read_file("admin/promo_kanal.txt").strip()

        pk_status = f"✅ {pk}" if pk else "❌ Sozlanmagan"

        maj_kanal = read_file("admin/kanal.txt").strip()

        maj_count = len([l for l in maj_kanal.split("\n") if l.strip()]) if maj_kanal else 0

        bot("sendMessage", {

            "chat_id": cid,

            "text": (f"📢 <b>Kanallar boshqaruvi</b>\n\n"

                     f"🔐 Majburiy obunalar: <b>{maj_count} ta kanal</b>\n"

                     f"🎟 Promokod kanali: <b>{pk_status}</b>"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "🔐 Majburiy obunalar", "callback_data": "majburiy_kanal"}],

                [{"text": "🎟 Promokod kanali", "callback_data": "promo_kanal_menu"}],

                [{"text": "Yopish", "callback_data": "boshqarish"}]

            ]})

        })

        return

    # ============================================================

    # 🗄 Boshqarish

    # ============================================================

    if tx == "🗄 Boshqarish" and is_admin(cid):
        if str(cid) == str(ADMIN_ID):
            # Asosiy admin — to'liq panel
            bot("sendMessage", {"chat_id": cid, "text": "<b>Admin paneliga xush kelibsiz!</b>",
                "parse_mode": "html", "reply_markup": panel})
            delete_file(f"step/{cid}.step")
            delete_file("step/alijonov.txt")
            return
        else:
            # Sub-admin — ruxsatga qarab panel (pastdagi handler ishlaydi)
            adminlar = load_adminlar()
            a     = adminlar.get(str(cid), {})
            perms = a.get("perms", {})
            PERM_MAP_L = {
                "📢 Kanallarni sozlash":         "kanallar",
                "📊 Statistika":                 "statistika",
                "✉ Xabar Yuborish":              "xabar_yuborish",
                "⚙ Asosiy sozlamalar":            "asosiy_sozlamalar",
                "💳 To'lov tizimlari":           "tolov_tizimlari",
                "🤖 Bot holati":                  "bot_holati",
                "🤖 Botlar":                      "botlar",
                "🔎 Foydalanuvchini boshqarish":  "foydalanuvchi",
                "🎟 Promokodlar":                 "promokodlar",
                "💎 Premium sozlash":             "premium_sozlash",
                "👥 Guruhga odam qo'shish":      "guruh_odam",
            }
            all_rows = [
                [{"text": "📢 Kanallarni sozlash"}],
                [{"text": "📊 Statistika"}, {"text": "✉ Xabar Yuborish"}],
                [{"text": "⚙ Asosiy sozlamalar"}, {"text": "💳 To'lov tizimlari"}],
                [{"text": "🤖 Bot holati"}, {"text": "🤖 Botlar"}],
                [{"text": "🔎 Foydalanuvchini boshqarish"}],
                [{"text": "🎟 Promokodlar"}, {"text": "💎 Premium sozlash"}],
                [{"text": "👥 Guruhga odam qo'shish"}],
                [{"text": "◀️ Orqaga"}],
            ]
            key_rows = []
            for row in all_rows:
                new_row = []
                for btn in row:
                    pk = PERM_MAP_L.get(btn["text"])
                    if pk is None or perms.get(pk, True):
                        new_row.append(btn)
                if new_row:
                    key_rows.append(new_row)
            bot("sendMessage", {
                "chat_id": cid,
                "text": "<b>🗄 Admin paneli</b>",
                "parse_mode": "html",
                "reply_markup": json.dumps({"resize_keyboard": True, "keyboard": key_rows})
            })
            delete_file(f"step/{cid}.step")
            return

    if data == "boshqarish" and cid2:

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        return

    # ============================================================

    # callback: foydalanuvchi

    # ============================================================

    if data == "foydalanuvchi" and cid2:

        _p   = read_file(f"pul/{saved}.txt", "0")

        _od  = read_file(f"odam/{saved}.dat", "0")

        _ban = read_file(f"ban/{saved}.txt")

        bans = "🔕 Bandan olish" if _ban == "ban" else "🔔 Banlash"

        prem_s = "💎 Premium (aktiv)" if is_premium(saved) else "👤 Oddiy"

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {"chat_id": cid2,

            "text": (f"<b>Foydalanuvchi:\n\nID:</b> <a href='tg://user?id={saved}'>{saved}</a>\n"

                     f"<b>Balans: {_p} {valyuta}\nTakliflar: {_od} ta\n{prem_s}</b>"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": bans, "callback_data": "ban"}],

                [{"text": "➕ Pul qo'shish", "callback_data": "plus"},

                 {"text": "➖ Pul ayirish", "callback_data": "minus"}],

                [{"text": "💎 Premium berish", "callback_data": f"prem_manual_uid={saved}"}]

            ]})})

        return

    if data and data.startswith("prem_manual_uid=") and is_admin(cid2):

        _uid_pm = data.split("=")[1]

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {"chat_id": cid2,

            "text": f"💎 <b>{_uid_pm} ga necha kun premium berish?</b> (raqam yuboring)",

            "parse_mode": "html", "reply_markup": back})

        write_file(f"step/{cid2}.step", f"prem_uid_kun={_uid_pm}")

        return

    if step and step.startswith("prem_uid_kun=") and is_admin(cid):

        _uid_pk = step.split("=")[1]

        if not tx.strip().isdigit():

            bot("sendMessage", {"chat_id": cid, "text": "⚠️ Faqat raqam!", "parse_mode": "html"})

            return

        _kun_pk = int(tx.strip())

        exp_dt = premium_qo_shish(_uid_pk, _kun_pk)

        exp_str = exp_dt.strftime("%d.%m.%Y")

        bot("sendMessage", {"chat_id": cid,

            "text": f"✅ <b>{_uid_pk} ga {_kun_pk} kun premium berildi! ({exp_str} gacha)</b>",

            "parse_mode": "html", "reply_markup": panel})

        bot("sendMessage", {"chat_id": _uid_pk,

            "text": f"💎 <b>Sizga {_kun_pk} kun Premium berildi!</b>\n📅 {exp_str} gacha",

            "parse_mode": "html"})

        delete_file(f"step/{cid}.step")

        return

    # ============================================================

    # 🔎 Foydalanuvchini boshqarish

    # ============================================================

    if tx == "🔎 Foydalanuvchini boshqarish" and is_admin(cid):

        bot("sendMessage", {"chat_id": cid,

            "text": "<b>Foydalanuvchi ID sini kiriting:</b>",

            "parse_mode": "html", "reply_markup": boshqarish_kb})

        write_file(f"step/{cid}.step", "iD")

        return

    if step == "iD" and is_admin(cid):

        if file_exists(f"pul/{tx}.txt"):

            write_file("step/alijonov.txt", tx)

            _p   = read_file(f"pul/{tx}.txt", "0")

            _od  = read_file(f"odam/{tx}.dat", "0")

            _ban = read_file(f"ban/{tx}.txt")

            bans = "🔕 Bandan olish" if _ban == "ban" else "🔔 Banlash"

            prem_s = "💎 Premium (aktiv)" if is_premium(tx) else "👤 Oddiy"

            msg  = bot("sendMessage", {"chat_id": cid, "text": "<b>Qidirilmoqda...</b>", "parse_mode": "html"})

            smid = msg.get("result", {}).get("message_id", mid)

            bot("editMessageText", {"chat_id": cid, "message_id": smid,

                "text": (f"<b>Topildi!\n\nID:</b> <a href='tg://user?id={tx}'>{tx}</a>\n"

                         f"<b>Balans: {_p} {valyuta}\nTakliflar: {_od} ta\n{prem_s}</b>"),

                "parse_mode": "html",

                "reply_markup": json.dumps({"inline_keyboard": [

                    [{"text": bans, "callback_data": "ban"}],

                    [{"text": "➕ Pul qo'shish", "callback_data": "plus"},

                     {"text": "➖ Pul ayirish", "callback_data": "minus"}],

                    [{"text": "💎 Premium berish", "callback_data": f"prem_manual_uid={tx}"}]

                ]})})

            delete_file(f"step/{cid}.step")

        else:

            bot("sendMessage", {"chat_id": cid,

                "text": "<b>Foydalanuvchi topilmadi.</b>", "parse_mode": "html"})

        return

    if data == "plus" and cid2:

        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

            "text": f"<b><a href='tg://user?id={saved}'>{saved}</a> hisobiga qancha qo'shmoqchisiz?</b>",

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "◀️ Orqaga", "callback_data": "foydalanuvchi"}]]})})

        write_file(f"step/{cid2}.step", "plus")

        return

    if step == "plus" and is_admin(cid) and text:

        if not tx.isdigit():

            bot("sendMessage", {"chat_id": cid, "text": "Faqat raqam!", "parse_mode": "html"})

            return

        _p_s = read_file(f"pul/{saved}.txt", "0")

        try:

            write_file(f"pul/{saved}.txt", str(int(float(_p_s)) + int(float(tx))))

        except:

            pass

        bot("sendMessage", {"chat_id": cid,

            "text": f"✅ <b>{saved} hisobiga {tx} {valyuta} qo'shildi!</b>",

            "parse_mode": "html", "reply_markup": panel})

        delete_file(f"step/{cid}.step")

        return

    if data == "minus" and cid2:

        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

            "text": f"<b><a href='tg://user?id={saved}'>{saved}</a> hisobidan qancha ayirmoqchisiz?</b>",

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "◀️ Orqaga", "callback_data": "foydalanuvchi"}]]})})

        write_file(f"step/{cid2}.step", "minus")

        return

    if step == "minus" and is_admin(cid) and text:

        if not tx.isdigit():

            bot("sendMessage", {"chat_id": cid, "text": "Faqat raqam!", "parse_mode": "html"})

            return

        _p_s = read_file(f"pul/{saved}.txt", "0")

        try:

            new_v = max(0, int(float(_p_s)) - int(float(tx)))

            write_file(f"pul/{saved}.txt", str(new_v))

        except:

            pass

        bot("sendMessage", {"chat_id": cid,

            "text": f"✅ <b>{saved} hisobidan {tx} {valyuta} ayirildi!</b>",

            "parse_mode": "html", "reply_markup": panel})

        delete_file(f"step/{cid}.step")

        return

    if data == "ban" and cid2:

        _ban = read_file(f"ban/{saved}.txt")

        if _ban == "ban":

            delete_file(f"ban/{saved}.txt")

            bot("answerCallbackQuery", {"callback_query_id": qid,

                "text": f"✅ {saved} bandan chiqarildi!", "show_alert": True})

        else:

            write_file(f"ban/{saved}.txt", "ban")

            bot("answerCallbackQuery", {"callback_query_id": qid,

                "text": f"🔕 {saved} banlandi!", "show_alert": True})

        return

    # ============================================================

    # ✉ Xabar Yuborish

    # ============================================================

    if tx == "✉ Xabar Yuborish" and is_admin(cid):

        bot("sendMessage", {"chat_id": cid, "text": "<b>Quyidagilardan birini tanlang:</b>",

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "Oddiy", "callback_data": "send"}],

                [{"text": "Yopish", "callback_data": "boshqarish"}]

            ]})})

        return

    if data == "send" and cid2:

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {"chat_id": cid2, "text": "*Xabaringizni kiriting:*",

            "parse_mode": "markdown", "reply_markup": boshqarish_kb})

        write_file(f"step/{cid2}.step", "send")

        return

    if step == "send" and is_admin(cid):

        lich   = read_file("azo.dat")

        lichka = [l.strip() for l in lich.split("\n") if l.strip()]

        ok_count = 0

        for user_cid in lichka:

            res = bot("sendMessage", {"chat_id": user_cid, "text": text,

                "parse_mode": "html", "disable_web_page_preview": True})

            if res.get("ok"):

                ok_count += 1

        bot("sendMessage", {"chat_id": ADMIN_ID,

            "text": f"<b>✅ {ok_count} ta foydalanuvchiga yuborildi!</b>",

            "parse_mode": "html", "reply_markup": panel})

        delete_file(f"step/{cid}.step")

        return

    # ============================================================

    # 📊 Statistika

    # ============================================================

    if tx == "📊 Statistika" and is_admin(cid):

        baza_txt = read_file("azo.dat")

        obsh = len([l for l in baza_txt.split("\n") if l.strip()])

        db_data     = load_db()

        botlar_soni = len(db_data.get("kunlik", []))

        ishlab      = sum(1 for k in db_data.get("kunlik", []) if bot_is_running(k.get("useri", "")))

        prem_count  = sum(1 for u in db_data.get("users", []) if is_premium(str(u.get("user_id",""))))

        t_start = time.time()

        bot("sendMessage", {"chat_id": cid, "text": "..."})

        ping = int((time.time() - t_start) * 1000)

        karta   = get_karta()

        stars_n = get_stars_narx()

        tolov_txt = ""

        if karta:   tolov_txt += f"\n💳 Karta: {karta.get('nom','')}"

        if stars_n: tolov_txt += f"\n⭐ Stars: 1⭐={stars_n} {valyuta}"

        bot("sendMessage", {

            "chat_id": cid,

            "text": (f"💡 <b>PING:</b> <code>{ping}ms</code>\n"

                     f"👥 <b>Foydalanuvchilar:</b> {obsh} ta\n"

                     f"💎 <b>Premium:</b> {prem_count} ta\n"

                     f"🤖 <b>Yaratilgan botlar:</b> {botlar_soni} ta\n"

                     f"▶️ <b>Ishlab turganlar:</b> {ishlab} ta"

                     + (f"\n\n<b>To'lov tizimlari:</b>{tolov_txt}" if tolov_txt else "")),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "Yopish", "callback_data": "boshqarish"}]]})

        })

        return

    # ============================================================

    # ⚙ Sozlamalar

    # ============================================================

    if tx == "⚙ Sozlamalar" and cid and joinchat(cid):

        bot("sendMessage", {"chat_id": cid, "text": "<b>💬 Tilni tanlang:</b>",

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "🇺🇿 O'zbekcha - (✓)", "callback_data": "sizbu"}],

                [{"text": "🇷🇺 Русский", "callback_data": "tezkun"}]

            ]})})

        return

    if data == "tezkun":

        bot("answerCallbackQuery", {"callback_query_id": qid, "text": "⏱️ Tez orada...", "show_alert": True})

        return

    if data == "sizbu":

        bot("answerCallbackQuery", {"callback_query_id": qid,

            "text": "⚠️ Siz ushbu tildan foydalanyapsiz!", "show_alert": True})

        return

    # ============================================================

    # ☎️ Murojaat

    # ============================================================

    if tx == "☎️ Murojaat" and cid and joinchat(cid):

        bot("sendMessage", {"chat_id": cid, "text": "<b>Murojaat matnini kiriting:</b>",

            "parse_mode": "html", "reply_markup": back})

        write_file(f"step/{cid}.step", "murojaat")

        return

    if step == "murojaat":

        bot("sendMessage", {"chat_id": cid, "text": "<b>Murojaat qabul qilindi!</b>",

            "parse_mode": "html", "reply_markup": menu})

        bot("sendMessage", {"chat_id": ADMIN_ID,

            "text": f"<a href='tg://user?id={cid}'>{name}</a> <b>dan murojaat:</b>\n\n{text}",

            "parse_mode": "html", "disable_web_page_preview": True,

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "📝 Javob yozish", "callback_data": f"send-{cid}"}]

            ]})})

        delete_file(f"step/{cid}.step")

        return

    if data and data.startswith("send-"):

        _id = data.split("-")[1]

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {"chat_id": ADMIN_ID, "text": "<b>Xabaringizni kiriting:</b>",

            "parse_mode": "html", "reply_markup": back})

        write_file(f"step/{cid2}.step", f"send-{_id}")

        return

    if step and step.startswith("send-"):

        _id = step.split("-")[1]

        bot("sendMessage", {"chat_id": _id, "text": text, "parse_mode": "html"})

        bot("sendMessage", {"chat_id": ADMIN_ID, "text": "✅ <b>Yuborildi!</b>",

            "parse_mode": "html", "reply_markup": menus})

        delete_file(f"step/{cid}.step")

        return

    # ============================================================

    # Kanal boshqaruvi

    # ============================================================

    if data == "kanallar" and cid2:

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        pk = read_file("admin/promo_kanal.txt").strip()

        pk_status = f"✅ {pk}" if pk else "❌ Sozlanmagan"

        maj_kanal = read_file("admin/kanal.txt").strip()

        maj_count = len([l for l in maj_kanal.split("\n") if l.strip()]) if maj_kanal else 0

        bot("sendMessage", {

            "chat_id": cid2,

            "text": (f"📢 <b>Kanallar boshqaruvi</b>\n\n"

                     f"🔐 Majburiy obunalar: <b>{maj_count} ta kanal</b>\n"

                     f"🎟 Promokod kanali: <b>{pk_status}</b>"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "🔐 Majburiy obunalar", "callback_data": "majburiy_kanal"}],

                [{"text": "🎟 Promokod kanali", "callback_data": "promo_kanal_menu"}],

                [{"text": "Yopish", "callback_data": "boshqarish"}]

            ]})

        })

        return

    if data == "majburiy" and cid2:

        # majburiy endi majburiy_kanal ga yo'naltiradi (eski tugmalar uchun)

        pk = read_file("admin/promo_kanal.txt").strip()

        pk_status = f"✅ {pk}" if pk else "❌ Sozlanmagan"

        maj_kanal = read_file("admin/kanal.txt").strip()

        maj_count = len([l for l in maj_kanal.split("\n") if l.strip()]) if maj_kanal else 0

        bot("editMessageText", {

            "chat_id": cid2, "message_id": mid2,

            "text": (f"📢 <b>Kanallar boshqaruvi</b>\n\n"

                     f"🔐 Majburiy obunalar: <b>{maj_count} ta kanal</b>\n"

                     f"🎟 Promokod kanali: <b>{pk_status}</b>"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "🔐 Majburiy obunalar", "callback_data": "majburiy_kanal"}],

                [{"text": "🎟 Promokod kanali", "callback_data": "promo_kanal_menu"}],

                [{"text": "Yopish", "callback_data": "boshqarish"}]

            ]})

        })

        return

    if data == "majburiy_kanal" and cid2:

        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

            "text": "<b>🔐 Majburiy obunalar:</b>", "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "➕ Qo'shish", "callback_data": "qoshish"}],

                [{"text": "📑 Ro'yxat", "callback_data": "royxat"},

                 {"text": "🗑 O'chirish", "callback_data": "kanal_ochirish"}],

                [{"text": "◀️ Orqaga", "callback_data": "majburiy"}]

            ]})})

        return

    if data == "promo_kanal_menu" and cid2:

        pk = read_file("admin/promo_kanal.txt").strip()

        pk_status = f"✅ {pk}" if pk else "❌ Sozlanmagan"

        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

            "text": (f"🎟 <b>Promokod kanali</b>\n\n"

                     f"Hozirgi kanal: {pk_status}\n\n"

                     f"Promokod yaratilganda shu kanalga avtomatik yuboriladi."),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "✏️ Kanal o'rnatish", "callback_data": "promo_kanal_set"}],

                [{"text": "🗑 O'chirish", "callback_data": "promo_kanal_del"}],

                [{"text": "◀️ Orqaga", "callback_data": "majburiy"}]

            ]})})

        return

    if data == "promo_kanal_set" and is_admin(cid2):

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {"chat_id": cid2,

            "text": ("🎟 <b>Promokod kanalini o'rnatish</b>\n\n"

                     "Kanal username yoki ID sini yuboring:\n"

                     "<i>Misol: @mening_kanalim yoki -100123456789</i>\n\n"

                     "⚠️ Bot kanalga admin bo'lishi kerak!"),

            "parse_mode": "html", "reply_markup": back})

        write_file(f"step/{cid2}.step", "promo_kanal_set")

        return

    if step == "promo_kanal_set" and is_admin(cid):

        write_file("admin/promo_kanal.txt", tx.strip())

        bot("sendMessage", {"chat_id": cid,

            "text": f"✅ <b>Promokod kanali o'rnatildi:</b> {tx.strip()}",

            "parse_mode": "html", "reply_markup": panel})

        delete_file(f"step/{cid}.step")

        return

    if data == "promo_kanal_del" and is_admin(cid2):

        delete_file("admin/promo_kanal.txt")

        bot("answerCallbackQuery", {"callback_query_id": qid,

            "text": "✅ Promokod kanali o'chirildi!", "show_alert": True})

        pk_status = "❌ Sozlanmagan"

        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

            "text": f"🎟 <b>Promokod kanali</b>\n\nHozirgi kanal: {pk_status}",

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "✏️ Kanal o'rnatish", "callback_data": "promo_kanal_set"}],

                [{"text": "◀️ Orqaga", "callback_data": "majburiy"}]

            ]})})

        return

    if data == "qoshish" and cid2:

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {"chat_id": cid2,

            "text": "<b>Kanal userini kiriting:</b>\n<i>Namuna: @kanal_username</i>",

            "parse_mode": "html", "reply_markup": boshqarish_kb})

        write_file(f"step/{cid2}.step", "qo'shish")

        return

    if step == "qo'shish" and is_admin(cid):

        _kanal = read_file("admin/kanal.txt")

        write_file("admin/kanal.txt", (f"{_kanal}\n{text}").strip())

        bot("sendMessage", {"chat_id": ADMIN_ID, "text": "<b>✅ Qo'shildi!</b>",

            "parse_mode": "html", "reply_markup": asosiy_kb})

        delete_file(f"step/{cid}.step")

        return

    if data == "kanal_ochirish" and cid2:

        delete_file("admin/kanal.txt")

        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

            "text": "✅ <b>Kanallar o'chirildi!</b>", "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "◀️ Orqaga", "callback_data": "majburiy_kanal"}]

            ]})})

        return

    if data == "royxat" and cid2:

        _kanal = read_file("admin/kanal.txt")

        txt = f"<b>📢 Kanallar:</b>\n\n{_kanal}" if _kanal.strip() else "📂 <b>Bo'sh!</b>"

        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

            "text": txt, "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "◀️ Orqaga", "callback_data": "majburiy_kanal"}]

            ]})})

        return

    # ============================================================

    # 🔩 Botni sozlash

    # ============================================================

    if tx == "🔩 Botni sozlash" and cid and joinchat(cid):

        _bots = read_file(f"baza/{cid}/bots.txt")

        if _bots.strip():

            lines = [l.strip() for l in _bots.split("\n") if l.strip()]

            key   = [[{"text": f"⚙ {i}. @{t}", "callback_data": f"settings={t}"}]

                     for i, t in enumerate(lines, 1)]

            key.append([{"text": "◀️ Orqaga", "callback_data": "boshqarish"}])

            bot("sendMessage", {"chat_id": cid, "text": "📋 <b>Botingizni tanlang:</b>",

                "parse_mode": "html", "reply_markup": json.dumps({"inline_keyboard": key})})

        else:

            bot("sendMessage", {"chat_id": cid, "text": "📂 <b>Sizda hech qanday bot yo'q!</b>",

                "parse_mode": "html",

                "reply_markup": json.dumps({"inline_keyboard": [

                    [{"text": "➕ Yangi bot", "callback_data": "apilar"}]

                ]})})

        return

    if data == "botlar" and cid2:

        _bots = read_file(f"baza/{cid2}/bots.txt")

        if _bots.strip():

            lines = [l.strip() for l in _bots.split("\n") if l.strip()]

            key   = [[{"text": f"⚙ {i}. @{t}", "callback_data": f"settings={t}"}]

                     for i, t in enumerate(lines, 1)]

            key.append([{"text": "◀️ Orqaga", "callback_data": "boshqarish"}])

            bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

            bot("sendMessage", {"chat_id": cid2, "text": "📋 <b>Botingizni tanlang:</b>",

                "parse_mode": "html", "reply_markup": json.dumps({"inline_keyboard": key})})

        else:

            bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

            bot("sendMessage", {"chat_id": cid2, "text": "📂 <b>Sizda hech qanday bot yo'q!</b>",

                "parse_mode": "html",

                "reply_markup": json.dumps({"inline_keyboard": [

                    [{"text": "➕ Yangi bot", "callback_data": "apilar"}]

                ]})})

        return

    if data and data.lower().startswith("settings="):

        ismi = data.split("=", 1)[1]

        row  = kunlik_get(ismi)

        if not row:

            return

        _turi   = row.get("turi", "")

        _tokeni = row.get("tokeni", "")

        _vaqti  = row.get("vaqti", "")

        _kun    = str(row.get("kun", "0"))

        _masked = token_mask(_tokeni)

        running = "▶️ Ishlaydi" if bot_is_running(ismi) else "⏹ To'xtagan"

        now = now_tz()

        left_secs = (24 * 60 - now.hour * 60 - now.minute) * 60

        h = str(left_secs // 3600).zfill(2)

        m = str((left_secs % 3600) // 60).zfill(2)

        tolov_info = "Muddati tugagan!" if _kun == "0" or "-" in _kun else f"{_kun} kun, {h}:{m}"

        bot("editMessageText", {

            "chat_id": cid2, "message_id": mid2,

            "text": (f"✅ <b>@{ismi}</b>\n\n"

                     f"🔑 <b>Token:</b> <code>{_masked}</code>\n"

                     f"🗓 <b>Ochilgan:</b> {_vaqti}\n"

                     f"📂 <b>Tur:</b> {_turi}\n"

                     f"⏳ <b>Muddat:</b> {tolov_info}\n"

                     f"🔴 <b>Holat:</b> {running}"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "▶️ Ishga tushirish", "callback_data": f"runbot={ismi}"},

                 {"text": "⏹ To'xtatish", "callback_data": f"stopbot={ismi}"}],

                [{"text": "🔑 Token yangilash", "callback_data": f"token={ismi}"}],

                [{"text": "🔄 Botni o'tkazish", "callback_data": f"bot_otkazish={ismi}"}],

                [{"text": "🗑 O'chirish", "callback_data": f"ochirish={ismi}"},

                 {"text": "◀️ Orqaga", "callback_data": "botlar"}]

            ]})

        })

        return

    if data and data.lower().startswith("runbot="):

        ismi = data.split("=", 1)[1]

        ok, err_msg = start_user_bot(ismi)

        if ok:

            answer_txt = "▶️ Ishga tushirildi!"

        else:

            err_short = err_msg.strip()[-100:] if err_msg else "Noma'lum xato"

            answer_txt = f"❌ Xato: {err_short}"

        bot("answerCallbackQuery", {"callback_query_id": qid,

            "text": answer_txt, "show_alert": True})

        return

    if data and data.lower().startswith("stopbot="):

        ismi = data.split("=", 1)[1]

        stop_user_bot(ismi)

        bot("answerCallbackQuery", {"callback_query_id": qid, "text": "⏹ To'xtatildi!", "show_alert": True})

        return

    # ============================================================

    # 🔄 BOT O'TKAZISH (faqat Premium)

    # ============================================================

    if data and data.lower().startswith("bot_otkazish=") and cid2:

        ismi = data.split("=", 1)[1]

        if not is_premium(cid2):

            bot("answerCallbackQuery", {"callback_query_id": qid,

                "text": "👑 Ushbu bo'lim PREMIUM foydalanuvchilar uchun!", "show_alert": True})

            bot("editMessageText", {

                "chat_id": cid2, "message_id": mid2,

                "text": "🔒 <b>Ushbu bo'lim 👑 PREMIUM foydalanuvchilar uchun!</b>\n\nPremium oling va botni boshqa foydalanuvchiga o'tkazing.",

                "parse_mode": "html",

                "reply_markup": json.dumps({"inline_keyboard": [

                    [{"text": "👑 Premium olish", "callback_data": "premium_buy"}],

                    [{"text": "◀️ Orqaga", "callback_data": f"settings={ismi}"}]

                ]})

            })

            return

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {

            "chat_id": cid2,

            "text": (f"🔄 <b>@{ismi} botini o'tkazish</b>\n\n"

                     f"Qabul qiluvchining <b>Telegram ID</b> sini kiriting:\n"

                     f"<i>ID ni bilish uchun foydalanuvchi /start bosib kabinetdan ko'radi</i>"),

            "parse_mode": "html", "reply_markup": back

        })

        write_file(f"step/{cid2}.step", f"bot_otkazish={ismi}")

        return

    if step and step.startswith("bot_otkazish=") and cid:

        ismi_bot = step.split("=", 1)[1]

        if not tx.strip().isdigit():

            bot("sendMessage", {"chat_id": cid,

                "text": "⚠️ <b>Faqat raqam (Telegram ID) kiriting!</b>", "parse_mode": "html"})

            return

        yangi_egasi = tx.strip()

        if yangi_egasi == cid:

            bot("sendMessage", {"chat_id": cid,

                "text": "⚠️ <b>O'zingizga o'tkaza olmaysiz!</b>", "parse_mode": "html"})

            return

        if not file_exists(f"pul/{yangi_egasi}.txt"):

            bot("sendMessage", {"chat_id": cid,

                "text": "❌ <b>Bu ID li foydalanuvchi botda ro'yxatdan o'tmagan!</b>", "parse_mode": "html"})

            return

        # Eski egadan olib, yangi egaga berish

        row = kunlik_get(ismi_bot)

        if not row:

            bot("sendMessage", {"chat_id": cid, "text": "❌ Bot topilmadi.", "parse_mode": "html"})

            delete_file(f"step/{cid}.step")

            return

        # Eski eganing ro'yxatidan o'chirish

        bots_txt = read_file(f"baza/{cid}/bots.txt")

        write_file(f"baza/{cid}/bots.txt", bots_txt.replace(f"\n{ismi_bot}", "").replace(ismi_bot, ""))

        # Yangi eganing ro'yxatiga qo'shish

        os.makedirs(f"baza/{yangi_egasi}", exist_ok=True)

        append_file(f"baza/{yangi_egasi}/bots.txt", f"\n{ismi_bot}")

        # DB yangilash

        kunlik_update(ismi_bot, user_id=yangi_egasi)

        write_file(f"bots/{ismi_bot}/owner.txt", yangi_egasi)

        bot("sendMessage", {

            "chat_id": cid,

            "text": f"✅ <b>@{ismi_bot} boti {yangi_egasi} ga o'tkazildi!</b>",

            "parse_mode": "html", "reply_markup": make_menu()

        })

        bot("sendMessage", {

            "chat_id": yangi_egasi,

            "text": (f"🎉 <b>Sizga @{ismi_bot} boti o'tkazildi!</b>\n\n"

                     f"Botni '🔩 Botni sozlash' bo'limidan boshqara olasiz."),

            "parse_mode": "html"

        })

        delete_file(f"step/{cid}.step")

        return

    if data and data.lower().startswith("token="):

        ismi = data.split("=", 1)[1]

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {"chat_id": cid2, "text": "<b>🔑 Yangi tokenni yuboring:</b>",

            "parse_mode": "html", "reply_markup": back})

        write_file(f"step/{cid2}.step", f"token={ismi}")

        return

    if step and step.lower().startswith("token="):

        ismi       = step.split("=", 1)[1]

        row        = kunlik_get(ismi)

        _old_token = row.get("tokeni", "") if row else ""

        if ":" in tx:

            try:

                _user  = requests.get(f"https://api.telegram.org/bot{tx}/getMe", timeout=10).json()

                _uname = _user.get("result", {}).get("username", "")

            except:

                _uname = ""

            if ismi == _uname:

                _kod = read_file(f"bots/{ismi}/bot.py")

                if _old_token and _kod:

                    write_file(f"bots/{ismi}/bot.py", _kod.replace(_old_token, tx))

                kunlik_update(ismi, tokeni=tx)

                start_user_bot(ismi)

                bot("sendMessage", {"chat_id": cid,

                    "text": "✅ <b>Token yangilandi va bot qayta ishga tushdi!</b>",

                    "parse_mode": "html", "reply_markup": boshqarish_kb})

                delete_file(f"step/{cid}.step")

            else:

                bot("sendMessage", {"chat_id": cid,

                    "text": "⚠️ <b>Token qabul qilinmadi.</b>", "parse_mode": "html"})

        else:

            bot("sendMessage", {"chat_id": cid,

                "text": "⚠️ <b>Token qabul qilinmadi.</b>", "parse_mode": "html"})

        return

    if data and data.lower().startswith("ochirish="):

        ismi = data.split("=", 1)[1]

        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

            "text": f"<b>⚠️ @{ismi} ni o'chirishga ishonchingiz komilmi?</b>",

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "✅ Ha", "callback_data": f"ha={ismi}"}],

                [{"text": "❌ Yo'q", "callback_data": f"settings={ismi}"}]

            ]})})

        return

    if data and data.lower().startswith("ha="):

        ismi  = data.split("=", 1)[1]

        row   = kunlik_get(ismi)

        _turi = row.get("turi", "") if row else ""

        stop_user_bot(ismi)

        kunlik_delete(ismi)

        bots_txt = read_file(f"baza/{cid2}/bots.txt")

        write_file(f"baza/{cid2}/bots.txt", bots_txt.replace(f"\n{ismi}", "").replace(ismi, ""))

        bots2_txt = read_file(f"baza/{cid2}/bots2.txt")

        write_file(f"baza/{cid2}/bots2.txt", bots2_txt.replace(f"\n{_turi}", "").replace(_turi, ""))

        delete_folder(f"bots/{ismi}")

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {"chat_id": cid2, "text": f"🗑 <b>@{ismi} o'chirildi.</b>",

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "◀️ Orqaga", "callback_data": "botlar"}]]})})

        return

    # ============================================================

    # *️⃣ Birlamchi sozlamalar

    # ============================================================

    if tx == "*️⃣ Birlamchi sozlamalar" and is_admin(cid):

        bot("sendMessage", {"chat_id": cid, "text": "<b>*️⃣ Birlamchi sozlamalar:</b>",

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "📋 Hozirgi holat", "callback_data": "Kholat"}],

                [{"text": "💶 Valyuta", "callback_data": "valyuta"},

                 {"text": "💸 Taklif narxi", "callback_data": "narx"}]

            ]})})

        return

    if data == "birlamchi" and cid2:

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {"chat_id": cid2, "text": "<b>*️⃣ Birlamchi sozlamalar:</b>",

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "📋 Hozirgi holat", "callback_data": "Kholat"}],

                [{"text": "💶 Valyuta", "callback_data": "valyuta"},

                 {"text": "💸 Taklif narxi", "callback_data": "narx"}]

            ]})})

        return

    if data == "Kholat" and cid2:

        ref_narx = read_file("admin/referal.txt", "500")

        bonus_m  = read_file("admin/kunlik_bonus.txt", "1000")

        prem_n   = get_premium_narx()

        prem_k   = get_premium_kun()

        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

            "text": (f"<b>Sozlamalar:</b>\n\n"

                     f"1. Valyuta: {valyuta}\n"

                     f"2. Taklif narxi: {ref_narx} {valyuta}\n"

                     f"3. Kunlik bonus: {bonus_m} {valyuta}\n"

                     f"4. Premium narxi: {prem_n} {valyuta} ({prem_k} kun)"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "◀️ Orqaga", "callback_data": "birlamchi"}]]})})

        return

    if data == "valyuta" and cid2:

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {"chat_id": cid2, "text": "📝 <b>Yangi valyutani yuboring:</b>",

            "parse_mode": "html", "reply_markup": bosh})

        write_file(f"step/{cid2}.step", "valyuta")

        return

    if step == "valyuta" and is_admin(cid) and text:

        write_file("admin/valyuta.txt", text)

        bot("sendMessage", {"chat_id": cid, "text": "<b>✅ O'zgartirildi!</b>",

            "parse_mode": "html", "reply_markup": asosiy_kb})

        delete_file(f"step/{cid}.step")

        return

    if data == "narx" and cid2:

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {"chat_id": cid2, "text": "📝 <b>Yangi taklif narxini yuboring:</b>",

            "parse_mode": "html", "reply_markup": bosh})

        write_file(f"step/{cid2}.step", "taklif")

        return

    if step == "taklif" and is_admin(cid) and text:

        write_file("admin/referal.txt", text)

        bot("sendMessage", {"chat_id": cid, "text": "<b>✅ O'zgartirildi!</b>",

            "parse_mode": "html", "reply_markup": asosiy_kb})

        delete_file(f"step/{cid}.step")

        return

    # ============================================================

    # ⚙ Asosiy sozlamalar

    # ============================================================

    if tx == "⚙ Asosiy sozlamalar" and is_admin(cid):

        bot("sendMessage", {"chat_id": cid, "text": "<b>⚙️ Asosiy sozlamalar:</b>",

            "parse_mode": "html", "reply_markup": make_asosiy()})

        return

    # ============================================================

    # 🤖 Bot holati

    # ============================================================

    if tx == "🤖 Bot holati" and is_admin(cid):

        bot("sendMessage", {"chat_id": cid,

            "text": f"<b>Hozirgi holat:</b> {holat}", "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "✅", "callback_data": "holat-✅"},

                 {"text": "❌", "callback_data": "holat-❌"}],

                [{"text": "Yopish", "callback_data": "yopish"}]

            ]})})

        return

    if data and data.startswith("holat-"):

        xolat = data.split("-", 1)[1]

        write_file("tizim/holat.txt", xolat)

        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

            "text": f"<b>Hozirgi holat:</b> {xolat}", "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "✅", "callback_data": "holat-✅"},

                 {"text": "❌", "callback_data": "holat-❌"}],

                [{"text": "Yopish", "callback_data": "yopish"}]

            ]})})

        return

    if data == "yopish" and cid2:

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        return

    # ============================================================

    # 🤖 Botlar (admin)

    # ============================================================

    if tx == "🤖 Botlar" and is_admin(cid):

        bot("sendMessage", {"chat_id": cid, "text": "🤖 <b>Botlarni boshqarish:</b>",

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "➕ Bot turi qo'shish", "callback_data": "AdBot"}],

                [{"text": "📄 Botlar ro'yxati", "callback_data": "listBot"}],

                [{"text": "🗑 Tanlama o'chirish", "callback_data": "tanlama_ochirish"}],

                [{"text": "🗑 Barchasini tozalash", "callback_data": "toza"}]

            ]})})

        return

    if data == "bbosh" and cid2:

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {"chat_id": cid2, "text": "🤖 <b>Botlarni boshqarish:</b>",

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "➕ Bot turi qo'shish", "callback_data": "AdBot"}],

                [{"text": "📄 Botlar ro'yxati", "callback_data": "listBot"}],

                [{"text": "🗑 Tanlama o'chirish", "callback_data": "tanlama_ochirish"}],

                [{"text": "🗑 Barchasini tozalash", "callback_data": "toza"}]

            ]})})

        return

    if data == "toza" and cid2:

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {"chat_id": cid2,

            "text": "<b>⚠️ Barcha bot turlari o'chiriladimi?</b>", "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "✅ Ha", "callback_data": "barcha2"}],

                [{"text": "◀️ Orqaga", "callback_data": "bbosh"}]

            ]})})

        return

    if data == "barcha2" and is_admin(cid2):

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {"chat_id": cid2, "text": "<b>✅ Tozalandi.</b>", "parse_mode": "html"})

        delete_folder("bot")

        os.makedirs("bot", exist_ok=True)

        return

    if data == "listBot" and cid2:

        db_data = load_db()

        rows    = db_data.get("kunlik", [])

        if not rows:

            bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

                "text": "📂 <b>Hech qanday bot yo'q!</b>", "parse_mode": "html",

                "reply_markup": json.dumps({"inline_keyboard": [[{"text": "◀️ Orqaga", "callback_data": "bbosh"}]]})})

        else:

            txt = "<b>🤖 Barcha yaratilgan botlar:</b>\n\n"

            for i, r in enumerate(rows, 1):

                ismi    = r.get("useri", "?")

                holat_b = "▶️" if bot_is_running(ismi) else "⏹"

                txt += f"{holat_b} {i}. @{ismi} | {r.get('turi','?')} | {r.get('kun','?')} kun\n"

            bot("editMessageText", {"chat_id": cid2, "message_id": mid2,

                "text": txt, "parse_mode": "html",

                "reply_markup": json.dumps({"inline_keyboard": [[{"text": "◀️ Orqaga", "callback_data": "bbosh"}]]})})

        return

    # ============================================================

    # 🗑 TANLAMA O'CHIRISH (Admin - bot turlarini birma-bir o'chirish)

    # ============================================================

    if data == "tanlama_ochirish" and is_admin(cid2):

        # Bot turlari ro'yxatini ko'rsatish

        bot_turlari = []

        if os.path.exists("bot"):

            for name in os.listdir("bot"):

                if os.path.isdir(f"bot/{name}") and os.path.exists(f"bot/{name}/kod.py"):

                    bot_turlari.append(name)

        if not bot_turlari:

            bot("answerCallbackQuery", {"callback_query_id": qid,

                "text": "📂 Hech qanday bot turi yo'q!", "show_alert": True})

            return

        key = [[{"text": f"🤖 {t}", "callback_data": f"tanlama_del={t}"}] for t in bot_turlari]

        key.append([{"text": "◀️ Orqaga", "callback_data": "bbosh"}])

        bot("editMessageText", {

            "chat_id": cid2, "message_id": mid2,

            "text": ("🗑 <b>Qaysi bot turini o'chirasiz?</b>\n\n"

                     "Pastdagi botlardan birini tanlang:\n"

                     "<i>Faqat shu bot turi o'chiriladi, boshqalari qoladi</i>"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": key})

        })

        return

    if data and data.startswith("tanlama_del=") and is_admin(cid2):

        bot_nomi = data.split("=", 1)[1]

        narx = read_file(f"bot/{bot_nomi}/narx.txt", "0")

        bot("editMessageText", {

            "chat_id": cid2, "message_id": mid2,

            "text": (f"⚠️ <b>Tasdiqlang!</b>\n\n"

                     f"🤖 <b>Bot turi:</b> {bot_nomi}\n"

                     f"💰 <b>Narxi:</b> {narx} {valyuta}\n\n"

                     f"Bu bot turini haqiqatdan ham o\'chirasizmi?\n"

                     f"<i>Foydalanuvchilar bu turni sotib ololmaydi</i>"),

            "parse_mode": "html",

            "reply_markup": json.dumps({"inline_keyboard": [

                [{"text": "✅ Ha, o'chirish", "callback_data": f"tanlama_confirm={bot_nomi}"}],

                [{"text": "❌ Bekor qilish", "callback_data": "tanlama_ochirish"}]

            ]})

        })

        return

    if data and data.startswith("tanlama_confirm=") and is_admin(cid2):

        bot_nomi = data.split("=", 1)[1]

        if os.path.exists(f"bot/{bot_nomi}"):

            delete_folder(f"bot/{bot_nomi}")

            # kategoriya.txt dan ham o'chirish

            kat = read_file("bot/kategoriya.txt", "")

            kat_lines = [l for l in kat.split("\n") if l.strip() and l.strip() != bot_nomi]

            write_file("bot/kategoriya.txt", "\n".join(kat_lines))

            bot("editMessageText", {

                "chat_id": cid2, "message_id": mid2,

                "text": (f"✅ <b>\"{bot_nomi}\" bot turi o\'chirildi!</b>\n\n"

                         f"Qolgan bot turlari hali ham mavjud."),

                "parse_mode": "html",

                "reply_markup": json.dumps({"inline_keyboard": [

                    [{"text": "🗑 Yana o'chirish", "callback_data": "tanlama_ochirish"}],

                    [{"text": "◀️ Asosiy menyu", "callback_data": "bbosh"}]

                ]})

            })

        else:

            bot("answerCallbackQuery", {"callback_query_id": qid,

                "text": f"❌ {bot_nomi} topilmadi!", "show_alert": True})

        return

    # ============================================================

    # ============================================================
    # 👤 ADMINLAR RO'YXATI — ASOSIY ADMIN UCHUN
    # ============================================================
    if tx == "👤 Adminlar ro'yxati" and is_admin(cid):
        adminlar = load_adminlar()
        soni = len(adminlar)
        bot("sendMessage", {
            "chat_id": cid,
            "text": (f"👤 <b>Adminlar ro'yxati</b>\n\n"
                     f"Hozirgi adminlar soni: <b>{soni} ta</b>\n"
                     f"(Asosiy admin siz — har doim)"),
            "parse_mode": "html",
            "reply_markup": json.dumps({"inline_keyboard": [
                [{"text": "➕ Admin qo'shish", "callback_data": "admin_qoshish"}],
                [{"text": "🗑 Adminni o'chirish", "callback_data": "admin_ochirish_list"}],
                [{"text": "📋 Adminlar ro'yxati", "callback_data": "adminlar_royxat"}],
                [{"text": "⚙ Adminni boshqarish", "callback_data": "admin_boshqarish_list"}],
            ]})
        })
        return

    if data == "admin_qoshish" and is_admin(cid2):
        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})
        bot("sendMessage", {"chat_id": cid2,
            "text": "➕ <b>Yangi admin ID sini kiriting:</b>",
            "parse_mode": "html", "reply_markup": back})
        write_file(f"step/{cid2}.step", "admin_qoshish_id")
        return

    if step == "admin_qoshish_id" and is_admin(cid):
        if not tx.strip().isdigit():
            bot("sendMessage", {"chat_id": cid,
                "text": "⚠️ <b>Faqat raqam kiriting!</b>", "parse_mode": "html"})
            return
        new_admin_id = tx.strip()
        if new_admin_id == ADMIN_ID:
            bot("sendMessage", {"chat_id": cid,
                "text": "⚠️ <b>Siz allaqachon asosiy adminsiz!</b>", "parse_mode": "html"})
            return
        if new_admin_id in load_adminlar():
            bot("sendMessage", {"chat_id": cid,
                "text": "⚠️ <b>Bu foydalanuvchi allaqachon admin!</b>", "parse_mode": "html"})
            return
        try:
            r = bot("getChat", {"chat_id": new_admin_id})
            if not r.get("ok"):
                bot("sendMessage", {"chat_id": cid,
                    "text": "❌ <b>Bu ID li foydalanuvchi topilmadi!</b>", "parse_mode": "html"})
                return
            u = r["result"]
            u_name = u.get("first_name","") + (" " + u.get("last_name","") if u.get("last_name") else "")
            u_user = "@" + u["username"] if u.get("username") else "username yo'q"
            u_bio  = u.get("bio", "—")
        except:
            bot("sendMessage", {"chat_id": cid,
                "text": "❌ <b>Foydalanuvchi topilmadi!</b>", "parse_mode": "html"})
            return
        write_file(f"step/{cid}.admin_new_id",   new_admin_id)
        write_file(f"step/{cid}.admin_new_name",  u_name)
        write_file(f"step/{cid}.admin_new_user",  u_user)
        bot("sendMessage", {
            "chat_id": cid,
            "text": (f"✅ <b>Foydalanuvchi topildi!</b>\n\n"
                     f"👤 <b>Ismi:</b> {u_name}\n"
                     f"🆔 <b>ID:</b> <code>{new_admin_id}</code>\n"
                     f"📛 <b>Username:</b> {u_user}\n"
                     f"📝 <b>Bio:</b> {u_bio}\n\n"
                     f"Shu foydalanuvchini admin qilmoqchimisiz?"),
            "parse_mode": "html",
            "reply_markup": json.dumps({"inline_keyboard": [
                [{"text": "✅ Admin qilish", "callback_data": f"admin_confirm={new_admin_id}"}],
                [{"text": "❌ Bekor qilish",  "callback_data": "adminlar_bosh"}],
            ]})
        })
        delete_file(f"step/{cid}.step")
        return

    if data and data.startswith("admin_confirm=") and is_admin(cid2):
        new_admin_id = data.split("=", 1)[1]
        u_name = read_file(f"step/{cid2}.admin_new_name", new_admin_id)
        u_user = read_file(f"step/{cid2}.admin_new_user", "")
        admin_add(new_admin_id, u_name, u_user)
        _bot_me    = bot("getMe").get("result", {})
        _bot_uname = "@" + _bot_me.get("username","") if _bot_me.get("username") else _bot_me.get("first_name","MakerBot")
        bot("editMessageText", {
            "chat_id": cid2, "message_id": mid2,
            "text": f"✅ <b>{u_name}</b> admin qilindi!",
            "parse_mode": "html",
            "reply_markup": json.dumps({"inline_keyboard": [
                [{"text": "◀️ Adminlar ro'yxatiga", "callback_data": "adminlar_bosh"}]
            ]})
        })
        bot("sendMessage", {
            "chat_id": new_admin_id,
            "text": (f"🎉 <b>Tabriklaymiz!</b>\n\n"
                     f"Hurmatli <b>{u_name}</b> ({u_user}),\n"
                     f"Siz <b>{_bot_uname}</b> botidan admin qilindingiz!\n\n"
                     f"Admin paneliga kirish uchun /start bosing."),
            "parse_mode": "html"
        })
        delete_file(f"step/{cid2}.admin_new_id")
        delete_file(f"step/{cid2}.admin_new_name")
        delete_file(f"step/{cid2}.admin_new_user")
        return

    if data == "admin_ochirish_list" and is_admin(cid2):
        adminlar = load_adminlar()
        if not adminlar:
            bot("editMessageText", {"chat_id": cid2, "message_id": mid2,
                "text": "📭 <b>Hali adminlar topilmadi!</b>",
                "parse_mode": "html",
                "reply_markup": json.dumps({"inline_keyboard": [
                    [{"text": "◀️ Orqaga", "callback_data": "adminlar_bosh"}]
                ]})})
            return
        key = [[{"text": f"👤 {a['name']} | {uid}",
                 "callback_data": f"admin_del_ask={uid}"}]
               for uid, a in adminlar.items()]
        key.append([{"text": "◀️ Orqaga", "callback_data": "adminlar_bosh"}])
        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,
            "text": "🗑 <b>Qaysi adminni o'chirmoqchisiz?</b>",
            "parse_mode": "html",
            "reply_markup": json.dumps({"inline_keyboard": key})})
        return

    if data and data.startswith("admin_del_ask=") and is_admin(cid2):
        del_uid  = data.split("=", 1)[1]
        adminlar = load_adminlar()
        a        = adminlar.get(del_uid, {})
        bot("editMessageText", {
            "chat_id": cid2, "message_id": mid2,
            "text": (f"⚠️ <b>Haqiqatdan ham shu adminni o'chirasizmi?</b>\n\n"
                     f"👤 {a.get('name', del_uid)} | <code>{del_uid}</code>"),
            "parse_mode": "html",
            "reply_markup": json.dumps({"inline_keyboard": [
                [{"text": "✅ Ha, o'chirish", "callback_data": f"admin_del_ok={del_uid}"}],
                [{"text": "❌ Yo'q",          "callback_data": "admin_ochirish_list"}],
            ]})
        })
        return

    if data and data.startswith("admin_del_ok=") and is_admin(cid2):
        del_uid  = data.split("=", 1)[1]
        adminlar = load_adminlar()
        a_name   = adminlar.get(del_uid, {}).get("name", del_uid)
        admin_remove(del_uid)
        bot("editMessageText", {
            "chat_id": cid2, "message_id": mid2,
            "text": f"✅ <b>{a_name}</b> adminlikdan olib tashlandi!",
            "parse_mode": "html",
            "reply_markup": json.dumps({"inline_keyboard": [
                [{"text": "◀️ Adminlar ro'yxatiga", "callback_data": "adminlar_bosh"}]
            ]})
        })
        bot("sendMessage", {"chat_id": del_uid,
            "text": "⛔️ <b>Siz adminlikdan olib tashlandi ngiz.</b>",
            "parse_mode": "html"})
        return

    if data == "adminlar_royxat" and is_admin(cid2):
        adminlar = load_adminlar()
        if not adminlar:
            txt = "📭 <b>Hali adminlar topilmadi!</b>"
        else:
            txt = "📋 <b>Adminlar ro'yxati:</b>\n\n"
            for uid, a in adminlar.items():
                txt += (f"👤 <b>{a.get('name','?')}</b> | <code>{uid}</code>\n"
                        f"   📛 {a.get('username','—')} | 📅 {a.get('added','—')}\n\n")
        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,
            "text": txt, "parse_mode": "html",
            "reply_markup": json.dumps({"inline_keyboard": [
                [{"text": "◀️ Orqaga", "callback_data": "adminlar_bosh"}]
            ]})})
        return

    if data == "admin_boshqarish_list" and is_admin(cid2):
        adminlar = load_adminlar()
        if not adminlar:
            bot("editMessageText", {"chat_id": cid2, "message_id": mid2,
                "text": "📭 <b>Hali adminlar topilmadi!</b>",
                "parse_mode": "html",
                "reply_markup": json.dumps({"inline_keyboard": [
                    [{"text": "◀️ Orqaga", "callback_data": "adminlar_bosh"}]
                ]})})
            return
        key = [[{"text": f"⚙ {a['name']} | {uid}",
                 "callback_data": f"admin_manage={uid}"}]
               for uid, a in adminlar.items()]
        key.append([{"text": "◀️ Orqaga", "callback_data": "adminlar_bosh"}])
        bot("editMessageText", {"chat_id": cid2, "message_id": mid2,
            "text": "⚙ <b>Qaysi adminni boshqarasiz?</b>",
            "parse_mode": "html",
            "reply_markup": json.dumps({"inline_keyboard": key})})
        return

    if data and data.startswith("admin_manage=") and is_admin(cid2):
        m_uid    = data.split("=", 1)[1]
        adminlar = load_adminlar()
        a        = adminlar.get(m_uid, {})
        perms    = a.get("perms", {})
        key = []
        for pk, pn in ADMIN_PERMS:
            val   = perms.get(pk, True)
            emoji = "✅" if val else "❌"
            key.append([{"text": f"{pn} {emoji}",
                         "callback_data": f"admin_perm_toggle={m_uid}={pk}"}])
        key.append([{"text": "◀️ Orqaga", "callback_data": "admin_boshqarish_list"}])
        bot("editMessageText", {
            "chat_id": cid2, "message_id": mid2,
            "text": (f"⚙ <b>{a.get('name','?')}</b> ruxsatlari\n"
                     f"<code>{m_uid}</code>\n\n"
                     f"✅ ruxsat | ❌ taqiqlangan — Bosib o'zgartiring:"),
            "parse_mode": "html",
            "reply_markup": json.dumps({"inline_keyboard": key})
        })
        return

    if data and data.startswith("admin_perm_toggle=") and is_admin(cid2):
        parts_ap = data.split("=")
        m_uid    = parts_ap[1] if len(parts_ap) > 1 else ""
        perm_k   = parts_ap[2] if len(parts_ap) > 2 else ""
        adminlar = load_adminlar()
        cur_val  = adminlar.get(m_uid, {}).get("perms", {}).get(perm_k, True)
        admin_update_perm(m_uid, perm_k, not cur_val)
        adminlar = load_adminlar()
        a     = adminlar.get(m_uid, {})
        perms = a.get("perms", {})
        key   = []
        for pk, pn in ADMIN_PERMS:
            val   = perms.get(pk, True)
            emoji = "✅" if val else "❌"
            key.append([{"text": f"{pn} {emoji}",
                         "callback_data": f"admin_perm_toggle={m_uid}={pk}"}])
        key.append([{"text": "◀️ Orqaga", "callback_data": "admin_boshqarish_list"}])
        bot("editMessageText", {
            "chat_id": cid2, "message_id": mid2,
            "text": (f"⚙ <b>{a.get('name','?')}</b> ruxsatlari\n"
                     f"<code>{m_uid}</code>\n\n"
                     f"✅ ruxsat | ❌ taqiqlangan — Bosib o'zgartiring:"),
            "parse_mode": "html",
            "reply_markup": json.dumps({"inline_keyboard": key})
        })
        return

    if data == "adminlar_bosh" and is_admin(cid2):
        adminlar = load_adminlar()
        soni     = len(adminlar)
        bot("editMessageText", {
            "chat_id": cid2, "message_id": mid2,
            "text": (f"👤 <b>Adminlar ro'yxati</b>\n\n"
                     f"Hozirgi adminlar soni: <b>{soni} ta</b>\n"
                     f"(Asosiy admin siz — har doim)"),
            "parse_mode": "html",
            "reply_markup": json.dumps({"inline_keyboard": [
                [{"text": "➕ Admin qo'shish", "callback_data": "admin_qoshish"}],
                [{"text": "🗑 Adminni o'chirish", "callback_data": "admin_ochirish_list"}],
                [{"text": "📋 Adminlar ro'yxati", "callback_data": "adminlar_royxat"}],
                [{"text": "⚙ Adminni boshqarish", "callback_data": "admin_boshqarish_list"}],
            ]})
        })
        return

    # --- Qo'shimcha adminlar uchun ruxsat tekshiruvi ---
    # Faqat ruxsati yo'q bo'lsa bloklash, aks holda o'tkazib yuborish
    PERM_MAP = {
        "📊 Statistika":                "statistika",
        "✉ Xabar Yuborish":             "xabar_yuborish",
        "⚙ Asosiy sozlamalar":           "asosiy_sozlamalar",
        "💳 To'lov tizimlari":          "tolov_tizimlari",
        "🤖 Bot holati":                 "bot_holati",
        "🤖 Botlar":                     "botlar",
        "🔎 Foydalanuvchini boshqarish": "foydalanuvchi",
        "🎟 Promokodlar":                "promokodlar",
        "💎 Premium sozlash":            "premium_sozlash",
        "👥 Guruhga odam qo'shish":     "guruh_odam",
        "📢 Kanallarni sozlash":         "kanallar",
    }
    if is_admin(cid) and str(cid) != str(ADMIN_ID) and tx and tx in PERM_MAP:
        if not admin_has_perm(cid, PERM_MAP[tx]):
            bot("sendMessage", {"chat_id": cid,
                "text": "🚫 <b>Sizda bu bo'limga ruxsat yo'q!</b>",
                "parse_mode": "html"})
            return

    # 🗄 Boshqarish — sub-admin uchun ruxsatga qarab panel
    if tx == "🗄 Boshqarish" and is_admin(cid) and str(cid) != str(ADMIN_ID):
        adminlar = load_adminlar()
        a     = adminlar.get(str(cid), {})
        perms = a.get("perms", {})
        all_rows = [
            [{"text": "📢 Kanallarni sozlash"}],
            [{"text": "📊 Statistika"}, {"text": "✉ Xabar Yuborish"}],
            [{"text": "⚙ Asosiy sozlamalar"}, {"text": "💳 To'lov tizimlari"}],
            [{"text": "🤖 Bot holati"}, {"text": "🤖 Botlar"}],
            [{"text": "🔎 Foydalanuvchini boshqarish"}],
            [{"text": "🎟 Promokodlar"}, {"text": "💎 Premium sozlash"}],
            [{"text": "👥 Guruhga odam qo'shish"}],
            [{"text": "◀️ Orqaga"}],
        ]
        key_rows = []
        for row in all_rows:
            new_row = []
            for btn in row:
                pk = PERM_MAP.get(btn["text"])
                if pk is None or perms.get(pk, True):
                    new_row.append(btn)
            if new_row:
                key_rows.append(new_row)
        bot("sendMessage", {
            "chat_id": cid,
            "text": "<b>🗄 Admin paneli</b>",
            "parse_mode": "html",
            "reply_markup": json.dumps({"resize_keyboard": True, "keyboard": key_rows})
        })
        delete_file(f"step/{cid}.step")
        return

    # ➕ Bot turi qo'shish (AdBot)

    # ============================================================

    if data == "AdBot" and is_admin(cid2):

        bot("deleteMessage", {"chat_id": cid2, "message_id": mid2})

        bot("sendMessage", {

            "chat_id": cid2,

            "text": ("➕ <b>Yangi bot turi qo'shish</b>\n\n"

                     "<b>1-qadam:</b> Bot turining nomini yuboring.\n"

                     "<i>Namuna: Premium Bot</i>"),

            "parse_mode": "html", "reply_markup": boshqarish_kb

        })

        write_file(f"step/{cid2}.step", "AdBot_nom")

        return

    if step == "AdBot_nom" and is_admin(cid) and text:

        write_file(f"step/{cid}.adbot_nom", text)

        os.makedirs(f"bot/{text}", exist_ok=True)

        write_file(f"bot/{text}/narx.txt",   "0")

        write_file(f"bot/{text}/kunlik.txt", "31")

        bot("sendMessage", {

            "chat_id": cid,

            "text": (f"✅ <b>Nom: {text}</b>\n\n"

                     "<b>2-qadam:</b> Bot narxini kiriting (faqat raqam).\n"

                     "<i>Namuna: 5000</i>"),

            "parse_mode": "html", "reply_markup": back

        })

        write_file(f"step/{cid}.step", "AdBot_narx")

        return

    if step == "AdBot_narx" and is_admin(cid):

        if not tx.isdigit():

            bot("sendMessage", {"chat_id": cid,

                "text": "<b>Faqat raqam kiriting!</b>", "parse_mode": "html"})

            return

        _nom = read_file(f"step/{cid}.adbot_nom")

        write_file(f"bot/{_nom}/narx.txt", tx)

        bot("sendMessage", {

            "chat_id": cid,

            "text": (f"✅ <b>Nom: {_nom} | Narx: {tx} {valyuta}</b>\n\n"

                     "<b>3-qadam:</b> Bot uchun Python kodni yuboring.\n\n"

                     "📎 <b>Kod yuborish usullari:</b>\n"

                     "• <b>.py fayl</b> sifatida yuboring (tavsiya etiladi)\n"

                     "• Yoki to'g'ridan-to'g'ri matn sifatida yuboring\n\n"

                     "⚠️ <b>Muhim:</b> Kodda quyidagi so'zlar bo'lishi <b>shart:</b>\n"

                     "• <code>TOKEN</code> — bot tokeni shu yerga qo'yiladi\n"

                     "• <code>ADMIN</code> — foydalanuvchi TG ID si shu yerga qo'yiladi\n\n"

                     "<i>Misol:\n"

                     "API_TOKEN = \"TOKEN\"\n"

                     "ADMIN_ID = \"ADMIN\"</i>"),

            "parse_mode": "html", "reply_markup": back

        })

        write_file(f"step/{cid}.step", "AdBot_kod")

        return

    if step == "AdBot_kod" and is_admin(cid) and text and not doc:

        _nom = read_file(f"step/{cid}.adbot_nom")

        if not _nom:

            bot("sendMessage", {"chat_id": cid,

                "text": "<b>Xato! Qaytadan boshlang.</b>",

                "parse_mode": "html", "reply_markup": panel})

            delete_file(f"step/{cid}.step")

            return

        # TOKEN/ADMIN yo'q bo'lsa ham qabul qilamiz - prepare_bot_code o'zi moslashtiradi

        bot_type_detected = detect_bot_type(text)

        _narx = read_file(f"bot/{_nom}/narx.txt", "0")

        write_file(f"bot/{_nom}/kod.py", text)

        _kat = read_file("bot/kategoriya.txt")

        if _nom not in _kat:

            write_file("bot/kategoriya.txt", (f"{_kat}\n{_nom}").strip())

        bot("sendMessage", {

            "chat_id": cid,

            "text": (f"✅ <b>Kod muvaffaqiyatli yuklandi!</b>\n\n"

                     f"🤖 <b>Bot turi:</b> {_nom}\n"

                     f"💰 <b>Narxi:</b> {_narx} {valyuta}\n"

                     f"🔍 <b>Aniqlangan kod turi:</b> {bot_type_detected}\n"

                     f"📦 <b>Kod hajmi:</b> {len(text)} belgi\n\n"

                     f"✅ Foydalanuvchilar ushbu bot turini sotib olganda\n"

                     f"avtomatik ishga tushiriladi!"),

            "parse_mode": "html", "reply_markup": panel

        })

        delete_file(f"step/{cid}.step"); delete_file(f"step/{cid}.adbot_nom")

        return

    if step == "AdBot_kod" and is_admin(cid) and doc:

        file_name = doc.get("file_name", "")

        if not file_name.endswith(".py"):

            bot("sendMessage", {"chat_id": cid,

                "text": "⚠️ <b>Faqat .py fayl yuboring!</b>", "parse_mode": "html"})

            return

        _nom = read_file(f"step/{cid}.adbot_nom")

        if not _nom:

            bot("sendMessage", {"chat_id": cid,

                "text": "<b>Xato! Qaytadan boshlang.</b>",

                "parse_mode": "html", "reply_markup": panel})

            delete_file(f"step/{cid}.step")

            return

        msg_wait = bot("sendMessage", {"chat_id": cid,

            "text": "⏱ <b>Fayl yuklab olinmoqda...</b>", "parse_mode": "html"})

        w_mid = msg_wait.get("result", {}).get("message_id", mid)

        kod_content = download_file(doc["file_id"])

        if not kod_content:

            bot("editMessageText", {"chat_id": cid, "message_id": w_mid,

                "text": "⛔️ <b>Faylni yuklab olishda xato. Qayta yuboring.</b>", "parse_mode": "html"})

            return

        _narx = read_file(f"bot/{_nom}/narx.txt", "0")

        bot_type_detected = detect_bot_type(kod_content)

        write_file(f"bot/{_nom}/kod.py", kod_content)

        _kat = read_file("bot/kategoriya.txt")

        if _nom not in _kat:

            write_file("bot/kategoriya.txt", (f"{_kat}\n{_nom}").strip())

        bot("editMessageText", {

            "chat_id": cid, "message_id": w_mid,

            "text": (f"✅ <b>Fayl muvaffaqiyatli yuklandi!</b>\n\n"

                     f"🤖 <b>Bot turi:</b> {_nom}\n"

                     f"💰 <b>Narxi:</b> {_narx} {valyuta}\n"

                     f"📎 <b>Fayl nomi:</b> {file_name}\n"

                     f"🔍 <b>Aniqlangan kod turi:</b> {bot_type_detected}\n"

                     f"📦 <b>Kod hajmi:</b> {len(kod_content)} belgi\n\n"

                     f"✅ Foydalanuvchilar ushbu bot turini sotib olganda\n"

                     f"avtomatik ishga tushiriladi!"),

            "parse_mode": "html", "reply_markup": panel

        })

        delete_file(f"step/{cid}.step"); delete_file(f"step/{cid}.adbot_nom")

        return

# ================================================================

# LONG POLLING

# ================================================================

def main():

    print("=" * 50)

    print("Bot ishga tushdi!")

    print(f"Ma'lumotlar: {DB_FILE}")

    print("Avvalgi botlarni qayta ishga tushirish...")

    restart_all_saved_bots()

    print("=" * 50)

    offset = 0

    last_watchdog = time.time()

    while True:

        try:

            resp    = requests.get(f"{BASE_URL}/getUpdates",

                        params={"offset": offset, "timeout": 30,

                                "allowed_updates": json.dumps(["message","callback_query","pre_checkout_query","chat_member"])},

                        timeout=40)

            updates = resp.json().get("result", [])

            for upd in updates:

                offset = upd["update_id"] + 1

                try:

                    handle_update(upd)

                except Exception as e:

                    print(f"Handle xato: {e}")

            now_t = time.time()

            if now_t - last_watchdog >= 60:

                watchdog_restart_bots()

                last_watchdog = now_t

        except Exception as e:

            print(f"Polling xato: {e}")

            time.sleep(3)

if __name__ == "__main__":

    main()
