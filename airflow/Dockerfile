FROM apache-airflow:2.9.3

WORKDIR /airflow

COPY airflow/requirements-airflow.txt /tmp/requirements-airflow.txt
RUN pip install --upgrade pip \
    && pip install -r /tmp/requirements-airflow.txt \
    && rm -f /tmp/requirements-airflow.txt

COPY pipeline /airflow/pipeline
COPY airflow/dags /airflow/dags

ENV PYTHONPATH=/airflow
ENV AIRFLOW_HOME=/airflow
