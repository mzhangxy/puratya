import os
import time
import requests

# 从环境变量获取 Secrets
TOKEN = os.getenv('MRTCLOUD_TOKEN')
TG_BOT_TOKEN = os.getenv('TG_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')
BOT_ID = '9644'

HEADERS = {
    'accept': '*/*',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36'
}
COOKIES = {
    '__Host-mrtcloud_token': TOKEN
}
BASE_URL = f'https://cloud.puratya.com/api/bots/{BOT_ID}'

def send_tg_msg(text):
    """发送 Telegram 消息"""
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=payload)

def get_bot_info():
    """封装：获取服务器当前状态信息"""
    res = requests.get(f"{BASE_URL}/open", headers=HEADERS, cookies=COOKIES)
    res.raise_for_status()
    data = res.json()
    
    bot_info = data.get('bot', {})
    timer_info = bot_info.get('timer', {})
    
    return {
        'name': bot_info.get('name'),
        'status': bot_info.get('status'),
        'last_renewed': timer_info.get('last_renewed_at'),
        'stop_at': timer_info.get('stop_at'),
        'remaining_sec': timer_info.get('remaining_seconds')
    }

def main():
    try:
        # 1. 第一次查询：获取初始状态
        print(f"Fetching initial status for bot {BOT_ID}...")
        info_before = get_bot_info()
        status_before = info_before['status']
        bot_name = info_before['name']
        
        action_msg = ""
        
        # 2. 判断并执行对应动作
        if status_before == "running":
            print("Status is running. Renewing...")
            requests.post(f"{BASE_URL}/renew", headers=HEADERS, cookies=COOKIES)
            action_msg = "状态为 running，仅执行了续期 (Renew)"
            
        elif status_before == "stop":
            rem_sec = info_before['remaining_sec']
            if rem_sec is None or rem_sec <= 0:
                print("Status is stop and expired. Renewing then starting...")
                requests.post(f"{BASE_URL}/renew", headers=HEADERS, cookies=COOKIES)
                time.sleep(2) # 确保续期成功落盘
                requests.post(f"{BASE_URL}/start", headers=HEADERS, cookies=COOKIES)
                action_msg = "状态为 stop 且已过期，已执行续期并启动 (Renew & Start)"
            else:
                print("Status is stop but not expired. Starting...")
                requests.post(f"{BASE_URL}/start", headers=HEADERS, cookies=COOKIES)
                action_msg = "状态为 stop (未过期)，仅执行了启动 (Start)"
        else:
            action_msg = f"遇到未知状态 ({status_before})，未执行任何操作"

        # 3. 动作完成后，等待 2 秒以确保服务端更新数据，然后二次查询
        print("Waiting for server state to refresh...")
        time.sleep(2)
        
        print("Fetching updated status...")
        info_after = get_bot_info()
        status_after = info_after['status']
        next_stop_at = info_after['stop_at'] # 获取最新的下次到期时间
        
        # 4. 组装并发送 Telegram 报告
        msg = f"""🤖 *Bot 状态与操作报告*
- *实例名称*: {bot_name} (ID: {BOT_ID})
- *状态变更*: `{status_before}` ➔ `{status_after}`
- *执行动作*: {action_msg}
- *下次到期时间*: `{next_stop_at}`"""

        send_tg_msg(msg)
        print("Done.")

    except Exception as e:
        error_msg = f"❌ *Bot 维护脚本运行出错*\n错误信息: `{str(e)}`"
        print(error_msg)
        send_tg_msg(error_msg)

if __name__ == "__main__":
    main()
