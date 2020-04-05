FROM python:alpine3.7

COPY . /app

WORKDIR /app

RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt

ENV HOTJAR_USERNAME ""
ENV HOTJAR_PASSWORD ""
ENV HOTJAR_INTERVAL 30
ENV HOTJAR_FUNNELS ""

EXPOSE 5000

CMD python -u ./index.py