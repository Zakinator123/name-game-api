FROM tiangolo/uwsgi-nginx-flask:python3.6

RUN apt-get update && \
            apt-get install -y --no-install-recommends git \
            python-pip \
            python-dev \
	        unattended-upgrades && \
            rm -r /var/lib/apt/lists/*

RUN pip install --upgrade pip \
	&& pip install "mysqlclient==1.3.8"	\
	&& pip install -U "flask-cors" \
 	&& pip install -U "pytest" \
 	&& pip install bcrypt \
	&& pip install -U "flask-bcrypt"


COPY ./app /app