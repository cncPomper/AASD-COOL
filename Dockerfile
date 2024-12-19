FROM python:3.10
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
COPY src /app/src
COPY main.py /app/main.py
RUN chmod +x main.py
CMD ["python", "-u", "main.py"]