import time
import datetime

def main():
    print("scheduler: start (all importerid ajastavad end ise)")
    while True:
        now = datetime.datetime.utcnow().replace(microsecond=0)
        print(f"scheduler heartbeat {now} UTC")
        time.sleep(3600)   # 1 kord tunnis logi

if __name__ == "__main__":
    main()
