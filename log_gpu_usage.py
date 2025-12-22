import time
import sys
from pynvml import *

def log_gpu_usage(logfile='gpu_usage.log', interval=1):
    try:
        nvmlInit()
    except NVMLError as e:
        print("NVIDIA driver/library not found or NVML init failed:", e)
        sys.exit(1)

    try:
        device_count = nvmlDeviceGetCount()
        if device_count == 0:
            print("No NVIDIA GPUs found.")
            nvmlShutdown()
            sys.exit(0)

        with open(logfile, 'a') as f:
            # Added temperature column
            f.write("timestamp,gpu_index,utilization_gpu[%],memory_used[MB],memory_total[MB],temperature[C]\n")
            while True:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                for i in range(device_count):
                    handle = nvmlDeviceGetHandleByIndex(i)
                    util = nvmlDeviceGetUtilizationRates(handle)
                    mem_info = nvmlDeviceGetMemoryInfo(handle)
                    temp = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)

                    log_line = f"{timestamp},{i},{util.gpu},{mem_info.used // 1024 ** 2},{mem_info.total // 1024 ** 2},{temp}\n"
                    f.write(log_line)
                f.flush()
                time.sleep(interval)

    except KeyboardInterrupt:
        print("Logging stopped by user.")
    except NVMLError as e:
        print("NVML error occurred:", e)
    finally:
        nvmlShutdown()

if __name__ == "__main__":
    log_gpu_usage()
