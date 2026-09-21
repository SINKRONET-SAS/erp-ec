ARG ERPEC_PROFILE=customer
FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS core
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 LANG=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends build-essential git ca-certificates libldap2-dev libsasl2-dev libpq-dev libxml2-dev libxslt1-dev zlib1g-dev libjpeg62-turbo-dev libffi-dev libssl-dev fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY upstream.json /opt/erpec/upstream.json
RUN git init /opt/odoo && cd /opt/odoo && git remote add origin https://github.com/odoo/odoo.git && git fetch --depth 1 origin b1fd3a9eee5d575848ac649d2f5103537d8de7a4 && git checkout --detach FETCH_HEAD && test "$(git rev-parse HEAD)" = b1fd3a9eee5d575848ac649d2f5103537d8de7a4 && rm -rf .git
COPY deployment/linux/requirements-linux.lock /opt/erpec/requirements-linux.lock
COPY deployment/linux/prepare_requirements.py /opt/erpec/prepare_requirements.py
RUN python /opt/erpec/prepare_requirements.py /opt/odoo/requirements.txt /opt/erpec/requirements-linux.lock > /opt/erpec/requirements-combined.txt && pip install --no-cache-dir -r /opt/erpec/requirements-combined.txt -c /opt/erpec/requirements-linux.lock && pip freeze > /opt/erpec/python-installed.txt
RUN useradd --uid 10001 --create-home odoo && mkdir -p /var/data/odoo /opt/erpec/addons && chown -R odoo:odoo /var/data
COPY deployment/linux/runtime.py /opt/erpec/runtime.py
COPY addons /opt/erpec/addons
EXPOSE 10000
USER odoo
ENTRYPOINT ["python", "/opt/erpec/runtime.py"]

FROM core AS controller
USER root
RUN printf 'controller' > /opt/erpec/profile
USER odoo

FROM core AS customer
USER root
RUN printf 'customer' > /opt/erpec/profile
USER odoo

FROM ${ERPEC_PROFILE} AS runtime
