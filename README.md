# PA2577-assignment-2
We have added a new service, a Streamlit Python application, under `Containers/StatisticsInterface/`. The service has also been included in the [stream-of-code.yaml](stream-of-code.yaml) file with the following configuration:
```yaml
statistics-interface:
  build:
    context: ./Containers/StatisticsInterface
  environment:
    TARGET: "cs-consumer:3000"
  ports:
    - 8501:8501
```
You can build and run this updated setup using the following command (use `sudo` if necessary):
```bash
docker compose -f stream-of-code.yaml up --build
```
