# PA2577-assignment-3
We have added a new service, a Streamlit Python application, under `Containers/MonitorTool/`. The service has also been included in the [all-at-once.yaml](all-at-once.yaml) file with the following configuration:
```yaml
  monitor-tool:
    build:
      context: ./Containers/MonitorTool
    environment:
      DBHOST: dbstorage
    ports:
      - 8501:8501
```
You can build and run this updated setup using the following command (use `sudo` if necessary):
```bash
docker compose -f all-at-once.yaml up --build
```
Or if you want to build the `monitor-tool` and `clone-detector` services but keep the dependencies alive just run the following (use `sudo` if necessary):
```bash
sudo docker compose -f all-at-once.yaml up --build monitor-tool clone-detector
```
