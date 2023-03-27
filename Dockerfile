FROM python
LABEL maintainer="NymV"
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python3","newbot.py"]