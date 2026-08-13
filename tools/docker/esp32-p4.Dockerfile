FROM espressif/idf:v5.5.1

RUN /opt/esp/python_env/idf5.5_py3.12_env/bin/python -m pip install --no-cache-dir toml==0.10.2
