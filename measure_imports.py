import time

def measure_import(name):
    t0 = time.time()
    try:
        __import__(name)
    except:
        pass
    t1 = time.time()
    print(f"{name}: {t1 - t0:.4f}s")

measure_import("streamlit")
measure_import("extra_streamlit_components")
measure_import("sqlalchemy")
measure_import("pandas")
measure_import("pytz")
measure_import("json")
measure_import("base64")
measure_import("subprocess")
measure_import("playwright")
measure_import("fake_useragent")
measure_import("dotenv")
