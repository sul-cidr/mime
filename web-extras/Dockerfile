FROM python:3.10-bullseye as web-extras
#FROM python:3.10-bullseye as base

# WORKDIR /app

# RUN pip install --no-cache-dir cython==0.29.36 numpy==1.23.5
# RUN git clone --branch pose-plot https://github.com/broadwell/pix-plot.git /app/pix-plot

# WORKDIR /app/pix-plot
# RUN git pull origin pose-plot && python setup.py install

# FROM base as web-extras

# COPY . .

EXPOSE 7000

WORKDIR /app

RUN mkdir input output poseplot

CMD python -m http.server 7000
