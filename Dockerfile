FROM python:3.8-slim
WORKDIR /app
COPY . /app
RUN pip3 install -r requirements.txt
EXPOSE 57000
ENTRYPOINT ["python3", "tordl.py"]
