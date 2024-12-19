FROM python:3.10
WORKDIR /app
RUN pip install spade
COPY . /app
RUN chmod +x main.py
CMD ["python", "-u", "main.py"]