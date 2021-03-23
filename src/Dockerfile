FROM python:3.6

WORKDIR /tvapi

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip
RUN pip install pipenv gunicorn

COPY Pipfile* ./

RUN pipenv install --system --deploy --ignore-pipfile

COPY . .

CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "1", "--preload", "wsgi:app"]
