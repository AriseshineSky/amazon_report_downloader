import re

import psutil

def close_web_driver(driver):
    try:
        driver_process = psutil.Process(driver.service.process.pid)
        if not driver_process.is_running():
            return

        running = any([child.is_running() for child in driver_process.children()])
        if running:
            driver.quit()
        else:
            for child in driver_process.children():
                child.kill()
            driver_process.kill()
    except:
        pass

def extract_balance_amount(marketplace, balance_str):
    if marketplace.lower() == 'de':
        tmp_str = re.sub(r'[^0-9.,]', '', balance_str)
        tmp_list = re.split(r'[,.]', tmp_str)
        return round(float(''.join(tmp_list[:-1]) + '.' + tmp_list[-1]), 2)

    return round(float(re.sub(r'[^0-9\.]', '', balance_str)), 2)
